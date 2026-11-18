"""Tests fuer eichen.py (Eichung der Schwelle fuer Schritt 4) und offline_probe.sh. Wegwerf-Vault in
tempfile, Testdaten erfunden; qmd und node werden nie aufgerufen.

    python3 -I -m unittest discover -s ~/.claude/skills/verknuepfen/scripts
"""
import atexit
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock

# Vorspann VOR dem Import: HOME und Einstellungsdatei zeigen in einen Wegwerf-Ordner, damit weder
# ein Test noch eine Mutation die echte Konfiguration oder den echten Vault liest oder beschreibt.
# Subprozesse erben os.environ und damit diese Werte.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="eichen-test-home-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eichen  # noqa: E402
import nachbarn as nb  # noqa: E402
import verknuepfen as vk  # noqa: E402
from test_nachbarn import Basis as _NachbarnBasis, einst  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HIER, "offline_probe.sh")
UMGELENKT = ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "QMD_CONFIG_DIR", "INDEX_PATH",
             "VERKNUEPFEN_EINSTELLUNGEN", "VERKNUEPFEN_QMD_PAKET", "CLAUDE_SKILLS_EINSTELLUNGEN")


def setUpModule():
    os.environ["VERKNUEPFEN_TEST"] = "1"


class Basis(_NachbarnBasis):
    """Isolation aus test_nachbarn (HOME, XDG_*, QMD_CONFIG_DIR, INDEX_PATH, VERKNUEPFEN_QMD_PAKET umgelenkt,
    nb.NODE und nb.QMD gesperrt), dazu VERKNUEPFEN_EINSTELLUNGEN auf eine fehlende Datei im Wegwerf-Ordner."""

    def setUp(self):
        super().setUp()
        p = mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": os.path.join(self.tmp(), "nicht-da.json")})
        p.start()
        self.addCleanup(p.stop)

    def unterprozess_env(self):
        """Umgelenkte Umgebung fuer Unterprozesse; PATH ist ein leerer Ordner, also weder qmd noch node."""
        env = {k: os.environ[k] for k in UMGELENKT}
        env["PATH"] = self.tmp()
        env["VERKNUEPFEN_TEST"] = "1"
        return env


class SchwelleWaehlen(unittest.TestCase):
    def test_getrennte_werte_mitte(self):
        self.assertEqual(eichen.schwelle_waehlen([(0.8, True), (0.7, True), (0.4, False), (0.3, False)]), 0.55)

    def test_ueberlappend_zwischen_den_klassen(self):
        s = eichen.schwelle_waehlen([(0.6, True), (0.5, False), (0.55, True), (0.2, False)])
        self.assertGreater(s, 0.5)
        self.assertLessEqual(s, 0.55)

    def test_fehler_unvermeidbar_breitester_bereich(self):
        # (0.2, 0.4] und (0.5, 0.8] haben je einen Fehler; der breitere gewinnt, seine Mitte ist 0.65
        self.assertEqual(eichen.schwelle_waehlen([(0.8, True), (0.4, True), (0.5, False), (0.2, False)]), 0.65)

    def test_wenigste_fehler_vor_breite(self):
        # (0.45, 0.5] ist schmal, aber fehlerfrei; (0.5, 1.0] ist breit, hat aber zwei Fehler
        s = eichen.schwelle_waehlen([(0.5, True), (0.6, True), (0.45, False), (0.1, False)])
        self.assertGreater(s, 0.45)
        self.assertLessEqual(s, 0.5)

    def test_auf_zwei_stellen_gerundet(self):
        s = eichen.schwelle_waehlen([(0.9, True), (0.734, True), (0.4, False), (0.1, False)])
        self.assertEqual(s, 0.57)

    def test_gerundete_schwelle_trennt_noch(self):
        # Mitte 0.505; gleich gewertet wird ab der Schwelle, 0.50 wuerde 0.5 (nicht verwandt) mitnehmen
        s = eichen.schwelle_waehlen([(0.51, True), (0.5, False), (0.9, True), (0.1, False)])
        self.assertEqual(s, 0.51)

    def test_gerundete_mitte_auf_der_unteren_grenze_rueckt_ins_raster(self):
        # Mitte von (0.12, 0.13] rundet auf 0.12 und wuerde 0.12 (nicht verwandt) mitnehmen; 0.13 trennt
        werte = [(0.13, True), (0.12, False), (0.9, True), (0.01, False)]
        s = eichen.schwelle_waehlen(werte)
        self.assertEqual(s, 0.13)
        self.assertEqual(eichen.fehler(werte, s), 0)

    def test_gleichstand_an_der_schwelle_zaehlt_als_verwandt(self):
        # wie nachbarn(): score < schwelle faellt weg, score == schwelle bleibt
        s = eichen.schwelle_waehlen([(0.6, True), (0.3, False)])
        self.assertEqual(s, 0.45)
        self.assertEqual(eichen.fehler([(0.45, True), (0.45, False)], 0.45), 1)
        self.assertEqual(eichen.fehler([(0.44, True), (0.46, False)], 0.45), 2)

    def test_rand_unten_gewinnt_bei_weniger_fehlern(self):
        werte = [(0.0, True), (0.0, True), (0.5, False), (0.6, True)]
        s = eichen.schwelle_waehlen(werte)
        self.assertEqual(s, 0.0)
        self.assertEqual(eichen.fehler(werte, s), 1)

    def test_rand_oben_gewinnt_bei_weniger_fehlern(self):
        werte = [(1.0, False), (1.0, False), (0.5, False), (0.6, True)]
        s = eichen.schwelle_waehlen(werte)
        self.assertEqual(s, 1.01)
        self.assertEqual(eichen.fehler(werte, s), 1)

    def test_immer_die_wenigsten_fehler(self):
        # gegen alle Schwellen auf dem Raster von -0.05 bis 1.05
        import random
        zufall = random.Random(7)
        for _ in range(300):
            werte = [(round(zufall.choice([0.0, 1.0, zufall.random()]), 2), zufall.random() < 0.5)
                     for _ in range(zufall.randint(2, 7))]
            if len({v for _, v in werte}) < 2:
                continue
            bestes = min(eichen.fehler(werte, k / 100) for k in range(-5, 106))
            self.assertEqual(eichen.fehler(werte, eichen.schwelle_waehlen(werte)), bestes, werte)

    def test_nur_eine_klasse_ist_valueerror(self):
        with self.assertRaises(ValueError):
            eichen.schwelle_waehlen([(0.8, True), (0.3, True)])
        with self.assertRaises(ValueError):
            eichen.schwelle_waehlen([(0.8, False)])
        with self.assertRaisesRegex(ValueError, "keine Paare"):
            eichen.schwelle_waehlen([])


class PaareLesen(unittest.TestCase):
    def test_zeilen(self):
        text = ("# Eichpaare\n\nVorrede mit [[Kappa]].\n"
                "- [[02 Projekte/Kappa/Kappa]] | [[Rho GmbH]] | verwandt\n"
                "-   [[Omega]]|[[Kappa Plan]]|nicht  \n"
                "- [[Omega]] | [[Kappa]]\n"
                "- [[Omega]] | [[Kappa]] | vielleicht\n"
                "* [[Omega]] | [[Kappa]] | nicht\n"
                "- [[Omega]] | Kappa | nicht\n"
                "Schwelle: 0.55\n")
        self.assertEqual(eichen.paare_lesen(text), [
            ("02 Projekte/Kappa/Kappa", "Rho GmbH", True),
            ("Omega", "Kappa Plan", False),
        ])

    def test_nfd_wird_nfc(self):
        nfd = unicodedata.normalize("NFD", "- [[Kappa Übersicht]] | [[Rho Größe]] | verwandt\n")
        a, b, _ = eichen.paare_lesen(nfd)[0]
        self.assertEqual((a, b), ("Kappa Übersicht", "Rho Größe"))
        self.assertTrue(unicodedata.is_normalized("NFC", a + b))

    def test_unbekannte_klasse_wird_gemeldet(self):
        w = []
        paare = eichen.paare_lesen("- [[A]] | [[B]] | nicht verwandt\n- [[A]] | [[C]] | Verwandt\n"
                                   "- [[A]] | [[D]] | nicht\nfrei [[A]] | [[B]] | x\n", w)
        self.assertEqual(paare, [("A", "D", False)])
        self.assertEqual(len(w), 2)
        self.assertTrue(all(z.startswith("unbekannte Klasse: ") for z in w), w)
        self.assertIn("nicht verwandt", w[0])

    def test_crlf(self):
        self.assertEqual(eichen.paare_lesen("- [[A]] | [[B]] | nicht\r\n"), [("A", "B", False)])


VAULT = {
    "02 Projekte/Kappa/Kappa.md": "---\ntags: [projekt]\n---\nKappaText Projekt der Rho GmbH.\n",
    "02 Projekte/Kappa/Kappa Plan.md": "KappaPlanText Etappen fuer Kappa.\n",
    "03 Bereiche/Omega/Omega.md": "OmegaText Bereich ohne Bezug.\n",
    "04 Ressourcen/Sigma.md": "SigmaText Sammlung.\n",
    "04 Ressourcen/Leer.md": "---\na: 1\n---\n",
    "memory/Kappa Notiz.md": "MemoryText.\n",
    "03 Bereiche/Finanzen/Rho Rechnung.md": "FinanzText.\n",
    "02 Projekte/Kappa/Doppel.md": "DoppelEins.\n",
    "03 Bereiche/Omega/Doppel.md": "DoppelZwei.\n",
}

# Treffer je Ausgangsnotiz (erstes Wort der Abfrage): (rel, score)
TREFFER = {
    "KappaText": [("02 Projekte/Kappa/Kappa Plan.md", 0.8), ("03 Bereiche/Omega/Omega.md", 0.4)],
    "SigmaText": [("02 Projekte/Kappa/Kappa Plan.md", 0.7)],
    "OmegaText": [("04 Ressourcen/Sigma.md", 0.3)],
}

PAARE_GUT = ("# Eichpaare\n"
             "- [[02 Projekte/Kappa/Kappa]] | [[Kappa Plan]] | verwandt\n"
             "- [[Omega]] | [[Sigma]] | nicht\n"
             "- [[Kappa]] | [[Omega]] | nicht\n"
             "- [[Sigma]] | [[Kappa Plan]] | verwandt\n")


class MitVault(Basis):
    def setUp(self):
        super().setUp()
        self.root = self.bau(VAULT)
        self.v = vk.load_vault(self.root)

    def fake(self, tabelle=None, fehler=None):
        tabelle = TREFFER if tabelle is None else tabelle
        calls = []

        def run(index, abfrage, frist, n=20):
            calls.append((index, abfrage, frist, n))
            if fehler:
                raise nb.NachbarnFehler(fehler)
            return json.dumps([self.treffer(self.root, rel, s) for rel, s in tabelle.get(abfrage.split()[0], [])])
        run.calls = calls
        return run


class ScorePaar(MitVault):
    def test_bester_score_und_n_2000(self):
        tab = {"KappaText": [("04 Ressourcen/Sigma.md", 0.4), ("02 Projekte/Kappa/Kappa Plan.md", 0.61),
                             ("04 Ressourcen/Sigma.md", 0.72)]}
        run = self.fake(tab)
        e = einst(qmd_index="meins", qmd_frist=7)
        s = eichen.score_paar(self.v, "02 Projekte/Kappa/Kappa.md", "04 Ressourcen/Sigma.md", e, runner=run)
        self.assertEqual(s, 0.72)
        self.assertEqual(len(run.calls), 1)
        index, abfrage, frist, n = run.calls[0]
        self.assertEqual((index, frist, n), ("meins", 7, 2000))
        self.assertEqual(abfrage, nb.abfrage_text(VAULT["02 Projekte/Kappa/Kappa.md"]))

    def test_nicht_dabei_ist_null(self):
        run = self.fake()
        s = eichen.score_paar(self.v, "03 Bereiche/Omega/Omega.md", "02 Projekte/Kappa/Kappa Plan.md", einst(),
                              runner=run)
        self.assertEqual(s, 0.0)

    def test_treffer_ausserhalb_des_vaults_zaehlt_nicht(self):
        fremd = self.tmp()

        def run(index, abfrage, frist, n=20):
            return json.dumps([self.treffer(fremd, "04 Ressourcen/Sigma.md", 0.9)])
        s = eichen.score_paar(self.v, "02 Projekte/Kappa/Kappa.md", "04 Ressourcen/Sigma.md", einst(), runner=run)
        self.assertEqual(s, 0.0)

    def test_schwelle_null_sperrt_die_eichung_nicht(self):
        run = self.fake()
        s = eichen.score_paar(self.v, "02 Projekte/Kappa/Kappa.md", "02 Projekte/Kappa/Kappa Plan.md",
                              einst(schwelle=None), runner=run)
        self.assertEqual(s, 0.8)


class Cli(MitVault):
    def liste(self, text):
        d = self.tmp()
        p = os.path.join(d, "Eichpaare.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def lauf(self, argv, run):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(nb, "qmd_runner", run), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = eichen.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_lauf_druckt_scores_schwelle_quote_und_schreibt_nichts(self):
        p = self.liste(PAARE_GUT)
        vorher = os.stat(p)
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, p], run)
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), [
            "0.800 verwandt 02 Projekte/Kappa/Kappa | Kappa Plan",
            "0.300 nicht Omega | Sigma",
            "0.400 nicht Kappa | Omega",
            "0.700 verwandt Sigma | Kappa Plan",
            "Schwelle: 0.55",
            "Trefferquote: 4/4 (100 %)",
        ])
        self.assertEqual([c[3] for c in run.calls], [2000] * 4)
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), PAARE_GUT)
        self.assertEqual(os.stat(p).st_mtime_ns, vorher.st_mtime_ns)
        self.assertEqual(sorted(os.listdir(os.path.dirname(p))), ["Eichpaare.md"])

    def test_trefferquote_mit_fehler(self):
        tab = dict(TREFFER, OmegaText=[("04 Ressourcen/Sigma.md", 0.75)])
        code, out, err = self.lauf(["--vault", self.root, self.liste(PAARE_GUT)], self.fake(tab))
        self.assertEqual(code, 0, err)
        self.assertIn("Trefferquote: 3/4 (75 %)", out.splitlines())

    def test_ausgeschlossene_und_fehlende_notizen_werden_nicht_abgefragt(self):
        p = self.liste("- [[memory/Kappa Notiz]] | [[Kappa]] | verwandt\n"
                       "- [[Kappa]] | [[Rho Rechnung]] | nicht\n"
                       "- [[Kappa]] | [[Gibt es nicht]] | nicht\n"
                       "- [[Doppel]] | [[Kappa]] | verwandt\n")
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, p], run)
        self.assertEqual(len(run.calls), 0)
        zeilen = [z for z in out.splitlines() if z.startswith("übersprungen: ")]
        self.assertEqual(len(zeilen), 4, out)
        self.assertIn("memory/Kappa Notiz", zeilen[0])
        self.assertIn("ausgeschlossen", zeilen[0])
        self.assertIn("Rho Rechnung", zeilen[1])
        self.assertIn("ausgeschlossen", zeilen[1])
        self.assertIn("fehlt", zeilen[2])
        self.assertIn("mehrdeutig", zeilen[3])
        self.assertEqual(code, 1)  # keine Paare uebrig

    def test_uebersprungen_mitten_in_der_liste(self):
        p = self.liste(PAARE_GUT + "- [[Kappa]] | [[Rho Rechnung]] | nicht\n- [[Leer]] | [[Kappa]] | nicht\n")
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, p], run)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(run.calls), 4)
        self.assertIn("Trefferquote: 4/4 (100 %)", out.splitlines())
        self.assertEqual(sum(z.startswith("übersprungen: ") for z in out.splitlines()), 2)

    def test_ausschluss_aus_einstellungsdatei_und_feste_muster(self):
        e = os.path.join(self.tmp(), "e.json")
        with open(e, "w", encoding="utf-8") as fh:
            json.dump({"graph": {"ausschluss": ["04 Ressourcen/**"]}}, fh)
        p = self.liste(PAARE_GUT)
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, "--einstellungen", e, p], run)
        # Sigma liegt jetzt im Ausschluss; Rest: Kappa|Kappa Plan (verwandt), Kappa|Omega (nicht)
        self.assertEqual(len(run.calls), 2)
        self.assertEqual(sum(z.startswith("übersprungen: ") for z in out.splitlines()), 2)
        self.assertEqual(code, 0, err)
        # feste Muster sind nicht abschaltbar
        with mock.patch.object(eichen.vk, "load_vault", lambda r: self.v):
            self.v.texts[".trash/Kappa Alt.md"] = "KappaText.\n"
            self.v.resolver = vk.vl.Resolver(list(self.v.texts))
            p2 = self.liste("- [[.trash/Kappa Alt]] | [[Kappa Plan]] | verwandt\n")
            run2 = self.fake()
            self.lauf(["--vault", self.root, "--einstellungen", e, p2], run2)
            self.assertEqual(len(run2.calls), 0)

    def test_mehrdeutig_auch_mit_anker_alias_und_schraegstrich(self):
        p = self.liste("- [[Doppel#Kopf]] | [[Kappa]] | verwandt\n"
                       "- [[Kappa]] | [[Doppel|Anzeige]] | nicht\n"
                       "- [[/Doppel]] | [[Kappa]] | nicht\n"
                       "- [[Doppel^block]] | [[Kappa]] | nicht\n")
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, p], run)
        self.assertEqual(len(run.calls), 0)
        zeilen = [z for z in out.splitlines() if z.startswith("übersprungen: ")]
        self.assertEqual(len(zeilen), 4, out)
        self.assertTrue(all("mehrdeutig" in z for z in zeilen), zeilen)

    def test_einstellungsdatei_fehlt_exit_1(self):
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, "--einstellungen", os.path.join(self.tmp(), "fehlt.json"),
                                    self.liste(PAARE_GUT)], run)
        self.assertEqual((code, len(run.calls)), (1, 0))
        self.assertIn("Einstellungsdatei", err)

    def test_unbekannte_klasse_auf_stderr_und_keine_paare(self):
        p = self.liste("- [[Kappa]] | [[Kappa Plan]] | nicht verwandt\n- [[Kappa]] | [[Omega]] | Verwandt\n")
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, p], run)
        self.assertEqual((code, len(run.calls)), (1, 0))
        self.assertEqual(err.count("unbekannte Klasse: "), 2, err)
        self.assertIn("keine Paare", err)
        self.assertNotIn("Klasse)", err)

    def test_alle_scores_null_exit_1(self):
        run = self.fake({})
        code, out, err = self.lauf(["--vault", self.root, self.liste(PAARE_GUT)], run)
        self.assertEqual(code, 1)
        self.assertEqual(len(run.calls), 4)
        self.assertIn("alle Scores 0", err)
        self.assertNotIn("Schwelle:", out)

    def test_nur_eine_klasse_exit_1_ohne_traceback(self):
        p = self.liste("- [[Kappa]] | [[Kappa Plan]] | verwandt\n")
        code, out, err = self.lauf(["--vault", self.root, p], self.fake())
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("nur eine Klasse", err)
        self.assertNotIn("Schwelle:", out)

    def test_yaml_fehlt_exit_1_ohne_abfrage(self):
        os.remove(os.path.join(self.cfg, "vault.yml"))
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, self.liste(PAARE_GUT)], run)
        self.assertEqual(code, 1)
        self.assertEqual(len(run.calls), 0)
        self.assertIn("nicht gebaut", err)

    def test_yaml_mit_fremdmodell_exit_1_ohne_abfrage(self):
        with open(os.path.join(self.cfg, "vault.yml"), "a", encoding="utf-8") as fh:
            fh.write('models:\n  embed: "https://api.example.invalid/v1#modell"\n')
        run = self.fake()
        code, out, err = self.lauf(["--vault", self.root, self.liste(PAARE_GUT)], run)
        self.assertEqual(code, 1)
        self.assertEqual(len(run.calls), 0)
        self.assertIn("Fremdmodell", err)

    def test_index_aus_einstellungen(self):
        e = os.path.join(self.tmp(), "e.json")
        with open(e, "w", encoding="utf-8") as fh:
            json.dump({"graph": {"qmd_index": "fehlt-hier"}}, fh)
        run = self.fake()
        code, _, err = self.lauf(["--vault", self.root, "--einstellungen", e, self.liste(PAARE_GUT)], run)
        self.assertEqual((code, len(run.calls)), (1, 0))
        self.assertIn("fehlt-hier.yml", err)

    def test_runner_fehler_bricht_ab(self):
        run = self.fake(fehler="node nicht gefunden")
        code, out, err = self.lauf(["--vault", self.root, self.liste(PAARE_GUT)], run)
        self.assertEqual(code, 1)
        self.assertIn("node nicht gefunden", err)
        self.assertNotIn("Traceback", err)

    def test_paarliste_fehlt(self):
        code, _, err = self.lauf(["--vault", self.root, os.path.join(self.tmp(), "fehlt.md")], self.fake())
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)

    def test_vault_fehlt(self):
        code, _, err = self.lauf(["--vault", os.path.join(self.tmp(), "kein-vault"), self.liste(PAARE_GUT)],
                                 self.fake())
        self.assertEqual(code, 2)

    def test_unter_isolated_python(self):
        """eichen.py unter python3 -I findet seine Module; node ist im PATH nicht erreichbar."""
        r = subprocess.run([sys.executable, "-I", os.path.join(HIER, "eichen.py"), "--vault", self.root,
                            self.liste(PAARE_GUT)], capture_output=True, text=True, env=self.unterprozess_env(),
                           cwd="/")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("node nicht", r.stderr)

    def test_python_zu_alt_exit_1_ueber_gemeinsame_pruefung(self):
        run = self.fake()
        with mock.patch.object(nb, "PurePosixPath", type("Alt", (), {})), \
                mock.patch.object(nb, "python_grund", return_value="Python-Grund aus nachbarn"):
            code, out, err = self.lauf(["--vault", self.root, self.liste(PAARE_GUT)], run)
        self.assertEqual(code, 1)
        self.assertIn("Python-Grund aus nachbarn", err)
        self.assertEqual(run.calls, [])

    def test_unter_isolated_python_ohne_yaml(self):
        os.remove(os.path.join(self.cfg, "vault.yml"))
        r = subprocess.run([sys.executable, "-I", os.path.join(HIER, "eichen.py"), "--vault", self.root,
                            self.liste(PAARE_GUT)], capture_output=True, text=True, env=self.unterprozess_env(),
                           cwd="/")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("nicht gebaut", r.stderr)


class Kopplung(MitVault):
    """eichen.py und nachbarn() teilen Schwellenregel und YAML-Pruefung (je eine Funktion in nachbarn.py)."""

    def vault_nachbarn(self, schwelle):
        tab = {"KappaText": [("04 Ressourcen/Sigma.md", 0.1)]}
        return nb.nachbarn(self.v, "02 Projekte/Kappa/Kappa.md", einst(schwelle=schwelle), runner=self.fake(tab))

    def test_schwellenregel_gemeinsam(self):
        self.assertEqual(self.vault_nachbarn(0.5)[0], [])
        self.assertEqual(eichen.fehler([(0.1, False)], 0.5), 0)
        with mock.patch.object(nb, "ueber_schwelle", lambda s, t: True):
            self.assertEqual([n.rel for n in self.vault_nachbarn(0.5)[0]], ["04 Ressourcen/Sigma.md"])
            self.assertEqual(eichen.fehler([(0.1, False)], 0.5), 1)
        self.assertTrue(nb.ueber_schwelle(0.5, 0.5))
        self.assertFalse(nb.ueber_schwelle(0.49, 0.5))

    def test_yaml_pruefung_gemeinsam(self):
        with mock.patch.object(nb, "yaml_grund", lambda e, env=None: "Kopplung Kappa"):
            self.assertEqual(self.vault_nachbarn(0.5), ([], "Kopplung Kappa"))
            run = self.fake()
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(nb, "qmd_runner", run), contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                p = os.path.join(self.tmp(), "p.md")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(PAARE_GUT)
                code = eichen.main(["--vault", self.root, p])
            self.assertEqual((code, len(run.calls)), (1, 0))
            self.assertIn("Kopplung Kappa", err.getvalue())

    def test_yaml_grund_werte(self):
        e = einst(qmd_index="vault")
        self.assertIsNone(nb.yaml_grund(e))
        self.assertEqual(nb.yaml_grund(einst(qmd_index="fehlt")), "qmd-Index nicht gebaut (verknuepfen.py index)")
        with open(os.path.join(self.cfg, "vault.yml"), "a", encoding="utf-8") as fh:
            fh.write('models:\n  embed: "https://x.invalid/m"\n')
        self.assertEqual(nb.yaml_grund(e), "qmd-Konfiguration mit Fremdmodell")
        anders = self.tmp()
        self.assertEqual(nb.yaml_grund(e, {"QMD_CONFIG_DIR": anders}), "qmd-Index nicht gebaut (verknuepfen.py index)")


FAKE_QMD = r'''#!/bin/bash
# Fake-qmd: Verhalten je Konfigurationsordner und Schritt ueber FAKE_QMD_<ordner>_<schritt>=rc[:sekunden]
cfg=$(basename "$QMD_CONFIG_DIR" | tr -- '-' '_'); schritt=$3
echo "qmd $cfg $schritt index=$INDEX_PATH" >> "$FAKE_LOG"
var="FAKE_QMD_${cfg}_${schritt}"; wert=${!var:-0}
rc=${wert%%:*}; [ "$wert" != "$rc" ] && sleep "${wert#*:}"
if [ "$schritt" = update ]; then
  python3 -I -c 'import sqlite3, sys; c = sqlite3.connect(sys.argv[1]); c.execute("create table if not exists content_vectors (h text)"); c.commit()' "$INDEX_PATH"
fi
vvar="FAKE_QMD_${cfg}_vektoren"
if [ "$schritt" = embed ] && [ -n "${!vvar:-}" ]; then
  python3 -I -c 'import sqlite3, sys; c = sqlite3.connect(sys.argv[1]); c.execute("insert into content_vectors values (1)"); c.commit()' "$INDEX_PATH"
fi
echo "qmd $schritt Zeile 1"; echo "qmd $schritt fertig"
exit "$rc"
'''
FAKE_NODE = r'''#!/bin/bash
cat > /dev/null
echo "node $*" >> "$FAKE_LOG"
printf '%s\n' "$FAKE_NODE_OUT"
exit "${FAKE_NODE_RC:-0}"
'''
# Echte Sandbox mit dem Profil der Probe; FAKE_SANDBOX_OFFEN laesst die Netzsperre weg
FAKE_SANDBOX = r'''#!/bin/bash
echo "sandbox-exec $2" >> "$FAKE_LOG"
if [ -n "${FAKE_SANDBOX_OFFEN:-}" ]; then shift 2; exec /usr/bin/sandbox-exec -p '(version 1)(allow default)' "$@"; fi
exec /usr/bin/sandbox-exec "$@"
'''


@unittest.skipUnless(os.path.exists("/usr/bin/sandbox-exec"), "nur macOS")
class ProbeMitFakes(Basis):
    """offline_probe.sh mit VERKNUEPFEN_QMD_PROBE=1, aber Fake-qmd und Fake-node im PATH; HOME, XDG_*,
    QMD_CONFIG_DIR und INDEX_PATH umgelenkt, Schritt d bekommt also nur den Wegwerf-Pfad."""

    def lauf(self, faktor="0.05", **fakes):
        fb = self.tmp()
        for name, text in (("qmd", FAKE_QMD), ("node", FAKE_NODE), ("sandbox-exec", FAKE_SANDBOX)):
            with open(os.path.join(fb, name), "w", encoding="utf-8") as fh:
                fh.write(text)
            os.chmod(os.path.join(fb, name), 0o755)
        os.symlink(sys.executable, os.path.join(fb, "python3"))
        env = self.unterprozess_env()
        self.tmpdir = self.tmp()
        self.log = os.path.join(self.tmp(), "fake.log")
        env.update({"PATH": fb + ":/usr/bin:/bin", "TMPDIR": self.tmpdir, "VERKNUEPFEN_QMD_PROBE": "1",
                    "VERKNUEPFEN_PROBE_FRIST_FAKTOR": faktor, "FAKE_LOG": self.log,
                    "FAKE_NODE_OUT": json.dumps([{"score": 0.5, "file": "/kappa/a.md", "title": "a"}]),
                    "FAKE_QMD_cfg_remote_embed": "1"})
        env.update(fakes)
        r = subprocess.run(["/bin/bash", PROBE], capture_output=True, text=True, env=env, cwd="/", timeout=120)
        with open(self.log, encoding="utf-8") as fh:
            self.protokoll = fh.read()
        return r

    def test_gutfall_exit_0_und_aufgeraeumt(self):
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FEHLER", r.stdout)
        self.assertIn("OK Sandbox sperrt Netz", r.stdout)
        self.assertIn("Exit 1", [z for z in r.stdout.splitlines() if "Fremdmodell" in z and "Vektor" in z][0])
        self.assertEqual(os.listdir(self.tmpdir), [])
        # Schritt d fragt den umgelenkten Index, nie die echte Datenbank
        self.assertIn(os.environ["INDEX_PATH"] + " 3", self.protokoll)
        self.assertNotIn(os.path.expanduser("~/.cache"), self.protokoll)

    def test_schritt_d_nimmt_index_aus_den_einstellungen(self):
        ed = self.tmp()
        ep = os.path.join(ed, "e.json")
        with open(ep, "w", encoding="utf-8") as fh:
            json.dump({"graph": {"qmd_index": "kappa"}}, fh)
        xdg = self.tmp()
        # INDEX_PATH leer gilt als nicht gesetzt: Schritt d folgt dann XDG_CACHE_HOME und dem Indexnamen
        with mock.patch.dict(os.environ, {"VERKNUEPFEN_EINSTELLUNGEN": ep, "XDG_CACHE_HOME": xdg, "INDEX_PATH": ""}):
            r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(os.path.join(xdg, "qmd", "kappa.sqlite") + " 3", self.protokoll)
        self.assertNotIn("vault.sqlite", self.protokoll)

    def test_fremdmodell_embed_laeuft_durch_ist_fehler(self):
        r = self.lauf(FAKE_QMD_cfg_remote_embed="0")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("FEHLER", [z for z in r.stdout.splitlines() if "Fremdmodell" in z and "Vektor" in z][0])

    def test_fremdmodell_mit_vektoren_ist_fehler(self):
        r = self.lauf(FAKE_QMD_cfg_remote_vektoren="1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("1 Vektor", r.stdout)

    def test_fremdmodell_haengt_frist_abgelaufen_ist_ok(self):
        r = self.lauf(FAKE_QMD_cfg_remote_embed="0:30")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        zeile = [z for z in r.stdout.splitlines() if "Fremdmodell" in z and "Vektor" in z][0]
        self.assertTrue(zeile.startswith("OK"), zeile)
        self.assertIn("Frist abgelaufen", zeile)

    def test_sandbox_ohne_netzsperre_ist_fehler(self):
        r = self.lauf(FAKE_SANDBOX_OFFEN="1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue([z for z in r.stdout.splitlines() if z.startswith("FEHLER Sandbox sperrt Netz")], r.stdout)

    def test_frist_in_schritt_b_ist_fehler(self):
        r = self.lauf(faktor="0.01", FAKE_QMD_cfg_embed="0:30")
        self.assertEqual(r.returncode, 1, r.stdout)
        zeile = [z for z in r.stdout.splitlines() if "qmd embed ohne Netz" in z][0]
        self.assertTrue(zeile.startswith("FEHLER"), zeile)
        self.assertIn("Frist abgelaufen", zeile)

    def test_leere_trefferliste_und_kaputtes_json_sind_fehler(self):
        for aus in ("[]", "kein json"):
            r = self.lauf(FAKE_NODE_OUT=aus)
            self.assertEqual(r.returncode, 1, (aus, r.stdout))
            self.assertNotIn("Traceback", r.stdout + r.stderr, aus)


class OfflineProbe(Basis):
    def test_ohne_variable_exit_0_mit_hinweis(self):
        for wert in (None, "", "0", "ja"):
            env = self.unterprozess_env()
            env["PATH"] = "/usr/bin:/bin"  # bash, mktemp; qmd und node liegen nicht hier
            if wert is not None:
                env["VERKNUEPFEN_QMD_PROBE"] = wert
            r = subprocess.run(["/bin/bash", PROBE], capture_output=True, text=True, env=env, cwd="/")
            self.assertEqual(r.returncode, 0, (wert, r.stdout, r.stderr))
            self.assertIn("VERKNUEPFEN_QMD_PROBE=1", r.stdout + r.stderr, wert)
            self.assertNotIn("OK", r.stdout, wert)
            self.assertNotIn("FEHLER", r.stdout, wert)

    def test_syntax(self):
        r = subprocess.run(["/bin/bash", "-n", PROBE], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_loescht_nur_den_eigenen_ordner(self):
        with open(PROBE, encoding="utf-8") as fh:
            text = fh.read()
        rm = [z.strip() for z in text.splitlines() if re.search(r"\brm\b", z) and not z.lstrip().startswith("#")]
        self.assertEqual(rm, ['rm -rf -- "$W"'])
        self.assertIn('W=$(mktemp -d)', text)
        self.assertIn("(deny network*)", text)
        self.assertNotIn("XDG_CACHE_HOME", text)


if __name__ == "__main__":
    unittest.main()
