"""Tests fuer die Dossier-Pipeline: Zusammenbau, Dedupe und Aufraeumen.

Die Fehlerpfade (Bilder oder Transkript fehlen) werden mit monkeypatch auf
die aufgerufenen Funktionen simuliert — echte kaputte Videos braucht es
dafuer nicht. Nur der Anhang-Test am Ende laeuft komplett echt (ffmpeg +
ggf. Whisper) gegen die Fixture.
"""
import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from src.pipeline import dossier_pfad, raeume_auf


def test_gleiche_url_ergibt_gleichen_pfad(tmp_path):
    a = dossier_pfad("https://www.youtube.com/shorts/abc", tmp_path)
    b = dossier_pfad("https://www.youtube.com/shorts/abc", tmp_path)
    assert a == b


def test_verschiedene_urls_ergeben_verschiedene_pfade(tmp_path):
    a = dossier_pfad("https://www.youtube.com/shorts/abc", tmp_path)
    b = dossier_pfad("https://www.youtube.com/shorts/xyz", tmp_path)
    assert a != b


def test_anhang_wird_verarbeitet_und_dedupliziert(tmp_path):
    # Der zweite Eingangsweg: ein weitergeleitetes Video statt eines Links.
    from src.pipeline import verarbeite_datei
    fixture = Path(__file__).parent / "fixtures" / "sample.mp4"
    if not fixture.exists():
        pytest.skip("tests/fixtures/make_fixture.sh zuerst ausfuehren")

    erst = verarbeite_datei(fixture, tmp_path)
    assert erst["bereits_verarbeitet"] is False
    assert len(erst["frames"]) >= 1

    zweit = verarbeite_datei(fixture, tmp_path)
    assert zweit["bereits_verarbeitet"] is True


def test_aufraeumen_loescht_nur_altes(tmp_path):
    alt = tmp_path / "alt"; alt.mkdir()
    neu = tmp_path / "neu"; neu.mkdir()
    vor_20_tagen = time.time() - 20 * 86400
    os.utime(alt, (vor_20_tagen, vor_20_tagen))

    geloescht = raeume_auf(tmp_path, max_alter_tage=14)

    assert geloescht == 1
    assert not alt.exists()
    assert neu.exists()


# --- Abweichung A: Bilder und Transkript duerfen einzeln fehlen ---

def test_frames_fehler_wird_abgefangen_dossier_trotzdem_geschrieben(tmp_path, monkeypatch):
    from src import pipeline

    def fake_hole_reel(url, ordner, cookies_browser=None):
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "video.mp4").write_bytes(b"\x00")
        return {"title": "T", "uploader": "U", "description": "C", "duration": 5}

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        raise pipeline.FrameFehler("kaputtes Video")

    def fake_hole_transkript(ordner):
        return ("untertitel", "Hallo Welt")

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    dossier = pipeline.verarbeite("https://example.com/frames-fehler", "youtube", tmp_path)

    assert dossier["frames"] == []
    assert dossier["frames_fehler"] == "kaputtes Video"
    assert dossier["transkript"] == "Hallo Welt"
    assert dossier["transkript_fehler"] is None
    dossier_datei = pipeline.dossier_pfad("https://example.com/frames-fehler", tmp_path) / "dossier.json"
    assert dossier_datei.exists()


def test_transkript_fehler_wird_abgefangen_dossier_trotzdem_geschrieben(tmp_path, monkeypatch):
    from src import pipeline

    def fake_hole_reel(url, ordner, cookies_browser=None):
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "video.mp4").write_bytes(b"\x00")
        return {"title": "T", "uploader": "U", "description": "C", "duration": 5}

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        return [zielordner / "frame_001.jpg"]

    def fake_hole_transkript(ordner):
        raise pipeline.TranskriptFehler("ffmpeg kaputt")

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    dossier = pipeline.verarbeite("https://example.com/transkript-fehler", "youtube", tmp_path)

    assert len(dossier["frames"]) == 1
    assert dossier["frames_fehler"] is None
    assert dossier["transkript"] == ""
    assert dossier["transkript_quelle"] == "fehler"
    assert dossier["transkript_fehler"] == "ffmpeg kaputt"
    dossier_datei = pipeline.dossier_pfad("https://example.com/transkript-fehler", tmp_path) / "dossier.json"
    assert dossier_datei.exists()


# --- Abweichung B: beide Haelften fehlgeschlagen -> kein Dossier ---

def test_beide_fehlschlagen_wirft_beschaffungsfehler_und_schreibt_kein_dossier(tmp_path, monkeypatch):
    from src import pipeline
    from src.fetch import BeschaffungsFehler

    def fake_hole_reel(url, ordner, cookies_browser=None):
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "video.mp4").write_bytes(b"\x00")
        return {"title": "T"}

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        raise pipeline.FrameFehler("keine Bilder")

    def fake_hole_transkript(ordner):
        raise pipeline.TranskriptFehler("kein Ton extrahierbar")

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    ordner = pipeline.dossier_pfad("https://example.com/beide-fehler", tmp_path)
    with pytest.raises(BeschaffungsFehler) as exc_info:
        pipeline.verarbeite("https://example.com/beide-fehler", "youtube", tmp_path)

    assert "keine Bilder" in str(exc_info.value)
    assert "kein Ton extrahierbar" in str(exc_info.value)
    assert not (ordner / "dossier.json").exists()


def test_verarbeite_datei_beide_fehlschlagen_wirft_und_schreibt_kein_dossier(tmp_path, monkeypatch):
    from src import pipeline
    from src.fetch import BeschaffungsFehler

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        raise pipeline.FrameFehler("keine Bilder")

    def fake_hole_transkript(ordner):
        raise pipeline.TranskriptFehler("kein Ton extrahierbar")

    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    quelle = tmp_path / "quelle.mp4"
    quelle.write_bytes(b"irgendein inhalt")

    with pytest.raises(BeschaffungsFehler):
        pipeline.verarbeite_datei(quelle, tmp_path / "wurzel")

    kennung = hashlib.sha256(quelle.read_bytes()).hexdigest()[:12]
    ordner = tmp_path / "wurzel" / kennung
    assert not (ordner / "dossier.json").exists()


def test_beschaffungsfehler_von_hole_reel_laeuft_unveraendert_durch(tmp_path, monkeypatch):
    # BeschaffungsFehler wird NICHT abgefangen: kein Video, nichts zu dokumentieren.
    from src import pipeline
    from src.fetch import BeschaffungsFehler

    def fake_hole_reel(url, ordner, cookies_browser=None):
        raise BeschaffungsFehler("yt-dlp fehlgeschlagen")

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)

    with pytest.raises(BeschaffungsFehler):
        pipeline.verarbeite("https://example.com/kaputt", "youtube", tmp_path)


# --- Abweichung C: verarbeite_datei() darf finde_video() nicht mehrdeutig machen ---

def test_verarbeite_datei_raeumt_stale_video_anderer_endung_vor_dem_kopieren(tmp_path, monkeypatch):
    # Szenario: ein frueherer Versuch fuer denselben Inhalts-Hash ist
    # abgebrochen, bevor das Dossier geschrieben wurde (z.B. weil beide
    # Haelften fehlschlugen), und hat eine Videodatei mit ANDERER Endung
    # hinterlassen. Ein erneuter Aufruf mit dem inhaltsgleichen Video unter
    # neuer Endung darf nicht zu zwei Videodateien im selben Ordner fuehren —
    # sonst wirft finde_video() innerhalb von hole_transkript() wegen
    # Mehrdeutigkeit (Ausnahme 1).
    from src import pipeline

    inhalt = b"identischer inhalt fuer beide endungen"
    kennung = hashlib.sha256(inhalt).hexdigest()[:12]
    wurzel = tmp_path / "wurzel"
    ordner = wurzel / kennung
    ordner.mkdir(parents=True)
    (ordner / "video.mov").write_bytes(inhalt)  # Stale-Rest eines fruehen Versuchs

    gefundene_videos_beim_transkribieren = []

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        # Bewusst NICHT leer: dieser Test prueft die Raeumung alter
        # Videodateien (Punkt C), nicht das Verhalten bei leerem Inhalt
        # (das deckt test_beide_liefern_leer_ohne_ausnahme_... ab).
        return [zielordner / "frame_001.jpg"]

    def fake_hole_transkript(ordner_arg):
        from src.fetch import finde_video
        video = finde_video(ordner_arg)  # wirft BeschaffungsFehler bei Mehrdeutigkeit
        gefundene_videos_beim_transkribieren.append(video)
        return ("keins", "")

    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    quelle_neu = tmp_path / "quelle.mp4"  # gleicher Inhalt, ANDERE Endung als video.mov
    quelle_neu.write_bytes(inhalt)

    dossier = pipeline.verarbeite_datei(quelle_neu, wurzel)

    video_dateien = sorted(p.name for p in ordner.iterdir() if p.is_file() and p.suffix in {".mp4", ".mov"})
    assert video_dateien == ["video.mp4"], f"Erwartet nur video.mp4, gefunden: {video_dateien}"
    assert gefundene_videos_beim_transkribieren[0].name == "video.mp4"
    assert dossier["bereits_verarbeitet"] is False
    assert len(dossier["frames"]) == 1


def test_verarbeite_raeumt_alte_videodatei_vor_erneutem_download(tmp_path, monkeypatch):
    # Fund 2 (Fix-Runde 1): der Loesch-Zweig in _raeume_alte_videos() war
    # bisher nur ueber verarbeite_datei() getestet. Dieser Test deckt ihn
    # auch fuer den verarbeite()-Pfad ab (src/pipeline.py:107, Aufruf vor
    # hole_reel()): ein abgebrochener frueherer Versuch fuer denselben
    # URL-Hash hat eine Videodatei mit ANDERER Endung hinterlassen; der neue
    # Versuch legt ueber hole_reel() eine Datei mit wieder anderer Endung an.
    from src import pipeline

    url = "https://example.com/alter-rest"
    ordner = pipeline.dossier_pfad(url, tmp_path)
    ordner.mkdir(parents=True)
    alte_datei = ordner / "video.webm"
    alte_datei.write_bytes(b"alter stale rest eines abgebrochenen versuchs")

    def fake_hole_reel(url_arg, ordner_arg, cookies_browser=None):
        ordner_arg.mkdir(parents=True, exist_ok=True)
        (ordner_arg / "video.mp4").write_bytes(b"\x00")
        return {"title": "T"}

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        return [zielordner / "frame_001.jpg"]

    def fake_hole_transkript(ordner_arg):
        from src.fetch import finde_video
        # Beweist: finde_video() sieht nach der Raeumung nur noch EIN Video.
        video = finde_video(ordner_arg)
        assert video is not None and video.name == "video.mp4"
        return ("keins", "")

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    dossier = pipeline.verarbeite(url, "youtube", tmp_path)

    assert not alte_datei.exists()
    assert (ordner / "video.mp4").exists()
    video_dateien = sorted(p.name for p in ordner.iterdir() if p.is_file() and p.suffix in {".mp4", ".webm"})
    assert video_dateien == ["video.mp4"]
    assert dossier["bereits_verarbeitet"] is False


# --- Fund 1 (Fix-Runde 1): "kein Dossier ohne Inhalt" muss auch OHNE Ausnahme greifen ---

def test_beide_liefern_leer_ohne_ausnahme_wirft_trotzdem_und_schreibt_kein_dossier(tmp_path, monkeypatch):
    # schneide_keyframes() kann legitim [] liefern und hole_transkript()
    # legitim ("keins", "") — beides OHNE FrameFehler/TranskriptFehler. Ein
    # reiner Ausnahme-Check (frames_fehler and transkript_fehler) haette
    # diesen stillen Leerfall durchgelassen und trotzdem ein inhaltsloses
    # Dossier geschrieben. Die Pruefung muss auf dem INHALT beruhen.
    from src import pipeline
    from src.fetch import BeschaffungsFehler

    def fake_hole_reel(url, ordner, cookies_browser=None):
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "video.mp4").write_bytes(b"\x00")
        return {"title": "T"}

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        return []  # legitim leer, KEINE Ausnahme

    def fake_hole_transkript(ordner):
        return ("keins", "")  # legitim leer, KEINE Ausnahme

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    ordner = pipeline.dossier_pfad("https://example.com/beide-leer-ohne-fehler", tmp_path)
    with pytest.raises(BeschaffungsFehler) as exc_info:
        pipeline.verarbeite("https://example.com/beide-leer-ohne-fehler", "youtube", tmp_path)

    # Die Fehlermeldung muss auch dann brauchbar sein, wenn keine der beiden
    # Seiten eine Ausnahme geworfen hat.
    fehlertext = str(exc_info.value)
    assert "ohne dass ein Fehler auftrat" in fehlertext
    assert not (ordner / "dossier.json").exists()


# --- Fund 3 (Fix-Runde 1, Task 11a): untertitel_fehler wird ins Dossier durchgereicht ---
#
# fetch.hole_reel() haelt einen gescheiterten Untertitel-Nachhol-Versuch seit
# Task 11a in info["untertitel_fehler"] fest. Ohne diesen Abschnitt landete
# das nur im Rueckgabewert von hole_reel(), aber nie im Dossier -- die
# Besitzerin haette im Drosselungsfall ein vollstaendiges Whisper-Dossier
# bekommen, ohne erkennen zu koennen, dass Untertitel aktiv verweigert
# wurden statt schlicht zu fehlen.

def test_untertitel_fehler_wird_ins_dossier_durchgereicht(tmp_path, monkeypatch):
    from src import pipeline

    def fake_hole_reel(url, ordner, cookies_browser=None):
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "video.mp4").write_bytes(b"\x00")
        return {
            "title": "T", "uploader": "U", "description": "C", "duration": 5,
            "untertitel_fehler": "Untertitel-Abruf fehlgeschlagen (1) — Rate-Limit erreicht.",
        }

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        return [zielordner / "frame_001.jpg"]

    def fake_hole_transkript(ordner):
        return ("whisper", "Hallo Welt")  # Whisper-Rueckfall greift trotz Untertitel-Fehlschlag

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    dossier = pipeline.verarbeite("https://example.com/untertitel-fehler", "youtube", tmp_path)

    assert dossier["transkript_quelle"] == "whisper"  # Whisper hat trotzdem geliefert
    assert dossier["untertitel_fehler"] == "Untertitel-Abruf fehlgeschlagen (1) — Rate-Limit erreicht."


def test_ohne_untertitel_fehler_ist_das_feld_none(tmp_path, monkeypatch):
    from src import pipeline

    def fake_hole_reel(url, ordner, cookies_browser=None):
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "video.mp4").write_bytes(b"\x00")
        return {"title": "T", "uploader": "U", "description": "C", "duration": 5}

    def fake_schneide_keyframes(video, zielordner, *a, **kw):
        return [zielordner / "frame_001.jpg"]

    def fake_hole_transkript(ordner):
        return ("untertitel", "Hallo Welt")

    monkeypatch.setattr(pipeline, "hole_reel", fake_hole_reel)
    monkeypatch.setattr(pipeline, "schneide_keyframes", fake_schneide_keyframes)
    monkeypatch.setattr(pipeline, "hole_transkript", fake_hole_transkript)

    dossier = pipeline.verarbeite("https://example.com/kein-untertitel-fehler", "youtube", tmp_path)

    assert dossier["untertitel_fehler"] is None
