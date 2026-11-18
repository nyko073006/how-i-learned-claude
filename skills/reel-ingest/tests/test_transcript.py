from pathlib import Path
import pytest
from src.transcript import hole_transkript, srt_zu_text


def test_srt_wird_zu_reinem_text():
    srt = """1
00:00:00,000 --> 00:00:02,000
Das hier ist ein Tool

2
00:00:02,000 --> 00:00:04,000
das Links prueft
"""
    assert srt_zu_text(srt) == "Das hier ist ein Tool das Links prueft"


def test_untertitel_haben_vorrang_vor_whisper(tmp_path):
    # Whisper ist teuer. Liegen Untertitel vor, wird nicht transkribiert.
    (tmp_path / "video.de.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHallo Welt\n"
    )
    quelle, text = hole_transkript(tmp_path)
    assert quelle == "untertitel"
    assert text == "Hallo Welt"


def test_ohne_ton_und_ohne_untertitel_kein_absturz(tmp_path):
    quelle, text = hole_transkript(tmp_path)
    assert quelle == "keins"
    assert text == ""


def test_rollende_untertitel_werden_entdupliziert():
    # YouTube-Auto-Untertitel rollen: jeder Block wiederholt das Ende des
    # vorigen, damit der Text im Bild mitlaeuft. Vier ueberlappende Bloecke.
    srt = """1
00:00:00,000 --> 00:00:02,000
hey what's going on guys welcome back

2
00:00:02,000 --> 00:00:04,000
hey what's going on guys welcome back
to another video

3
00:00:04,000 --> 00:00:06,000
to another video
today we're going to talk about

4
00:00:06,000 --> 00:00:08,000
today we're going to talk about
a really cool tool
"""
    text = srt_zu_text(srt)
    for phrase in [
        "hey what's going on guys welcome back",
        "to another video",
        "today we're going to talk about",
        "a really cool tool",
    ]:
        assert text.count(phrase) == 1
    assert text == (
        "hey what's going on guys welcome back to another video "
        "today we're going to talk about a really cool tool"
    )


def test_markup_und_inline_zeitstempel_werden_entfernt():
    # Auto-Untertitel schreiben Wort-fuer-Wort-Markup mit <c>-Tags und
    # Inline-Zeitmarken direkt in den Text.
    srt = (
        "1\n"
        "00:00:00,000 --> 00:00:02,000\n"
        "hey<00:00:00,320><c> what's</c><00:00:00,560><c.colorE5E5E5> going</c>"
        "<00:00:00,800><c> on</c><00:00:01,040><c> guys</c>\n"
    )
    text = srt_zu_text(srt)
    assert "<" not in text
    assert ">" not in text
    assert text == "hey what's going on guys"


def test_unterschiedliche_zeilen_mit_gemeinsamem_wort_bleiben_beide_erhalten():
    # Absicherung gegen zu aggressive Entduplizierung: zwei echt
    # unterschiedliche Bloecke, die zufaellig ein gemeinsames Wort teilen,
    # duerfen nicht ineinander aufgehen.
    srt = """1
00:00:00,000 --> 00:00:02,000
the quick brown fox jumps

2
00:00:02,000 --> 00:00:04,000
the lazy dog sleeps
"""
    text = srt_zu_text(srt)
    assert text == "the quick brown fox jumps the lazy dog sleeps"


def test_entduplizierung_verschluckt_keine_kurzen_eigenstaendigen_bloecke():
    # "Jahr" ist zufaellig als Zeichenkette im vorigen, laengeren Block
    # enthalten, ist aber ein eigenstaendiger Block und darf nicht spurlos
    # verschwinden — nur exakte Wiederholungen der letzten Zeile fallen weg.
    srt = """1
00:00:00,000 --> 00:00:02,000
Wir haben letztes Jahr das Projekt gestartet

2
00:00:02,000 --> 00:00:04,000
Jahr
"""
    text = srt_zu_text(srt)
    assert text == "Wir haben letztes Jahr das Projekt gestartet Jahr"


def test_ffmpeg_timeout_bei_tonspur_extraktion_wird_zu_transkriptfehler(tmp_path, monkeypatch):
    """Task 11c: ein haengendes ffmpeg bei der Tonspur-Extraktion (z.B.
    kaputter Codec) darf nicht unbegrenzt weiterlaufen. subprocess.
    TimeoutExpired darf NICHT als nackter Traceback durchschlagen, sondern
    muss als TranskriptFehler mit deutscher Meldung samt Zeitangabe
    auftauchen -- die Pipeline faengt TranskriptFehler ab und degradiert das
    Dossier, statt ganz zu scheitern (siehe pipeline._hole_transkript_sicher)."""
    import subprocess
    from src.transcript import TranskriptFehler, FFMPEG_ZEITLIMIT_SEKUNDEN

    (tmp_path / "video.mp4").write_bytes(b"\x00")  # finde_video() muss etwas finden

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(TranskriptFehler) as exc_info:
        hole_transkript(tmp_path)

    meldung = str(exc_info.value)
    assert str(FFMPEG_ZEITLIMIT_SEKUNDEN) in meldung
    assert "nicht abgeschlossen" in meldung


def test_saubere_untertitel_gewinnen_gegen_rollende_trotz_alphabet(tmp_path):
    # video.de.srt steht alphabetisch vorn, ist aber (wie bei echten
    # YouTube-Downloads oft der Fall) die automatische Spur mit vielen
    # Rollwiederholungen. video.en.srt ist sauber und muss trotzdem gewinnen
    # — Auswahl nach Qualitaet (Verlustanteil durch die Entduplizierung),
    # nicht nach Dateiname.
    (tmp_path / "video.de.srt").write_text("""1
00:00:00,000 --> 00:00:02,000
hallo und willkommen zurück

2
00:00:02,000 --> 00:00:04,000
hallo und willkommen zurück
zu einem neuen video

3
00:00:04,000 --> 00:00:06,000
zu einem neuen video
heute geht es um ein tool

4
00:00:06,000 --> 00:00:08,000
heute geht es um ein tool
das links prüft

5
00:00:08,000 --> 00:00:10,000
das links prüft
und kaputte verweise findet
""")
    (tmp_path / "video.en.srt").write_text("""1
00:00:00,000 --> 00:00:02,000
This is a clean subtitle track

2
00:00:02,000 --> 00:00:04,000
with completely distinct lines

3
00:00:04,000 --> 00:00:06,000
and no repeated phrases at all

4
00:00:06,000 --> 00:00:08,000
so the loss ratio should be zero
""")
    quelle, text = hole_transkript(tmp_path)
    assert quelle == "untertitel"
    assert text == (
        "This is a clean subtitle track with completely distinct lines "
        "and no repeated phrases at all so the loss ratio should be zero"
    )
