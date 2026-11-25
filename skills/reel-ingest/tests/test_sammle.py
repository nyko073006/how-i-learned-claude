"""Sammelmodus: Bild- und Karussell-Posts ueber gallery-dl statt yt-dlp."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import sammle  # noqa: E402

# Ersatz fuer gallery-dl: legt zwei Bilder in vertauschter Dateireihenfolge,
# eine Video-Folie und die Metadaten so an, wie gallery-dl mit -f/--write-metadata.
FAKE = r'''#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
ziel = Path(sys.argv[sys.argv.index("-D") + 1])
for name, farbe, gr in [("002.jpg", "blue", "400x500"), ("001.jpg", "red", "640x640")]:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color={farbe}:s={gr}",
                    "-frames:v", "1", str(ziel / name)], check=True)
    (ziel / f"{name}.json").write_text(json.dumps({
        "description": "Caption mit Tipp", "username": "creator", "post_shortcode": "ABC123",
        "post_date": "2026-10-01 10:00:00"}))
(ziel / "003.mp4").write_bytes(b"kein echtes video")
'''


def _pixel(bild: Path) -> bytes:
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(bild), "-vf", "crop=2:2:540:674",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True).stdout


def test_hole_bilder_baut_dossier_in_karussell_reihenfolge(tmp_path, monkeypatch):
    fake = tmp_path / "gallery-dl"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    monkeypatch.setattr(sammle, "GALLERY_DL", fake)

    ordner = sammle.hole_bilder("https://www.instagram.com/p/ABC123/", wurzel=tmp_path / "reels")

    d = json.loads((ordner / "dossier.json").read_text(encoding="utf-8"))
    assert ordner.name == "bild-ABC123"
    assert d["caption"] == "Caption mit Tipp" and d["uploader"] == "creator"
    assert d["art"] == "bilder" and d["videos_ausgelassen"] == 1
    frames = sorted((ordner / "frames").glob("frame_*.jpg"))
    assert [f.name for f in frames] == ["frame_001.jpg", "frame_002.jpg"]
    assert d["frames"] == [str(f) for f in frames]
    rot, blau = _pixel(frames[0]), _pixel(frames[1])
    assert rot[0] > 200 and rot[2] < 60      # erste Folie ist 001.jpg (rot)
    assert blau[2] > 200 and blau[0] < 60
    # steckbrief kachelt nur gleich grosse Bilder: alle auf ein Mass gebracht
    masse = {subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                             "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout
             for f in frames}
    assert masse == {"1080,1350\n"}
    assert sammle.steckbrief(ordner).exists()


def test_hole_faellt_auf_bilder_zurueck(monkeypatch, capsys):
    def kaputt(url):
        raise subprocess.CalledProcessError(1, "yt-dlp")
    monkeypatch.setattr(sammle, "hole", kaputt)
    monkeypatch.setattr(sammle, "hole_bilder", lambda url: Path("/x/bild-ABC"))
    monkeypatch.setattr(sys, "argv", ["sammle.py", "hole", "https://www.instagram.com/p/ABC/"])
    sammle.main()
    assert capsys.readouterr().out.strip() == "/x/bild-ABC"


def test_beide_wege_scheitern_gibt_fehlerzeile(monkeypatch, capsys):
    def kaputt(url):
        raise RuntimeError("weg")
    monkeypatch.setattr(sammle, "hole", kaputt)
    monkeypatch.setattr(sammle, "hole_bilder", kaputt)
    monkeypatch.setattr(sys, "argv", ["sammle.py", "hole", "https://www.instagram.com/p/ABC/"])
    sammle.main()
    assert capsys.readouterr().out.startswith("FEHLER https://www.instagram.com/p/ABC/")


def test_reel_link_einer_folie_holt_den_ganzen_post(tmp_path, monkeypatch):
    # dm liefert bei Karussells die Kennung einer Folie; gallery-dl muss den Post bekommen
    fake = tmp_path / "gallery-dl"
    fake.write_text(FAKE + '(ziel / "url.txt").write_text(sys.argv[-1])\n')
    fake.chmod(0o755)
    monkeypatch.setattr(sammle, "GALLERY_DL", fake)
    monkeypatch.setattr(sammle, "_post_kennung", lambda url: "POST999")

    ordner = sammle.hole_bilder("https://www.instagram.com/reel/FOLIE1/", wurzel=tmp_path / "r")

    d = json.loads((ordner / "dossier.json").read_text(encoding="utf-8"))
    assert d["post_url"] == "https://www.instagram.com/p/POST999/"
    assert d["url"] == "https://www.instagram.com/reel/FOLIE1/"
    assert len(d["frames"]) == 2


def _einstellungen(tmp_path, monkeypatch, **werte):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_text(json.dumps(werte), encoding="utf-8")
    monkeypatch.setenv("CLAUDE_SKILLS_EINSTELLUNGEN", str(pfad))
    return pfad


def test_chrome_profil_aus_einstellungen(tmp_path, monkeypatch):
    _einstellungen(tmp_path, monkeypatch, reel_chrome_profil="Profile 9")
    assert sammle.chrome_profil() == "Profile 9"
    # frisch je Aufruf, nicht beim Laden zwischengespeichert
    _einstellungen(tmp_path, monkeypatch, reel_chrome_profil="Default")
    assert sammle.chrome_profil() == "Default"


def test_chrome_profil_leer_ohne_einstellung(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_SKILLS_EINSTELLUNGEN", str(tmp_path / "gibt-es-nicht.json"))
    assert sammle.chrome_profil() == ""
    _einstellungen(tmp_path, monkeypatch, vault="/irgendwo")
    assert sammle.chrome_profil() == ""


def test_dm_ohne_profil_exit2(tmp_path, monkeypatch, capsys):
    pfad = _einstellungen(tmp_path, monkeypatch, reel_chrome_profil="")
    aufrufe = []
    monkeypatch.setattr(sammle, "links_aus_dm", lambda chat=None: aufrufe.append(chat) or [])
    monkeypatch.setattr(sys, "argv", ["sammle.py", "dm"])
    assert sammle.main() == 2
    assert aufrufe == []
    out = capsys.readouterr()
    assert f"FEHLER reel_chrome_profil fehlt in {pfad}" in out.out + out.err


def test_dm_mit_profil_laeuft(tmp_path, monkeypatch, capsys):
    _einstellungen(tmp_path, monkeypatch, reel_chrome_profil="Profile 9")
    monkeypatch.setattr(sammle, "links_aus_dm", lambda chat=None: ["https://www.instagram.com/reel/X/"])
    monkeypatch.setattr(sys, "argv", ["sammle.py", "dm"])
    assert sammle.main() == 0
    assert "https://www.instagram.com/reel/X/" in capsys.readouterr().out


@pytest.mark.parametrize("inhalt", ["{kaputt", "[1, 2]"])
def test_dm_mit_kaputter_einstellungsdatei_meldet_nicht_lesbar(tmp_path, monkeypatch, capsys, inhalt):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_text(inhalt, encoding="utf-8")
    monkeypatch.setenv("CLAUDE_SKILLS_EINSTELLUNGEN", str(pfad))
    aufrufe = []
    monkeypatch.setattr(sammle, "links_aus_dm", lambda chat=None: aufrufe.append(chat) or [])
    monkeypatch.setattr(sys, "argv", ["sammle.py", "dm"])
    assert sammle.main() == 2
    assert aufrufe == []
    out = capsys.readouterr()
    assert f"FEHLER Einstellungsdatei {pfad} nicht lesbar" in out.err
    assert "reel_chrome_profil fehlt" not in out.out + out.err


def test_dm_ohne_einstellungsdatei_meldet_weiter_profil_fehlt(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "gibt-es-nicht.json"
    monkeypatch.setenv("CLAUDE_SKILLS_EINSTELLUNGEN", str(pfad))
    monkeypatch.setattr(sys, "argv", ["sammle.py", "dm"])
    assert sammle.main() == 2
    out = capsys.readouterr()
    assert f"FEHLER reel_chrome_profil fehlt in {pfad}" in out.err
    assert "nicht lesbar" not in out.out + out.err


def _dm_meldung(monkeypatch, capsys, pfad, befehl=("dm",)):
    monkeypatch.setenv("CLAUDE_SKILLS_EINSTELLUNGEN", str(pfad))
    monkeypatch.setattr(sys, "argv", ["sammle.py", *befehl])
    code = sammle.main()
    out = capsys.readouterr()
    return code, out


def test_kaputte_einstellungsdatei_nennt_grund(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_text("{kaputt", encoding="utf-8")
    code, out = _dm_meldung(monkeypatch, capsys, pfad)
    grund = out.err.split("nicht lesbar: ", 1)[1].strip()
    assert code == 2 and grund


def test_einstellungspfad_ist_verzeichnis_nicht_lesbar(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "verzeichnis.json"
    pfad.mkdir()
    code, out = _dm_meldung(monkeypatch, capsys, pfad)
    assert code == 2
    assert f"FEHLER Einstellungsdatei {pfad} nicht lesbar" in out.err
    assert "reel_chrome_profil fehlt" not in out.err


def test_einstellungsdatei_kein_utf8_nicht_lesbar(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_bytes(b"\xff\xfe\x00{")
    code, out = _dm_meldung(monkeypatch, capsys, pfad)
    assert code == 2
    assert f"FEHLER Einstellungsdatei {pfad} nicht lesbar" in out.err


def test_einstellungsdatei_leeres_objekt_meldet_profil_fehlt(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_text("{}", encoding="utf-8")
    code, out = _dm_meldung(monkeypatch, capsys, pfad)
    assert code == 2
    assert f"FEHLER reel_chrome_profil fehlt in {pfad}" in out.err
    assert "nicht lesbar" not in out.err


def test_einstellungsdatei_tief_verschachtelt_nicht_lesbar(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_text("[" * 100000, encoding="utf-8")
    try:
        code, out = _dm_meldung(monkeypatch, capsys, pfad)
    except RecursionError:
        pytest.fail("Traceback (RecursionError) statt Meldung 'nicht lesbar'")
    assert code == 2
    assert f"FEHLER Einstellungsdatei {pfad} nicht lesbar" in out.err


def test_hole_mit_kaputter_einstellungsdatei_bricht_ab(tmp_path, monkeypatch, capsys):
    pfad = tmp_path / "einstellungen.json"
    pfad.write_text("{kaputt", encoding="utf-8")
    # Rueckfall auf Bild-Posts: yt-dlp-Weg scheitert, hole_bilder liest das Profil
    def kein_video(url):
        raise RuntimeError("kein Video")
    monkeypatch.setattr(sammle, "hole", kein_video)
    # Testsperre: faellt einstellungen() je wieder auf {} zurueck, darf kein echtes gallery-dl ins Netz gehen
    monkeypatch.setattr(sammle, "GALLERY_DL", tmp_path / "kein-gallery-dl")
    code, out = _dm_meldung(monkeypatch, capsys, pfad,
                            ("hole", "https://www.instagram.com/p/ABC123/"))
    assert code == 2
    assert f"FEHLER Einstellungsdatei {pfad} nicht lesbar: " in out.err
    assert out.out == ""
