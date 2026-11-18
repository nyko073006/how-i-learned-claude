"""Tests fuer den Hook ~/.claude/hooks/auto-link-entities.py (Subprozess, Wegwerf-Vault).

    python3 -I -m unittest discover -s ~/.claude/skills/verknuepfen/scripts
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Der Hook ist Code unter Test (nur gelesen); sein Pfad zaehlt ab dem Home des angemeldeten Nutzers,
# nicht ab HOME: andere Testdateien biegen HOME beim Sammeln schon um.
try:
    import pwd
    _NUTZER_HOME = pwd.getpwuid(os.getuid()).pw_dir
except (ImportError, KeyError):  # pragma: no cover
    _NUTZER_HOME = os.path.expanduser("~")
HOOK = os.path.join(_NUTZER_HOME, ".claude", "hooks", "auto-link-entities.py")

# Vorspann VOR dem Import: HOME und Einstellungsdatei zeigen in einen Wegwerf-Ordner, damit weder
# ein Test noch eine Mutation die echte Konfiguration oder den echten Vault liest oder beschreibt.
# Subprozesse erben os.environ und damit diese Werte.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="hook-test-home-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verknuepfen as vk  # noqa: E402

SKILL = os.path.dirname(os.path.abspath(__file__))
ENT = "04 Ressourcen/Entitäten"
KAPPA = ENT + "/Kappa.md"
RHO = ENT + "/Rho GmbH.md"
NOTIZ = "03 Bereiche/Notizen/Test.md"
FM = "---\ntags: [test]\n---\n"


def ent(typ, aliases="[]"):
    return f"---\ntags: [entitaet]\ntype: {typ}\naliases: {aliases}\n---\n# Notiz\n"


BASIS = {KAPPA: ent("werkzeug", '["Kappa Tool"]'), RHO: ent("firma", "[Rho]")}


# Der Hook wird nicht mit dem Skill ausgeliefert; ohne ihn entfallen seine Tests statt rot zu werden.
@unittest.skipUnless(os.path.exists(HOOK), "Hook ~/.claude/hooks/auto-link-entities.py nicht installiert (nicht mitgeliefert)")
class HookBasis(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="hook-test-")
        self.addCleanup(shutil.rmtree, self.d)
        self.vault = os.path.join(self.d, "vault")
        self.sperre = os.path.join(self.d, "sperre.json")
        self.log = os.path.join(self.d, "hook.log")
        self.einst = os.path.join(self.d, "einstellungen.json")
        with open(self.einst, "w", encoding="utf-8") as fh:
            json.dump({"vault": self.vault}, fh)
        self.write(BASIS)

    def write(self, files):
        for rel, content in files.items():
            p = os.path.join(self.vault, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(content)

    def read(self, rel):
        with open(os.path.join(self.vault, rel), "rb") as fh:
            return fh.read().decode("utf-8")

    def run_hook(self, payload, raw=None):
        # ASSUMPTION: VERKNUEPFEN_TEST wird im Hook-Lauf nicht gesetzt, weil write_locked auch den
        # per Einstellungsdatei gesetzten Temp-Vault sperrt (bestehender Test); der Temp-Vault ist
        # hier ausdruecklich gesetzt und liegt nie unter dem echten Vault.
        env = {k: v for k, v in os.environ.items() if k != "VERKNUEPFEN_TEST"}
        env.update(CLAUDE_SKILLS_EINSTELLUNGEN=self.einst, AUTO_LINK_SPERRE=self.sperre,
                   AUTO_LINK_LOG=self.log, VERKNUEPFEN_DIR=SKILL)
        data = raw if raw is not None else json.dumps(payload)
        r = subprocess.run([sys.executable, "-I", HOOK], input=data, text=True, env=env,
                           capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")
        return r

    def lauf(self, rel=NOTIZ):
        return self.run_hook({"tool_input": {"file_path": os.path.join(self.vault, rel)}})

    def state(self):
        with open(self.sperre, encoding="utf-8") as fh:
            return json.load(fh)


class Hook(HookBasis):
    def test_alias_wird_verlinkt(self):
        self.write({NOTIZ: FM + "Wir setzen das Kappa Tool ein.\n"})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Wir setzen das [[Kappa|Kappa Tool]] ein.\n")
        self.assertEqual(self.state()["notes"][NOTIZ]["gesetzt"], [KAPPA])

    def test_ausweich_tool_response(self):
        self.write({NOTIZ: FM + "Kappa hier.\n"})
        self.run_hook({"tool_response": {"filePath": os.path.join(self.vault, NOTIZ)}})
        self.assertIn("[[Kappa]]", self.read(NOTIZ))

    def test_eingerueckter_codeblock_bleibt(self):
        body = FM + "Beispiel:\n\n    kappa --version\n"
        self.write({NOTIZ: body})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), body)

    def test_allgemeines_wort_bleibt(self):
        body = FM + "Ein Werkzeug, eine Firma, ein Projekt und eine Person.\n"
        self.write({NOTIZ: body})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), body)

    def test_entfernter_link_wird_gesperrt(self):
        self.write({NOTIZ: FM + "Kappa und Rho GmbH.\n"})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "[[Kappa]] und [[Rho GmbH]].\n")
        self.write({NOTIZ: FM + "Kappa und [[Rho GmbH]].\n"})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Kappa und [[Rho GmbH]].\n")
        e = self.state()["notes"][NOTIZ]
        self.assertEqual(e["gesperrt"], [KAPPA])
        self.assertEqual(e["gesetzt"], [RHO])

    def test_erstkontakt_von_hand_gesetzter_link_kommt_nicht_zurueck(self):
        self.write({NOTIZ: FM + "Kappa und [[Rho GmbH]].\n"})
        self.lauf()  # Erstkontakt: Rho ist schon verlinkt, gilt als gesetzt
        e = self.state()["notes"][NOTIZ]
        self.assertEqual(sorted(e["gesetzt"]), sorted([KAPPA, RHO]))
        self.write({NOTIZ: FM + "Kappa und Rho GmbH.\n"})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Kappa und Rho GmbH.\n")
        self.assertEqual(sorted(self.state()["notes"][NOTIZ]["gesperrt"]), sorted([KAPPA, RHO]))

    def test_nie_verlinkte_entitaet_weder_gesetzt_noch_gesperrt(self):
        self.write({NOTIZ: FM + "Nur ein Satz ohne Namen.\n"})
        self.lauf()
        self.write({NOTIZ: FM + "Nur ein Satz, [[Rho GmbH]] steht drin.\n"})
        self.lauf()
        self.write({NOTIZ: FM + "Nur ein Satz ohne Namen.\n"})
        self.lauf()
        e = self.state()["notes"][NOTIZ]
        self.assertNotIn(KAPPA, e["gesetzt"] + e["gesperrt"])

    def test_spaeter_von_hand_gesetzter_link_kommt_nicht_zurueck(self):
        self.write({NOTIZ: FM + "Nur ein Satz ohne Namen.\n"})
        self.lauf()  # Lauf 1: kein Fund
        self.write({NOTIZ: FM + "Hier [[Kappa]] von Hand.\n"})
        self.lauf()  # Lauf 2
        self.assertEqual(self.state()["notes"][NOTIZ]["gesetzt"], [KAPPA])
        self.write({NOTIZ: FM + "Hier Kappa von Hand.\n"})
        self.lauf()  # Lauf 3
        self.assertEqual(self.read(NOTIZ), FM + "Hier Kappa von Hand.\n")
        self.assertEqual(self.state()["notes"][NOTIZ]["gesperrt"], [KAPPA])

    def test_gesperrte_entitaet_wird_nicht_gesetzt(self):
        self.write({NOTIZ: FM + "Kappa hier.\n"})
        self.lauf()
        self.write({NOTIZ: FM + "Kappa hier.\n"})
        self.lauf()  # gesperrt
        self.write({NOTIZ: FM + "[[Kappa]] hier.\n"})
        self.lauf()
        e = self.state()["notes"][NOTIZ]
        self.assertEqual((e["gesetzt"], e["gesperrt"]), ([], [KAPPA]))

    def test_nicht_entitaet_weder_gesetzt_noch_gesperrt(self):
        self.write({"03 Bereiche/Notizen/Andere Notiz.md": FM + "Inhalt.\n",
                    NOTIZ: FM + "[[Andere Notiz]] und [[Kappa]].\n"})
        self.lauf()
        self.write({NOTIZ: FM + "Andere Notiz und [[Kappa]].\n"})
        self.lauf()
        e = self.state()["notes"][NOTIZ]
        self.assertEqual((e["gesetzt"], e["gesperrt"]), ([KAPPA], []))
        with open(self.log, "a+", encoding="utf-8") as fh:
            fh.seek(0)
            self.assertNotIn("gesperrt", fh.read())

    def test_kein_leerer_eintrag(self):
        self.write({NOTIZ: FM + "Nur ein Satz ohne Namen.\n"})
        self.lauf()
        self.assertFalse(os.path.exists(self.sperre))

    def test_zustandsordner_schreibgeschuetzt(self):
        lock = os.path.join(self.d, "zu")
        os.makedirs(lock)
        self.sperre = os.path.join(lock, "sperre.json")
        self.write({NOTIZ: FM + "Kappa hier.\n"})
        os.chmod(lock, 0o555)
        try:
            self.lauf()
        finally:
            os.chmod(lock, 0o755)
        self.assertEqual(self.read(NOTIZ), FM + "Kappa hier.\n")  # Notiz nicht geschrieben
        self.assertFalse(os.path.exists(self.sperre))
        with open(self.log, encoding="utf-8") as fh:
            self.assertIn("Zustandsdatei", fh.read())
        self.lauf()  # jetzt schreibbar
        self.assertEqual(self.read(NOTIZ), FM + "[[Kappa]] hier.\n")
        self.write({NOTIZ: FM + "Kappa hier.\n"})
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Kappa hier.\n")

    def test_schreibfehler_stellt_zustand_wieder_her(self):
        p = os.path.join(self.vault, NOTIZ)
        self.write({ENT + "/Tau.md": ent("werkzeug"), NOTIZ: FM + "Kappa hier.\n"})
        self.lauf()  # Erstkontakt, Kappa gesetzt
        vorher = self.state()
        # Kappa von Hand entfernt, dazu neue Erwaehnung Tau; Schreiben scheitert
        self.write({NOTIZ: FM + "Kappa und Tau.\n"})
        os.chmod(p, 0o444)
        self.addCleanup(os.chmod, p, 0o644)
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Kappa und Tau.\n")
        self.assertEqual(self.state(), vorher)  # weder Sperre noch Tau gespeichert

    def test_zweiter_lauf_byte_gleich(self):
        self.write({NOTIZ: FM + "Kappa und Rho.\n"})
        self.lauf()
        erst = self.read(NOTIZ).encode()
        self.lauf()
        self.assertEqual(self.read(NOTIZ).encode(), erst)

    def test_kein_eingriff_ausserhalb(self):
        out = os.path.join(self.d, "aussen.md")
        txt = os.path.join(self.vault, "03 Bereiche", "n.txt")
        arch = "06 Archiv/alt.md"
        body = FM + "Kappa.\n"
        self.write({"03 Bereiche/n.txt": body, arch: body})
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(body)
        for p in (out, txt, os.path.join(self.vault, arch)):
            self.run_hook({"tool_input": {"file_path": p}})
            with open(p, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), body)
        self.assertFalse(os.path.exists(self.sperre))

    def test_kaputter_payload(self):
        self.write({NOTIZ: FM + "Kappa.\n"})
        for raw in ("", "{kaputt", "[]", "null", '{"tool_input": 5}', '{"tool_input": {"file_path": 7}}'):
            self.run_hook(None, raw=raw)
        self.assertEqual(self.read(NOTIZ), FM + "Kappa.\n")

    def test_kaputte_sperrliste(self):
        self.write({NOTIZ: FM + "Kappa.\n"})
        with open(self.sperre, "w", encoding="utf-8") as fh:
            fh.write("{kaputt")
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "[[Kappa]].\n")
        self.assertEqual(self.state()["notes"][NOTIZ]["gesetzt"], [KAPPA])

    def test_fehlender_skill(self):
        env = {k: v for k, v in os.environ.items()}
        env.update(CLAUDE_SKILLS_EINSTELLUNGEN=self.einst, AUTO_LINK_SPERRE=self.sperre, AUTO_LINK_LOG=self.log,
                   VERKNUEPFEN_DIR=os.path.join(self.d, "gibtsnicht"))
        r = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(
            {"tool_input": {"file_path": os.path.join(self.vault, NOTIZ)}}), text=True, env=env,
            capture_output=True, timeout=60)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        with open(self.log, encoding="utf-8") as fh:
            self.assertEqual(len(fh.read().splitlines()), 1)

    def test_ohne_vault_einstellung_nur_logzeile(self):
        self.write({NOTIZ: FM + "Kappa.\n"})
        with open(self.einst, "w", encoding="utf-8") as fh:
            fh.write("{}")
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Kappa.\n")
        with open(self.log, encoding="utf-8") as fh:
            zeilen = fh.read().splitlines()
        self.assertEqual(len(zeilen), 1)
        self.assertIn("Vault-Pfad fehlt", zeilen[0])

    def test_interner_fehler_exit_null(self):
        fake = os.path.join(self.d, "fakeskill")
        os.makedirs(fake)
        with open(os.path.join(fake, "verknuepfen.py"), "w", encoding="utf-8") as fh:
            fh.write("class vl:\n    vault_vorgabe = staticmethod(lambda: %r)\n    nfc = staticmethod(lambda s: s)\n"
                     % self.vault +
                     "def is_source(rel):\n    return True\n"
                     "def load_vault(v):\n    raise RuntimeError('kaputt')\n")
        self.write({NOTIZ: FM + "Kappa.\n"})
        env = dict(os.environ, CLAUDE_SKILLS_EINSTELLUNGEN=self.einst, AUTO_LINK_SPERRE=self.sperre,
                   AUTO_LINK_LOG=self.log, VERKNUEPFEN_DIR=fake)
        r = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(
            {"tool_input": {"file_path": os.path.join(self.vault, NOTIZ)}}), text=True, env=env,
            capture_output=True, timeout=60)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        with open(self.log, encoding="utf-8") as fh:
            self.assertIn("RuntimeError", fh.read())
        self.assertEqual(self.read(NOTIZ), FM + "Kappa.\n")

    def test_logzeile_bei_aenderung(self):
        self.write({NOTIZ: FM + "Kappa.\n"})
        self.lauf()
        with open(self.log, encoding="utf-8") as fh:
            zeilen = fh.read().splitlines()
        self.assertEqual(len(zeilen), 1)
        self.assertIn(NOTIZ, zeilen[0])
        self.lauf()  # keine Aenderung: keine weitere Zeile
        with open(self.log, encoding="utf-8") as fh:
            self.assertEqual(len(fh.read().splitlines()), 1)

    def test_schreibfehler_ins_log_nicht_nach_stderr(self):
        p = os.path.join(self.vault, NOTIZ)
        self.write({NOTIZ: FM + "Kappa.\n"})
        os.chmod(p, 0o444)
        self.addCleanup(os.chmod, p, 0o644)
        self.lauf()
        self.assertEqual(self.read(NOTIZ), FM + "Kappa.\n")
        self.assertFalse(os.path.exists(self.sperre))  # nicht geschrieben: Zustand unveraendert
        with open(self.log, encoding="utf-8") as fh:
            self.assertIn("nicht geschrieben", fh.read())


class Parallel(HookBasis):
    """Aus den Gegentests des Abschlussreviews: Mehrere Hook-Laeufe gleichzeitig auf verschiedenen
    Notizen, jeder Eintrag muss im Zustand stehen (Fix-Welle 1)."""

    def parallel(self, rels):
        groesse = "Fuelltext ohne Namen. " * 20000   # ~440 KB, verlaengert das Fenster wie grosse Vault-Notizen
        self.write({r: FM + groesse + "\nKappa am Ende.\n" for r in rels})
        env = {k: v for k, v in os.environ.items() if k != "VERKNUEPFEN_TEST"}
        env.update(CLAUDE_SKILLS_EINSTELLUNGEN=self.einst, AUTO_LINK_SPERRE=self.sperre,
                   AUTO_LINK_LOG=self.log, VERKNUEPFEN_DIR=SKILL)
        procs = [subprocess.Popen([sys.executable, "-I", "-B", HOOK], stdin=subprocess.PIPE, text=True,
                                  env=env) for _ in rels]
        for p, r in zip(procs, rels):
            p.stdin.write(json.dumps({"tool_input": {"file_path": os.path.join(self.vault, r)}}))
            p.stdin.close()
        for p in procs:
            self.assertEqual(p.wait(timeout=120), 0)

    def test_parallele_laeufe_verlieren_keinen_eintrag(self):
        rels = ["03 Bereiche/Notizen/P%02d.md" % i for i in range(12)]
        self.parallel(rels)
        verlinkt = [r for r in rels if "[[Kappa]]" in self.read(r)]
        im_zustand = [r for r in rels if KAPPA in self.state()["notes"].get(r, {}).get("gesetzt", [])]
        self.assertEqual(len(verlinkt), 12)
        self.assertEqual(sorted(im_zustand), sorted(verlinkt))

    def test_entfernter_link_kommt_nach_parallellauf_nicht_zurueck(self):
        rels = ["03 Bereiche/Notizen/Q%02d.md" % i for i in range(12)]
        self.parallel(rels)
        rueck = 0
        for r in rels:                        # Nutzer entfernt den Link in Obsidian (kein Hook) ...
            self.write({r: self.read(r).replace("[[Kappa]]", "Kappa")})
            self.lauf(r)                      # ... naechster Claude-Edit loest den Hook aus
            rueck += "[[Kappa]]" in self.read(r)
        self.assertEqual(rueck, 0)


class FenceDivergenz(HookBasis):
    """Aus den Gegentests des Abschlussreviews: mask() schliesst den Block an der Fence in Spalte 0,
    strip_code (note_links) oeffnet dort einen. Ein Link dort gilt beim naechsten Lauf als entfernt."""

    TEXT = FM + "- Liste\n    ```python\n    x = 1\n```\nText mit Kappa danach.\n"

    def test_nie_entfernter_link_wird_nicht_gesperrt(self):
        self.write({NOTIZ: self.TEXT})
        self.lauf()
        nach1 = self.read(NOTIZ)
        # Angepasst (Fix-Welle 3): Der Gegentest verlangte hier "[[Kappa]]" in nach1; die vorgegebene
        # Loesung verwirft Links, die note_links nicht sieht, also bleibt die Notiz unveraendert.
        self.assertEqual(nach1, self.TEXT)
        self.lauf()                                # Lauf 2, niemand hat etwas entfernt
        self.assertEqual(self.read(NOTIZ), nach1)
        st = self.state() if os.path.exists(self.sperre) else {"notes": {}}
        self.assertNotIn(KAPPA, st["notes"].get(NOTIZ, {}).get("gesperrt", []))


class HookZeilenenden(HookBasis):
    def test_crlf_notiz_wird_geschrieben(self):
        p = os.path.join(self.vault, NOTIZ)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(b"---\r\ntags: [test]\r\n---\r\nKappa hier.\r\n")
        self.lauf()
        with open(p, "rb") as fh:
            self.assertEqual(fh.read(), b"---\r\ntags: [test]\r\n---\r\n[[Kappa]] hier.\r\n")
        self.lauf()   # zweiter Lauf: nichts zu tun, keine Meldung
        with open(p, "rb") as fh:
            self.assertEqual(fh.read(), b"---\r\ntags: [test]\r\n---\r\n[[Kappa]] hier.\r\n")
        with open(self.log, encoding="utf-8") as fh:
            log = fh.read()
        self.assertNotIn("Fehler", log)
        self.assertEqual(self.state()["notes"][NOTIZ], {"gesetzt": [KAPPA], "gesperrt": []})


class SperreCli(unittest.TestCase):
    """CLI link nutzt die Sperrliste (Gegentests aus dem Review, I1)."""

    def setUp(self):
        self.old = {k: os.environ.get(k) for k in ("VERKNUEPFEN_TEST", "AUTO_LINK_SPERRE")}
        self.d = tempfile.mkdtemp(prefix="cli-test-")
        self.addCleanup(shutil.rmtree, self.d)
        self.v = os.path.join(self.d, "vault")
        self.s = os.path.join(self.d, "sperre.json")
        os.environ["VERKNUEPFEN_TEST"] = "1"
        os.environ["AUTO_LINK_SPERRE"] = self.s
        self.addCleanup(self.restore)
        self.w(KAPPA, ent("werkzeug"))

    def restore(self):
        for k, x in self.old.items():
            if x is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = x

    def w(self, rel, t):
        p = os.path.join(self.v, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(t)

    def r(self, rel):
        with open(os.path.join(self.v, rel), encoding="utf-8") as fh:
            return fh.read()

    def link(self, *extra):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            vk.main(["link", "--vault", self.v, *extra, os.path.join(self.v, NOTIZ)])

    def test_cli_entfernter_link_bleibt_weg(self):
        self.w(NOTIZ, FM + "Kappa hier.\n")
        self.link()
        self.assertEqual(self.r(NOTIZ), FM + "[[Kappa]] hier.\n")
        self.w(NOTIZ, FM + "Kappa hier.\n")
        self.link()
        self.assertEqual(self.r(NOTIZ), FM + "Kappa hier.\n")
        with open(self.s, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["notes"][NOTIZ]["gesperrt"], [KAPPA])

    def test_cli_dry_run_schreibt_keinen_zustand(self):
        self.w(NOTIZ, FM + "Kappa hier.\n")
        st = {"version": 1, "notes": {NOTIZ: {"gesetzt": [KAPPA], "gesperrt": []}}}
        with open(self.s, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        self.link("--dry-run")
        with open(self.s, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), st)

    def test_dry_run_legt_keinen_erstkontakt_an(self):
        self.w(NOTIZ, FM + "Kappa und [[Rho GmbH]].\n")
        self.w(RHO, ent("firma"))
        self.link("--dry-run")
        self.assertFalse(os.path.exists(self.s))


class SperreKern(unittest.TestCase):
    def test_pruefen_und_merken(self):
        s = {"version": 1, "notes": {}}
        self.assertEqual(vk.sperre_pruefen(s, "a.md", set()), set())
        vk.sperre_merken(s, "a.md", ["x.md", "y.md"])
        vk.sperre_merken(s, "a.md", ["x.md"])
        self.assertEqual(s["notes"]["a.md"]["gesetzt"], ["x.md", "y.md"])
        self.assertEqual(vk.sperre_pruefen(s, "a.md", {"x.md"}), {"y.md"})
        self.assertEqual(s["notes"]["a.md"]["gesetzt"], ["x.md"])
        self.assertEqual(vk.sperre_pruefen(s, "a.md", set()), {"x.md", "y.md"})

    def test_laden_fehlertolerant_und_atomar(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        p = os.path.join(d, "s.json")
        self.assertEqual(vk.sperre_load(p), {"version": 1, "notes": {}})
        with open(p, "w") as fh:
            fh.write('{"notes": []}')
        self.assertEqual(vk.sperre_load(p), {"version": 1, "notes": {}})
        st = {"version": 1, "notes": {"a.md": {"gesetzt": ["x"], "gesperrt": []}}}
        self.assertTrue(vk.sperre_save(st, p))
        self.assertEqual(vk.sperre_load(p), st)
        self.assertEqual(os.listdir(d), ["s.json"])

    def test_zurueck_setzt_nur_eigenen_eintrag(self):
        """Fix-Welle 1: Scheitert write_note, kommt nur der Eintrag der eigenen Notiz zurueck; was
        inzwischen fuer andere Notizen im Zustand steht, bleibt."""
        from unittest import mock
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        vault, p = os.path.join(d, "vault"), os.path.join(d, "s.json")
        for rel, t in ((KAPPA, ent("werkzeug")), (NOTIZ, FM + "Kappa hier.\n")):
            os.makedirs(os.path.dirname(os.path.join(vault, rel)), exist_ok=True)
            with open(os.path.join(vault, rel), "w", encoding="utf-8") as fh:
                fh.write(t)
        alt = {"version": 1, "notes": {"x.md": {"gesetzt": ["a.md"], "gesperrt": []}}}
        vk.sperre_save(alt, p)
        anderer = {"gesetzt": ["b.md"], "gesperrt": []}

        def scheitert(*_a):
            st = vk.sperre_load(p)
            st["notes"]["y.md"] = anderer
            vk.sperre_save(st, p)
            return False

        v = vk.load_vault(vault)
        state = vk.sperre_load(p)
        with mock.patch.object(vk, "write_note", side_effect=scheitert):
            ok, _ch, fehler = vk.link_and_record(v, NOTIZ, state, p, False)
        self.assertFalse(ok)
        self.assertEqual(fehler, "nicht geschrieben")
        self.assertEqual(vk.sperre_load(p)["notes"], {"x.md": alt["notes"]["x.md"], "y.md": anderer})


if __name__ == "__main__":
    unittest.main()
