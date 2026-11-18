import os
import subprocess
from pathlib import Path

WURZEL = Path(__file__).parent.parent
WAECHTER = WURZEL / "hooks" / "reel_guard.sh"


def _lauf(nutzlast: str, tmp_path):
    # Der Waechter sucht den Skill unter $HOME/.claude/skills/reel-ingest; conftest setzt HOME auf
    # einen Wegwerf-Ordner, also dort einen Verweis auf diese Skill-Wurzel anlegen.
    home = tmp_path / "home"
    (home / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    link = home / ".claude" / "skills" / "reel-ingest"
    if not link.exists():
        link.symlink_to(WURZEL)
    env = dict(os.environ, HOME=str(home))
    return subprocess.run([str(WAECHTER)], input=nutzlast,
                          capture_output=True, text=True, env=env)


def test_normaler_prompt_wird_sofort_durchgelassen(tmp_path):
    # Der Waechter feuert bei JEDEM Prompt — er muss ohne Wirkung aussteigen.
    e = _lauf('{"prompt": "lass mal die Tests laufen"}', tmp_path)
    assert e.returncode == 0
    assert e.stdout.strip() == ""


def test_reel_link_ohne_telegram_wird_ignoriert(tmp_path):
    # Ein im Terminal getippter Link soll die Kette nicht anwerfen.
    e = _lauf('{"prompt": "https://www.youtube.com/shorts/abc"}', tmp_path)
    assert e.returncode == 0
    assert e.stdout.strip() == ""


def test_fyi_praefix_wird_ignoriert(tmp_path):
    nutzlast = ('{"prompt": "<channel source=\\"telegram\\"> fyi: '
                'https://www.youtube.com/shorts/abc"}')
    e = _lauf(nutzlast, tmp_path)
    assert e.returncode == 0
    assert e.stdout.strip() == ""


def test_kaputte_nutzlast_bringt_den_waechter_nicht_um(tmp_path):
    # Ein Hook, der bei Muell abstuerzt, blockiert jede Eingabe.
    assert _lauf("kein json", tmp_path).returncode == 0
    assert _lauf("", tmp_path).returncode == 0


def test_fehlende_config_faellt_auf_standard_zurueck(tmp_path, monkeypatch):
    # Eine geloeschte oder kaputte config.json darf die Kette nicht lahmlegen.
    import cli
    monkeypatch.setattr(cli, "WURZEL", tmp_path)
    assert cli.lade_config()["aktiv"] is True
    (tmp_path / "config.json").write_text("{kaputt")
    assert cli.lade_config()["aktiv"] is True


def test_untertitel_fehler_wird_in_der_zusammenfassung_angezeigt(tmp_path, monkeypatch, capsys):
    # Fund 3 (Fix-Runde 1, Task 11a): dossier["untertitel_fehler"] (siehe
    # pipeline._ergaenze_oder_wirf) muss tatsaechlich in der CLI-Ausgabe
    # ankommen, nicht nur im Dossier-dict stehen -- sonst sieht die
    # Besitzerin den Hinweis nie.
    import io
    import json as json_mod
    import sys
    import cli

    monkeypatch.setattr(cli, "WURZEL", tmp_path)          # keine config.json -> Standard
    monkeypatch.setattr(cli, "raeume_auf", lambda **kw: 0)  # nicht den echten Home-Ordner anfassen

    def fake_verarbeite(url, plattform, cookies_browser=None):
        return {
            "bereits_verarbeitet": False,
            "ordner": str(tmp_path),
            "titel": "T", "uploader": "U",
            "transkript_quelle": "whisper", "transkript": "hallo",
            "frames": [], "caption": "",
            "frames_fehler": None, "transkript_fehler": None,
            "untertitel_fehler": "Untertitel-Abruf fehlgeschlagen (1) — Rate-Limit erreicht.",
        }

    monkeypatch.setattr(cli, "verarbeite", fake_verarbeite)
    nutzlast = json_mod.dumps({
        "prompt": '<channel source="telegram"> https://www.youtube.com/shorts/abc'
    })
    monkeypatch.setattr(sys, "stdin", io.StringIO(nutzlast))

    cli.main()

    ausgabe = capsys.readouterr().out
    assert "Untertitel nicht verfuegbar" in ausgabe
    assert "Rate-Limit erreicht" in ausgabe


def test_ohne_untertitel_fehler_kein_hinweis_in_der_zusammenfassung(tmp_path, monkeypatch, capsys):
    # Gegenprobe: ist untertitel_fehler nicht gesetzt (None), darf die
    # Hinweis-Zeile nicht erscheinen.
    import io
    import json as json_mod
    import sys
    import cli

    monkeypatch.setattr(cli, "WURZEL", tmp_path)
    monkeypatch.setattr(cli, "raeume_auf", lambda **kw: 0)

    def fake_verarbeite(url, plattform, cookies_browser=None):
        return {
            "bereits_verarbeitet": False,
            "ordner": str(tmp_path),
            "titel": "T", "uploader": "U",
            "transkript_quelle": "untertitel", "transkript": "hallo",
            "frames": [], "caption": "",
            "frames_fehler": None, "transkript_fehler": None,
            "untertitel_fehler": None,
        }

    monkeypatch.setattr(cli, "verarbeite", fake_verarbeite)
    nutzlast = json_mod.dumps({
        "prompt": '<channel source="telegram"> https://www.youtube.com/shorts/abc'
    })
    monkeypatch.setattr(sys, "stdin", io.StringIO(nutzlast))

    cli.main()

    ausgabe = capsys.readouterr().out
    assert "Untertitel nicht verfuegbar" not in ausgabe
