"""Tests fuer nachbarn.py (Schritt 4: semantische Nachbarn ueber qmd). Wegwerf-Vault in tempfile,
qmd wird nie aufgerufen.

    python3 -I -m unittest discover -s ~/.claude/skills/verknuepfen/scripts
"""
import atexit
import contextlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock

# Vorspann VOR dem Import: HOME und Einstellungsdatei zeigen in einen Wegwerf-Ordner, damit weder
# ein Test noch eine Mutation die echte Konfiguration oder den echten Vault liest oder beschreibt.
# Subprozesse erben os.environ und damit diese Werte.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="nachbarn-test-home-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nachbarn as nb  # noqa: E402
import verknuepfen as vk  # noqa: E402

AUS = "03 Bereiche/Notizen/Ausgang.md"
FM = "---\ntags: [test]\n---\n"


def setUpModule():
    os.environ["VERKNUEPFEN_TEST"] = "1"


def einst(**graph):
    e = {"graph": {"ausschluss": ["03 Bereiche/Finanzen/**", "02 Projekte/Dienst/**", "memory/**"],
                   "schwelle": 0.5, "max_nachbarn": 5, "qmd_index": "vault", "qmd_frist": 30},
         "warnungen": []}
    e["graph"].update(graph)
    return e


GUTE_YAML = 'collections:\n  vault:\n    path: "/x/vault"\n    pattern: "**/*.md"\n'


class Basis(unittest.TestCase):
    def setUp(self):
        # qmd-Konfiguration nur im Wegwerf-Ordner; nie ~/.config/qmd oder ~/.cache/qmd
        self.cfg = self.tmp()
        for name in ("vault", "meins"):
            with open(os.path.join(self.cfg, name + ".yml"), "w", encoding="utf-8") as fh:
                fh.write(GUTE_YAML)
        # HOME und XDG_* ebenfalls umbiegen: selbst ein Fehler in den Pfadregeln trifft nie das echte ~/.config
        fremd = self.tmp()
        p = mock.patch.dict(os.environ, {"QMD_CONFIG_DIR": self.cfg, "HOME": fremd,
                                         "XDG_CONFIG_HOME": fremd, "XDG_CACHE_HOME": fremd,
                                         "INDEX_PATH": os.path.join(self.cfg, "kein.sqlite")})
        p.start()
        self.addCleanup(p.stop)
        # zentrale Sperre: weder echtes qmd noch echtes node noch echtes qmd-Paket; Tests, die ein
        # Programm brauchen, setzen ein Fake selbst
        weg = os.path.join(self.cfg, "nicht-vorhanden")
        p2 = mock.patch.dict(os.environ, {"VERKNUEPFEN_QMD_PAKET": os.path.join(weg, "paket")})
        p2.start()
        self.addCleanup(p2.stop)
        for name in ("NODE", "QMD"):
            pp = mock.patch.object(nb, name, os.path.join(weg, name.lower()))
            pp.start()
            self.addCleanup(pp.stop)

    def tmp(self):
        d = tempfile.mkdtemp(prefix="nachbarn-test-")
        self.addCleanup(shutil.rmtree, d)
        return d

    def bau(self, files):
        d = self.tmp()
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(content)
        return d

    def treffer(self, root, rel, score, **extra):
        return {"score": score, "file": os.path.join(os.path.realpath(root), rel), "line": 1,
                "title": "Titel", "snippet": "…", **extra}

    def runner(self, treffer):
        calls = []

        def run(index, abfrage, frist, n=20):
            calls.append((index, abfrage, frist, n))
            return json.dumps(treffer)
        run.calls = calls
        return run


class Einstellungen(Basis):
    def test_vorgaben_ohne_datei(self):
        e = nb.einstellungen_laden("/nicht/da")
        self.assertEqual(e["graph"]["max_nachbarn"], 5)
        self.assertIsNone(e["graph"]["schwelle"])
        self.assertEqual(e["graph"]["ausschluss"], ["03 Bereiche/Finanzen/**", "memory/**"])
        self.assertEqual(e["graph"]["qmd_index"], "vault")
        self.assertEqual(e["graph"]["qmd_frist"], 30)
        self.assertEqual(e["warnungen"], [])

    def test_datei_ueberschreibt(self):
        d = self.bau({"e.json": json.dumps({"graph": {"schwelle": 0.62, "max_nachbarn": 3}})})
        e = nb.einstellungen_laden(os.path.join(d, "e.json"))
        self.assertEqual(e["graph"]["schwelle"], 0.62)
        self.assertEqual(e["graph"]["max_nachbarn"], 3)
        self.assertEqual(e["graph"]["qmd_index"], "vault")  # tief zusammengefuehrt
        self.assertEqual(len(e["graph"]["ausschluss"]), 2)

    def test_kaputtes_json_gibt_vorgaben_und_warnung(self):
        d = self.bau({"e.json": "{kaputt"})
        e = nb.einstellungen_laden(os.path.join(d, "e.json"))
        self.assertEqual(e["graph"]["max_nachbarn"], 5)
        self.assertIsNone(e["graph"]["schwelle"])
        self.assertEqual(len(e["warnungen"]), 1)

    def test_ausschluss_als_text_gilt_vorgabe_mit_warnung(self):
        for falsch in ["memory/**", ["ok", 5], None, {"a": 1}]:
            d = self.bau({"e.json": json.dumps({"graph": {"ausschluss": falsch}})})
            e = nb.einstellungen_laden(os.path.join(d, "e.json"))
            self.assertEqual(e["graph"]["ausschluss"], nb.VORGABEN["graph"]["ausschluss"], falsch)
            self.assertEqual(len(e["warnungen"]), 1, falsch)
        # Vorgabe wird nicht durch Aenderung am Ergebnis veraendert
        e["graph"]["ausschluss"].append("x")
        self.assertEqual(nb.VORGABEN["graph"]["ausschluss"], ["03 Bereiche/Finanzen/**", "memory/**"])

    def test_leere_liste_ist_gueltig(self):
        d = self.bau({"e.json": json.dumps({"graph": {"ausschluss": []}})})
        e = nb.einstellungen_laden(os.path.join(d, "e.json"))
        self.assertEqual((e["graph"]["ausschluss"], e["warnungen"]), ([], []))

    def test_typfehler_je_schluessel_gilt_vorgabe_mit_warnung(self):
        faelle = [("schwelle", "0.37"), ("schwelle", True), ("schwelle", [0.4]),
                  ("max_nachbarn", "5"), ("max_nachbarn", -1), ("max_nachbarn", 2.5), ("max_nachbarn", True),
                  ("qmd_frist", "30"), ("qmd_frist", 0), ("qmd_frist", -3), ("qmd_frist", False),
                  ("qmd_index", 7), ("qmd_index", ""), ("qmd_index", "a/b"), ("qmd_index", None)]
        for schluessel, falsch in faelle:
            with self.subTest(schluessel=schluessel, wert=falsch):
                d = self.bau({"e.json": json.dumps({"graph": {schluessel: falsch, "ausschluss": ["Kappa/**"]}})})
                e = nb.einstellungen_laden(os.path.join(d, "e.json"))
                self.assertEqual(e["graph"][schluessel], nb.VORGABEN["graph"][schluessel])
                self.assertEqual(len(e["warnungen"]), 1)
                self.assertIn("graph." + schluessel, e["warnungen"][0])
                self.assertEqual(e["graph"]["ausschluss"], ["Kappa/**"])  # gueltige Schluessel bleiben

    def test_graph_kein_objekt_gibt_vorgaben_mit_warnung(self):
        for falsch in (5, "x", [1], None):
            with self.subTest(wert=falsch):
                d = self.bau({"e.json": json.dumps({"graph": falsch})})
                try:
                    e = nb.einstellungen_laden(os.path.join(d, "e.json"))
                except Exception as ex:  # vorher: AttributeError, Traceback beim Nutzer
                    self.fail("Ausnahme statt Vorgabe: %r" % ex)
                self.assertEqual(e["graph"], nb.VORGABEN["graph"])
                self.assertEqual(len(e["warnungen"]), 1)
                self.assertIn("graph", e["warnungen"][0])

    def test_gueltige_typen_ohne_warnung(self):
        for schluessel, gut in [("schwelle", 0.37), ("schwelle", 1), ("schwelle", None), ("max_nachbarn", 0),
                                ("qmd_frist", 0.5), ("qmd_frist", 10), ("qmd_index", "kappa")]:
            with self.subTest(schluessel=schluessel, wert=gut):
                d = self.bau({"e.json": json.dumps({"graph": {schluessel: gut}})})
                e = nb.einstellungen_laden(os.path.join(d, "e.json"))
                self.assertEqual((e["graph"][schluessel], e["warnungen"]), (gut, []))

    def test_umgebungsvariable_bestimmt_pfad(self):
        d = self.bau({"e.json": json.dumps({"graph": {"max_nachbarn": 2}})})
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": os.path.join(d, "e.json")}):
            self.assertEqual(nb.einstellungen_laden()["graph"]["max_nachbarn"], 2)


class Ausschluss(Basis):
    def test_ausschluss_muster(self):
        m = nb.einstellungen_laden("/nicht/da")["graph"]["ausschluss"]
        for rel in ["03 Bereiche/Finanzen/Kappa-Konto.md", "memory/x.md", "07 Anhaenge/a.md",
                    ".obsidian/a.md", ".trash/a.md"]:
            self.assertTrue(nb.ist_ausgeschlossen(rel, m), rel)
        for rel in ["03 Bereiche/Finanzen-Ideen.md", "02 Projekte/Kappa/Kappa - PMO HUB.md",
                    "02 Projekte/Dienst/x/y.md"]:   # Dienstordner nur, wenn die Einstellung ihn nennt
            self.assertFalse(nb.ist_ausgeschlossen(rel, m), rel)
        self.assertTrue(nb.ist_ausgeschlossen("02 Projekte/Dienst/x/y.md", einst()["graph"]["ausschluss"]))

    def test_feste_muster_nicht_abschaltbar(self):
        self.assertTrue(nb.ist_ausgeschlossen(".obsidian/a.md", []))
        self.assertTrue(nb.ist_ausgeschlossen("07 Anhaenge/a.md", []))

    def test_nfd_muster_und_pfad(self):
        nfd = unicodedata.normalize("NFD", "03 Bereiche/Ärger/x.md")
        self.assertTrue(nb.ist_ausgeschlossen(nfd, ["03 Bereiche/Ärger/**"]))


class Abfrage(Basis):
    def test_abfrage_text(self):
        text = (FM + "Kappa ist ein Werkzeug.\n\n```\nGEHEIMER_CODE\n```\n\nRho GmbH   liefert\n\n\n"
                + "wort " * 1000)
        a = nb.abfrage_text(text)
        self.assertNotIn("tags:", a)
        self.assertNotIn("GEHEIMER_CODE", a)
        self.assertNotIn("\n", a)
        self.assertNotIn("  ", a)
        self.assertIn("Kappa ist ein Werkzeug.", a)
        self.assertLessEqual(len(a), 2000)
        self.assertEqual(nb.ABFRAGE_ZEICHEN, 2000)


FAKE_PAKET_JS = """
export async function createStore({ dbPath }) {
  return {
    listCollections: async () => [{ name: "vault", pwd: "/x/vault" }],
    searchVector: async (q, { limit }) => [
      { score: 0.73, displayPath: "vault/a/B.md", title: q.trim() + "|" + limit },
      { score: 0.5, displayPath: "fremd/C.md", title: "weg" },
    ],
    close: async () => {},
  };
}
"""


def fake_programm(d, zeilen):
    p = os.path.join(d, "fake-node")
    with open(p, "w") as fh:
        fh.write("#!/bin/sh\n" + zeilen + "\n")
    os.chmod(p, 0o755)
    return p


class Runner(Basis):
    def test_aufruf_node_mit_stdin_cwd_und_gruppe(self):
        class P:
            returncode = 0
            pid = 1

            def communicate(self, inp=None, timeout=None):
                P.inp, P.timeout = inp, timeout
                return "[]", ""
        with mock.patch.dict(os.environ, {"INDEX_PATH": "/kappa/ordner mit Leerzeichen/idx.sqlite"}), \
                mock.patch.object(subprocess, "Popen", return_value=P()) as popen:
            self.assertEqual(nb.qmd_runner("idx", "--Kappa Text", 7.5, 12), "[]")
        args, kw = popen.call_args
        self.assertEqual(args[0], [nb.NODE, nb.VEKTOR_SKRIPT, "/kappa/ordner mit Leerzeichen/idx.sqlite", "12"])
        self.assertTrue(nb.VEKTOR_SKRIPT.endswith("qmd_vektor.mjs"))
        self.assertEqual(kw["cwd"], "/")
        self.assertTrue(kw["start_new_session"])
        self.assertFalse(kw.get("shell", False))
        self.assertEqual((P.inp, P.timeout), ("--Kappa Text", 7.5))

    def test_node_fehlt(self):
        with mock.patch.object(nb, "NODE", "/nicht/da/node"):
            with self.assertRaises(nb.NachbarnFehler) as c:
                nb.qmd_runner("i", "a", 1)
        self.assertIn("node nicht gefunden", str(c.exception))

    def test_exitcode_mit_letzter_stderr_zeile_gekuerzt(self):
        d = self.tmp()
        prog = fake_programm(d, "echo erste >&2; python3 -c \"import sys; sys.stderr.write('x' * 500 + '\\n')\"; exit 3")
        with mock.patch.object(nb, "NODE", prog):
            with self.assertRaises(nb.NachbarnFehler) as c:
                nb.qmd_runner("i", "a", 5)
        g = str(c.exception)
        self.assertTrue(g.startswith("qmd Exitcode 3: xxx"), g)
        self.assertNotIn("erste", g)
        self.assertEqual(len(g), len("qmd Exitcode 3: ") + nb.STDERR_ZEICHEN)

    def test_ungueltige_bytes_auf_stderr_und_stdout_sind_kein_absturz(self):
        d = self.tmp()
        prog = fake_programm(d, "printf 'Hinweis \\377\\n' >&2; printf '[]'; exit 0")
        with mock.patch.object(nb, "NODE", prog):
            self.assertEqual(nb.qmd_runner("i", "a", 5), "[]")
        prog = fake_programm(d, "printf '[\\377]'; exit 0")
        with mock.patch.object(nb, "NODE", prog):
            out = nb.qmd_runner("i", "a", 5)
        with self.assertRaises(nb.NachbarnFehler):
            nb.vsearch_lesen(out, "/")  # Unsinn wird Grund, keine Ausnahme
        prog = fake_programm(d, "printf 'Fehler \\377\\n' >&2; exit 2")
        with mock.patch.object(nb, "NODE", prog):
            with self.assertRaises(nb.NachbarnFehler) as c:
                nb.qmd_runner("i", "a", 5)
        self.assertTrue(str(c.exception).startswith("qmd Exitcode 2: Fehler "), str(c.exception))

    def test_nachbarn_mit_ungueltigem_byte_gibt_liste(self):
        d, v = Nachbarn.vault(self)
        prog = fake_programm(d, "printf 'Hinweis \\377\\n' >&2; printf '[]'; exit 0")
        with mock.patch.object(nb, "NODE", prog):
            self.assertEqual(nb.nachbarn(v, AUS, einst()), ([], None))

    def test_absturz_grund_ueberspringt_node_versionszeile(self):
        d = self.tmp()
        prog = fake_programm(d, "printf 'Error: kaputt\\n    at x\\n\\nNode.js v26.13.0\\n' >&2; exit 1")
        with mock.patch.object(nb, "NODE", prog):
            with self.assertRaises(nb.NachbarnFehler) as c:
                nb.qmd_runner("i", "a", 5)
        # festgelegt: letzte nicht leere Zeile, die keine Node-Versionszeile ist
        self.assertEqual(str(c.exception), "qmd Exitcode 1: at x")
        prog = fake_programm(d, "printf 'Node.js v26.13.0\\n' >&2; exit 1")
        with mock.patch.object(nb, "NODE", prog):
            with self.assertRaises(nb.NachbarnFehler) as c:
                nb.qmd_runner("i", "a", 5)
        self.assertEqual(str(c.exception), "qmd Exitcode 1")

    def test_frist_beendet_auch_kinder(self):
        d = self.tmp()
        pidf = os.path.join(d, "kind.pid")
        # Die PID-Datei entsteht per mv in einem Stück: nie halb geschrieben, wenn die Frist dazwischenfährt.
        prog = fake_programm(d, "sleep 20 &\necho $! > '%s.neu'\nmv '%s.neu' '%s'\nsleep 20" % (pidf, pidf, pidf))
        import time
        # Unter Last startet das Programm manchmal später, als die Frist dauert. Dann fehlt die PID-Datei, und der
        # Lauf sagt nichts über das Kind. Deshalb die Frist verdoppeln, bis das Programm sein Kind gemeldet hat.
        for frist in (0.5, 1, 2, 4, 8):
            t0 = time.time()
            with mock.patch.object(nb, "NODE", prog):
                with self.assertRaises(nb.NachbarnFehler) as c:
                    nb.qmd_runner("i", "a", frist)
            # ohne Gruppenkill wartet communicate auf das Kind (20 s)
            self.assertLess(time.time() - t0, frist + 4.5)
            self.assertIn("Frist", str(c.exception))
            if os.path.exists(pidf):
                break
        else:
            self.fail("Programm kam auch mit 8 s Frist nicht bis zur PID-Datei")
        with open(pidf) as fh:
            pid = int(fh.read())
        for _ in range(100):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.kill(pid, 9)
            self.fail("Kindprozess lebt nach Fristablauf noch")


@unittest.skipUnless(shutil.which("node"), "node fehlt")
class VektorSkript(Basis):
    def lauf(self, home, paket, abfrage="Kappa Wert", db=None, n="7"):
        env = {"PATH": os.environ["PATH"], "HOME": home}
        if paket:
            env["VERKNUEPFEN_QMD_PAKET"] = paket
        if db is None:
            db = os.path.join(home, "db mit Leerzeichen", "idx.sqlite")
        return subprocess.run(["node", nb.VEKTOR_SKRIPT, db, n], input=abfrage, capture_output=True,
                              text=True, encoding="utf-8", env=env, cwd="/", timeout=60)

    def umgebung(self, db=True):
        home = self.tmp()
        paket = self.bau({"dist/index.js": FAKE_PAKET_JS, "package.json": '{"type": "module"}'})
        if db:
            os.makedirs(os.path.join(home, "db mit Leerzeichen"))
            open(os.path.join(home, "db mit Leerzeichen", "idx.sqlite"), "w").close()
        return home, paket

    def test_json_form_mit_fake_paket(self):
        home, paket = self.umgebung()
        r = self.lauf(home, paket, "-Ärger Kappa")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout),
                         [{"score": 0.73, "file": "/x/vault/a/B.md", "title": "-Ärger Kappa|7"}])

    def test_fehlende_datenbank_exit_3(self):
        home, paket = self.umgebung(db=False)
        r = self.lauf(home, paket)
        self.assertEqual(r.returncode, 3)
        self.assertIn("nicht gefunden", r.stderr)

    def test_fehlendes_paket_exit_1(self):
        home, paket = self.umgebung()
        r = self.lauf(home, os.path.join(home, "kein-paket"))
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr.strip())

    def test_runner_end_zu_ende(self):
        home, paket = self.umgebung()
        db = os.path.join(home, "db mit Leerzeichen", "idx.sqlite")
        with mock.patch.dict(os.environ, {"INDEX_PATH": db, "VERKNUEPFEN_QMD_PAKET": paket}), \
                mock.patch.object(nb, "NODE", shutil.which("node")):
            out = nb.qmd_runner("idx", "Kappa", 60, 3)
        self.assertEqual(json.loads(out)[0]["title"], "Kappa|3")


class Pfade(Basis):
    def test_db_index_path_gewinnt(self):
        env = {"INDEX_PATH": "/k/x.sqlite", "XDG_CACHE_HOME": "/xdg", "HOME": "/h"}
        self.assertEqual(nb.qmd_db_pfad("idx", env), "/k/x.sqlite")

    def test_db_xdg_cache_home(self):
        self.assertEqual(nb.qmd_db_pfad("idx", {"XDG_CACHE_HOME": "/xdg", "HOME": "/h"}), "/xdg/qmd/idx.sqlite")

    def test_db_home_vorgabe(self):
        self.assertEqual(nb.qmd_db_pfad("idx", {"HOME": "/h"}), "/h/.cache/qmd/idx.sqlite")

    def test_db_leere_variable_gilt_als_nicht_gesetzt(self):
        self.assertEqual(nb.qmd_db_pfad("idx", {"INDEX_PATH": "", "XDG_CACHE_HOME": "", "HOME": "/h"}),
                         "/h/.cache/qmd/idx.sqlite")

    def test_yaml_config_dir_gewinnt(self):
        env = {"QMD_CONFIG_DIR": "/c", "XDG_CONFIG_HOME": "/xdg", "HOME": "/h"}
        self.assertEqual(nb.qmd_yaml_pfad("idx", env), "/c/idx.yml")

    def test_yaml_xdg_config_home(self):
        self.assertEqual(nb.qmd_yaml_pfad("idx", {"XDG_CONFIG_HOME": "/xdg", "HOME": "/h"}), "/xdg/qmd/idx.yml")

    def test_yaml_home_vorgabe(self):
        self.assertEqual(nb.qmd_yaml_pfad("idx", {"HOME": "/h"}), "/h/.config/qmd/idx.yml")

    def test_ohne_env_gilt_os_environ(self):
        with mock.patch.dict(os.environ, {"QMD_CONFIG_DIR": "/c2", "INDEX_PATH": "/d2.sqlite"}):
            self.assertEqual(nb.qmd_yaml_pfad("i"), "/c2/i.yml")
            self.assertEqual(nb.qmd_db_pfad("i"), "/d2.sqlite")


class Yaml(Basis):
    def test_yaml_enthaelt_ausschluss_und_kein_models(self):
        d = self.tmp()
        t = nb.qmd_yaml(d, einst())
        for m in ["03 Bereiche/Finanzen/**", "02 Projekte/Dienst/**", "memory/**",
                  ".obsidian/**", ".trash/**", "07 Anhaenge/**"]:
            self.assertIn('      - "%s"\n' % m, t)
        self.assertNotIn("models", t)
        self.assertNotIn("global_context", t)
        self.assertTrue(t.startswith("collections:\n  vault:\n"))
        self.assertIn('    path: "%s"\n' % os.path.realpath(d), t)
        self.assertIn('    pattern: "**/*.md"\n', t)
        self.assertIn("    includeByDefault: true\n", t)
        self.assertEqual(nb.pruefe_yaml(t), [])

    def test_yaml_ausschluss_aus_einstellung_und_feste_nur_einmal(self):
        t = nb.qmd_yaml(self.tmp(), einst(ausschluss=["Kappa/**", ".obsidian/**"]))
        self.assertIn('      - "Kappa/**"\n', t)
        self.assertNotIn("memory/**", t)
        self.assertEqual(t.count('"%s"' % ".obsidian/**"), 1)
        self.assertIn('      - "07 Anhaenge/**"\n', t)

    def test_yaml_nicht_ascii_muster_in_nfc_und_nfd(self):
        nfc = unicodedata.normalize("NFC", "02 Projekte/Bücher/**")
        nfd = unicodedata.normalize("NFD", nfc)
        for eingabe in (nfc, nfd):
            with self.subTest(form="NFC" if eingabe == nfc else "NFD"):
                t = nb.qmd_yaml(self.tmp(), einst(ausschluss=[eingabe, "memory/**"]))
                self.assertEqual(t.count('      - "%s"\n' % nfc), 1)
                self.assertEqual(t.count('      - "%s"\n' % nfd), 1)
                self.assertEqual(t.count('      - "memory/**"\n'), 1)
                self.assertEqual(t.count("      - "), 2 + 1 + 3)

    def test_yaml_leere_liste_hat_nur_feste_muster(self):
        t = nb.qmd_yaml(self.tmp(), einst(ausschluss=[]))
        self.assertEqual(t.count("      - "), 3)


class PruefeYaml(Basis):
    def test_pruefe_yaml_findet_remote(self):
        t = GUTE_YAML + 'models:\n  embed: "https://api.openai.com/v1#text-embedding-3-small"\n'
        self.assertEqual(len(nb.pruefe_yaml(t)), 2)

    def test_hf_standardmodelle_sind_kein_befund(self):
        t = (GUTE_YAML + "models:\n  embed: hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf\n"
             "  rerank: hf:ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/qwen3-reranker-0.6b-q8_0.gguf\n"
             "  generate: hf:tobil/qmd-query-expansion-1.7B-gguf/qmd-query-expansion-1.7B-q4_k_m.gguf\n")
        self.assertEqual(nb.pruefe_yaml(t), [])

    def test_zeile_models_allein_ist_kein_befund(self):
        self.assertEqual(nb.pruefe_yaml(GUTE_YAML + "models:\n"), [])

    def test_hf_in_anfuehrungszeichen_ist_kein_befund(self):
        self.assertEqual(nb.pruefe_yaml("models:\n  embed: \"hf:a/b.gguf\"\n  gen: 'hf:c/d.gguf'\n"), [])

    def test_nicht_hf_modell_ohne_adresse_ist_befund(self):
        b = nb.pruefe_yaml('models:\n  embed: "openai:text-embedding-3-small"\n')
        self.assertEqual(len(b), 1)
        self.assertIn("openai:text-embedding-3-small", b[0])

    def test_adresse_irgendwo_ist_befund(self):
        self.assertEqual(len(nb.pruefe_yaml(GUTE_YAML + "# siehe http://example.org\n")), 1)
        self.assertEqual(len(nb.pruefe_yaml('collections:\n  vault:\n    path: "HTTPS://x"\n')), 1)

    def test_wert_nach_dem_models_block_ist_kein_befund(self):
        t = "models:\n  embed: hf:a/b.gguf\nandere: etwas\n"
        self.assertEqual(nb.pruefe_yaml(t), [])
        self.assertEqual(nb.pruefe_yaml("embed: etwas\nmodels:\n"), [])

    def test_models_schluessel_in_anderen_schreibweisen(self):
        for zeile in ['models : {embed: openai}', '"models": {embed: openai}', "\ufeffmodels: {embed: x}",
                      '"models" :\n  embed: openai']:
            t = "collections:\n  vault:\n    path: /x\n" + zeile + "\n"
            self.assertTrue(nb.pruefe_yaml(t), repr(zeile))
        # nur der Schluessel in Anfuehrungszeichen, mit hf: wie bei qmd
        self.assertEqual(nb.pruefe_yaml('"models":\n  embed: hf:a/b.gguf\n'), [])
        self.assertEqual(nb.pruefe_yaml("\ufeffmodels:\n  embed: hf:a/b.gguf\n"), [])

    def test_models_block_nach_anfuehrungszeichen_wird_geprueft(self):
        self.assertEqual(len(nb.pruefe_yaml('"models" :\n  embed: openai\n')), 1)
        self.assertEqual(len(nb.pruefe_yaml("\ufeffmodels:\n  embed: openai\n")), 1)

    def test_flow_stil_und_komplexer_schluessel_sind_befund(self):
        for t in ["{collections: {}, models: {embed: x}}\n", "\ufeff{a: 1}\n", "? models\n: x\n"]:
            b = nb.pruefe_yaml(t)
            self.assertTrue(any("YAML-Form nicht erlaubt" in x for x in b), (t, b))
        self.assertEqual(nb.pruefe_yaml(GUTE_YAML), [])

    def test_models_mit_inline_wert_ist_befund(self):
        self.assertEqual(len(nb.pruefe_yaml("models: {embed: openai}\n")), 1)


class PruefeIndex(Basis):
    def db(self, zeilen, ordner=None):
        pfad = os.path.join(ordner or self.tmp(), "idx.sqlite")
        con = sqlite3.connect(pfad)
        con.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, collection TEXT, path TEXT, "
                    "title TEXT, hash TEXT, active INTEGER)")
        for path, active in zeilen:
            con.execute("INSERT INTO documents (collection, path, title, hash, active) VALUES "
                        "('vault', ?, 't', 'h', ?)", (path, active))
        con.commit()
        con.close()
        return pfad

    def test_pruefe_index(self):
        db = self.db([("03 Bereiche/Notizen/Kappa.md", 1), ("memory/Rho.md", 1)])
        self.assertEqual(nb.pruefe_index(db, "/v", einst()["graph"]["ausschluss"]), ["memory/Rho.md"])

    def test_fremde_collection_ist_befund(self):
        db = self.db([("Kappa.md", 1)])
        con = sqlite3.connect(db)
        con.execute("INSERT INTO documents (collection, path, title, hash, active) VALUES ('mem', 'Omega.md', 't', 'h', 1)")
        con.execute("INSERT INTO documents (collection, path, title, hash, active) VALUES ('alt', 'Kappa2.md', 't', 'h', 0)")
        con.commit()
        con.close()
        b = nb.pruefe_index(db, "/v", ["memory/**"])
        self.assertEqual(sorted(b), ["fremde Collection alt: Kappa2.md", "fremde Collection mem: Omega.md"])

    def test_pruefe_index_meldet_auch_inaktive(self):
        db = self.db([("memory/Omega.md", 0), ("03 Bereiche/Finanzen/Rho GmbH.md", 0)])
        self.assertEqual(sorted(nb.pruefe_index(db, "/v", einst()["graph"]["ausschluss"])),
                         ["03 Bereiche/Finanzen/Rho GmbH.md", "memory/Omega.md"])

    def test_pruefe_index_feste_muster_und_nfd(self):
        nfd = unicodedata.normalize("NFD", "memory/Ärger.md")
        db = self.db([(".obsidian/x.md", 1), ("07 Anhaenge/a.md", 1), (nfd, 1), ("Kappa.md", 1)])
        self.assertEqual(sorted(nb.pruefe_index(db, "/v", ["memory/**"])), sorted([".obsidian/x.md", "07 Anhaenge/a.md", nfd]))

    def test_pruefe_index_pfad_mit_leerzeichen_und_schreibschutz(self):
        d = os.path.join(self.tmp(), "Ordner mit Leerzeichen")
        os.makedirs(d)
        db = self.db([("memory/a.md", 1)], d)
        vorher = os.path.getmtime(db)
        self.assertEqual(nb.pruefe_index(db, "/v", ["memory/**"]), ["memory/a.md"])
        self.assertEqual(os.path.getmtime(db), vorher)
        self.assertEqual(os.listdir(d), ["idx.sqlite"])  # kein -journal, kein -wal

    def test_fehlende_datenbank_ist_befund_kein_traceback(self):
        db = os.path.join(self.tmp(), "gibt-es-nicht.sqlite")
        b = nb.pruefe_index(db, "/v", ["memory/**"])
        self.assertEqual(len(b), 1)
        self.assertIn("gibt-es-nicht.sqlite", b[0])
        self.assertIn("fehlt", b[0])
        self.assertFalse(os.path.exists(db))  # legt nichts an

    def test_datenbank_wird_nur_lesend_geoeffnet(self):
        d = os.path.join(self.tmp(), "Ordner mit Leerzeichen")
        os.makedirs(d)
        db = self.db([("memory/a.md", 1)], d)
        echt = sqlite3.connect
        with mock.patch.object(sqlite3, "connect", side_effect=echt) as c:
            nb.pruefe_index(db, "/v", ["memory/**"])
        args, kw = c.call_args
        self.assertTrue(args[0].startswith("file:///"), args[0])
        self.assertIn("Ordner%20mit%20Leerzeichen", args[0])
        self.assertTrue(args[0].endswith("/idx.sqlite?mode=ro"), args[0])
        self.assertTrue(kw.get("uri"))

    def test_datenbank_ohne_tabelle_ist_befund(self):
        pfad = os.path.join(self.tmp(), "leer.sqlite")
        sqlite3.connect(pfad).close()
        b = nb.pruefe_index(pfad, "/v", ["memory/**"])
        self.assertEqual(len(b), 1)
        self.assertIn("nicht lesbar", b[0])


class Lesen(Basis):
    def test_lesen_relativ_und_ausserhalb(self):
        root = self.tmp()
        r = os.path.realpath(root)
        out = json.dumps([
            {"score": 0.7, "file": r + "/a/B.md", "title": "x"},
            {"score": 0.6, "file": "./a/C.md", "title": "x"},
            {"score": 0.6, "file": "qmd://vault/a/D.md", "docid": "#1"},
            {"score": 0.6, "file": "/fremd/E.md"},
            {"score": 0.6, "file": r + "-anders/F.md"},
        ])
        self.assertEqual(nb.vsearch_lesen(out, root), [("a/B.md", 0.7, "B")])

    def test_kaputt(self):
        for s in ["{kaputt", "{}", '[{"score": "x"}]', '["a"]']:
            with self.assertRaises(nb.NachbarnFehler):
                nb.vsearch_lesen(s, "/")


class Nachbarn(Basis):
    def vault(self, extra=None):
        files = {AUS: FM + "Kappa und Rho.\n"}
        files.update(extra or {})
        d = self.bau(files)
        return d, vk.load_vault(d)

    def test_schwelle_null_ruft_nicht(self):
        d, v = self.vault()
        run = self.runner([])
        res = nb.nachbarn(v, AUS, einst(schwelle=None), run)
        self.assertEqual(res, ([], "Schwelle nicht geeicht"))
        self.assertEqual(len(run.calls), 0)

    def test_ausgeschlossene_ausgangsnotiz_ruft_nicht(self):
        fin = "03 Bereiche/Finanzen/Konto.md"
        d, v = self.vault({fin: "Geheim.\n"})
        run = self.runner([])
        res = nb.nachbarn(v, fin, einst(), run)
        self.assertEqual(res, ([], "Notiz vom Vektorindex ausgeschlossen"))
        self.assertEqual(len(run.calls), 0)

    def test_filter(self):
        gueltig = ["03 Bereiche/Notizen/G%d.md" % i for i in range(7)]
        files = {g: "Inhalt.\n" for g in gueltig}
        files.update({
            "03 Bereiche/Notizen/Doppelt.md": "x\n",
            "memory/m.md": "x\n",
            "03 Bereiche/Notizen/Verlinkt.md": "x\n",
            "03 Bereiche/Notizen/Schwach.md": "x\n",
        })
        d, v = self.vault(files)
        v.texts[AUS] = FM + "Siehe [[Verlinkt]].\n"
        t = [self.treffer(d, AUS, 0.99),
             self.treffer(d, "03 Bereiche/Notizen/Doppelt.md", 0.64),
             self.treffer(d, "03 Bereiche/Notizen/Doppelt.md", 0.81),
             self.treffer(d, "memory/m.md", 0.95),
             self.treffer(d, "03 Bereiche/Notizen/Weg.md", 0.9),
             self.treffer(d, "03 Bereiche/Notizen/Verlinkt.md", 0.9),
             self.treffer(d, "03 Bereiche/Notizen/Schwach.md", 0.3)]
        t += [self.treffer(d, g, 0.6 + i / 100) for i, g in enumerate(gueltig)]
        run = self.runner(t)
        res, grund = nb.nachbarn(v, AUS, einst(), run)
        self.assertIsNone(grund)
        self.assertEqual(len(res), 5)
        scores = [n.score for n in res]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(res[0].rel, "03 Bereiche/Notizen/Doppelt.md")
        self.assertEqual(res[0].score, 0.81)
        self.assertEqual(res[0].titel, "Doppelt")
        self.assertEqual(len({n.rel for n in res}), 5)
        rels = {n.rel for n in res}
        for verboten in [AUS, "memory/m.md", "03 Bereiche/Notizen/Weg.md",
                         "03 Bereiche/Notizen/Verlinkt.md", "03 Bereiche/Notizen/Schwach.md"]:
            self.assertNotIn(verboten, rels)

    def test_doppelte_datei_einmal_beim_besten_score(self):
        ziel = "03 Bereiche/Notizen/Ziel.md"
        d, v = self.vault({ziel: "x\n"})
        t = [self.treffer(d, ziel, 0.55), self.treffer(d, ziel, 0.81), self.treffer(d, ziel, 0.6)]
        res, _ = nb.nachbarn(v, AUS, einst(), self.runner(t))
        self.assertEqual([(n.rel, n.score) for n in res], [(ziel, 0.81)])

    def test_schwelle_filtert_unter_und_behaelt_gleich(self):
        a, b, c = ("03 Bereiche/Notizen/%s.md" % x for x in "ABC")
        d, v = self.vault({a: "x\n", b: "x\n", c: "x\n"})
        t = [self.treffer(d, a, 0.49), self.treffer(d, b, 0.5), self.treffer(d, c, 0.8)]
        res, _ = nb.nachbarn(v, AUS, einst(), self.runner(t))
        self.assertEqual([n.rel for n in res], [c, b])

    def test_nfd_pfad(self):
        name = "03 Bereiche/Notizen/Ärger.md"
        d, v = self.vault({name: "x\n"})
        nfd = unicodedata.normalize("NFD", name)
        self.assertNotEqual(nfd, name)
        t = [{"score": 0.7, "file": os.path.join(os.path.realpath(d), nfd), "title": "t"}]
        res, grund = nb.nachbarn(v, AUS, einst(), self.runner(t))
        self.assertIsNone(grund)
        self.assertEqual([(n.rel, n.titel) for n in res], [(name, "Ärger")])

    def test_nfd_ausgangsnotiz_wird_nicht_selbsttreffer(self):
        name = "03 Bereiche/Notizen/Ärger.md"
        d, v = self.vault({name: "x\n"})
        nfd = unicodedata.normalize("NFD", name)
        t = [{"score": 0.9, "file": os.path.join(os.path.realpath(d), nfd), "title": "t"}]
        res, _ = nb.nachbarn(v, name, einst(), self.runner(t))
        self.assertEqual(res, [])

    def test_fehler_wird_grund(self):
        d, v = self.vault()

        def wirft(*a, **k):
            raise nb.NachbarnFehler("qmd nicht gefunden")

        res, grund = nb.nachbarn(v, AUS, einst(), wirft)
        self.assertEqual((res, grund), ([], "qmd nicht gefunden"))
        res, grund = nb.nachbarn(v, AUS, einst(), lambda *a, **k: "{kaputt")
        self.assertEqual((res, grund), ([], "Ausgabe von qmd nicht lesbar"))

    def test_schwelle_kommt_aus_einstellung(self):
        a = "03 Bereiche/Notizen/A.md"
        d, v = self.vault({a: "x\n"})
        t = [self.treffer(d, a, 0.3)]
        self.assertEqual(len(nb.nachbarn(v, AUS, einst(schwelle=0.2), self.runner(t))[0]), 1)
        self.assertEqual(nb.nachbarn(v, AUS, einst(schwelle=0.9), self.runner(t))[0], [])

    def test_max_nachbarn_kommt_aus_einstellung(self):
        rels = ["03 Bereiche/Notizen/N%d.md" % i for i in range(4)]
        d, v = self.vault({r: "x\n" for r in rels})
        t = [self.treffer(d, r, 0.7) for r in rels]
        self.assertEqual(len(nb.nachbarn(v, AUS, einst(max_nachbarn=2), self.runner(t))[0]), 2)
        self.assertEqual(len(nb.nachbarn(v, AUS, einst(max_nachbarn=4), self.runner(t))[0]), 4)

    def test_ausschluss_kommt_aus_einstellung(self):
        eig = "03 Bereiche/Eigen/Ziel.md"
        aus = "03 Bereiche/Eigen/Start.md"
        d, v = self.vault({eig: "x\n", aus: "Text.\n", "memory/m.md": "x\n"})
        run = self.runner([self.treffer(d, eig, 0.7), self.treffer(d, "memory/m.md", 0.7)])
        res, _ = nb.nachbarn(v, AUS, einst(ausschluss=["03 Bereiche/Eigen/**"]), run)
        # memory/ ist hier nicht mehr ausgeschlossen, Eigen/ schon
        self.assertEqual([n.rel for n in res], ["memory/m.md"])
        run = self.runner([])
        res = nb.nachbarn(v, aus, einst(ausschluss=["03 Bereiche/Eigen/**"]), run)
        self.assertEqual(res, ([], "Notiz vom Vektorindex ausgeschlossen"))
        self.assertEqual(len(run.calls), 0)
        # mit der Vorgabe waere Start.md nicht ausgeschlossen
        self.assertEqual(len(nb.nachbarn(v, aus, einst(), run)[1:]), 1)
        self.assertEqual(len(run.calls), 1)

    def test_python_zu_alt(self):
        d, v = self.vault()
        run = self.runner([])
        with mock.patch.object(nb, "PurePosixPath", type("Alt", (), {})):
            res = nb.nachbarn(v, AUS, einst(), run)
        self.assertEqual(res, ([], "Python ab 3.13 nötig"))
        self.assertEqual(len(run.calls), 0)

    def test_python_grund_gemeinsam(self):
        self.assertIsNone(nb.python_grund())
        with mock.patch.object(nb, "PurePosixPath", type("Alt", (), {})):
            self.assertEqual(nb.python_grund(), "Python ab 3.13 nötig")

    def test_notiz_ohne_text_ruft_nicht(self):
        for body in [FM, FM + "```\nnur Code\n```\n", ""]:
            d, v = self.vault({"03 Bereiche/Notizen/Leer.md": body})
            run = self.runner([])
            res = nb.nachbarn(v, "03 Bereiche/Notizen/Leer.md", einst(), run)
            self.assertEqual(res, ([], "Notiz ohne Text"), repr(body))
            self.assertEqual(len(run.calls), 0)

    def test_gleichnamige_notizen_geben_pfad(self):
        a, b = "02 Projekte/A/Fehlerlog.md", "02 Projekte/B/Fehlerlog.md"
        eind = "03 Bereiche/Notizen/Eindeutig.md"
        d, v = self.vault({a: "x\n", b: "x\n", eind: "x\n"})
        t = [self.treffer(d, a, 0.8), self.treffer(d, b, 0.7), self.treffer(d, eind, 0.6)]
        res, _ = nb.nachbarn(v, AUS, einst(), self.runner(t))
        self.assertEqual([n.titel for n in res],
                         ["Fehlerlog", "02 Projekte/B/Fehlerlog", "Eindeutig"])
        # Der nackte Name loest wie in Obsidian auf A auf (kuerzester Pfad); B braucht den Pfad.
        for n in res:
            self.assertEqual(v.resolver.resolve(n.titel, AUS), n.rel)

    def test_nachbarn_bricht_bei_remote_yaml(self):
        d, v = self.vault()
        with open(os.path.join(self.cfg, "vault.yml"), "w") as fh:
            fh.write(GUTE_YAML + 'models:\n  embed: "https://api.openai.com/v1#text-embedding-3-small"\n')
        run = self.runner([])
        res = nb.nachbarn(v, AUS, einst(), run)
        self.assertEqual(res, ([], "qmd-Konfiguration mit Fremdmodell"))
        self.assertEqual(len(run.calls), 0)

    def test_nachbarn_ohne_yaml_ruft_nicht(self):
        d, v = self.vault()
        os.remove(os.path.join(self.cfg, "vault.yml"))
        run = self.runner([])
        res = nb.nachbarn(v, AUS, einst(), run)
        self.assertEqual(res, ([], "qmd-Index nicht gebaut (verknuepfen.py index)"))
        self.assertEqual(len(run.calls), 0)

    def test_nachbarn_yaml_pfad_ist_ordner_gibt_grund(self):
        d, v = self.vault()
        pfad = os.path.join(self.cfg, "vault.yml")
        os.remove(pfad)
        os.mkdir(pfad)
        run = self.runner([])
        res, grund = nb.nachbarn(v, AUS, einst(), run)
        self.assertEqual(res, [])
        self.assertTrue(grund.startswith("qmd-Konfiguration nicht lesbar"), grund)
        self.assertEqual(len(run.calls), 0)

    def test_nachbarn_prueft_yaml_des_eingestellten_index(self):
        d, v = self.vault()
        with open(os.path.join(self.cfg, "meins.yml"), "w") as fh:
            fh.write("models:\n  embed: openai\n")
        run = self.runner([])
        self.assertEqual(nb.nachbarn(v, AUS, einst(qmd_index="meins"), run)[1], "qmd-Konfiguration mit Fremdmodell")
        self.assertEqual(len(run.calls), 0)
        self.assertEqual(nb.nachbarn(v, AUS, einst(), run)[1], None)  # vault.yml ist gut
        self.assertEqual(len(run.calls), 1)

    def test_yaml_pruefung_kommt_nach_schwelle_und_ausschluss(self):
        fin = "03 Bereiche/Finanzen/Konto.md"
        d, v = self.vault({fin: "Geheim.\n"})
        os.remove(os.path.join(self.cfg, "vault.yml"))
        run = self.runner([])
        self.assertEqual(nb.nachbarn(v, AUS, einst(schwelle=None), run)[1], "Schwelle nicht geeicht")
        self.assertEqual(nb.nachbarn(v, fin, einst(), run)[1], "Notiz vom Vektorindex ausgeschlossen")
        self.assertEqual(len(run.calls), 0)

    def test_runner_bekommt_einstellungen(self):
        d, v = self.vault()
        run = self.runner([])
        nb.nachbarn(v, AUS, einst(qmd_index="meins", qmd_frist=9), run)
        index, abfrage, frist, _n = run.calls[0]
        self.assertEqual((index, frist), ("meins", 9))
        self.assertIn("Kappa und Rho.", abfrage)
        self.assertNotIn("tags:", abfrage)


class Cli(Basis):
    def lauf(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vk.main(argv)
        return code, out.getvalue()

    def test_cli_uebersprungen_exit_0(self):
        d = self.bau({AUS: FM + "Kappa.\n"})
        e = os.path.join(self.tmp(), "nicht-da.json")
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": e}):
            code, out = self.lauf(["nachbarn", "--vault", d, AUS])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Schritt 4 übersprungen: Schwelle nicht geeicht")

    def test_cli_punkt_schraegstrich_und_ausbruch(self):
        d = self.bau({AUS: FM + "Kappa.\n"})
        e = os.path.join(self.tmp(), "nicht-da.json")
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": e}):
            code, out = self.lauf(["nachbarn", "--vault", d, "./" + AUS])
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), "Schritt 4 übersprungen: Schwelle nicht geeicht")
            code, _ = self.lauf(["nachbarn", "--vault", d, "../" + AUS])
            self.assertEqual(code, 1)

    def test_cli_vorschlaege_und_json(self):
        ziel = "03 Bereiche/Notizen/Ziel.md"
        d = self.bau({AUS: FM + "Kappa.\n", ziel: "x\n"})
        ed = self.tmp()
        ep = os.path.join(ed, "e.json")
        with open(ep, "w") as fh:
            json.dump({"graph": {"schwelle": 0.5}}, fh)
        t = [self.treffer(d, ziel, 0.73)]
        jp = os.path.join(ed, "out.json")
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": ep}), \
                mock.patch.object(nb, "qmd_runner", lambda *a, **k: json.dumps(t)):
            code, out = self.lauf(["nachbarn", "--vault", d, "--json", jp, AUS])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Verwandt: [[Ziel]] (0.73)")
        with open(jp) as fh:
            data = json.load(fh)
        self.assertEqual(data["nachbarn"][0]["rel"], ziel)

    def test_cli_unter_isolated_python(self):
        d = self.bau({AUS: FM + "Kappa.\n"})
        e = os.path.join(self.tmp(), "nicht-da.json")
        env = {"PATH": os.environ["PATH"], "VERKNUEPFEN_EINSTELLUNGEN": e, "VERKNUEPFEN_TEST": "1"}
        for k in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "QMD_CONFIG_DIR", "INDEX_PATH", "VERKNUEPFEN_QMD_PAKET"):
            env[k] = os.environ[k]  # die umgelenkten Werte aus Basis.setUp
        r = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(nb.__file__), "verknuepfen.py"),
                            "nachbarn", "--vault", d, AUS], capture_output=True, text=True, env=env, cwd="/")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "Schritt 4 übersprungen: Schwelle nicht geeicht")

    def test_cli_json_ordner_fehlt_exit_2_mit_textausgabe(self):
        d = self.bau({AUS: FM + "Kappa.\n"})
        e = os.path.join(self.tmp(), "nicht-da.json")
        jp = os.path.join(self.tmp(), "fehlt", "out.json")
        env = {"PATH": os.environ["PATH"], "VERKNUEPFEN_EINSTELLUNGEN": e, "VERKNUEPFEN_TEST": "1"}
        for k in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "QMD_CONFIG_DIR", "INDEX_PATH", "VERKNUEPFEN_QMD_PAKET"):
            env[k] = os.environ[k]
        r = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(nb.__file__), "verknuepfen.py"),
                            "nachbarn", "--vault", d, "--json", jp, AUS], capture_output=True, text=True, env=env,
                           cwd="/")
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(r.stdout.strip(), "Schritt 4 übersprungen: Schwelle nicht geeicht")
        self.assertIn(jp, r.stderr)
        self.assertFalse(os.path.exists(os.path.dirname(jp)))

    def test_cli_unbekannte_notiz(self):
        d = self.bau({AUS: "x\n"})
        code, _ = self.lauf(["nachbarn", "--vault", d, "gibt/es/nicht.md"])
        self.assertEqual(code, 1)


class Index(Basis):
    """verknuepfen.py index mit gefaktem qmd (nb.qmd_aufruf); Pfade nur in Wegwerf-Ordnern."""

    def aufbau(self, rc=None, db_zeilen=None, nach_update=None, cleanup_loescht=True):
        self.vault = self.bau({AUS: FM + "Kappa.\n"})
        # die YAML aus Basis.setUp zeigt auf /x/vault und waere eine fremde Konfiguration
        os.remove(os.path.join(self.cfg, "vault.yml"))
        self.db = os.path.join(self.cfg, "kein.sqlite")  # INDEX_PATH aus Basis.setUp
        self.calls = []
        rc = rc or {}

        def aufruf(index, schritt):
            self.calls.append((index, schritt))
            if schritt == "update":
                con = sqlite3.connect(self.db)
                con.execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, collection TEXT, "
                            "path TEXT, title TEXT, hash TEXT, active INTEGER)")
                for p, a in (db_zeilen or []):
                    con.execute("INSERT INTO documents (collection, path, title, hash, active) "
                                "VALUES ('vault', ?, 't', 'h', ?)", (p, a))
                con.commit()
                con.close()
                if nach_update:
                    nach_update()
            if schritt == "cleanup" and cleanup_loescht:  # qmd cleanup: DELETE FROM documents WHERE active = 0
                con = sqlite3.connect(self.db)
                con.execute("DELETE FROM documents WHERE active = 0")
                con.commit()
                con.close()
            return rc.get(schritt, 0)
        return aufruf

    def lauf(self, aufruf, extra_env=None):
        out, err = io.StringIO(), io.StringIO()
        e = os.path.join(self.tmp(), "nicht-da.json")
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": e, **(extra_env or {})}), \
                mock.patch.object(nb, "qmd_aufruf", aufruf), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vk.main(["index", "--vault", self.vault])
        return code, out.getvalue(), err.getvalue()

    def yaml_pfad(self):
        return os.path.join(self.cfg, "vault.yml")

    def test_index_schreibt_yaml_und_ruft_drei_schritte_in_reihenfolge(self):
        auf = self.aufbau(db_zeilen=[("03 Bereiche/Notizen/Kappa.md", 1)])
        self.assertFalse(os.path.exists(self.yaml_pfad()))
        code, out, err = self.lauf(auf)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.calls, [("vault", "update"), ("vault", "cleanup"), ("vault", "embed")])
        with open(self.yaml_pfad(), encoding="utf-8") as fh:
            self.assertIn('path: "%s"' % os.path.realpath(self.vault), fh.read())

    def test_index_schreibt_yaml_immer_neu(self):
        auf = self.aufbau()
        with open(self.yaml_pfad(), "w") as fh:
            fh.write('collections:\n  vault:\n    path: "%s"\n    ignore:\n      - "alt/**"\n'
                     % os.path.realpath(self.vault))
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 0, err)
        with open(self.yaml_pfad(), encoding="utf-8") as fh:
            t = fh.read()
        self.assertEqual(t, nb.qmd_yaml(self.vault, nb.einstellungen_laden(os.path.join(self.cfg, "x.json"))))

    FREMD = {
        "fremde Collection": 'collections:\n  notizen:\n    path: "/irgendwo/notizen"\n    pattern: "**/*.md"\n'
                             'global_context: "eigene Beschreibung"\n',
        "zweite Collection": 'collections:\n  vault:\n    path: "{v}"\n  notizen:\n    path: "/irgendwo"\n',
        "anderer Pfad": 'collections:\n  vault:\n    path: "/irgendwo/anders"\n    pattern: "**/*.md"\n',
        "anderer Pfad ohne Anfuehrung": 'collections:\n  vault:\n    path: /irgendwo/anders\n',
        "fremder Schluessel": 'collections:\n  vault:\n    path: "{v}"\nglobal_context: "x"\n',
        "fremder Schluessel mit models": 'collections:\n  vault:\n    path: {v}\nmodels:\n  embed: hf:a/b\n'
                                         'contexts:\n  x: y\n',
        "Flow-Form": 'collections: {{vault: {{path: "{v}"}}}}\n',
    }

    def test_index_fremde_yaml_bleibt_byte_gleich_ohne_qmd(self):
        for name, vorlage in self.FREMD.items():
            with self.subTest(name):
                auf = self.aufbau()
                inhalt = vorlage.format(v=os.path.realpath(self.vault)).encode("utf-8")
                with open(self.yaml_pfad(), "wb") as fh:
                    fh.write(inhalt)
                code, out, err = self.lauf(auf)
                self.assertEqual(code, 1, err)
                self.assertEqual(self.calls, [])
                with open(self.yaml_pfad(), "rb") as fh:
                    self.assertEqual(fh.read(), inhalt)
                self.assertIn("fremde qmd-Konfiguration in %s" % self.yaml_pfad(), err)
                self.assertIn("graph.qmd_index", err)
                self.assertEqual(sorted(os.listdir(self.cfg)), ["meins.yml", "vault.yml"])

    def test_index_eigene_yaml_mit_models_block_wird_ueberschrieben(self):
        auf = self.aufbau()
        # Form, in der qmd die Datei nach update zurueckschreibt: ohne Anfuehrungszeichen, mit models:
        with open(self.yaml_pfad(), "w", encoding="utf-8") as fh:
            fh.write("collections:\n  vault:\n    path: %s\n    pattern: \"**/*.md\"\n    ignore:\n"
                     "      - memory/**\n      - 06 Archiv/Alt */**\n    includeByDefault: true\nmodels:\n"
                     "  embed: hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf\n"
                     % os.path.realpath(self.vault))
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 0, err)
        self.assertEqual([c[1] for c in self.calls], ["update", "cleanup", "embed"])
        with open(self.yaml_pfad(), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), nb.qmd_yaml(self.vault, nb.einstellungen_laden(os.path.join(self.cfg, "x"))))

    def test_index_eigene_yaml_ueber_symlink_und_nfd_pfad(self):
        auf = self.aufbau()
        link = os.path.join(self.tmp(), "Ärger-ln")
        os.symlink(self.vault, link)
        with open(self.yaml_pfad(), "w", encoding="utf-8") as fh:
            fh.write("collections:\n  vault:\n    path: '%s'\n" % unicodedata.normalize("NFD", link))
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 0, err)

    def test_index_aktive_ausgeschlossene_zeile_nach_cleanup_kein_embed(self):
        auf = self.aufbau(db_zeilen=[("memory/Omega.md", 1), ("03 Bereiche/Notizen/Kappa.md", 1)])
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [("vault", "update"), ("vault", "cleanup")])
        self.assertIn("memory/Omega.md", err)
        self.assertIn("nach cleanup", err)
        self.assertIn("-wal", err)

    def test_index_inaktive_ausgeschlossene_zeile_cleanup_raeumt_weg(self):
        # neuer Ausschluss: update setzt die Notiz nur auf active=0, cleanup loescht sie
        auf = self.aufbau(db_zeilen=[("memory/Omega.md", 0), ("03 Bereiche/Notizen/Kappa.md", 1)])
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 0, err)
        self.assertEqual([c[1] for c in self.calls], ["update", "cleanup", "embed"])
        self.assertNotIn("neu bauen", err)
        self.assertNotIn("Omega", err)

    def test_index_inaktive_ausgeschlossene_zeile_uebersteht_cleanup(self):
        auf = self.aufbau(db_zeilen=[("memory/Omega.md", 0)], cleanup_loescht=False)
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertEqual([c[1] for c in self.calls], ["update", "cleanup"])
        self.assertIn("memory/Omega.md", err)
        self.assertIn("nach cleanup", err)
        self.assertIn("-wal", err)
        self.assertIn("neu", err)

    def test_index_python_zu_alt_exit_1_ohne_qmd(self):
        auf = self.aufbau()
        with mock.patch.object(nb, "PurePosixPath", type("Alt", (), {})):
            code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [])
        self.assertIn("Python ab 3.13 nötig", err)
        self.assertFalse(os.path.exists(self.yaml_pfad()))

    def test_index_schritt_scheitert_exit_1_und_nennt_schritt(self):
        auf = self.aufbau(rc={"embed": 3})
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertIn("embed", err)
        self.assertEqual([c[1] for c in self.calls], ["update", "cleanup", "embed"])  # Prüfung nach dem Lauf entfällt

    def test_index_befund_im_index_exit_1_mit_liste_und_hinweis(self):
        auf = self.aufbau(db_zeilen=[("memory/Omega.md", 1), ("03 Bereiche/Notizen/Kappa.md", 1)])
        code, out, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertIn("memory/Omega.md", err)
        self.assertNotIn("Kappa.md", err)
        self.assertIn("neu", err)

    def test_index_befund_nach_dem_lauf(self):
        basis = self.aufbau()

        def auf(index, schritt):
            rc = basis(index, schritt)
            if schritt == "embed":  # ausgeschlossene Zeile erst beim letzten Schritt
                con = sqlite3.connect(self.db)
                con.execute("INSERT INTO documents (collection, path, title, hash, active) "
                            "VALUES ('vault', 'memory/Omega.md', 't', 'h', 1)")
                con.commit()
                con.close()
            return rc
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertEqual([c[1] for c in self.calls], ["update", "cleanup", "embed"])
        self.assertIn("memory/Omega.md", err)
        self.assertIn("nach dem Lauf", err)

    def test_index_yaml_befund_vor_qmd_exit_1(self):
        auf = self.aufbau()
        ep = os.path.join(self.tmp(), "e.json")
        with open(ep, "w") as fh:
            json.dump({"graph": {"ausschluss": ["https://kappa.example/**"]}}, fh)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": ep}), \
                mock.patch.object(nb, "qmd_aufruf", auf), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vk.main(["index", "--vault", self.vault])
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [])
        self.assertIn("https://", err.getvalue())

    def test_index_fremdmodell_nach_dem_lauf_exit_1(self):
        def umschreiben():
            with open(self.yaml_pfad(), "a") as fh:
                fh.write("models:\n  embed: openai:text-embedding-3-small\n")
        auf = self.aufbau(nach_update=umschreiben)
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertIn("openai:text-embedding-3-small", err)

    def test_index_fremdmodell_nach_update_kein_embed(self):
        def umschreiben():
            with open(self.yaml_pfad(), "a") as fh:
                fh.write("models:\n  embed: openai:text-embedding-3-small\n")
        auf = self.aufbau(nach_update=umschreiben)
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [("vault", "update")])
        self.assertIn("nach update", err)
        self.assertIn("openai:text-embedding-3-small", err)

    def test_index_fremdmodell_nach_cleanup_exit_1(self):
        basis = self.aufbau()

        def auf(index, schritt):
            rc = basis(index, schritt)
            if schritt == "cleanup":
                with open(self.yaml_pfad(), "a") as fh:
                    fh.write("models:\n  embed: openai:text-embedding-3-small\n")
            return rc
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertEqual([c[1] for c in self.calls], ["update", "cleanup"])  # kein embed
        self.assertIn("nach cleanup", err)
        self.assertIn("openai:text-embedding-3-small", err)

    def test_index_fremdmodell_nach_embed_nach_dem_lauf(self):
        basis = self.aufbau()

        def auf(index, schritt):
            rc = basis(index, schritt)
            if schritt == "embed":
                with open(self.yaml_pfad(), "a") as fh:
                    fh.write("models:\n  embed: openai:text-embedding-3-small\n")
            return rc
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 1)
        self.assertIn("nach dem Lauf", err)

    def test_index_hinweis_nennt_wal_und_shm(self):
        auf = self.aufbau(db_zeilen=[("memory/Omega.md", 1)])
        _, _, err = self.lauf(auf)
        self.assertIn("-wal", err)
        self.assertIn("-shm", err)

    def test_index_qmd_standardmodelle_sind_ok(self):
        def umschreiben():
            with open(self.yaml_pfad(), "a") as fh:
                fh.write("models:\n  embed: hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf\n")
        auf = self.aufbau(nach_update=umschreiben)
        code, _, err = self.lauf(auf)
        self.assertEqual(code, 0, err)

    def test_index_qmd_fehlt_exit_1(self):
        self.aufbau()

        def wirft(index, schritt):
            raise nb.NachbarnFehler("qmd nicht gefunden")
        code, _, err = self.lauf(wirft)
        self.assertEqual(code, 1)
        self.assertIn("qmd nicht gefunden", err)

    def test_index_vault_fehlt_exit_2(self):
        self.vault = os.path.join(self.tmp(), "gibt-es-nicht")
        code, _, err = self.lauf(lambda i, s: 0)
        self.assertEqual(code, 2)

    def test_index_db_unter_xdg_pfad_ohne_index_path(self):
        auf = self.aufbau()
        xdg = self.tmp()
        self.db = os.path.join(xdg, "qmd", "vault.sqlite")
        os.makedirs(os.path.dirname(self.db))
        env = {"XDG_CACHE_HOME": xdg}
        with mock.patch.dict(os.environ):
            del os.environ["INDEX_PATH"]
            code, _, err = self.lauf(auf, env)
        self.assertEqual(code, 0, err)
        self.assertTrue(os.path.exists(self.db))

    def test_qmd_aufruf_liste_ohne_shell_ohne_frist(self):
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=4)) as run:
            self.assertEqual(nb.qmd_aufruf("idx", "embed"), 4)
        args, kw = run.call_args
        self.assertEqual(args[0], [nb.QMD, "--index", "idx", "embed"])
        self.assertFalse(kw.get("shell", False))
        self.assertNotIn("timeout", kw)
        self.assertNotIn("capture_output", kw)
        self.assertNotIn("stdout", kw)

    def test_qmd_aufruf_ohne_programm(self):
        with mock.patch.object(nb, "QMD", "/nicht/da/qmd"):
            with self.assertRaises(nb.NachbarnFehler) as c:
                nb.qmd_aufruf("idx", "update")
        self.assertIn("qmd nicht gefunden", str(c.exception))


if __name__ == "__main__":
    unittest.main()
