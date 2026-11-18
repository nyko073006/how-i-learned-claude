"""Schneidet aus dem Video die Bilder, die etwas zeigen."""
import subprocess
from pathlib import Path


class FrameFehler(Exception):
    """Fehler beim Extrahieren von Keyframes."""
    pass


# Zeitlimit fuer jeden der (bis zu zwei) ffmpeg-Aufrufe in schneide_keyframes()
# (Task 11c). Ohne timeout= blieb ein haengendes ffmpeg unbegrenzt am Leben --
# der aeussere Waechter (hooks/reel_guard.sh) killt nur den Python-Prozess,
# ffmpeg haengt als verwaistes Enkelkind weiter.
#
# FFMPEG_ZEITLIMIT_SEKUNDEN = 30: gemessen 1,04s fuer einen einzelnen
# erfolgreichen Szenenerkennungs-Lauf (echter Lauf, Task 11 Durchstich, Video
# von mehreren Minuten Laenge). Reine lokale CPU-Arbeit ohne Netzwerk-Varianz
# -- 30s sind knapp das 29-fache der Messung und liegen weit ueber jeder
# Reel/Short/TikTok-Laenge (alle <= ~90s bis 3 Min). Ein echtes Haengen hier
# deutet eher auf ein kaputtes/unlesbares Video als auf legitime Langsamkeit,
# das Limit darf also vergleichsweise eng sein.
FFMPEG_ZEITLIMIT_SEKUNDEN = 30


def _lauf(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False,
                              timeout=FFMPEG_ZEITLIMIT_SEKUNDEN)
    except subprocess.TimeoutExpired as fehler:
        raise FrameFehler(
            f"ffmpeg hat nach {FFMPEG_ZEITLIMIT_SEKUNDEN}s nicht reagiert -- abgebrochen."
        ) from fehler


def schneide_keyframes(video: Path, zielordner: Path,
                       max_frames: int = 20, schwelle: float = 0.3) -> list[Path]:
    """Bilder an Szenenwechseln. Findet das nichts, greift ein festes Intervall.

    Szenenwechsel trifft die tatsaechlich gezeigten Bildschirme; ein festes
    Intervall trifft oft nur Uebergaenge. Bildschirmaufnahmen sind aber
    manchmal so statisch, dass die Erkennung nichts findet — dafuer der
    Rueckfall.
    """
    zielordner.mkdir(parents=True, exist_ok=True)

    # Alte Bilder loeschen, damit Glob-Ergebnis definitionsgemaess den aktuellen Lauf widerspiegelt.
    for alte_datei in zielordner.glob("frame_*.jpg"):
        alte_datei.unlink()

    muster = str(zielordner / "frame_%03d.jpg")

    result_szenenerkennung = _lauf([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-vf", f"select='gt(scene,{schwelle})'",
        "-fps_mode", "vfr",
        "-frames:v", str(max_frames),
        muster,
    ])
    frames = sorted(zielordner.glob("frame_*.jpg"))
    if frames:
        return frames

    # Rueckfall: alle 2 Sekunden ein Bild.
    result_rueckfall = _lauf([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-vf", "fps=1/2",
        "-frames:v", str(max_frames),
        muster,
    ])
    frames = sorted(zielordner.glob("frame_*.jpg"))
    if frames:
        return frames

    # Beide Stufen haben nichts geliefert — Fehler mit stderr des letzten Laufs.
    fehlermeldung = result_rueckfall.stderr or result_szenenerkennung.stderr or "Unbekannter Fehler"
    raise FrameFehler(f"Keyframe-Extraktion fehlgeschlagen: {fehlermeldung}")
