from pathlib import Path
import pytest
from src.frames import schneide_keyframes

FIXTURE = Path(__file__).parent / "fixtures" / "sample.mp4"


@pytest.fixture(autouse=True)
def fixture_vorhanden():
    if not FIXTURE.exists():
        pytest.skip("tests/fixtures/make_fixture.sh zuerst ausfuehren")


def test_liefert_mindestens_ein_bild(tmp_path):
    frames = schneide_keyframes(FIXTURE, tmp_path)
    assert len(frames) >= 1
    assert all(f.exists() and f.stat().st_size > 0 for f in frames)


def test_haelt_die_obergrenze_ein(tmp_path):
    frames = schneide_keyframes(FIXTURE, tmp_path, max_frames=2)
    assert len(frames) <= 2


def test_rueckfall_greift_bei_statischem_video(tmp_path, monkeypatch):
    # Ein Video ohne jeden Szenenwechsel darf nicht null Bilder ergeben —
    # Bildschirmaufnahmen sind oft fast statisch.
    # Dieser Test beweist, dass der Rueckfall (zwei ffmpeg-Aufrufe) wirklich läuft.
    import subprocess
    from src import frames as frames_module

    # Zaehle die Aufrufe von _lauf
    aufrufe = []
    original_lauf = frames_module._lauf

    def mock_lauf(cmd):
        aufrufe.append(cmd)
        return original_lauf(cmd)

    monkeypatch.setattr(frames_module, "_lauf", mock_lauf)

    statisch = tmp_path / "statisch.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=blue:duration=3:size=320x240:rate=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(statisch),
    ], check=True)

    out_dir = tmp_path / "out"
    frames = schneide_keyframes(statisch, out_dir)

    # Beweise: 2 Aufrufe bedeuten, dass Stufe 1 nichts fand und Stufe 2 (Rueckfall) lief.
    assert len(aufrufe) == 2, f"Erwartet 2 ffmpeg-Aufrufe, got {len(aufrufe)}"
    assert len(frames) >= 1


def test_fehler_bei_nicht_existierendem_video(tmp_path):
    # Kaputtes oder nicht existierendes Video — beide ffmpeg-Aufrufe schlagen fehl.
    from src.frames import FrameFehler

    nicht_existierend = tmp_path / "nicht_da.mp4"
    out_dir = tmp_path / "out"

    with pytest.raises(FrameFehler) as exc_info:
        schneide_keyframes(nicht_existierend, out_dir)

    # Fehler sollte stderr-Ausgabe enthalten — damit weiss der Aufrufer, was schiefging.
    # Pruefen sowohl Praefix als auch echten ffmpeg-Inhalt.
    error_msg = str(exc_info.value)
    assert "Keyframe-Extraktion fehlgeschlagen" in error_msg
    # "No such file" ist der typische ffmpeg-Fehler bei fehlender Datei.
    assert "No such file" in error_msg, f"stderr-Inhalt nicht gefunden. Meldung: {error_msg}"


def test_ffmpeg_timeout_wird_zu_framefehler(tmp_path, monkeypatch):
    """Task 11c: ein haengendes ffmpeg (z.B. kaputter Codec, der ffmpeg in
    eine Endlosschleife schickt) darf nicht unbegrenzt weiterlaufen.
    subprocess.TimeoutExpired darf NICHT als nackter Traceback durchschlagen,
    sondern muss als FrameFehler mit deutscher Meldung samt Zeitangabe
    auftauchen."""
    import subprocess
    from src.frames import FrameFehler, FFMPEG_ZEITLIMIT_SEKUNDEN

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FrameFehler) as exc_info:
        schneide_keyframes(FIXTURE, tmp_path)

    meldung = str(exc_info.value)
    assert str(FFMPEG_ZEITLIMIT_SEKUNDEN) in meldung
    assert "nicht reagiert" in meldung


def test_ffmpeg_aufruf_bekommt_das_modul_eigene_zeitlimit(tmp_path, monkeypatch):
    """Verdrahtungs-Check: subprocess.run() muss tatsaechlich mit der
    modul-eigenen Konstante aufgerufen werden."""
    import subprocess
    from src.frames import FFMPEG_ZEITLIMIT_SEKUNDEN

    gesehene_timeouts = []
    original_run = subprocess.run

    def spionierender_run(cmd, **kwargs):
        gesehene_timeouts.append(kwargs.get("timeout"))
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", spionierender_run)
    schneide_keyframes(FIXTURE, tmp_path)

    assert gesehene_timeouts
    assert all(t == FFMPEG_ZEITLIMIT_SEKUNDEN for t in gesehene_timeouts)


def test_alte_frames_werden_geloescht(tmp_path):
    # Zielordner mit altem frame_001.jpg + kaputtes Video => alte Datei wird NICHT zurueckgegeben.
    from src.frames import FrameFehler

    kaputt = tmp_path / "kaputt.mp4"
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Alte Datei schreiben
    alte_datei = out_dir / "frame_001.jpg"
    alte_datei.write_bytes(b"fake jpg")

    # kaputtes Video (ungueltiger Inhalt)
    kaputt.write_bytes(b"nicht wirklich ein mp4")

    # schneide_keyframes sollte FrameFehler werfen und die alte Datei räumen.
    with pytest.raises(FrameFehler):
        schneide_keyframes(kaputt, out_dir)

    # Alte Datei sollte nicht mehr existieren (wurde geloescht am Anfang).
    assert not alte_datei.exists()
