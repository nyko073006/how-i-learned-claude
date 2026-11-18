"""Macht aus dem Reel Text — bevorzugt ohne Whisper."""
import re
import subprocess
from pathlib import Path

from .fetch import finde_video

ZEITSTEMPEL = re.compile(r"^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->")
MARKUP = re.compile(r"<[^>]*>")

# ffmpeg (8.1) meldet das, wenn die Eingabe schlicht keine Tonspur hat
# (z.B. reines Bildmaterial) — kein Fehler, sondern ein legitimer Zustand.
KEIN_TON_MUSTER = "does not contain any stream"

# Zeitlimit fuer den ffmpeg-Aufruf, der die Tonspur extrahiert (Task 11c).
# Ohne timeout= blieb ein haengendes ffmpeg unbegrenzt am Leben -- der
# aeussere Waechter (hooks/reel_guard.sh) killt nur den Python-Prozess,
# ffmpeg haengt als verwaistes Enkelkind weiter.
#
# FFMPEG_ZEITLIMIT_SEKUNDEN = 30: aus dem Live-Durchstich liegt fuer genau
# diesen Aufruf keine Messung vor (Untertitel waren verfuegbar, der
# Whisper-Fallback-Pfad wurde nicht genommen). Als naechstliegender Proxy
# dient die ffmpeg-Messung aus frames.py (1,04s fuer eine Szenenerkennung
# auf einem mehrminuetigen Video) -- vergleichbare lokale Decode-Arbeit auf
# demselben Video, nur ohne Bildausgabe. Gleicher Wert wie dort (30s, ~29x
# Headroom auf die Proxy-Messung) haelt beide lokalen ffmpeg-Schritte
# symmetrisch.
FFMPEG_ZEITLIMIT_SEKUNDEN = 30


class TranskriptFehler(RuntimeError):
    """ffmpeg oder Whisper sind an einem echten Fehler gescheitert (nicht: kein Ton)."""


def _entdupliziere(zeilen: list[str]) -> list[str]:
    """Entfernt bei rollenden Untertiteln wiederholte Phrasen.

    YouTube-Auto-Untertitel rollen: jeder Block wiederholt das Ende des
    vorigen, damit der Text im Bild mitlaeuft. Eine Zeile faellt nur weg,
    wenn sie exakt mit der zuletzt uebernommenen Zeile identisch ist — ein
    reiner Substring-Vergleich wuerde kurze eigenstaendige Bloecke
    (Fuellwoerter, Jahreszahlen, Namen) spurlos verschlucken, sobald sie
    zufaellig als Zeichenkette im vorigen, laengeren Block vorkommen. Ist
    umgekehrt die zuletzt uebernommene Zeile vollstaendig in der neuen
    enthalten, ersetzt die neue (erweiterte) Zeile die alte — dabei geht
    kein Text verloren.
    """
    ergebnis: list[str] = []
    for zeile in zeilen:
        if not ergebnis:
            ergebnis.append(zeile)
            continue
        letzte = ergebnis[-1]
        if zeile == letzte:
            continue  # exaktes Duplikat der letzten Zeile
        if letzte in zeile:
            ergebnis[-1] = zeile  # neue Zeile ist die erweiterte Fassung
            continue
        ergebnis.append(zeile)
    return ergebnis


def _bereinigte_zeilen(srt: str) -> list[str]:
    """Wirft Nummern, Zeitstempel, Markup und Leerzeilen weg — noch unentdupliziert."""
    zeilen = []
    for roh in srt.splitlines():
        ohne_markup = MARKUP.sub("", roh)
        z = " ".join(ohne_markup.split())  # Leerraum normalisieren
        if not z or z.isdigit() or ZEITSTEMPEL.match(z):
            continue
        zeilen.append(z)
    return zeilen


def srt_zu_text(srt: str) -> str:
    """Wirft Nummern, Zeitstempel, Markup und Leerzeilen weg.

    Entdupliziert danach rollende Auto-Untertitel (siehe _entdupliziere).
    """
    return " ".join(_entdupliziere(_bereinigte_zeilen(srt)))


def hole_transkript(ordner: Path) -> tuple[str, str]:
    """Untertitel wenn vorhanden, sonst Whisper, sonst nichts.

    Untertitel haben Vorrang: sie sind umsonst, sofort da und bei YouTube
    meist besser als eine Transkription des komprimierten Tons.
    """
    # Bei mehreren *.srt (z.B. --sub-langs de,en) ist am Dateinamen nicht zu
    # erkennen, ob es sich um die manuelle oder die automatische Spur
    # handelt — automatische Spuren sind rollend und deshalb voller exakter
    # Wiederholungen. Der Verlustanteil, den die Entduplizierung wegwirft,
    # ist deshalb ein guter Qualitaetsmassstab: nahe null bei sauberen
    # Spuren, deutlich hoeher bei rollenden.
    kandidaten: list[tuple[float, str, str]] = []
    for srt in sorted(ordner.glob("*.srt")):
        zeilen = _bereinigte_zeilen(srt.read_text(errors="replace"))
        entdupliziert = _entdupliziere(zeilen)
        text = " ".join(entdupliziert)
        if not text:
            continue
        verlustanteil = 1 - (len(entdupliziert) / len(zeilen))
        kandidaten.append((verlustanteil, srt.name, text))

    if kandidaten:
        # geringster Verlustanteil gewinnt, bei Gleichstand alphabetisch (Dateiname).
        _, _, bester_text = min(kandidaten, key=lambda k: (k[0], k[1]))
        return ("untertitel", bester_text)

    video = finde_video(ordner)
    if video is None:
        return ("keins", "")

    tonspur = ordner / "audio.wav"
    try:
        ergebnis = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(tonspur),
        ], capture_output=True, text=True, check=False, timeout=FFMPEG_ZEITLIMIT_SEKUNDEN)
    except subprocess.TimeoutExpired as fehler:
        raise TranskriptFehler(
            f"ffmpeg hat die Tonspur-Extraktion nach {FFMPEG_ZEITLIMIT_SEKUNDEN}s "
            "nicht abgeschlossen -- abgebrochen."
        ) from fehler

    if ergebnis.returncode != 0:
        stderr = (ergebnis.stderr or "").strip()
        if KEIN_TON_MUSTER in stderr.lower():
            # Das Video hat wirklich keine Tonspur — kein Fehler, nur nichts zu holen.
            return ("keins", "")
        raise TranskriptFehler(
            f"ffmpeg konnte die Tonspur nicht extrahieren: {stderr or 'kein stderr'}"
        )
    if not tonspur.exists():
        return ("keins", "")

    # Muster aus dem Broken-Links-Projekt (whisper_temp/transcribe_local.py).
    from faster_whisper import WhisperModel
    try:
        modell = WhisperModel("base", device="cpu", compute_type="int8")
        segmente, _ = modell.transcribe(str(tonspur), beam_size=5)
        text = " ".join(s.text.strip() for s in segmente).strip()
    finally:
        # Auch wenn Whisper unterwegs wirft, soll die Tonspur nicht liegenbleiben.
        tonspur.unlink(missing_ok=True)
    return ("whisper", text) if text else ("keins", "")
