"""Fuehrt Beschaffen, Zerlegen und Transkribieren zu einem Dossier zusammen.

Zwei Eingangswege muenden im selben Dossier-Format:
- verarbeite(url, ...)       fuer per Link geschickte Reels
- verarbeite_datei(video, ...) fuer per Telegram weitergeleitete Videos
  (download_attachment ist ein MCP-Werkzeug, das nur das Modell aufrufen
  kann — eine Shell kommt da nicht ran, deshalb der zweite Einstieg).

Bilder und Transkript duerfen einzeln fehlen, ohne dass das Dossier
verlorengeht: ein Reel ohne brauchbare Bilder kann trotzdem ein gutes
Transkript haben und umgekehrt. Nur wenn BEIDE Haelften inhaltlich nichts
liefern — leere Bilderliste UND leerer Text, ob mit oder ohne Ausnahme —,
gibt es nichts zu dokumentieren — dann wird kein Dossier geschrieben.
"""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from .fetch import hole_reel, finde_video, BeschaffungsFehler, VIDEO_ENDUNGEN
from .frames import schneide_keyframes, FrameFehler
from .palette import hole_palette_aus_video, PaletteFehler
from .transcript import hole_transkript, TranskriptFehler

WURZEL = Path.home() / ".claude" / "channels" / "telegram" / "reels"


def dossier_pfad(url: str, wurzel: Path = WURZEL) -> Path:
    """Stabiler Pfad je URL — dasselbe Reel landet immer im selben Ordner.

    Das ist zugleich das Dedupe: existiert der Ordner mit fertigem Dossier
    schon, wird nicht erneut heruntergeladen.
    """
    kennung = hashlib.sha256(url.encode()).hexdigest()[:12]
    return wurzel / kennung


def _raeume_alte_videos(ordner: Path, behalten: Path | None = None) -> None:
    """Loescht Videodateien im Ordner, die nicht `behalten` sind.

    Schuetzt vor Mehrdeutigkeit: finde_video() wirft BeschaffungsFehler,
    sobald mehr als eine Videodatei im Ordner liegt. Das kann passieren,
    wenn ein frueherer Versuch fuer denselben Dedupe-Schluessel abgebrochen
    ist, bevor das Dossier geschrieben wurde (z.B. weil Bilder UND
    Transkript fehlschlugen, siehe _ergaenze_oder_wirf) und dabei eine
    Videodatei mit anderer Endung hinterlassen hat.
    """
    if not ordner.exists():
        return
    for alte_datei in ordner.iterdir():
        if (alte_datei.is_file()
                and alte_datei.suffix.lower() in VIDEO_ENDUNGEN
                and alte_datei != behalten):
            alte_datei.unlink()


def _hole_frames_sicher(video: Path, zielordner: Path) -> tuple[list[Path], str | None]:
    """schneide_keyframes(), aber FrameFehler faellt das Dossier nicht weg.

    Fehlende Bilder sind kein Grund, ein brauchbares Transkript wegzuwerfen.
    """
    try:
        return schneide_keyframes(video, zielordner), None
    except FrameFehler as fehler:
        return [], str(fehler)


def _hole_palette_sicher(video: Path) -> tuple[list[dict], str | None]:
    """Farbpalette aus dem VIDEO, aber ein Fehlschlag faellt das Dossier nicht weg.

    Dieselbe Linie wie _hole_frames_sicher: die Farbpalette ist eine Zugabe
    fuer den Design-Modus, kein Grund, ein brauchbares Transkript oder
    brauchbare Bilder wegzuwerfen.

    AUS DEM VIDEO, NICHT AUS DEN KEYFRAMES -- der Unterschied ist gemessen
    und kein Geschmack: die Keyframes entstehen an Szenenwechseln, ein
    Testvideo aus zwei gleich langen Farbhaelften ergab ueber sie eine
    Palette mit EINER Farbe zu 100 Prozent. Siehe hole_palette_aus_video().
    """
    try:
        return hole_palette_aus_video(video), None
    except (PaletteFehler, OSError, subprocess.TimeoutExpired) as fehler:
        return [], str(fehler)


def _hole_transkript_sicher(ordner: Path) -> tuple[str, str, str | None]:
    """hole_transkript(), aber TranskriptFehler faellt das Dossier nicht weg.

    Ein gescheitertes Transkript ist kein Grund, brauchbare Bilder wegzuwerfen.
    """
    try:
        quelle, text = hole_transkript(ordner)
        return quelle, text, None
    except TranskriptFehler as fehler:
        return "fehler", "", str(fehler)


def _ergaenze_oder_wirf(dossier: dict, frames_fehler: str | None,
                        transkript_fehler: str | None,
                        untertitel_fehler: str | None = None) -> dict:
    """Haengt die Fehlerfelder an — oder wirft, wenn beide Haelften nichts liefern.

    Massgeblich ist der INHALT (dossier["frames"], dossier["transkript"]),
    nicht nur, ob eine Ausnahme geflogen ist: schneide_keyframes() kann
    legitim [] liefern und hole_transkript() legitim ("keins", "") — beides
    OHNE FrameFehler bzw. TranskriptFehler (z.B. ein wirklich stummes,
    bewegungsloses Video). Ein reiner Ausnahme-Check wuerde diesen stillen
    Leerfall durchlassen und trotzdem ein inhaltsloses Dossier schreiben —
    genau das, was vermieden werden soll: es wuerde vortaeuschen, es sei
    etwas verarbeitet worden. BeschaffungsFehler wird hier weiterverwendet
    statt eines vierten Ausnahmetyps.

    untertitel_fehler geht NICHT in die obige Leer-Pruefung ein: ein
    gescheiterter Untertitel-Nachhol-Versuch (siehe fetch.hole_reel) ist
    per Design folgenlos fuer den Transkript-Inhalt — hole_transkript()
    faellt ohne .srt automatisch auf Whisper zurueck. Das Feld ist rein
    informativ (Fund 3, Fix-Runde 1): ohne es bekam die Besitzerin im
    Drosselungsfall ein vollstaendiges Whisper-Dossier, konnte darin aber
    nicht erkennen, ob Untertitel schlicht fehlten oder aktiv verweigert
    wurden.
    """
    if not dossier["frames"] and not dossier["transkript"]:
        frames_grund = frames_fehler or "keine Bilder gefunden, ohne dass ein Fehler auftrat"
        transkript_grund = transkript_fehler or "kein Transkript gefunden, ohne dass ein Fehler auftrat"
        raise BeschaffungsFehler(
            "Weder Bilder noch Transkript verfuegbar — "
            f"Frames: {frames_grund} | Transkript: {transkript_grund}"
        )
    dossier["frames_fehler"] = frames_fehler
    dossier["transkript_fehler"] = transkript_fehler
    dossier["untertitel_fehler"] = untertitel_fehler
    return dossier


def verarbeite(url: str, plattform: str, wurzel: Path = WURZEL,
               cookies_browser: str | None = None) -> dict:
    """Erzeugt das Dossier. Gibt es das schon, wird es unveraendert gemeldet."""
    ordner = dossier_pfad(url, wurzel)
    dossier_datei = ordner / "dossier.json"
    if dossier_datei.exists():
        dossier = json.loads(dossier_datei.read_text())
        dossier["bereits_verarbeitet"] = True
        return dossier

    _raeume_alte_videos(ordner)  # Rest eines abgebrochenen frueheren Versuchs raeumen
    info = hole_reel(url, ordner, cookies_browser)
    video = finde_video(ordner)
    if video is None:
        raise BeschaffungsFehler("Kein Video im Dossier-Ordner nach dem Download")

    frames, frames_fehler = _hole_frames_sicher(video, ordner / "frames")
    quelle, text, transkript_fehler = _hole_transkript_sicher(ordner)
    palette, palette_fehler = _hole_palette_sicher(video)

    dossier = _ergaenze_oder_wirf({
        "url": url,
        "plattform": plattform,
        "titel": info.get("title", ""),
        "uploader": info.get("uploader", ""),
        "caption": info.get("description", ""),
        "dauer_sekunden": info.get("duration"),
        "transkript_quelle": quelle,
        "transkript": text,
        "frames": [str(f) for f in frames],
        "palette": palette,
        "palette_fehler": palette_fehler,
        "ordner": str(ordner),
        "bereits_verarbeitet": False,
    }, frames_fehler, transkript_fehler, info.get("untertitel_fehler"))

    dossier_datei.write_text(json.dumps(dossier, ensure_ascii=False, indent=2))
    return dossier


def verarbeite_datei(video: Path, wurzel: Path = WURZEL) -> dict:
    """Wie verarbeite(), aber fuer ein bereits heruntergeladenes Video.

    Der Weg fuer per Telegram weitergeleitete Videos: das Modell holt die
    Datei mit download_attachment und uebergibt sie hier. Kennung ist der
    Inhalts-Hash, damit dasselbe Video zweimal geschickt nicht zweimal
    verarbeitet wird.
    """
    kennung = hashlib.sha256(video.read_bytes()).hexdigest()[:12]
    ordner = wurzel / kennung
    dossier_datei = ordner / "dossier.json"
    if dossier_datei.exists():
        dossier = json.loads(dossier_datei.read_text())
        dossier["bereits_verarbeitet"] = True
        return dossier

    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"video{video.suffix}"
    if ziel != video:
        # Vor dem Kopieren raeumen: siehe _raeume_alte_videos — sonst kann
        # ein Stale-Rest mit anderer Endung finde_video() spaeter mehrdeutig
        # machen (Punkt C, hole_transkript() ruft finde_video() intern auf).
        _raeume_alte_videos(ordner, behalten=ziel)
        shutil.copy(video, ziel)

    frames, frames_fehler = _hole_frames_sicher(ziel, ordner / "frames")
    quelle, text, transkript_fehler = _hole_transkript_sicher(ordner)
    palette, palette_fehler = _hole_palette_sicher(ziel)

    # Kein untertitel_fehler-Argument: dieser Pfad ruft nie hole_reel() auf
    # (das Video liegt schon vor), es gibt also gar keinen Untertitel-
    # Nachhol-Versuch, dessen Fehlschlag festzuhalten waere.
    dossier = _ergaenze_oder_wirf({
        "url": "", "plattform": "telegram-anhang",
        "titel": video.stem, "uploader": "", "caption": "",
        "dauer_sekunden": None,
        "transkript_quelle": quelle, "transkript": text,
        "frames": [str(f) for f in frames],
        "palette": palette,
        "palette_fehler": palette_fehler,
        "ordner": str(ordner), "bereits_verarbeitet": False,
    }, frames_fehler, transkript_fehler)

    dossier_datei.write_text(json.dumps(dossier, ensure_ascii=False, indent=2))
    return dossier


def raeume_auf(wurzel: Path = WURZEL, max_alter_tage: int = 14) -> int:
    """Loescht Dossiers aelter als N Tage. Gibt die Anzahl zurueck."""
    if not wurzel.exists():
        return 0
    grenze = time.time() - max_alter_tage * 86400
    anzahl = 0
    for ordner in wurzel.iterdir():
        if ordner.is_dir() and ordner.stat().st_mtime < grenze:
            shutil.rmtree(ordner, ignore_errors=True)
            anzahl += 1
    return anzahl
