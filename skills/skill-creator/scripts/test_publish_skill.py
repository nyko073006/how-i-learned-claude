"""Tests fuer publish_skill.py: Einstellungsdatei, Sperrlisten-Pruefung und oeffentliches Ziel.

Alles laeuft in tempfile-Ordnern; HOME und CLAUDE_SKILLS_EINSTELLUNGEN zeigen dorthin, damit kein Test
echte Einstellungen, Sperrlisten oder Repos liest oder schreibt. Kein Netz, kein Remote. Alle Begriffe
der Sperrlisten sind erfunden.

    cd ~/.claude/skills/skill-creator/scripts && python3 -m unittest test_publish_skill -v
"""
import atexit
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Vorspann VOR dem Import: Alles, was publish_skill beim Import aus HOME oder Env festhaelt, zeigt
# damit in einen Wegwerf-Ordner, nie auf echte Repos, Vault oder Einstellungen.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="publish-skill-test-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")
os.environ["GIT_ALLOW_PROTOCOL"] = "file"
os.environ["GIT_TERMINAL_PROMPT"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publish_skill as ps  # noqa: E402

LISTE_TEXT = "# k\nanna\n!anna073006\nbeispielfirma\n\n"
# Zusammengesetzt, damit diese Datei selbst die Sperrprobe besteht.
NUTZERPFAD = "/Us" + "ers/x/a"
SITZUNGSLINK = "claude.ai/code/" + "session_abc"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


class Basis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        (self.tmp / "home").mkdir()
        self.einst = self.tmp / "einstellungen.json"
        env = {
            "HOME": str(self.tmp / "home"),
            "CLAUDE_SKILLS_EINSTELLUNGEN": str(self.einst),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        self.liste = ps.parse_sperrliste(LISTE_TEXT)

    def datei(self, rel, inhalt):
        pfad = self.tmp / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(inhalt, bytes):
            pfad.write_bytes(inhalt)
        else:
            pfad.write_text(inhalt, encoding="utf-8")
        return pfad

    def hits(self, text, liste=None):
        wurzel = self.tmp / "probe"
        self.datei("probe/a.md", text)
        return ps.pruefe_dateien(wurzel, [Path("a.md")], liste or self.liste)

    def repo(self, name):
        pfad = self.tmp / name
        pfad.mkdir(parents=True)
        git(pfad, "init", "-q", "-b", "main")
        return pfad

    def skill(self, name="demo", inhalt="---\nname: demo\nversion: 1.0.0\n---\nText\n"):
        self.datei(f"skills/{name}/SKILL.md", inhalt)
        return self.tmp / "skills" / name

    def schreibe_einstellungen(self, daten):
        self.einst.write_text(json.dumps(daten), encoding="utf-8")


class SperrlisteTest(Basis):
    def test_parse(self):
        self.assertEqual(self.liste, (["anna", "beispielfirma"], ["anna073006"]))

    def test_normalisiere(self):
        self.assertEqual(ps.normalisiere("FírMa​"), "firma")

    def test_ausnahme_nur_mit_wortgrenze(self):
        self.assertEqual(self.hits("github.com/anna073006/x"), [])
        self.assertNotEqual(self.hits("Konto anna.xy"), [])
        self.assertNotEqual(self.hits("anna0730061"), [])
        self.assertNotEqual(self.hits("xanna073006"), [])  # A7: Wortgrenze auch vorn
        self.assertNotEqual(self.hits("_anna073006"), [])

    def test_unicode_varianten(self):
        for text in ("beispiel​firma", "BEISPIELFIRMA", "beispielfírma", "beispielfírma"):
            self.assertEqual(self.hits(text), ["a.md:1"], text)

    def test_zeilennummer_und_sauberer_text(self):
        self.assertEqual(self.hits("sauber\nnoch sauber\r\nhier anna\n"), ["a.md:3"])
        self.assertEqual(self.hits("nichts Privates"), [])

    def test_extra_begriffe_immer(self):
        eine = ps.parse_sperrliste("einbegriff\n")
        self.assertNotEqual(self.hits(NUTZERPFAD, eine), [])
        self.assertNotEqual(self.hits(SITZUNGSLINK, eine), [])
        self.assertEqual(self.hits("~/.claude/skills/x", eine), [])

    def test_treffer_im_dateinamen_maskiert(self):
        self.datei("probe/beispielfirma-notiz.md", "")
        ergebnis = ps.pruefe_dateien(self.tmp / "probe", [Path("beispielfirma-notiz.md")], self.liste)
        self.assertEqual(ergebnis, ["***-notiz.md:0"])
        self.assertNotIn("beispielfirma", "".join(ergebnis))

    def test_maskiert_im_pfad_auch_unicode_und_zeile(self):
        self.datei("probe/Beispielfírma/x.md", "anna\n")
        ergebnis = ps.pruefe_dateien(self.tmp / "probe", [Path("Beispielfírma/x.md")], self.liste)
        self.assertEqual(ergebnis, ["***/x.md:0", "***/x.md:1"])

    def test_binaer_png_mit_begriff(self):
        kopf = b"\x89PNG\r\n\x1a\n\x00\x00"
        self.datei("probe/bild.png", kopf + "anna.xy".encode("utf-16le"))
        self.datei("probe/versetzt.png", kopf + b"x" + "anna.xy".encode("utf-16le"))
        self.datei("probe/latin.png", kopf + b"anna.xy")
        self.datei("probe/sauber.png", kopf + "nichts".encode("utf-16le"))
        dateien = [Path(n) for n in ("bild.png", "versetzt.png", "latin.png", "sauber.png")]
        self.assertEqual(
            ps.pruefe_dateien(self.tmp / "probe", dateien, self.liste),
            ["bild.png:0 (binär)", "versetzt.png:0 (binär)", "latin.png:0 (binär)"],
        )

    def test_utf16_mit_bom_zeilenweise(self):
        self.datei("probe/w.txt", b"\xff\xfe" + "sauber\nanna\n".encode("utf-16le"))
        self.assertEqual(ps.pruefe_dateien(self.tmp / "probe", [Path("w.txt")], self.liste), ["w.txt:2"])


class OeffentlichTest(Basis):
    def test_publicignore_schliesst_aus(self):
        src = self.skill()
        self.datei("skills/demo/docs/a.md", "x")
        self.datei("skills/demo/scripts/s.py", "x")
        self.datei("skills/demo/notiz.tmp", "x")
        self.datei("skills/demo/.publicignore", "# Kommentar\ndocs/\n\n*.tmp\n")
        self.assertEqual(ps.oeffentliche_dateien(src), [Path("SKILL.md"), Path("scripts/s.py")])

    def test_spiegeln_bricht_bei_treffer_ab_und_kopiert_nichts(self):
        src = self.skill(inhalt="---\nname: demo\n---\nbeispielfirma\n")
        repo = self.repo("oeff")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertIn("SKILL.md:4", str(ctx.exception))
        self.assertNotIn("beispielfirma", str(ctx.exception))
        self.assertFalse((repo / "skills" / "demo").exists())

    def test_spiegeln_sauber_committet_ohne_push(self):
        src = self.skill()
        self.datei("skills/demo/docs/intern.md", "x")
        self.datei("skills/demo/.publicignore", "docs/\n")
        repo = self.repo("oeff")
        self.datei("oeff/skills/demo/alt.md", "veraltet")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "start")
        ergebnis = ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertEqual(ergebnis["treffer"], [])
        self.assertTrue(ergebnis["committed"])
        self.assertTrue(ergebnis["commit"])
        self.assertEqual(git(repo, "log", "-1", "--format=%s").strip(), "skills/demo: m")
        self.assertEqual(git(repo, "remote").strip(), "")
        self.assertFalse((repo / "skills/demo/alt.md").exists())
        self.assertFalse((repo / "skills/demo/docs").exists())
        self.assertFalse((repo / "skills/demo/.publicignore").exists())
        self.assertTrue((repo / "skills/demo/SKILL.md").is_file())
        # zweiter Lauf ohne Aenderung: kein Commit
        self.assertFalse(ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)["committed"])

    def test_spiegeln_dry_run_schreibt_nichts(self):
        src = self.skill()
        repo = self.repo("oeff")
        ergebnis = ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", True)
        self.assertFalse(ergebnis["committed"])
        self.assertFalse((repo / "skills").exists())

    def test_pruefe_oeffentlich_meldet_verwaiste(self):
        repo = self.repo("oeff")
        self.datei("oeff/skills/alt/x.md", "sauber")
        self.datei("oeff/skills/demo/x.md", "sauber")
        self.datei("oeff/skills/einstellungen.beispiel.json", '{"a": "anna"}\n')
        ergebnis = ps.pruefe_oeffentlich(repo, ["demo"], self.liste)
        self.assertIn("verwaist: skills/alt", ergebnis)
        self.assertNotIn("verwaist: skills/demo", ergebnis)
        self.assertNotIn("verwaist: skills/einstellungen.beispiel.json", ergebnis)
        self.assertIn("skills/einstellungen.beispiel.json:1", ergebnis)
        self.assertEqual(ps.pruefe_oeffentlich(repo, ["demo", "alt"], ps.parse_sperrliste("zzz\n")), [])

    def test_verwaist_maskiert_den_ordnernamen(self):  # I1
        repo = self.repo("oeff")
        self.datei("oeff/skills/beispielfirma-alt/x.md", "sauber")
        ergebnis = ps.pruefe_oeffentlich(repo, [], self.liste)
        self.assertIn("verwaist: skills/***-alt", ergebnis)
        self.assertNotIn("beispielfirma", "".join(ergebnis))

    def test_skillname_mit_begriff_wird_nicht_committet(self):  # I2
        src = self.skill("beispielfirma", inhalt="---\nname: x\n---\nsauber\n")
        repo = self.repo("oeff")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "beispielfirma", self.liste, "m", False)
        self.assertNotIn("beispielfirma", str(ctx.exception))
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")
        self.assertFalse((repo / "skills").exists())

    def test_nachricht_mit_begriff_wird_nicht_committet(self):  # I2
        src = self.skill()
        repo = self.repo("oeff")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "Fix fuer beispielfirma", False)
        self.assertNotIn("beispielfirma", str(ctx.exception))
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")
        self.assertFalse((repo / "skills").exists())

    def test_pruefe_veroeffentlichung_eine_funktion(self):  # I2 / M5
        src = self.skill()
        self.assertEqual(ps.pruefe_veroeffentlichung(src, "demo", "m", self.liste), [])
        self.assertEqual(len(ps.pruefe_veroeffentlichung(src, "anna-x", "m", self.liste)), 1)
        self.assertEqual(len(ps.pruefe_veroeffentlichung(src, "demo", "anna", self.liste)), 1)

    def test_ungetrackte_datei_im_ziel_wird_nicht_committet(self):  # I3
        src = self.skill()
        repo = self.repo("oeff")
        self.datei("oeff/skills/demo/lauf.log", "anna\n")
        self.datei("oeff/skills/demo/__pycache__/x.pyc", b"\x00anna")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertNotIn("anna", str(ctx.exception))
        self.assertEqual(git(repo, "ls-files").strip(), "")
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")
        self.assertTrue((repo / "skills/demo/lauf.log").is_file())  # fremde Datei bleibt liegen
        ergebnis = ps.pruefe_oeffentlich(repo, ["demo"], self.liste)
        self.assertIn("skills/demo/lauf.log:1", ergebnis)
        self.assertIn("skills/demo/__pycache__/x.pyc:0 (binär)", ergebnis)

    def test_ungetrackte_datei_mit_vorhandenem_head(self):  # I3, Index-Ruecksetzen mit HEAD
        src = self.skill()
        repo = self.repo("oeff")
        self.datei("oeff/README.md", "x")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "start")
        self.datei("oeff/skills/demo/lauf.log", "anna\n")
        with self.assertRaises(ps.PublishError):
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertEqual(git(repo, "ls-files").strip(), "README.md")
        self.assertEqual(git(repo, "log", "--format=%s").strip(), "start")

    def test_loeschung_mit_gesperrtem_pfad_wird_committet(self):  # N1
        src = self.skill()
        self.datei("skills/demo/anna-notiz.md", "sauber\n")
        repo = self.repo("oeff")
        self.assertTrue(ps.spiegle_oeffentlich(src, repo, "demo", ps.parse_sperrliste("zzz\n"), "m", False)["committed"])
        (src / "anna-notiz.md").unlink()
        ergebnis = ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "aufraeumen", False)
        self.assertTrue(ergebnis["committed"])
        self.assertNotIn("skills/demo/anna-notiz.md", git(repo, "ls-tree", "-r", "--name-only", "HEAD").split())

    def test_kaputter_symlink_im_ziel_wird_nicht_committet(self):  # S1a
        src = self.skill()
        repo = self.repo("oeff")
        (repo / "skills" / "demo").mkdir(parents=True)
        os.symlink("/Us" + "ers/zzz-x/geheim.txt", repo / "skills/demo/lauf.log")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertIn("skills/demo/lauf.log:0 (symlink)", str(ctx.exception))
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")
        self.assertEqual(git(repo, "ls-files").strip(), "")
        self.assertTrue(os.path.islink(repo / "skills/demo/lauf.log"))  # fremder Link bleibt liegen

    def test_intakter_symlink_im_ziel_wird_nicht_committet(self):  # S1a, Ziel sauber, Link trotzdem gesperrt
        src = self.skill()
        repo = self.repo("oeff")
        self.datei("oeff/sauber.txt", "sauber\n")
        (repo / "skills" / "demo").mkdir(parents=True)
        # *.log ueberspringt der Spiegel beim Aufraeumen, der Link bleibt also im Ziel stehen
        os.symlink("../../sauber.txt", repo / "skills/demo/intakt.log")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertIn("skills/demo/intakt.log:0 (symlink)", str(ctx.exception))
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")

    def test_fremder_symlink_ohne_ausschluss_bricht_ab(self):  # S1a, seit A1 Abbruch statt Wegraeumen
        src = self.skill()
        repo = self.repo("oeff")
        (repo / "skills" / "demo").mkdir(parents=True)
        os.symlink("/Us" + "ers/zzz-x/geheim.txt", repo / "skills/demo/link.txt")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertIn("skills/demo/link.txt", str(ctx.exception))
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")
        self.assertTrue(os.path.islink(repo / "skills/demo/link.txt"))  # fremder Link bleibt liegen

    def aussen(self):
        """Fremder Ordner ausserhalb des Repos mit einer Datei, die kein Spiegel anfassen darf."""
        self.datei("aussen/fremd.md", "fremd\n")
        return self.tmp / "aussen"

    def assert_aussen_unberuehrt(self, aussen):
        self.assertEqual(sorted(p.name for p in aussen.iterdir()), ["fremd.md"])
        self.assertEqual((aussen / "fremd.md").read_text(encoding="utf-8"), "fremd\n")

    def test_a1_zielordner_ist_symlink(self):
        src = self.skill()
        repo = self.repo("oeff")
        aussen = self.aussen()
        (repo / "skills").mkdir()
        os.symlink(str(aussen), repo / "skills/demo")
        with self.assertRaises(ps.PublishError):
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assert_aussen_unberuehrt(aussen)
        self.assertEqual(git(repo, "rev-list", "--all").strip(), "")

    def test_a1_elternordner_ist_symlink(self):
        src = self.skill()
        repo = self.repo("oeff")
        aussen = self.aussen()
        os.symlink(str(aussen), repo / "skills")
        with self.assertRaises(ps.PublishError):
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assert_aussen_unberuehrt(aussen)

    def test_a1_datei_im_ziel_ist_symlink(self):
        src = self.skill()
        repo = self.repo("oeff")
        aussen = self.aussen()
        (repo / "skills/demo").mkdir(parents=True)
        os.symlink(str(aussen / "fremd.md"), repo / "skills/demo/SKILL.md")
        with self.assertRaises(ps.PublishError):
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assert_aussen_unberuehrt(aussen)

    def test_a1_unterordner_im_ziel_ist_symlink(self):
        src = self.skill()
        self.datei("skills/demo/scripts/s.py", "x = 1\n")
        repo = self.repo("oeff")
        aussen = self.aussen()
        (repo / "skills/demo").mkdir(parents=True)
        os.symlink(str(aussen), repo / "skills/demo/scripts")
        with self.assertRaises(ps.PublishError):
            ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assert_aussen_unberuehrt(aussen)

    def test_a1_privater_spiegel_folgt_keinem_symlink(self):
        src = self.skill()
        repo = self.repo("privat")
        aussen = self.aussen()
        os.symlink(str(aussen), repo / "demo")
        with self.assertRaises(ps.PublishError):
            ps.mirror_skill(src, repo / "demo", False, wurzel=repo)
        self.assert_aussen_unberuehrt(aussen)

    def test_symlink_in_ausgeschlossenem_ordner_sperrt_nicht(self):
        ziel = self.tmp / "repo/demo"
        for ordner in ("node_modules/paket", "venv/lib"):
            (ziel / ordner).mkdir(parents=True)
            os.symlink("/nicht/da", ziel / ordner / "link")
        try:
            ps.pruefe_symlinks(self.tmp / "repo", ziel)
        except ps.PublishError as exc:
            self.fail(f"Links in node_modules/venv duerfen nicht sperren: {exc}")
        os.symlink("/nicht/da", ziel / "node_modules" / "oben")
        os.symlink(str(self.tmp), ziel / ".venv")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.pruefe_symlinks(self.tmp / "repo", ziel)
        self.assertIn("demo/.venv:0 (symlink)", str(ctx.exception))
        self.assertNotIn("oben", str(ctx.exception))

    def test_symlinks_ohne_oserror_gemeldet(self):  # S1b
        repo = self.repo("oeff")
        self.datei("oeff/skills/demo/x.md", "sauber")
        os.symlink("/nicht/da", repo / "skills/demo/kaputt.log")
        os.symlink(str(self.tmp), repo / "skills/demo/ordnerlink")
        ergebnis = ps.pruefe_oeffentlich(repo, ["demo"], self.liste)
        self.assertIn("skills/demo/kaputt.log:0 (symlink)", ergebnis)
        self.assertIn("skills/demo/ordnerlink:0 (symlink)", ergebnis)
        src = self.skill()
        os.symlink("/nicht/da", src / "kaputt.md")
        self.assertEqual(ps.pruefe_dateien(src, [Path("kaputt.md")], self.liste), ["kaputt.md:0 (symlink)"])

    def test_unlesbare_datei_ohne_oserror(self):  # S1b
        src = self.skill()
        gesperrt = self.datei("skills/demo/zu.md", "sauber\n")
        gesperrt.chmod(0)
        self.addCleanup(gesperrt.chmod, 0o644)
        self.assertEqual(ps.pruefe_dateien(src, [Path("zu.md")], self.liste), ["zu.md:0 (unlesbar)"])

    def test_spiegeln_pusht_nie(self):  # I6
        src = self.skill()
        repo = self.repo("oeff")
        bare = self.tmp / "bare.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
        git(repo, "remote", "add", "origin", str(bare))
        git(repo, "config", "branch.main.remote", "origin")  # M2: auch ein nacktes "git push" faende ein Ziel
        git(repo, "config", "branch.main.merge", "refs/heads/main")
        ergebnis = ps.spiegle_oeffentlich(src, repo, "demo", self.liste, "m", False)
        self.assertTrue(ergebnis["committed"])
        self.assertEqual(git(bare, "rev-list", "--all").strip(), "")


class EinstellungenTest(Basis):
    def test_einstellungen_fehlen(self):
        self.assertEqual(ps.lade_einstellungen(), {})
        self.einst.write_text("{kaputt", encoding="utf-8")
        with self.assertRaises(ps.PublishError) as ctx:
            ps.lade_einstellungen()
        self.assertIn(str(self.einst), str(ctx.exception))
        self.schreibe_einstellungen({"skill_repo": "~/r"})
        self.assertEqual(ps.lade_einstellungen(), {"skill_repo": "~/r"})
        anders = self.datei("anders.json", '{"vault": "v"}')
        self.assertEqual(ps.lade_einstellungen(anders), {"vault": "v"})

    def test_sperrliste_vorgabe_ohne_schluessel(self):  # I5
        vorgabe = self.tmp / "home" / ".config" / "cockpit" / "public-denylist.txt"
        vorgabe.parent.mkdir(parents=True)
        vorgabe.write_text("beispielfirma\n", encoding="utf-8")
        self.assertEqual(ps.lade_sperrliste({}), (["beispielfirma"], []))
        eigene = self.datei("eigene.txt", "anna\n")
        self.assertEqual(ps.lade_sperrliste({"sperrliste": str(eigene)}), (["anna"], []))
        vorgabe.write_text("# leer\n", encoding="utf-8")
        with self.assertRaises(ps.PublishError):
            ps.lade_sperrliste({})
        vorgabe.unlink()
        with self.assertRaises(ps.PublishError) as ctx:
            ps.lade_sperrliste({})
        self.assertIn("public-denylist.txt", str(ctx.exception))

    def test_a3_sperrliste_nicht_utf8(self):
        kaputt = self.datei("kaputt.txt", b"anna\n\xff\xfe\xfa\n")
        with self.assertRaises(ps.EinstellungsFehler) as ctx:
            ps.lade_sperrliste({"sperrliste": str(kaputt)})
        self.assertIn(str(kaputt), str(ctx.exception))

    def test_a4_oeffentlich_muss_liste_sein(self):
        self.assertEqual(ps.oeffentlich_liste({}), [])
        self.assertEqual(ps.oeffentlich_liste({"oeffentlich": None}), [])
        self.assertEqual(ps.oeffentlich_liste({"oeffentlich": ["demo", "lint"]}), ["demo", "lint"])
        for falsch in ("demo", "demo,lint", {"demo": 1}, ["demo", 3]):
            with self.assertRaises(ps.EinstellungsFehler, msg=repr(falsch)) as ctx:
                ps.oeffentlich_liste({"oeffentlich": falsch})
            self.assertIn("oeffentlich", str(ctx.exception))


class CliTest(Basis):
    def setUp(self):
        super().setUp()
        # Schutz: Feste Vorgabepfade im Modul (alte Fassung) wuerden echte Repos und den Vault beschreiben.
        for name in ("HOME", "DEFAULT_SKILLS_DIR", "DEFAULT_REPO_DIR", "DEFAULT_VAULT_DIR", "DEFAULT_REMOTE_SLUG"):
            if hasattr(ps, name):
                self.fail(f"publish_skill.{name} existiert noch; CLI-Tests laufen nicht gegen feste Pfade")
        self.assertEqual(Path.home(), self.tmp / "home")

    def lauf(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ps.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cli_ohne_skill_repo_klartext(self):
        self.schreibe_einstellungen({})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "x", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn("skill_repo", err)
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))

    def test_a6_subprozess_ohne_datei_nennt_pfad(self):
        self.assertFalse(self.einst.exists())
        src = self.skill()
        proc = subprocess.run([sys.executable, "-I", ps.__file__, "demo", "-m", "x",
                               "--skills-dir", str(src.parent)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("skill_repo", proc.stderr)
        self.assertIn(str(self.einst), proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_a5_skillname_mit_pfad_exit2(self):
        privat = self.repo("privat")
        self.schreibe_einstellungen({"skill_repo": str(privat)})
        src = self.skill()
        self.skill("lint")
        for name in ("../skills/lint", "../x", ".versteckt", "a b", "lint/../demo"):
            code, _, err = self.lauf([name, "-m", "neu", "--skills-dir", str(src.parent)])
            self.assertEqual(code, 2, name)
            self.assertIn("Skillname", err, name)
        self.assertEqual(sorted(p.name for p in privat.iterdir()), [".git"])
        self.assertIn("version: 1.0.0", (self.tmp / "skills/lint/SKILL.md").read_text(encoding="utf-8"))

    def test_a4_cli_oeffentlich_als_string_exit2(self):
        repo = self.oeffentlich_einrichten()
        daten = json.loads(self.einst.read_text(encoding="utf-8"))
        daten["oeffentlich"] = "demo"
        self.schreibe_einstellungen(daten)
        self.datei("oeff/skills/demo/a.md", "sauber\n")
        code, _, err = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn("oeffentlich", err)
        daten["skill_repo"] = str(self.repo("privat"))
        self.schreibe_einstellungen(daten)
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue((repo / "skills/demo/a.md").is_file())

    def test_a8_fehlender_doku_ordner_vor_jedem_schreiben(self):
        privat = self.repo("privat")
        (self.tmp / "vault").mkdir()
        self.schreibe_einstellungen({"skill_repo": str(privat), "vault": str(self.tmp / "vault")})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn("03 Bereiche", err)
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(privat, "log", "--oneline", "--all").strip(), "")
        self.assertFalse((privat / "demo").exists())

    def test_a8_skill_repo_ohne_git_vor_jedem_schreiben(self):
        kein_repo = self.tmp / "keinrepo"
        kein_repo.mkdir()
        self.schreibe_einstellungen({"skill_repo": str(kein_repo)})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn(str(kein_repo), err)
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(list(kein_repo.iterdir()), [])

    def test_a8_oeffentliches_repo_ohne_git_vor_jedem_schreiben(self):
        privat = self.repo("privat")
        sperr = self.datei("sperrliste.txt", LISTE_TEXT)
        (self.tmp / "oeff").mkdir()
        self.schreibe_einstellungen({"skill_repo": str(privat), "oeffentlich": ["demo"],
                                     "oeffentlich_repo": str(self.tmp / "oeff"), "sperrliste": str(sperr)})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn("oeff", err)
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(privat, "log", "--oneline", "--all").strip(), "")

    def test_symlink_im_privaten_ziel_vor_jedem_schreiben(self):
        privat = self.repo("privat")
        aussen = self.tmp / "aussen"
        aussen.mkdir()
        os.symlink(str(aussen), privat / "demo")
        self.schreibe_einstellungen({"skill_repo": str(privat)})
        src = self.skill()
        with self.assertRaises(ps.PublishError) as ctx:
            self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertIn("demo:0 (symlink)", str(ctx.exception))
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(list(aussen.iterdir()), [])

    def test_symlink_im_oeffentlichen_ziel_vor_jedem_schreiben(self):
        repo = self.oeffentlich_einrichten()
        daten = json.loads(self.einst.read_text(encoding="utf-8"))
        privat = self.repo("privat")
        daten["skill_repo"] = str(privat)
        self.schreibe_einstellungen(daten)
        self.datei("oeff/skills/demo/a.md", "sauber\n")
        os.symlink("/nicht/da", repo / "skills/demo/link.md")
        src = self.skill()
        with self.assertRaises(ps.PublishError) as ctx:
            self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertIn("skills/demo/link.md:0 (symlink)", str(ctx.exception))
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(privat, "log", "--oneline", "--all").strip(), "")
        self.assertFalse((privat / "demo").exists())

    def test_create_remote_ohne_slug_vor_jedem_schreiben(self):
        privat = self.repo("privat")
        self.schreibe_einstellungen({"skill_repo": str(privat)})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--create-remote", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn("skill_remote", err)
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(privat, "log", "--oneline", "--all").strip(), "")
        self.assertFalse((privat / "demo").exists())

    def test_bump_hebt_auch_skill_en(self):
        privat = self.repo("privat")
        self.schreibe_einstellungen({"skill_repo": str(privat)})
        src = self.skill()
        self.datei("skills/demo/SKILL.en.md", "---\nname: demo\nversion: 1.0.0\n---\nText en\n")
        code, _, err = self.lauf(["demo", "-m", "neu", "--bump", "minor", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 0, err)
        self.assertIn("version: 1.1.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual((src / "SKILL.en.md").read_text(encoding="utf-8"),
                         "---\nname: demo\nversion: 1.1.0\n---\nText en\n")
        self.assertIn("version: 1.1.0", (privat / "demo/SKILL.en.md").read_text(encoding="utf-8"))

    def test_create_remote_ohne_slug_mit_origin_laeuft(self):
        privat = self.repo("privat")
        bare = self.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
        git(privat, "remote", "add", "origin", str(bare))
        self.schreibe_einstellungen({"skill_repo": str(privat)})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--create-remote", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 0, err)
        self.assertIn("version: 1.0.1", (src / "SKILL.md").read_text(encoding="utf-8"))

    # --- A2: Historien-Gate -------------------------------------------------

    def historie_einrichten(self):
        """Oeffentliches Repo mit Wegwerf-origin (bare); ein sauberer Commit ist gepusht."""
        repo = self.oeffentlich_einrichten()
        bare = self.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
        git(repo, "remote", "add", "origin", str(bare))
        self.datei("oeff/skills/demo/SKILL.md", "sauber\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "start")
        git(repo, "push", "-q", "-u", "origin", "main")
        return repo

    def commit(self, repo, nachricht):
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", nachricht)
        return git(repo, "rev-parse", "--short=7", "HEAD").strip()

    def test_a2_verwaister_ordner_nur_in_zwischencommit(self):
        repo = self.historie_einrichten()
        self.datei("oeff/skills/beispielfirma-alt/x.md", "sauber\n")
        sha = self.commit(repo, "dazu")
        git(repo, "rm", "-q", "-r", "skills/beispielfirma-alt")
        self.commit(repo, "weg")
        self.assertEqual(ps.pruefe_oeffentlich(repo, ["demo"], ps.parse_sperrliste(LISTE_TEXT)), [])
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn(f"verwaist in Historie: skills/***-alt ({sha})", out)
        self.assertNotIn("beispielfirma", out)

    def test_a2_sperrbegriff_nur_in_zwischencommit(self):
        repo = self.historie_einrichten()
        self.datei("oeff/skills/demo/notiz.md", "sauber\nhier beispielfirma\n")
        sha = self.commit(repo, "dazu")
        self.datei("oeff/skills/demo/notiz.md", "sauber\n")
        self.commit(repo, "bereinigt")
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn(f"skills/demo/notiz.md:2 ({sha})", out)
        self.assertNotIn("beispielfirma", out)

    def test_a2_sperrbegriff_in_commit_nachricht(self):
        repo = self.historie_einrichten()
        self.datei("oeff/skills/demo/notiz.md", "sauber\n")
        sha = self.commit(repo, "Kopf\n\nFix fuer anna")
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn(f"Commit-Nachricht ({sha}):3", out)
        self.assertNotIn("Fix fuer anna", out)

    def test_a2_saubere_historie_exit0(self):
        repo = self.historie_einrichten()
        self.datei("oeff/skills/demo/notiz.md", "sauber\n")
        self.commit(repo, "sauber")
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 0, out)
        self.assertIn("Historie", out)

    def test_a2_ohne_upstream_nur_arbeitsbaum_mit_hinweis(self):
        repo = self.oeffentlich_einrichten()
        self.datei("oeff/skills/demo/SKILL.md", "beispielfirma\n")
        self.commit(repo, "start")
        self.datei("oeff/skills/demo/SKILL.md", "sauber\n")
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 0, out)
        self.assertIn("kein Upstream", out)

    def oeffentlich_einrichten(self, liste_text=LISTE_TEXT):
        repo = self.repo("oeff")
        sperr = self.datei("sperrliste.txt", liste_text)
        self.schreibe_einstellungen({"oeffentlich_repo": str(repo), "oeffentlich": ["demo"],
                                     "sperrliste": str(sperr)})
        return repo

    def test_cli_pruefe_oeffentlich_exit2_bei_treffer(self):
        self.oeffentlich_einrichten()
        self.datei("oeff/skills/demo/a.md", "beispielfirma\n")
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn("skills/demo/a.md:1", out)
        self.assertNotIn("beispielfirma", out)
        self.datei("oeff/skills/demo/a.md", "sauber\n")
        self.assertEqual(self.lauf(["--pruefe-oeffentlich"])[0], 0)
        self.datei("oeff/skills/weg/a.md", "sauber\n")
        code, out, _ = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn("verwaist: skills/weg", out)

    def test_cli_pruefe_oeffentlich_ohne_liste_oder_repo(self):
        self.oeffentlich_einrichten(liste_text="# nur Kommentar\n")
        code, _, err = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn("Sperrliste", err)
        self.schreibe_einstellungen({"oeffentlich": ["demo"]})
        code, _, err = self.lauf(["--pruefe-oeffentlich"])
        self.assertEqual(code, 2)
        self.assertIn("oeffentlich_repo", err)

    def test_normalaufruf_mit_oeffentlichem_schritt(self):
        privat = self.repo("privat")
        repo = self.oeffentlich_einrichten()
        daten = json.loads(self.einst.read_text(encoding="utf-8"))
        daten["skill_repo"] = str(privat)
        self.schreibe_einstellungen(daten)
        src = self.skill()
        code, out, _ = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 0)
        self.assertIn("6/6 Öffentlich", out)
        self.assertIn("Vault", out)  # Warnung: kein vault gesetzt, Doku-Schritt entfaellt
        self.assertEqual(git(privat, "log", "-1", "--format=%s").strip(), "demo: neu")
        self.assertEqual(git(repo, "log", "-1", "--format=%s").strip(), "skills/demo: neu")
        self.assertIn("version: 1.0.1", (repo / "skills/demo/SKILL.md").read_text(encoding="utf-8"))

    def test_normalaufruf_nicht_oeffentlich_ohne_schritt_6(self):
        privat = self.repo("privat")
        self.schreibe_einstellungen({"skill_repo": str(privat)})
        src = self.skill()
        code, out, _ = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("5/5", out)
        self.assertNotIn("Öffentlich", out)

    def test_oeffentlicher_skill_mit_treffer_bricht_vor_jedem_schreiben_ab(self):
        privat = self.repo("privat")
        repo = self.oeffentlich_einrichten()
        daten = json.loads(self.einst.read_text(encoding="utf-8"))
        daten["skill_repo"] = str(privat)
        self.schreibe_einstellungen(daten)
        src = self.skill(inhalt="---\nname: demo\nversion: 1.0.0\n---\nanna\n")
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ps.PublishError):
                ps.main(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertFalse((repo / "skills").exists())
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(privat, "log", "--oneline", "--all").strip(), "")

    def test_oeffentlicher_skill_ohne_sperrliste_bricht_vor_jedem_schreiben_ab(self):
        privat = self.repo("privat")
        self.schreibe_einstellungen({"skill_repo": str(privat), "oeffentlich": ["demo"],
                                     "oeffentlich_repo": str(self.tmp / "oeff")})
        src = self.skill()
        code, _, err = self.lauf(["demo", "-m", "neu", "--skills-dir", str(src.parent)])
        self.assertEqual(code, 2)
        self.assertIn("public-denylist.txt", err)  # Vorgabepfad fehlt im Temp-Home
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))

    def test_oeffentlicher_skill_nachricht_mit_begriff_bricht_vor_jedem_schreiben_ab(self):  # I2
        privat = self.repo("privat")
        repo = self.oeffentlich_einrichten()
        daten = json.loads(self.einst.read_text(encoding="utf-8"))
        daten["skill_repo"] = str(privat)
        self.schreibe_einstellungen(daten)
        src = self.skill()
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ps.PublishError) as ctx:
                ps.main(["demo", "-m", "Fix fuer beispielfirma", "--skills-dir", str(src.parent)])
        self.assertNotIn("beispielfirma", str(ctx.exception))
        self.assertFalse((repo / "skills").exists())
        self.assertIn("version: 1.0.0", (src / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(git(privat, "log", "--oneline", "--all").strip(), "")


if __name__ == "__main__":
    unittest.main()
