"""Tests fuer reload_verlust.py. Jeder Test baut sich Wegwerf-Ordner (Transkripte, Cockpit, Vault, Git-Repo)."""
import atexit
import contextlib
import datetime as dt
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

# Vorspann VOR dem Import: HOME und Einstellungsdatei zeigen in einen Wegwerf-Ordner, damit kein Test
# die echte Konfiguration, den echten Vault oder echte Repos liest.
_VORSPANN_HOME = tempfile.mkdtemp(prefix="reload-verlust-home-")
atexit.register(shutil.rmtree, _VORSPANN_HOME, True)
os.environ["HOME"] = _VORSPANN_HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_VORSPANN_HOME, "fehlt.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reload_verlust as rv  # noqa: E402


@contextlib.contextmanager
def mit_einstellungen(**werte):
    """Temp-Einstellungsdatei mit diesen Werten, per CLAUDE_SKILLS_EINSTELLUNGEN aktiv."""
    d = tempfile.mkdtemp(prefix="reload-verlust-einst-")
    try:
        pfad = os.path.join(d, "einstellungen.json")
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(werte, fh)
        with mock.patch.dict(os.environ, {"CLAUDE_SKILLS_EINSTELLUNGEN": pfad}):
            yield pfad
    finally:
        shutil.rmtree(d, ignore_errors=True)

CUT = dt.datetime(2026, 10, 21, 14, 0).astimezone()


def at(minutes_before):
    return CUT - dt.timedelta(minutes=minutes_before)


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = self.tmp.name
        self.projects, self.cockpit, self.vault, self.repos = (os.path.join(b, x) for x in ("projects", "cockpit", "vault", "repos"))
        for d in (os.path.join(self.projects, "-proj"), os.path.join(self.cockpit, "sessions"), self.vault, self.repos):
            os.makedirs(d)

    def transcript(self, sid, msgs, bridge=None, cwd="/nirgends", open_call=False):
        """msgs: [(minuten_vor_cut, kontext)]"""
        lines = []
        if bridge:
            lines.append({"type": "bridge-session", "sessionId": sid, "bridgeSessionId": "cse_" + bridge})
        for i, (mins, ctx) in enumerate(msgs):
            lines.append({"type": "user", "cwd": cwd, "timestamp": iso(at(mins)), "message": {"content": f"Frage {i}"}})
            content = [{"type": "text", "text": "Antwort"}]
            if open_call and i == len(msgs) - 1:
                content.append({"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "sleep 99"}})
            lines.append({"type": "assistant", "cwd": cwd, "timestamp": iso(at(mins)), "message": {
                "content": content, "usage": {"input_tokens": ctx, "cache_read_input_tokens": 0}}})
        p = os.path.join(self.projects, "-proj", sid + ".jsonl")
        with open(p, "w") as fh:
            fh.write("\n".join(json.dumps(x) for x in lines) + "\n")
        os.utime(p, (at(msgs[-1][0]).timestamp(),) * 2 if msgs else None)

    def status(self, sid, minutes_before, ctx):
        with open(os.path.join(self.cockpit, "sessions", sid + ".json"), "w") as fh:
            json.dump({"session_id": sid, "written_at": int(at(minutes_before).timestamp()), "context_tokens": ctx,
                       "model": "Test"}, fh)

    def note(self, rel, text, minutes_before):
        p = os.path.join(self.vault, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
        os.utime(p, (at(minutes_before).timestamp(),) * 2)

    def repo(self, name):
        p = os.path.join(self.repos, name)
        os.makedirs(p)
        subprocess.run(["git", "init", "-q", "-b", "main", p], check=True)
        return p

    def commit(self, repo, msg, minutes_before):
        with open(os.path.join(repo, "f.txt"), "a") as fh:
            fh.write(msg + "\n")
        env = dict(os.environ, GIT_AUTHOR_DATE=at(minutes_before).isoformat(), GIT_COMMITTER_DATE=at(minutes_before).isoformat(),
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        subprocess.run(["git", "-C", repo, "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", repo, "commit", "-q", "-m", msg], check=True, env=env)

    def run(self):
        return rv.analyse(CUT, 12, self.projects, self.cockpit, self.vault, [self.repos])

    def verdicts(self):
        return {r["id"]: r["verdict"] for r in self.run()["rows"]}


BR = "01AAAAAAAAAAAAAAAAAAAAAAAA"
BR2 = "01BBBBBBBBBBBBBBBBBBBBBBBB"


def session_url(kennung):
    # In zwei Teilen: der Test-Fixture soll keine echt aussehende Session-Adresse als Text tragen.
    return "https://claude.ai/code/" + "session_" + kennung


class TestBelege(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def tearDown(self):
        self.f.tmp.cleanup()

    def test_kontext_abweichung_ist_verlust(self):
        self.f.transcript("s1", [(200, 1000)])
        self.f.status("s1", 10, 5000)
        self.assertEqual(self.f.verdicts()["s1"], "VERLUST")

    def test_leerlauf_mit_neuem_zeitstempel_ist_ok(self):
        # Statuszeile schreibt auch im Leerlauf; gleicher Kontext heisst: nichts Neues.
        self.f.transcript("s1", [(200, 1000)])
        self.f.status("s1", 1, 1000)
        self.assertEqual(self.f.verdicts()["s1"], "OK")

    def test_commit_mit_eigenem_trailer_ist_verlust(self):
        repo = self.f.repo("r")
        self.f.transcript("s1", [(200, 1000)], bridge=BR, cwd=repo)
        self.f.commit(repo, f"Arbeit\n\nClaude-Session: {session_url(BR)}", 30)
        res = self.f.run()
        row = res["rows"][0]
        self.assertEqual(row["verdict"], "VERLUST")
        self.assertIn("Commit", row["proof"][0][1])

    def test_commit_mit_fremdem_trailer_ist_kein_beleg(self):
        repo = self.f.repo("r")
        self.f.transcript("s1", [(200, 1000)], bridge=BR, cwd=repo)
        self.f.commit(repo, f"Arbeit\n\nClaude-Session: {session_url(BR2)}", 30)
        self.assertEqual(self.f.run()["loose"], [])  # ohne betroffene Sitzung kein Fenster
        self.f.transcript("s2", [(250, 1000)])
        self.f.status("s2", 10, 5000)
        res = self.f.run()
        self.assertEqual({r["id"]: r["verdict"] for r in res["rows"]}, {"s1": "OK", "s2": "VERLUST"})
        self.assertEqual(len(res["loose"]), 1)

    def test_commit_kurz_nach_letzter_nachricht_ist_kein_beleg(self):
        repo = self.f.repo("r")
        self.f.transcript("s1", [(200, 1000)], bridge=BR, cwd=repo)
        self.f.commit(repo, f"Arbeit\n\nClaude-Session: {session_url(BR)}", 195)
        self.assertEqual(self.f.verdicts()["s1"], "OK")

    def test_vault_datei_mit_session_url_ist_verlust(self):
        self.f.transcript("s1", [(200, 1000)], bridge=BR)
        self.f.note("Handoffs/h.md", f"chat_url: {session_url(BR)}\n", 20)
        self.assertEqual(self.f.verdicts()["s1"], "VERLUST")

    def test_vault_datei_vor_letzter_nachricht_ist_kein_beleg(self):
        self.f.transcript("s1", [(200, 1000)], bridge=BR)
        self.f.note("Handoffs/h.md", f"chat_url: {session_url(BR)}\n", 300)
        self.assertEqual(self.f.verdicts()["s1"], "OK")

    def test_geteilte_remote_session_gehoert_der_juengsten(self):
        # Nach /clear behaelt der Tab die Remote-Session; nur die juengere Sitzung bekommt den Beleg.
        self.f.transcript("alt", [(400, 1000)], bridge=BR)
        self.f.transcript("neu", [(200, 1000)], bridge=BR)
        self.f.note("h.md", f"session_{BR}", 20)
        self.assertEqual(self.f.verdicts(), {"alt": "OK", "neu": "VERLUST"})

    def test_geteilte_remote_session_commit_gehoert_der_juengsten(self):
        repo = self.f.repo("r")
        self.f.transcript("alt", [(400, 1000)], bridge=BR, cwd=repo)
        self.f.transcript("neu", [(200, 1000)], bridge=BR, cwd=repo)
        self.f.commit(repo, f"Arbeit\n\nClaude-Session: {session_url(BR)}", 20)
        self.assertEqual(self.f.verdicts(), {"alt": "OK", "neu": "VERLUST"})

    def test_git_ignoriert_ctime(self):
        # iCloud-Ordner: ohne trustctime=false haengt git status pro Worktree bis zum Zeitlimit.
        self.assertIn("core.trustctime=false", rv.GIT)

    def test_tab_ohne_transkript(self):
        self.f.status("voll", 30, 120000)
        self.f.status("leer", 30, 0)
        self.f.status("danach", -5, 50000)
        self.assertEqual(self.f.verdicts(), {"voll": "KEIN TRANSKRIPT"})

    def test_offener_aufruf(self):
        self.f.transcript("s1", [(300, 1000), (60, 1000)], open_call=True)
        self.assertEqual(self.f.verdicts()["s1"], "OFFENER AUFRUF")

    def test_nachrichten_nach_dem_neustart_zaehlen_nicht_als_davor(self):
        self.f.transcript("s1", [(200, 1000), (-30, 9000)])
        row = self.f.run()["rows"][0]
        self.assertEqual(row["tr"]["after"], 2)
        self.assertEqual(row["tr"]["last_ctx"], 1000)

    def test_ungesicherter_worktree_wird_gemeldet(self):
        repo = self.f.repo("r")
        self.f.commit(repo, "basis", 600)
        self.f.transcript("s1", [(200, 1000)], cwd=repo)
        self.f.status("s1", 10, 5000)
        with open(os.path.join(repo, "neu.txt"), "w") as fh:
            fh.write("x")
        res = self.f.run()
        self.assertEqual([d[0] for d in res["dirty"]], [os.path.realpath(repo)])

    def test_bericht_nennt_belege(self):
        self.f.transcript("s1", [(200, 1000)])
        self.f.status("s1", 10, 5000)
        out = io.StringIO()
        rv.report(CUT, "test", None, self.f.run(), 12, out=out)
        self.assertIn("[VERLUST]", out.getvalue())
        self.assertIn("1 von 1 Sitzungen betroffen", out.getvalue())


class TestZeit(unittest.TestCase):
    def test_parse_zeit(self):
        now = dt.datetime(2026, 10, 21, 18, 0).astimezone()
        self.assertEqual(rv.parse_zeit("14:06", now).strftime("%d %H:%M"), "21 14:06")
        self.assertEqual(rv.parse_zeit("2026-10-20 09:05").strftime("%d %H:%M"), "20 09:05")
        with self.assertRaises(ValueError):
            rv.parse_zeit("gestern")

    def test_falsche_zeit_gibt_exit_1(self):
        stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            self.assertEqual(rv.main(["--zeit", "quatsch"]), 1)
        finally:
            sys.stderr = stderr


class TestEinstellungen(unittest.TestCase):
    def lauf(self, argv):
        """main mit gesperrter Analyse; liefert (exit, analyse-Aufruf oder None, stderr)."""
        aufrufe = []
        err = io.StringIO()
        with mock.patch.object(rv, "analyse", side_effect=lambda *a: aufrufe.append(a) or {}), \
                mock.patch.object(rv, "report"), mock.patch("sys.stderr", err):
            code = rv.main(["--zeit", "2026-10-20 09:05"] + argv)
        return code, (aufrufe[0] if aufrufe else None), err.getvalue()

    def test_vault_aus_einstellungen(self):
        with tempfile.TemporaryDirectory() as d, mit_einstellungen(vault=d):
            code, aufruf, _ = self.lauf([])
        self.assertEqual(code, 0)
        self.assertEqual(aufruf[4], d)

    def test_vault_argument_geht_vor(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as e, mit_einstellungen(vault=d):
            code, aufruf, _ = self.lauf(["--vault", e])
        self.assertEqual(aufruf[4], e)

    def test_ohne_vault_exit2(self):
        with mit_einstellungen() as pfad:
            code, aufruf, err = self.lauf([])
        self.assertEqual(code, 2)
        self.assertIsNone(aufruf)
        self.assertIn("Vault-Pfad fehlt", err)
        self.assertIn(pfad, err)
        self.assertNotIn("Traceback", err)

    def test_fehlender_vault_ordner_exit2(self):  # B3: nicht still uebergehen
        with tempfile.TemporaryDirectory() as d:
            weg = os.path.join(d, "gibt-es-nicht")
            for argv, werte in (([], {"vault": weg}), (["--vault", weg], {})):
                with mit_einstellungen(**werte):
                    code, aufruf, err = self.lauf(argv)
                self.assertEqual(code, 2, argv)
                self.assertIsNone(aufruf)
                self.assertIn("Vault nicht gefunden: %s" % weg, err)
                self.assertNotIn("Traceback", err)

    def test_kaputte_einstellungen_exit2_ohne_traceback(self):
        d = tempfile.mkdtemp()
        try:
            pfad = os.path.join(d, "e.json")
            with open(pfad, "w") as fh:
                fh.write("{kaputt")
            with mock.patch.dict(os.environ, {"CLAUDE_SKILLS_EINSTELLUNGEN": pfad}):
                code, aufruf, err = self.lauf(["--vault", d])
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(code, 2)
        self.assertIn(pfad, err)
        self.assertNotIn("Traceback", err)

    def test_repos_vorgabe_aus_einstellungen(self):
        with tempfile.TemporaryDirectory() as v, mit_einstellungen(vault=v, repo_wurzeln=["/a/eins", "/a/zwei"]):
            code, aufruf, _ = self.lauf([])
        self.assertEqual(aufruf[5], ["/a/eins", "/a/zwei"])

    def test_repo_wurzeln_falscher_typ_exit2(self):
        for wert in ("~/Developer", 5, [], [1, "a"], ["a", None], {"a": 1}, True):
            with self.subTest(wert=wert), tempfile.TemporaryDirectory() as v, \
                    mit_einstellungen(vault=v, repo_wurzeln=wert) as pfad:
                code, aufruf, err = self.lauf([])
                self.assertEqual(code, 2)
                self.assertIsNone(aufruf)
                self.assertIn("repo_wurzeln", err)
                self.assertIn(pfad, err)
                self.assertNotIn("Traceback", err)

    def test_repo_wurzeln_falscher_typ_egal_mit_repos_argument(self):
        # ASSUMPTION: --repos ersetzt die Einstellung, also wird sie dann nicht geprueft, weil sie nicht gebraucht wird
        with tempfile.TemporaryDirectory() as v, mit_einstellungen(vault=v, repo_wurzeln=5):
            code, aufruf, _ = self.lauf(["--repos", "/b/drei"])
        self.assertEqual(code, 0)
        self.assertEqual(aufruf[5], ["/b/drei"])

    def test_repo_wurzeln_leere_strings_exit2(self):
        for wert in ([""], ["  "], ["/a/eins", ""]):
            with self.subTest(wert=wert), tempfile.TemporaryDirectory() as v, \
                    mit_einstellungen(vault=v, repo_wurzeln=wert) as pfad:
                code, aufruf, err = self.lauf([])
                self.assertEqual(code, 2)
                self.assertIsNone(aufruf)
                self.assertIn("repo_wurzeln", err)
                self.assertIn(pfad, err)

    def test_repo_wurzeln_null_nimmt_vorgabe(self):
        with tempfile.TemporaryDirectory() as v, mit_einstellungen(vault=v, repo_wurzeln=None):
            code, aufruf, _ = self.lauf([])
        self.assertEqual(code, 0)
        self.assertEqual(aufruf[5], [os.path.expanduser("~/Developer")])

    def test_repos_vorgabe_ohne_einstellung(self):
        with tempfile.TemporaryDirectory() as v, mit_einstellungen(vault=v):
            code, aufruf, _ = self.lauf([])
        self.assertEqual(aufruf[5], [os.path.expanduser("~/Developer")])

    def test_repos_argument_geht_vor(self):
        with tempfile.TemporaryDirectory() as v, mit_einstellungen(vault=v, repo_wurzeln=["/a/eins"]):
            code, aufruf, _ = self.lauf(["--repos", "/b/drei"])
        self.assertEqual(aufruf[5], ["/b/drei"])


if __name__ == "__main__":
    unittest.main()
