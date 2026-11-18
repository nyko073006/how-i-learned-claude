"""Die Farben, die ein Reel wirklich benutzt -- gemessen, nicht geschaetzt.

WARUM NICHT `ffmpeg palettegen`: das erzeugt zwar eine Palette, sagt aber
nicht, WIE VIEL Flaeche jede Farbe einnimmt. Genau das ist die Angabe, auf
die es beim Nachbauen ankommt -- eine Akzentfarbe mit 3 Prozent Flaeche ist
etwas anderes als ein Hintergrund mit 60, obwohl beide in derselben Palette
stehen. Deshalb wird hier ueber die bereits geschnittenen Keyframes gezaehlt.

WARUM KEINE NEUE ABHAENGIGKEIT (Pillow, OpenCV, colorthief): der Skill bricht
laut eigener Regel ab, wenn eine Umsetzung eine neue Abhaengigkeit braucht --
diese Regel gilt fuer ihn selbst genauso. ffmpeg ist ohnehin da (frames.py),
numpy ebenso. ffmpeg wandelt das JPEG in rohe RGB-Bytes, numpy zaehlt sie.

WARUM QUANTISIERT WIRD: ein JPEG hat durch die verlustbehaftete Kompression
tausende minimal verschiedener Farbwerte. Ungebuendelt gezaehlt waere jede
Farbe einzigartig und jeder Anteil winzig -- die Messung saehe aus wie
Rauschen. Gebuendelt wird ueber die oberen Bits, ZURUECKGEGEBEN wird aber der
echte Mittelwert des Buendels: sonst waere der Hex-Wert auf ein Raster
gerundet und damit nicht der Farbwert, den das Reel zeigt.
"""
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np


class PaletteFehler(Exception):
    """Ein Bild liess sich nicht als Farbe lesen."""
    pass


# Zeitlimit je ffmpeg-Aufruf. Deutlich kleiner als FFMPEG_ZEITLIMIT_SEKUNDEN
# in frames.py (30s): dort wird ein ganzes Video durchsucht, hier nur ein
# einzelnes, bereits geschnittenes Standbild auf 64x64 verkleinert. Gemessen
# unter 0,05s je Bild -- 10s sind das Zweihundertfache und fangen ein echtes
# Haengen ab, ohne einen langsamen Rechner zu bestrafen.
FFMPEG_ZEITLIMIT_SEKUNDEN = 10

# Kantenlaenge, auf die jedes Bild vor dem Zaehlen verkleinert wird.
# 64x64 = 4.096 Bildpunkte je Frame. Bei bis zu 20 Keyframes sind das rund
# 82.000 Punkte -- genug, dass ein Element von einem Prozent Bildflaeche noch
# mit ~40 Punkten je Frame vertreten ist, und wenig genug, dass die Messung
# im Millisekundenbereich bleibt. Farbanteile sind Flaechenverhaeltnisse;
# gleichmaessiges Verkleinern laesst sie unveraendert.
RASTER = 64

# Buendelbreite je Farbkanal, als Anzahl zu verwerfender Bits.
# 3 Bits = 32 Stufen je Kanal statt 256. Feiner (2 Bits) zerfaellt ein
# einzelner Farbverlauf in mehrere Eintraege; groeber (4 Bits) wirft
# unterscheidbare Markenfarben zusammen -- z.B. laegen zwei Blautoene, die
# sich um 15 Einheiten unterscheiden, im selben Buendel.
BUENDEL_BITS = 3


def _hex_zu_rgb(farbe: str) -> tuple[int, int, int]:
    """'#1a2b3c' -> (26, 43, 60). Auch fuer Tests, deshalb hier."""
    wert = farbe.lstrip("#")
    return tuple(int(wert[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_zu_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(round(k)) for k in rgb))


def _bildpunkte(bild: Path) -> np.ndarray:
    """Ein Bild als (N, 3)-Feld roher RGB-Werte.

    ffmpeg schreibt nach stdout, damit keine Zwischendatei entsteht -- eine
    Zwischendatei je Bild waere bei 20 Keyframes 20-mal Aufraeumarbeit, die
    bei einem Abbruch liegen bliebe.
    """
    ergebnis = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(bild),
        "-vf", f"scale={RASTER}:{RASTER}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ], capture_output=True, timeout=FFMPEG_ZEITLIMIT_SEKUNDEN)

    roh = ergebnis.stdout
    if ergebnis.returncode != 0 or len(roh) < 3:
        meldung = (ergebnis.stderr or b"").decode("utf-8", "replace").strip()
        raise PaletteFehler(
            f"{bild.name} liess sich nicht als Bild lesen: "
            f"{meldung or 'ffmpeg lieferte keine Bildpunkte'}")

    # Angeschnittene Zeilen abschneiden statt zu raten: len(roh) muss durch 3
    # teilbar sein, sonst ist der letzte Bildpunkt unvollstaendig.
    nutzbar = len(roh) - (len(roh) % 3)
    return np.frombuffer(roh[:nutzbar], dtype=np.uint8).reshape(-1, 3)


def _auswerten(zaehler: dict, summen: dict, farben: int) -> list[dict]:
    """Gezaehlte Buendel -> Palette. Der gemeinsame Kern beider Wege.

    Getrennt, damit `hole_palette` (aus Bildern) und `hole_palette_aus_video`
    nicht zwei Rechenwege fuer dieselbe Frage haben -- zwei Wege waeren zwei
    Gelegenheiten, sich zu widersprechen.
    """
    gesamt = sum(zaehler.values())
    if not gesamt:
        return []
    haeufigste = sorted(zaehler.items(), key=lambda p: p[1], reverse=True)[:farben]
    return [{"hex": _rgb_zu_hex(summen[wert] / wieoft),
             "anteil": round(wieoft / gesamt, 4)}
            for wert, wieoft in haeufigste]


def _einsortieren(punkte: np.ndarray, zaehler: dict, summen: dict) -> None:
    """Bildpunkte in die Buendel einzaehlen (veraendert zaehler/summen)."""
    gebuendelt = punkte >> BUENDEL_BITS
    schluessel = (gebuendelt[:, 0].astype(np.int32) << 16 |
                  gebuendelt[:, 1].astype(np.int32) << 8 |
                  gebuendelt[:, 2].astype(np.int32))

    werte, anzahl = np.unique(schluessel, return_counts=True)
    for wert, wieoft in zip(werte.tolist(), anzahl.tolist()):
        zaehler[wert] += wieoft
        maske = schluessel == wert
        summen[wert] += punkte[maske].sum(axis=0, dtype=np.int64)


def hole_palette_aus_video(video: Path, farben: int = 6,
                           abtastrate: float = 2.0) -> list[dict]:
    """Die Farben des VIDEOS, gleichmaessig ueber seine Laufzeit abgetastet.

    DER RICHTIGE WEG FUER EINE FARBPALETTE, und der Grund steht in einem
    echten Fehlschlag: die erste Fassung las die Farben aus den Keyframes,
    die `schneide_keyframes` an SZENENWECHSELN schneidet. Ein Testvideo aus
    zwei gleich langen Haelften (blau, dann orange) ergab damit eine Palette
    mit einer einzigen Farbe zu 100 Prozent -- weil es genau einen Wechsel
    gab und damit genau ein Bild. Die Messung behauptete die Farbverteilung
    des Videos und zeigte die eines Standbilds.

    `abtastrate` in Bildern je Sekunde. 2.0 heisst: alle 0,5 Sekunden ein
    Bild. Bei einem Reel von 30 Sekunden sind das 60 Abtastungen -- fein
    genug, dass ein zwei Sekunden langer Farbwechsel mit rund 4 Bildern
    vertreten ist, und grob genug, dass die Messung im Sekundenbereich
    bleibt. Anteile sind damit ZEITanteile mal FLAECHENanteile, also genau
    das, was ein Betrachter als "dominante Farbe" wahrnimmt.

    Ein Aufruf, keine Zwischendateien: ffmpeg skaliert und schreibt die
    rohen Bildpunkte nach stdout.
    """
    ergebnis = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(video),
        "-vf", f"fps={abtastrate},scale={RASTER}:{RASTER}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ], capture_output=True, timeout=FFMPEG_ZEITLIMIT_SEKUNDEN * 3)

    roh = ergebnis.stdout
    if ergebnis.returncode != 0 or len(roh) < 3:
        meldung = (ergebnis.stderr or b"").decode("utf-8", "replace").strip()
        raise PaletteFehler(
            f"{video.name} liess sich nicht abtasten: "
            f"{meldung or 'ffmpeg lieferte keine Bildpunkte'}")

    nutzbar = len(roh) - (len(roh) % 3)
    punkte = np.frombuffer(roh[:nutzbar], dtype=np.uint8).reshape(-1, 3)

    zaehler = defaultdict(int)
    summen = defaultdict(lambda: np.zeros(3, dtype=np.int64))
    _einsortieren(punkte, zaehler, summen)
    return _auswerten(zaehler, summen, farben)


def hole_palette(bilder: list[Path], farben: int = 6,
                 nachsichtig: bool = False) -> list[dict]:
    """Die haeufigsten Farben ueber alle Bilder, absteigend nach Flaechenanteil.

    Rueckgabe: `[{"hex": "#1a2b3c", "anteil": 0.42}, ...]`, hoechstens
    `farben` Eintraege. `anteil` bezieht sich auf ALLE gezaehlten Bildpunkte,
    nicht nur auf die zurueckgegebenen -- die Summe der gezeigten Anteile ist
    also kleiner als 1, sobald `farben` abschneidet. Das ist Absicht: ein auf
    1 hochgerechneter Anteil wuerde behaupten, die Palette sei vollstaendig.

    Ohne Bilder kommt `[]` zurueck. Das ist eine leere Messung und kein
    Fehler -- der Aufrufer soll selbst entscheiden, nicht eine erfundene
    Farbe bekommen.

    `nachsichtig=True` ueberspringt unlesbare Bilder, statt abzubrechen: bei
    zwanzig Keyframes ist ein kaputtes kein Grund, die uebrigen wegzuwerfen.
    Bleibt am Ende KEIN einziges lesbares Bild uebrig, wird trotzdem
    geworfen -- sonst saehe "alles kaputt" wie "keine Farben" aus.
    """
    if not bilder:
        return []

    zaehler = defaultdict(int)
    summen = defaultdict(lambda: np.zeros(3, dtype=np.int64))
    gelesen = 0

    for bild in bilder:
        try:
            punkte = _bildpunkte(bild)
        except (PaletteFehler, subprocess.TimeoutExpired):
            if nachsichtig:
                continue
            raise
        gelesen += 1
        _einsortieren(punkte, zaehler, summen)

    if gelesen == 0:
        raise PaletteFehler(
            f"Keines der {len(bilder)} Bilder liess sich lesen -- das ist "
            f"kein Ergebnis, sondern ein Ausfall der Messung.")

    return _auswerten(zaehler, summen, farben)
