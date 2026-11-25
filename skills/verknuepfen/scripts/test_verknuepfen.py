"""Tests fuer verknuepfen.py. Jeder Test arbeitet auf einem Wegwerf-Vault in tempfile.

    python3 -I -m unittest discover -s ~/.claude/skills/verknuepfen/scripts
"""
import atexit
import contextlib
import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
from unittest import mock

# Vorspann VOR dem Import: HOME und Einstellungsdatei zeigen in einen Wegwerf-Ordner, damit weder
# ein Test noch eine Mutation die echte Konfiguration oder den echten Vault liest oder beschreibt.
# Subprozesse erben os.environ und damit diese Werte.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="verknuepfen-home-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import verknuepfen as vk  # noqa: E402
import vault_lint as vl  # noqa: E402
import nachbarn as nb  # noqa: E402

TESTDATEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdaten")
ENT = "04 Ressourcen/Entitäten"
NB = "03 Bereiche/Notizen/"
KAPPA = ENT + "/Kappa.md"
RHO = ENT + "/Rho GmbH.md"
SIGMA = ENT + "/Sigma Müller.md"
OMEGA = "02 Projekte/Omega/Omega - PMO HUB.md"
NOTIZ = "03 Bereiche/Notizen/Test.md"
FM = "---\ntags: [test]\n---\n"
DIENST = "02 Projekte/Dienst"


@contextlib.contextmanager
def mit_einstellungen(**werte):
    """Temp-Einstellungsdatei mit diesen Werten, per CLAUDE_SKILLS_EINSTELLUNGEN aktiv."""
    d = tempfile.mkdtemp(prefix="verknuepfen-einst-")
    try:
        pfad = os.path.join(d, "einstellungen.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(werte, fh)
        with mock.patch.dict(os.environ, {"CLAUDE_SKILLS_EINSTELLUNGEN": pfad}):
            yield pfad
    finally:
        shutil.rmtree(d, ignore_errors=True)


def setUpModule():
    os.environ["VERKNUEPFEN_TEST"] = "1"
    # Die Tests lesen und schreiben nie die echte Zustandsdatei (Sperrliste).
    global _SPERRE_DIR
    _SPERRE_DIR = tempfile.mkdtemp(prefix="verknuepfen-sperre-")
    os.environ["AUTO_LINK_SPERRE"] = os.path.join(_SPERRE_DIR, "sperre.json")


def tearDownModule():
    shutil.rmtree(_SPERRE_DIR, ignore_errors=True)
    os.environ.pop("AUTO_LINK_SPERRE", None)


def ent(typ, aliases="[]"):
    return f"---\ntags: [entitaet]\ntype: {typ}\naliases: {aliases}\n---\n# Notiz\n"


BASIS = {
    KAPPA: ent("werkzeug", '["Kappa Tool"]'),
    RHO: ent("firma", "[Rho]"),
    SIGMA: ent("person"),
    OMEGA: ent("projekt"),
}


class Basis(unittest.TestCase):
    def setUp(self):
        # Je Test eine leere Zustandsdatei (Sperrliste), sonst wirken Notizen gleichen Namens aufeinander.
        try:
            os.unlink(os.environ["AUTO_LINK_SPERRE"])
        except OSError:
            pass

    def tmp(self):
        d = tempfile.mkdtemp(prefix="verknuepfen-test-")
        self.addCleanup(shutil.rmtree, d)
        return d

    def bau(self, files):
        d = self.tmp()
        for rel, content in {**BASIS, **files}.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(content)
        return d

    def link(self, body, rel=NOTIZ, extra=None):
        """Verlinkt eine Notiz mit Inhalt body; gibt (neuer Text oder None, Aenderungen)."""
        d = self.bau({rel: body, **(extra or {})})
        v = vk.load_vault(d)
        return vk.link_note(v, rel, set())

    def kopie(self, name):
        d = self.tmp()
        ziel = os.path.join(d, "vault")
        shutil.copytree(os.path.join(TESTDATEN, name), ziel)
        return ziel


class Link(Basis):
    # --- Spec-Faelle ---
    def test_alias_wird_link_mit_anzeigetext(self):
        new, ch = self.link(FM + "Wir setzen das Kappa Tool ein.\n")
        self.assertEqual(new, FM + "Wir setzen das [[Kappa|Kappa Tool]] ein.\n")
        self.assertEqual(ch, [{"entity": KAPPA, "name": "Kappa Tool", "line": 4, "link": "[[Kappa|Kappa Tool]]"}])

    def test_eingerueckter_codeblock_bleibt(self):
        body = FM + "Beispiel:\n\n    kappa --version\n"
        self.assertEqual(self.link(body), (None, []))

    def test_allgemeines_wort_bleibt(self):
        body = FM + "Ein Werkzeug, eine Firma, ein Projekt und eine Person.\n"
        self.assertEqual(self.link(body), (None, []))

    # --- Linkregeln ---
    def test_erste_fundstelle_ueber_alle_namen(self):
        new, ch = self.link(FM + "Erst Rho, dann Rho GmbH.\n")
        self.assertEqual(new, FM + "Erst [[Rho GmbH|Rho]], dann Rho GmbH.\n")

    def test_laengerer_name_bei_gleicher_position(self):
        new, ch = self.link(FM + "Die Rho GmbH liefert.\n")
        self.assertEqual(new, FM + "Die [[Rho GmbH]] liefert.\n")
        self.assertEqual(ch[0]["name"], "Rho GmbH")

    def test_nur_ein_link_je_entitaet(self):
        new, ch = self.link(FM + "Kappa hier.\nKappa dort.\n")
        self.assertEqual(new, FM + "[[Kappa]] hier.\nKappa dort.\n")

    def test_schon_verlinkt_wikilink(self):
        self.assertEqual(self.link(FM + "[[Kappa]] und Kappa.\n"), (None, []))

    def test_schon_verlinkt_markdownlink(self):
        self.assertEqual(self.link(FM + "[Werkzeug](../../04%20Ressourcen/Entitäten/Kappa.md) und Kappa.\n"),
                         (None, []))

    def test_schon_verlinkt_hub_alias(self):
        self.assertEqual(self.link(FM + "[[Omega - PMO HUB|Omega]] und Omega.\n"), (None, []))

    def test_kein_selbstlink(self):
        d = self.bau({})
        with open(os.path.join(d, KAPPA), "a", encoding="utf-8") as fh:
            fh.write("Kappa ist toll.\n")
        self.assertEqual(vk.link_note(vk.load_vault(d), KAPPA, set()), (None, []))

    def test_bindestrich_und_endung(self):
        self.assertEqual(self.link(FM + "Kappa-Admin, Admin-Kappa und Kappas.\n"), (None, []))

    def test_grossschreibung(self):
        new, _ = self.link(FM + "KAPPA laeuft.\n")
        self.assertEqual(new, FM + "[[Kappa|KAPPA]] laeuft.\n")

    def test_nfd_text_wird_verlinkt(self):
        body = unicodedata.normalize("NFD", FM + "Gespräch mit Sigma Müller.\n")
        new, ch = self.link(body)
        self.assertEqual(new, FM + "Gespräch mit [[Sigma Müller]].\n")
        self.assertEqual(ch[0]["line"], 4)

    def test_umlaut_und_tab_vor_fundstelle(self):
        body = unicodedata.normalize("NFD", FM + "Über Äpfel\tund Öl: Kappa.\n")
        new, _ = self.link(body)
        self.assertEqual(new, FM + "Über Äpfel\tund Öl: [[Kappa]].\n")

    def test_tabelle_titel_exakt(self):
        new, _ = self.link(FM + "| Werkzeug | Wert |\n|---|---|\n| Kappa | 1 |\n")
        self.assertEqual(new, FM + "| Werkzeug | Wert |\n|---|---|\n| [[Kappa]] | 1 |\n")

    def test_tabelle_alias_noetig_kein_link(self):
        self.assertEqual(self.link(FM + "| Werkzeug |\n|---|\n| Kappa Tool |\n"), (None, []))

    def test_tabelle_eingerueckt_alias_noetig(self):
        self.assertEqual(self.link(FM + "  | KAPPA |\n"), (None, []))

    def test_person_im_dienstlichen_nie(self):
        rel = DIENST + "/Notiz.md"
        with mit_einstellungen(dienst_ordner=DIENST):
            new, ch = self.link(FM + "Sigma Müller nutzt Kappa.\n", rel=rel)
        self.assertEqual(new, FM + "Sigma Müller nutzt [[Kappa]].\n")
        self.assertEqual([c["entity"] for c in ch], [KAPPA])

    def test_person_ausserhalb_dienstlich(self):
        new, _ = self.link(FM + "Sigma Müller nutzt Kappa.\n")
        self.assertEqual(new, FM + "[[Sigma Müller]] nutzt [[Kappa]].\n")

    def test_titel_kollidiert_ziel_als_pfad(self):
        new, ch = self.link(FM + "Kappa hilft.\n", extra={"03 Bereiche/Notizen/Kappa.md": FM + "Keine Entitaet.\n"})
        self.assertEqual(new, FM + "[[04 Ressourcen/Entitäten/Kappa|Kappa]] hilft.\n")
        self.assertEqual(ch[0]["link"], "[[04 Ressourcen/Entitäten/Kappa|Kappa]]")

    def test_mehrere_entitaeten_eine_zeile_positionen(self):
        new, ch = self.link(FM + "Kappa, Rho und Omega.\n")
        self.assertEqual(new, FM + "[[Kappa]], [[Rho GmbH|Rho]] und [[Omega - PMO HUB|Omega]].\n")
        self.assertEqual(sorted(c["entity"] for c in ch), sorted([KAPPA, RHO, OMEGA]))

    def test_ueberlappung_laengere_entitaet_gewinnt(self):
        new, ch = self.link(FM + "Das Omega Kappa Team, danach Kappa.\n",
                            extra={ENT + "/Omega Kappa.md": ent("firma")})
        # Erste Fundstelle von Kappa und Omega liegt im laengeren Namen: beide entfallen (ASSUMPTION im Code)
        self.assertEqual(new, FM + "Das [[Omega Kappa]] Team, danach Kappa.\n")
        self.assertEqual([c["entity"] for c in ch], [ENT + "/Omega Kappa.md"])

    def test_sperre_wird_beachtet(self):
        d = self.bau({NOTIZ: FM + "Kappa und Rho.\n"})
        new, ch = vk.link_note(vk.load_vault(d), NOTIZ, {KAPPA})
        self.assertEqual(new, FM + "Kappa und [[Rho GmbH|Rho]].\n")

    def test_keine_quelle(self):
        for rel in ("06 Archiv/Alt.md", "Briefings/B.md", "memory/m.md", "03 Bereiche/_Vorlage.md", "Index.md"):
            with self.subTest(rel=rel):
                self.assertEqual(self.link(FM + "Kappa.\n", rel=rel), (None, []))

    def test_is_source(self):
        self.assertTrue(vk.is_source("03 Bereiche/A/Notiz.md"))
        for rel in ("06 Archiv/A.md", "Briefings/A.md", "memory/a.md", "03 Bereiche/_x.md",
                    "Index.md", "Lint-Reports/r.md", "07 Anhaenge/a.md", "03 Bereiche/bild.png"):
            self.assertFalse(vk.is_source(rel), rel)

    def test_mask_gleiche_laenge_und_umbrueche(self):
        t = FM + "a `b` c\n\n    code\n> zitat\n%% k\nk %%\n<!-- h -->\nx [[y]] #tag a/b kappa.io\n"
        m = vk.mask(t)
        self.assertEqual(len(m), len(t))
        self.assertEqual([i for i, c in enumerate(m) if c == "\n"], [i for i, c in enumerate(t) if c == "\n"])
        self.assertEqual(m.split("\n")[3], "a     c")
        self.assertEqual(m.split("\n")[:3], ["   ", " " * 12, "   "])
        self.assertEqual(set("".join(m.split("\n")[5:-2])), {" "})
        self.assertEqual(set(m.split("\n")[-2]), {"x", " "})

    def test_linked_targets(self):
        res = vl.Resolver([NOTIZ, KAPPA, RHO])
        self.assertEqual(vk.linked_targets(NOTIZ, "[[Kappa]] [r](../../04%20Ressourcen/Entitäten/Rho%20GmbH.md)\n", res),
                         {KAPPA, RHO})

    # --- Zusammenspiel mit Lint ---
    def test_lint_l1_danach_nur_geschuetzte_funde(self):
        d = self.kopie("link")
        heute = datetime.date(2026, 11, 16)
        vorher = vl.analyse(d, heute)["graph"]["L1"]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(vk.main(["link", "--vault", d, "--alle"]), 0)
        nachher = vl.analyse(d, heute)["graph"]["L1"]
        self.assertEqual(len(vorher), 12)
        # Codeblock: eingerueckter Code; Geschuetzt: Zitat, Kommentar, Hashtag, Pfad; Netz: Domain, HTML-Kommentar
        self.assertEqual(sorted((vl.stem(f["note"]), vl.stem(f["entity"])) for f in nachher), [
            ("Codeblock", "Kappa"),
            ("Geschuetzt", "Kappa"), ("Geschuetzt", "Omega - PMO HUB"),
            ("Geschuetzt", "Rho GmbH"), ("Geschuetzt", "Sigma Müller"),
            ("Netz", "Kappa"), ("Netz", "Rho GmbH"),
        ])
        self.assertIn("5 Links in 2 Notizen", out.getvalue())

    # --- write_note ---
    def test_write_note_zwischendurch_geaendert(self):
        d = self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("neu von Hand\n")
        self.assertFalse(vk.write_note(p, "alt\n", "verlinkt\n"))
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "neu von Hand\n")

    def test_write_note_schreibt(self):
        d = self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("alt\n")
        self.assertTrue(vk.write_note(p, "alt\n", "neu\n"))
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "neu\n")
        self.assertEqual(sorted(os.listdir(d)), ["n.md"])

    def test_testsperre_echter_vault(self):
        echt = self.tmp()
        with mit_einstellungen(vault=echt):
            self.assertTrue(vk.write_locked(os.path.join(echt, "03 Bereiche", "x.md")))
            self.assertTrue(vk.write_locked(echt))
            self.assertFalse(vk.write_locked(os.path.join(self.tmp(), "x.md")))
            self.assertFalse(vk.write_locked(echt + "-Nachbar/x.md"))
            with mock.patch.dict(os.environ, {"VERKNUEPFEN_TEST": "0"}):
                self.assertFalse(vk.write_locked(os.path.join(echt, "x.md")))

    def test_testsperre_vault_des_echten_nutzers(self):
        """Umgebogenes HOME und CLAUDE_SKILLS_EINSTELLUNGEN geben den Vault aus der Datei des
        angemeldeten Nutzers nicht frei; ~ zaehlt dort ab dessen Home."""
        home = self.tmp()
        os.makedirs(os.path.join(home, ".config", "claude-skills"))
        with open(os.path.join(home, ".config", "claude-skills", "einstellungen.json"), "w") as fh:
            json.dump({"vault": "~/Mein Vault"}, fh)
        with mock.patch.object(vk, "_nutzer_home", return_value=home):
            self.assertTrue(vk.write_locked(os.path.join(home, "Mein Vault", "a.md")))
            self.assertFalse(vk.write_locked(os.path.join(home, "Anderes", "a.md")))
            with open(os.path.join(home, ".config", "claude-skills", "einstellungen.json"), "w") as fh:
                fh.write("{kaputt")
            self.assertTrue(vk.write_locked(os.path.join(self.tmp(), "a.md")))  # unlesbar: alles gesperrt

    def test_write_note_beachtet_testsperre(self):
        d = self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("alt\n")
        with mit_einstellungen(vault=d), mock.patch.dict(os.environ, {"VERKNUEPFEN_TEST": "1"}):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(vk.write_note(p, "alt\n", "neu\n"))
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "alt\n")

    def test_write_note_behaelt_inode(self):
        d = self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("alter, laengerer Inhalt\n")
        ino = os.stat(p).st_ino
        t = self.tmp()
        with mock.patch.object(tempfile, "tempdir", t):
            self.assertTrue(vk.write_note(p, "alter, laengerer Inhalt\n", "neu\n"))
        self.assertEqual(os.listdir(t), [], "Sicherungskopie nach Erfolg nicht entfernt")
        self.assertEqual(os.stat(p).st_ino, ino)
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "neu\n")

    def test_keine_quelle_kontext_und_wurzeldateien(self):
        for rel in ["00 Kontext/Claude.MD/History/2026-10-02.md", "00 Kontext/Claude.MD/Changelog.md",
                    *sorted(vl.ROOT_SYSTEM_FILES)]:
            self.assertFalse(vk.is_source(rel), rel)
        self.assertTrue(vk.is_source("00 Kontext/Schreibstil.md"))
        self.assertTrue(vk.is_source("Notiz.md"))
        self.assertEqual(self.link(FM + "Kappa.\n", rel="CLAUDE.md"), (None, []))

    def test_pfad_ohne_endung_nur_token(self):
        new, _ = self.link(FM + "Ordner a/b Kappa hier.\n")
        self.assertEqual(new, FM + "Ordner a/b [[Kappa]] hier.\n")

    def test_write_note_schreibgeschuetzt_liefert_false(self):
        d = self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("alt\n")
        os.chmod(p, 0o444)
        self.addCleanup(os.chmod, p, 0o644)
        self.assertFalse(vk.write_note(p, "alt\n", "neu\n"))
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "alt\n")

    def test_cli_schreibgeschuetzt_nicht_geschrieben_und_weiter(self):
        zwei = "03 Bereiche/Notizen/Zwei.md"
        d = self.bau({NOTIZ: FM + "Kappa\n", zwei: FM + "Rho GmbH\n"})
        p = os.path.join(d, NOTIZ)
        os.chmod(p, 0o444)
        self.addCleanup(os.chmod, p, 0o644)
        js = os.path.join(self.tmp(), "out.json")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(vk.main(["link", "--vault", d, "--json", js, "--alle"]), 0)
        self.assertEqual(out.getvalue().splitlines()[-1], "1 Links in 1 Notizen")
        self.assertIn("1 Notizen nicht geschrieben", err.getvalue())
        with open(js, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["not_written"], [NOTIZ])
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), FM + "Kappa\n")
        with open(os.path.join(d, zwei), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), FM + "[[Rho GmbH]]\n")

    P4 = r"""
import os, sys, signal, resource
sys.path.insert(0, sys.argv[1])
import verknuepfen as vk
p = os.path.join(sys.argv[2], "n.md")
old = "Vorne Kappa und ein wichtiger Schluss.\n"
new = "Vorne [[Kappa]] und ein wichtiger Schluss.\n"
with open(p, "w", encoding="utf-8") as fh:
    fh.write(old)
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (len(old.encode()), resource.RLIM_INFINITY))
r = vk.write_note(p, old, new)
resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
print(r)
print(open(p, encoding="utf-8").read() == old)
"""

    def test_write_note_schreibfehler_laesst_datei_unveraendert(self):
        # Probe P4 aus dem Re-Review: Dateigroessenlimit auf alter Laenge spielt vollen Datentraeger nach
        d, t = self.tmp(), self.tmp()
        env = dict(os.environ, TMPDIR=t, VERKNUEPFEN_TEST="1")
        r = subprocess.run([sys.executable, "-I", "-c", self.P4, os.path.dirname(os.path.abspath(vk.__file__)), d],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.stdout.splitlines(), ["False", "True"], r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertEqual(os.listdir(t), [], "Sicherung nach gelungenem Zurueckschreiben nicht entfernt")

    def test_write_note_zurueckschreiben_scheitert_sicherung_bleibt(self):
        d, t = self.tmp(), self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("alt Kappa\n")

        def kaputt(fh, data):
            raise OSError(5, "Eingabe-/Ausgabefehler")
        err = io.StringIO()
        with mock.patch.object(vk, "_write_all", kaputt), mock.patch.object(tempfile, "tempdir", t), \
                contextlib.redirect_stderr(err):
            self.assertFalse(vk.write_note(p, "alt Kappa\n", "alt [[Kappa]]\n"))
        sicherungen = os.listdir(t)
        self.assertEqual(len(sicherungen), 1)
        bak = os.path.join(t, sicherungen[0])
        with open(bak, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "alt Kappa\n")
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1)
        self.assertIn(bak, err.getvalue())

    def test_cli_eine_stderr_zeile_je_notiz(self):
        d = self.bau({NOTIZ: FM + "Kappa\n"})
        p = os.path.join(d, NOTIZ)
        os.chmod(p, 0o444)
        self.addCleanup(os.chmod, p, 0o644)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            vk.main(["link", "--vault", d, NOTIZ])
        zeilen = err.getvalue().strip().splitlines()
        self.assertEqual(len([z for z in zeilen if NOTIZ in z]), 1, zeilen)

    # --- CLI ---
    def test_cli_ausgabe_und_dry_run(self):
        d = self.bau({NOTIZ: FM + "Kappa\n\nund Rho.\n"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(vk.main(["link", "--vault", d, "--dry-run", os.path.join(d, NOTIZ)]), 0)
        self.assertEqual(out.getvalue().splitlines(), [
            NOTIZ + ":4 [[Kappa]]", NOTIZ + ":6 [[Rho GmbH|Rho]]", "2 Links in 1 Notizen"])
        with open(os.path.join(d, NOTIZ), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), FM + "Kappa\n\nund Rho.\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vk.main(["link", "--vault", d, NOTIZ]), 0)
        with open(os.path.join(d, NOTIZ), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), FM + "[[Kappa]]\n\nund [[Rho GmbH|Rho]].\n")


class RelPfad(Basis):
    """_rel: relative Pfade werden normalisiert (./, //, /./, ..), Ausbruch aus dem Vault bleibt abgelehnt."""

    def vault(self, extra=None):
        files = {NOTIZ: FM + "Kappa\n", NB + "A.md": "Tau GmbH, Pi GmbH.\n", NB + "B.md": "Tau GmbH.\n"}
        files.update(extra or {})
        d = self.bau(files)
        return d, vk.load_vault(d)

    def test_rel_normalisiert_relative_pfade(self):
        _, v = self.vault()
        for roh in ("./" + NOTIZ, "03 Bereiche/./Notizen/Test.md", "03 Bereiche//Notizen/Test.md",
                    "03 Bereiche/x/../Notizen/Test.md", "././" + NOTIZ, NOTIZ):
            with self.subTest(roh):
                self.assertEqual(vk._rel(v, roh), NOTIZ)

    def test_rel_ausbruch_bleibt_abgelehnt(self):
        d, v = self.vault()
        for roh in ("../" + NOTIZ, "03 Bereiche/../../" + NOTIZ, "./../" + NOTIZ,
                    "../" + os.path.basename(d) + "/" + NOTIZ):
            with self.subTest(roh):
                self.assertIsNone(vk._rel(v, roh))

    def test_rel_absolut_und_unbekannt_wie_vorher(self):
        d, v = self.vault()
        self.assertEqual(vk._rel(v, os.path.join(d, NOTIZ)), NOTIZ)
        self.assertIsNone(vk._rel(v, "/gibt/es/nicht.md"))
        self.assertIsNone(vk._rel(v, "gibt/es/nicht.md"))
        self.assertIsNone(vk._rel(v, "./gibt/es/nicht.md"))

    def test_rel_nfd_mit_punkt_schraegstrich(self):
        rel = unicodedata.normalize("NFC", "03 Bereiche/Notizen/Bär.md")
        _, v = self.vault({rel: "x\n"})
        self.assertEqual(vk._rel(v, "./" + unicodedata.normalize("NFD", rel)), rel)

    def test_rel_relativ_gilt_zum_vault_nicht_zum_arbeitsverzeichnis(self):
        d, v = self.vault()
        alt = os.getcwd()
        os.chdir(os.path.join(d, "03 Bereiche"))
        self.addCleanup(os.chdir, alt)
        self.assertEqual(vk._rel(v, "./" + NOTIZ), NOTIZ)
        self.assertIsNone(vk._rel(v, "./Notizen/Test.md"))

    def test_cli_link_mit_punkt_schraegstrich(self):
        d, _ = self.vault()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = vk.main(["link", "--vault", d, "--dry-run", "./" + NOTIZ])
        self.assertEqual(code, 0, err.getvalue())

    def test_cli_kandidaten_mit_punkt_schraegstrich(self):
        d, _ = self.vault()
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = vk.main(["kandidaten", "--vault", d, "--notiz", "./" + NB + "B.md"])
        self.assertEqual(code, 0, err.getvalue())

    def test_cli_ausbruch_wird_gemeldet(self):
        d, _ = self.vault()
        for argv in (["link", "--vault", d, "--dry-run", "../" + NOTIZ],
                     ["kandidaten", "--vault", d, "--notiz", "../" + NOTIZ]):
            with self.subTest(argv[0]):
                err = io.StringIO()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    self.assertEqual(vk.main(argv), 1)
                self.assertIn("Notiz nicht im Vault", err.getvalue())


# --- Je Schutzregel ein Fall: geschuetzte Erwaehnung bleibt, die zweite, freie wird verlinkt ---
SCHUTZ = {
    "frontmatter": ("---\ntags: [test]\nbeschreibung: Kappa\n---\n", ""),
    "codeblock_backticks": (FM, "```\nKappa\n```\n"),
    "codeblock_tilden": (FM, "~~~\nKappa\n~~~\n"),
    "eingerueckter_code_leerzeichen": (FM, "Text\n\n    Kappa\n"),
    "eingerueckter_code_tab": (FM, "Text\n\n\tKappa\n"),
    "zitat": (FM, "> Kappa sagt\n"),
    "callout": (FM, "> [!note] Hinweis\n> Kappa hier\n"),
    "inline_code": (FM, "Befehl `Kappa` hier\n"),
    "wikilink": (FM, "Siehe [[Rho GmbH|Kappa]] hier\n"),
    "markdownlink": (FM, "Siehe [Kappa](Ziel) hier\n"),
    "url": (FM, "Siehe <http://localhost:8080?q=Kappa> hier\n"),
    "hashtag": (FM, "Stichwort #Kappa hier\n"),
    "pfad": (FM, "Ablage Ordner\\Kappa hier\n"),
    "domain": (FM, "Seite www.kappa-tool.de und kappa.io hier\n"),
    "codeblock_in_liste_tab": (FM, "- Schritt\n\t- Unter\n\t\t```bash\n\t\tkappa deploy\n\t\t```\n"),
    "codeblock_in_liste_leerzeichen": (FM, "- Schritt\n    - Unter\n        ```\n        kappa deploy\n        ```\n"),
    # Proben P1/P2 aus dem Re-Review: eingerueckte Fence-Zeile im Fence schliesst den Block nicht
    "fence_im_fence_markdown": (FM, "```markdown\n- Schritt\n    ```bash\n    kappa deploy\n    ```\n```\n\n"
                                    "Text\n\n```\nkappa run\n```\n"),
    "fence_im_docstring": (FM, '```python\ndef f():\n    """\n    Beispiel:\n    ```\n    Kappa starten\n'
                               '    ```\n    """\n```\n'),
    # Tab zaehlt als 4: Fence mit Tab geoeffnet, mit 6 Leerzeichen geschlossen (6 <= 4 + 3)
    "fence_tab_als_vier": (FM, "- a\n\t```\n\tkappa x\n      ```\n"),
    "ueberschrift": (FM, "## Kappa im Einsatz\n"),
    "ueberschrift_h6": (FM, "###### Kappa\n"),
    "pfad_mit_leerzeichen": (FM, "Datei 03 Bereiche/X/2026-10-15 Omega Kappa Tabelle.md hier\n"),
    "pfad_mit_leerzeichen_klammer": (FM, "(04 Ressourcen/R/2026 Kappa Plan.pdf) hier\n"),
    "referenzlink": (FM, "Siehe [Kappa][1].\n\n[1]: https://beispiel.de\n"),
    "referenzdefinition": (FM, "[kappa]: ziel\n"),
    "fussnote": (FM, "Text[^kappa].\n\n[^kappa]: Anmerkung\n"),
    "obsidian_kommentar": (FM, "%% Kappa\nnoch Kappa %%\n"),
    "html_kommentar": (FM, "<!-- Kappa\n-->\n"),
}


def _schutz_test(kopf, geschuetzt):
    def test(self):
        body = kopf + geschuetzt + "\nFrei: Kappa.\n"
        new, ch = self.link(body)
        self.assertIsNotNone(new, "freie Erwaehnung wurde nicht verlinkt")
        self.assertEqual(new, kopf + geschuetzt + "\nFrei: [[Kappa]].\n")
        self.assertEqual(len(ch), 1)
    return test


for _name, (_kopf, _geschuetzt) in SCHUTZ.items():
    setattr(Link, "test_schutz_" + _name, _schutz_test(_kopf, _geschuetzt))


class NurSichtbareLinks(Basis):
    """Fix-Welle 3: Ein Link, den note_links nicht sieht, entfaellt (sonst sperrt ihn der naechste Lauf)."""

    def sichtbar(self, body):
        d = self.bau({NOTIZ: body})
        v = vk.load_vault(d)
        new, changes = vk.link_note(v, NOTIZ, set())
        if new is not None:
            seen = vk.linked_targets(NOTIZ, new, v.resolver)
            for c in changes:
                self.assertIn(c["entity"], seen, new)
        return new, changes

    def test_eckige_klammer_wird_kein_dreifachlink(self):
        new, changes = self.sichtbar(FM + "Siehe [Kappa] hier.\n")
        self.assertNotIn("[[[", new or "")
        self.assertEqual([c["entity"] for c in changes], [])

    def test_html_kommentar_mit_backtick(self):
        new, changes = self.sichtbar(FM + "<!-- ` --> Kappa hier ` x\n")
        self.assertEqual([c["entity"] for c in changes], [])

    def test_fence_divergenz(self):
        new, changes = self.sichtbar(FM + "- Liste\n    ```python\n    x = 1\n```\nText mit Kappa danach.\n")
        self.assertEqual([c["entity"] for c in changes], [])

    def test_sichtbare_entitaet_bleibt_neben_unsichtbarer(self):
        new, changes = self.sichtbar(FM + "Rho und [Kappa] hier.\n")
        self.assertEqual(new, FM + "[[Rho GmbH|Rho]] und [Kappa] hier.\n")
        self.assertEqual([c["entity"] for c in changes], [RHO])


class Zeilenenden(Basis):
    """Fix-Welle 6: CRLF-Notizen werden geschrieben, die Zeilenenden bleiben."""

    def datei(self, raw):
        d = self.tmp()
        p = os.path.join(d, "n.md")
        with open(p, "wb") as fh:
            fh.write(raw)
        return p

    def bytes_(self, p):
        with open(p, "rb") as fh:
            return fh.read()

    def test_crlf_wird_geschrieben_und_bleibt_crlf(self):
        p = self.datei(b"---\r\ntags: [t]\r\n---\r\nKappa hier.\r\n")
        old = vl.read(p)
        self.assertTrue(vk.write_note(p, old, old.replace("Kappa", "[[Kappa]]")))
        self.assertEqual(self.bytes_(p), b"---\r\ntags: [t]\r\n---\r\n[[Kappa]] hier.\r\n")

    def test_gemischte_zeilenenden_bleiben_unberuehrt(self):
        raw = b"a\r\nKappa hier.\n"
        p = self.datei(raw)
        old = vl.read(p)
        self.assertFalse(vk.write_note(p, old, old.replace("Kappa", "[[Kappa]]")))
        self.assertEqual(self.bytes_(p), raw)

    def test_crlf_geaendert_seit_lesen(self):
        p = self.datei(b"anders\r\n")
        self.assertFalse(vk.write_note(p, "alt\n", "neu\n"))
        self.assertEqual(self.bytes_(p), b"anders\r\n")

    def test_crlf_ueber_cli(self):
        d = self.bau({})
        p = os.path.join(d, NOTIZ)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(b"---\r\ntags: [t]\r\n---\r\nKappa hier.\r\n")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(vk.main(["link", "--vault", d, p]), 0)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(self.bytes_(p), b"---\r\ntags: [t]\r\n---\r\n[[Kappa]] hier.\r\n")


class Sperrfrist(Basis):
    """Die Dateisperre wartet hoechstens eine Frist (VERKNUEPFEN_SPERRFRIST), dann Abbruch."""

    def lies(self, d):
        with open(os.path.join(d, NOTIZ), "rb") as fh:
            return fh.read()

    def sperrpfad(self):
        return os.path.join(self.tmp(), "sperre.json")

    @contextlib.contextmanager
    def fremd_gehalten(self, sperre_pfad):
        import fcntl
        fh = open(sperre_pfad + ".lock", "a")
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fh.close()

    def mit_obergrenze(self, fn, grenze=5.0):
        """Fuehrt fn in einem Thread aus; haengt fn, scheitert der Test statt zu blockieren."""
        import threading
        erg = {}
        t = threading.Thread(target=lambda: erg.setdefault("wert", fn()), daemon=True)
        t.start()
        t.join(grenze)
        self.assertFalse(t.is_alive(), "haengt ueber die Obergrenze")
        return erg["wert"]

    def test_belegte_sperre_kehrt_nach_frist_zurueck(self):
        pfad = self.sperrpfad()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.3"}):
            with self.fremd_gehalten(pfad):
                t0 = time.monotonic()
                lk = self.mit_obergrenze(lambda: vk._sperre_lock(pfad))
                dauer = time.monotonic() - t0
        self.assertIs(lk, vk.SPERRE_BELEGT)
        self.assertGreaterEqual(dauer, 0.25)
        self.assertLess(dauer, 3.0)

    def test_belegte_sperre_laesst_notiz_unveraendert(self):
        d = self.bau({NOTIZ: FM + "Wir setzen das Kappa Tool ein.\n"})
        v = vk.load_vault(d)
        vorher = self.lies(d)
        pfad = self.sperrpfad()
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.3"}):
            with self.fremd_gehalten(pfad), contextlib.redirect_stderr(err):
                ok, changes, grund = self.mit_obergrenze(
                    lambda: vk.link_and_record(v, NOTIZ, {}, pfad, False))
        self.assertFalse(ok)
        self.assertTrue(changes)
        self.assertIn("Sperre belegt", grund)
        self.assertNotIn("nicht schreibbar", grund)
        self.assertEqual(self.lies(d), vorher)
        self.assertFalse(os.path.exists(pfad), "Zustandsdatei darf bei Fristablauf nicht entstehen")
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1)
        self.assertIn("Sperre belegt", err.getvalue())

    def test_belegte_sperre_laesst_zustandsdatei_unveraendert(self):
        d = self.bau({NOTIZ: FM + "Wir setzen das Kappa Tool ein.\n"})
        v = vk.load_vault(d)
        pfad = self.sperrpfad()
        roh = b'{"notes":   {}}  \n'
        with open(pfad, "wb") as fh:
            fh.write(roh)
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.3"}):
            with self.fremd_gehalten(pfad), contextlib.redirect_stderr(io.StringIO()):
                self.mit_obergrenze(lambda: vk.link_and_record(v, NOTIZ, {}, pfad, False))
        with open(pfad, "rb") as fh:
            self.assertEqual(fh.read(), roh)

    def test_anderer_oserror_beim_sperren_liefert_none(self):
        import errno
        import fcntl
        pfad = self.sperrpfad()
        geoeffnet = []
        echt_open = open

        def merk_open(*a, **k):
            fh = echt_open(*a, **k)
            geoeffnet.append(fh)
            return fh
        with mock.patch.object(fcntl, "flock", side_effect=OSError(errno.ENOLCK, "keine Sperren")), \
                mock.patch("builtins.open", merk_open):
            lk = vk._sperre_lock(pfad)
        self.assertIsNone(lk)
        self.assertTrue(geoeffnet and all(f.closed for f in geoeffnet))

    def test_eacces_gilt_nicht_als_belegt(self):
        import errno
        import fcntl
        pfad = self.sperrpfad()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.3"}), \
                mock.patch.object(fcntl, "flock", side_effect=PermissionError(errno.EACCES, "verweigert")):
            t0 = time.monotonic()
            lk = vk._sperre_lock(pfad)
            self.assertLess(time.monotonic() - t0, 0.2)
        self.assertIsNone(lk)

    def test_wartepfad_bekommt_sperre_nach_freigabe(self):
        import fcntl
        import threading
        pfad = self.sperrpfad()
        fremd = open(pfad + ".lock", "a")
        fcntl.flock(fremd, fcntl.LOCK_EX)
        timer = threading.Timer(0.2, fremd.close)
        timer.start()
        try:
            t0 = time.monotonic()
            lk = self.mit_obergrenze(lambda: vk._sperre_lock(pfad, 3.0))
            dauer = time.monotonic() - t0
        finally:
            timer.join()
        self.assertIsNot(lk, vk.SPERRE_BELEGT)
        self.assertTrue(hasattr(lk, "close"))
        lk.close()
        self.assertGreaterEqual(dauer, 0.15)
        self.assertLess(dauer, 2.0)

    def test_frist_nach_oben_gekappt(self):
        self.assertEqual(vk.SPERRFRIST_MAX, 12.0)
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "20"}):
            self.assertEqual(vk._sperrfrist(), 12.0)
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "11.5"}):
            self.assertEqual(vk._sperrfrist(), 11.5)

    def test_frist_null_ein_versuch(self):
        pfad = self.sperrpfad()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0"}):
            lk = vk._sperre_lock(pfad)
            self.assertTrue(hasattr(lk, "close"))
            lk.close()
            with self.fremd_gehalten(pfad):
                t0 = time.monotonic()
                lk = self.mit_obergrenze(lambda: vk._sperre_lock(pfad))
                self.assertLess(time.monotonic() - t0, 0.04)
        self.assertIs(lk, vk.SPERRE_BELEGT)

    def test_minus_null_erscheint_als_null(self):
        d = self.bau({NOTIZ: FM + "Wir setzen das Kappa Tool ein.\n"})
        v = vk.load_vault(d)
        pfad = self.sperrpfad()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "-0"}):
            self.assertEqual(str(vk._sperrfrist()), "0.0")
            with self.fremd_gehalten(pfad), contextlib.redirect_stderr(io.StringIO()):
                _ok, _c, grund = self.mit_obergrenze(lambda: vk.link_and_record(v, NOTIZ, {}, pfad, False))
        self.assertIn("Frist 0 s", grund)
        self.assertNotIn("-0", grund)

    def test_kein_versuch_nach_fristablauf(self):
        import errno
        import fcntl
        pfad = self.sperrpfad()
        zeit = [0.0]
        versuche = []

        def flock(*a):
            versuche.append(zeit[0])
            raise BlockingIOError(errno.EAGAIN, "belegt")

        def schlafe(s):
            zeit[0] += s + 1.0  # Schlaf ueberzieht die Frist
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.5"}), \
                mock.patch.object(fcntl, "flock", flock), \
                mock.patch.object(vk.time, "monotonic", lambda: zeit[0]), \
                mock.patch.object(vk.time, "sleep", schlafe):
            lk = vk._sperre_lock(pfad)
        self.assertIs(lk, vk.SPERRE_BELEGT)
        self.assertEqual(len(versuche), 1)

    def test_belegte_sperre_ohne_arbeit_meldet_nichts(self):
        d = self.bau({NOTIZ: FM + "Nichts zu verlinken.\n"})
        v = vk.load_vault(d)
        pfad = self.sperrpfad()
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.3"}):
            with self.fremd_gehalten(pfad):
                erg = self.mit_obergrenze(lambda: vk.link_and_record(v, NOTIZ, {}, pfad, False))
        self.assertEqual(erg, (False, [], None))

    def test_freie_sperre_greift_sofort(self):
        pfad = self.sperrpfad()
        t0 = time.monotonic()
        lk = vk._sperre_lock(pfad)
        dauer = time.monotonic() - t0
        self.assertTrue(hasattr(lk, "close"))
        lk.close()
        self.assertLess(dauer, 0.2)

    def test_ungueltige_frist_nimmt_vorgabe(self):
        for wert in ("abc", "", "-1", "nan", "inf"):
            with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": wert}):
                self.assertEqual(vk._sperrfrist(), vk.SPERRFRIST_VORGABE, wert)
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_SPERRFRIST": "0.5"}):
            self.assertEqual(vk._sperrfrist(), 0.5)
        self.assertEqual(vk.SPERRFRIST_VORGABE, 10.0)


class Dienst(Basis):
    def test_link_text_nutzt_is_dienst(self):
        rel = DIENST + "X/Notiz.md"   # Praefix ohne /: nicht dienstlich
        with mit_einstellungen(dienst_ordner=DIENST):
            new, _ = self.link(FM + "Sigma Müller kam.\n", rel=rel)
        self.assertIn("[[Sigma Müller]]", new or "")
        with mock.patch.object(vl, "is_dienst", return_value=True):
            self.assertEqual(self.link(FM + "Sigma Müller kam.\n", rel=rel), (None, []))

    def test_kandidaten_nutzt_is_dienst(self):
        body = FM + "Herr Lambda Theta kam.\n"
        d = self.bau({DIENST + "X/a.md": body, DIENST + "X/b.md": body})
        v = vk.load_vault(d)
        with mit_einstellungen(dienst_ordner=DIENST):
            self.assertEqual([r["name"] for r in vk.kandidaten(v)], ["Lambda Theta"])
        with mock.patch.object(vl, "is_dienst", return_value=True):
            self.assertEqual(vk.kandidaten(v), [])


class EingerueckterCode(Basis):
    def test_listenpunkt_ist_kein_code(self):
        new, _ = self.link(FM + "- a\n\n    - Kappa\n")
        self.assertEqual(new, FM + "- a\n\n    - [[Kappa]]\n")

    def test_vorzeile_text_ist_kein_code(self):
        new, _ = self.link(FM + "Text\n    Kappa\n")
        self.assertEqual(new, FM + "Text\n    [[Kappa]]\n")

    def test_fortsetzung_nach_code(self):
        self.assertEqual(self.link(FM + "Text\n\n    code\n    Kappa\n"), (None, []))


class Kandidaten(Basis):
    def lauf(self, minimum=2):
        v = vk.load_vault(self.kopie("kandidaten"))
        with mit_einstellungen(dienst_ordner=DIENST):
            return {k["name"]: k for k in vk.kandidaten(v, minimum)}, v

    def test_firma_in_zwei_notizen(self):
        k, _ = self.lauf()
        self.assertEqual((k["Tau GmbH"]["art"], k["Tau GmbH"]["notizen"]), ("firma", 3))
        self.assertEqual(len(k["Tau GmbH"]["beispiele"]), 2)

    def test_person_in_einer_notiz_keiner(self):
        k, _ = self.lauf()
        self.assertNotIn("Einzel Allein", k)
        self.assertEqual(k["Lambda Weber"]["art"], "person")

    def test_werkzeug_binnenmajuskel_in_zwei(self):
        k, _ = self.lauf()
        self.assertEqual((k["GitHub"]["art"], k["GitHub"]["notizen"]), ("werkzeug", 3))

    def test_vorhandene_entitaet_keiner(self):
        k, _ = self.lauf()
        for n in ("Rho GmbH", "Sigma Müller", "Kappa"):
            self.assertNotIn(n, k)

    def test_person_nur_unter_dienst_dir_keiner(self):
        k, _ = self.lauf()
        self.assertNotIn("Dienst Person", k)

    def test_firma_nur_im_codeblock_keiner(self):
        k, _ = self.lauf()
        self.assertNotIn("Psi GmbH", k)

    def test_sortierung_anzahl_dann_name(self):
        _, v = self.lauf()
        with mit_einstellungen(dienst_ordner=DIENST):
            res = vk.kandidaten(v)
        self.assertEqual([r["name"] for r in res], ["GitHub", "Tau GmbH", "Lambda Weber"])

    def test_ohne_dienst_ordner_auch_dienstnotizen(self):
        """Ohne dienst_ordner ist nichts dienstlich: die Person aus dem Testordner wird Kandidat."""
        v = vk.load_vault(self.kopie("kandidaten"))
        self.assertIn("Dienst Person", {k["name"] for k in vk.kandidaten(v)})

    def test_minimum_eins_zeigt_einzelne(self):
        k, _ = self.lauf(1)
        self.assertIn("Einzel Allein", k)

    def test_cli_json_und_zeilenlimit(self):
        d = self.kopie("kandidaten")
        out = os.path.join(self.tmp(), "k.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vk.main(["kandidaten", "--vault", d, "--json", out])
        self.assertEqual(code, 0)
        self.assertLessEqual(len(buf.getvalue().splitlines()), 30)
        self.assertIn("GitHub", buf.getvalue())
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)[0]["name"], "GitHub")

    # --- Fix-Runde 1 ---
    def kand(self, files, **kw):
        v = vk.load_vault(self.bau(files))
        return {(k["art"], k["name"]): k for k in vk.kandidaten(v, **kw)}

    def zwei(self, text):
        return {NB + "A.md": text, NB + "B.md": text}

    def test_titelkette_gibt_namen_nicht_dr(self):
        k = self.kand({NB + "A.md": "Herr Dr. Kappa Omega kam.\n", NB + "B.md": "Frau Dr. Kappa Omega rief an.\n",
                       NB + "C.md": "Prof. Dr. Kappa Omega schrieb.\n"})
        self.assertNotIn(("person", "Dr"), k)
        self.assertEqual(k[("person", "Kappa Omega")]["notizen"], 3)

    def test_titel_ohne_name_gibt_kein_dr(self):
        k = self.kand(self.zwei("Herr Dr. kam. Frau Prof. ging.\n"))
        self.assertEqual([x for x in k if x[0] == "person"], [])

    def test_artikel_allein_ist_keine_firma(self):
        k = self.kand(self.zwei("Eine GmbH kostet. Die AG lohnt.\n"))
        self.assertEqual([x for x in k if x[0] == "firma"], [])

    def test_dr_und_prof_allein(self):
        k = self.kand({NB + "A.md": "Dr. Kappa Omega.\n", NB + "B.md": "Prof. Kappa Omega.\n"})
        self.assertIn(("person", "Kappa Omega"), k)

    def test_rechtsform_ev(self):
        self.assertIn(("firma", "Phi e.V."), self.kand(self.zwei("Phi e.V. tagt.\n")))

    def test_vier_woerter_firma(self):
        self.assertIn(("firma", "Alpha Beta Gamma Delta GmbH"), self.kand(self.zwei("Alpha Beta Gamma Delta GmbH.\n")))

    def test_zeilenlimit_stdout(self):
        text = " ".join("fooBar%s" % (chr(97 + i % 26) * (1 + i // 26)) for i in range(40)) + "\n"
        d = self.bau(self.zwei(text))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            vk.main(["kandidaten", "--vault", d])
        self.assertLessEqual(len(buf.getvalue().splitlines()), 30)
        self.assertIn("weitere", buf.getvalue())

    def test_firma_ohne_zusatz_ist_vorhanden(self):
        # Entitaet heisst "Zeta" (ohne Alias); "Zeta GmbH" ist dann kein Kandidat.
        k = self.kand({**self.zwei("Die Zeta GmbH liefert.\n"), ENT + "/Zeta.md": ent("firma")})
        self.assertNotIn(("firma", "Zeta GmbH"), k)
        k = self.kand(self.zwei("Die Zeta GmbH liefert.\n"))
        self.assertIn(("firma", "Zeta GmbH"), k)

    def test_notiz_filter_und_zaehlung_vaultweit(self):
        files = {NB + "A.md": "Tau GmbH und Pi GmbH.\n", NB + "B.md": "Tau GmbH.\n",
                 NB + "C.md": "Pi GmbH.\n", NB + "D.md": "Tau GmbH und Pi GmbH.\n"}
        k = self.kand(files, notizen=[NB + "B.md"])
        self.assertEqual([x[1] for x in k], ["Tau GmbH"])
        self.assertEqual(k[("firma", "Tau GmbH")]["notizen"], 3)
        self.assertEqual(k[("firma", "Tau GmbH")]["alle_notizen"], [NB + n for n in ("A.md", "B.md", "D.md")])

    def test_notiz_filter_minimum_gilt_weiter(self):
        k = self.kand({NB + "A.md": "Tau GmbH.\n", NB + "B.md": "Pi GmbH.\n", NB + "C.md": "Pi GmbH.\n"},
                      notizen=[NB + "A.md"])
        self.assertEqual(k, {})

    def test_cli_notiz_absolut_und_relativ(self):
        d = self.bau({NB + "A.md": "Tau GmbH, Pi GmbH.\n", NB + "B.md": "Tau GmbH.\n", NB + "C.md": "Pi GmbH.\n"})
        out = os.path.join(self.tmp(), "k.json")
        with contextlib.redirect_stdout(io.StringIO()):
            code = vk.main(["kandidaten", "--vault", d, "--notiz", os.path.join(d, NB + "B.md"),
                            "--json", out])
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            self.assertEqual([r["name"] for r in json.load(fh)], ["Tau GmbH"])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(vk.main(["kandidaten", "--vault", d, "--notiz", "gibt/es/nicht.md"]), 1)


class VaultAusEinstellungen(Basis):
    """Vault-Pfad aus --vault oder der Einstellung vault; fehlt beides: Klartext, Exit 2."""

    def cli(self, skript, args, einst="{}"):
        d = self.tmp()
        pfad = os.path.join(d, "einstellungen.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(einst)
        env = dict(os.environ, CLAUDE_SKILLS_EINSTELLUNGEN=pfad, HOME=d, VERKNUEPFEN_TEST="1",
                   VERKNUEPFEN_EINSTELLUNGEN=os.path.join(d, "nicht-da.json"), PATH=d)
        r = subprocess.run([sys.executable, "-I", os.path.join(HIER, skript), *args],
                           capture_output=True, text=True, env=env, cwd=d, timeout=60)
        return r, pfad, d

    def test_verknuepfen_cli_ohne_vault_exit2(self):
        r, pfad, _ = self.cli("verknuepfen.py", ["link", "--dry-run", "--alle"])
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Vault-Pfad fehlt", r.stderr)
        self.assertIn(pfad, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_alle_befehle_ohne_vault_exit2(self):
        for args in (["kandidaten"], ["nachbarn", "a.md"], ["index"]):
            with self.subTest(args=args):
                r, _, _ = self.cli("verknuepfen.py", args)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("Vault-Pfad fehlt", r.stderr)
                self.assertNotIn("Traceback", r.stderr)
        r, _, d = self.cli("eichen.py", ["liste.md"])
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Vault-Pfad fehlt", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_kaputte_einstellungen_exit2(self):
        v = self.bau({})
        for einst, text in (("[1]", "JSON-Objekt"), ("{kaputt", "nicht lesbar")):
            for extra in ([], ["--vault", v]):   # auch mit --vault: kaputte Datei nie still uebergehen
                r, pfad, _ = self.cli("verknuepfen.py", ["link", "--dry-run", "--alle", *extra], einst=einst)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn(pfad, r.stderr)
                self.assertIn(text, r.stderr)
                self.assertNotIn("Traceback", r.stderr)

    def test_falscher_typ_exit2(self):
        v = self.bau({NOTIZ: FM + "Kappa hier.\n"})
        for schluessel in ("vault", "dienst_ordner"):
            for wert in (5, ["a"], {"a": 1}, True):
                with self.subTest(schluessel=schluessel, wert=wert):
                    r, pfad, d = self.cli("verknuepfen.py", ["link", "--dry-run", "--alle", "--vault", v],
                                          einst=json.dumps({schluessel: wert}))
                    self.assertEqual(r.returncode, 2, r.stderr)
                    self.assertIn(schluessel, r.stderr)
                    self.assertIn("String", r.stderr)
                    self.assertIn(pfad, r.stderr)
                    self.assertNotIn("Traceback", r.stderr)

    def test_richtiger_typ_bleibt_gruen(self):
        v = self.bau({NOTIZ: FM + "Kappa hier.\n"})
        for einst in ({"vault": v, "dienst_ordner": DIENST}, {"dienst_ordner": ""}):
            r, _, _ = self.cli("verknuepfen.py", ["link", "--dry-run", "--alle", "--vault", v],
                               einst=json.dumps(einst))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_eichen_falscher_typ_exit2(self):
        v = self.bau({NOTIZ: FM + "Kappa hier.\n"})
        for schluessel in ("vault", "dienst_ordner"):
            with self.subTest(schluessel=schluessel):
                r, pfad, _ = self.cli("eichen.py", ["--vault", v, "liste.md"], einst=json.dumps({schluessel: 5}))
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn(schluessel, r.stderr)
                self.assertIn(pfad, r.stderr)
                self.assertNotIn("Traceback", r.stderr)

    def test_vault_aus_einstellung(self):
        v = self.bau({NOTIZ: FM + "Kappa hier.\n"})
        r, _, d = self.cli("verknuepfen.py", ["link", "--dry-run", "--alle", "--json", "out.json"],
                           einst=json.dumps({"vault": v}))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(d, "out.json"), encoding="utf-8") as fh:
            out = json.load(fh)
        self.assertEqual((out["vault"], out["links"]), (os.path.abspath(v), 1))
        with open(os.path.join(v, NOTIZ), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), FM + "Kappa hier.\n")  # dry-run schreibt nicht

    def test_argument_schlaegt_einstellung(self):
        v = self.bau({NOTIZ: FM + "Kappa hier.\n"})
        r, _, d = self.cli("verknuepfen.py", ["link", "--dry-run", "--alle", "--vault", v, "--json", "out.json"],
                           einst=json.dumps({"vault": os.path.join(v, "gibt-es-nicht")}))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(d, "out.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["vault"], os.path.abspath(v))

    def test_vorgaben_neutral(self):
        self.assertEqual(nb.VORGABEN["graph"]["ausschluss"], ["03 Bereiche/Finanzen/**", "memory/**"])
        self.assertEqual(nb.VORGABEN["graph"]["qmd_index"], "vault")
        self.assertEqual(nb.VORGABEN["graph"]["max_nachbarn"], 5)
        self.assertEqual(nb.VORGABEN["graph"]["qmd_frist"], 30)
        self.assertIsNone(nb.VORGABEN["graph"]["schwelle"])


if __name__ == "__main__":
    unittest.main()
