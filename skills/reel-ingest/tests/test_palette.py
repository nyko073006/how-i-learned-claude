"""Die Farben, die das Reel wirklich benutzt -- nicht die, die man erinnert.

Testvideos werden hier mit `ffmpeg -f lavfi` erzeugt statt als Datei
mitgeliefert: eine bekannte Farbe hinein, dieselbe Farbe muss herauskommen.
Das ist die einzige Art, eine Farbmessung zu pruefen, ohne ihr zu glauben.
"""
import subprocess
from pathlib import Path

import pytest

from src.palette import PaletteFehler, hole_palette, _hex_zu_rgb


def _bild(pfad: Path, farbe: str, groesse: str = "160x120") -> Path:
    """Ein einfarbiges JPEG mit ffmpeg erzeugen."""
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c={farbe}:size={groesse}",
        "-frames:v", "1", str(pfad),
    ], check=True, capture_output=True)
    return pfad


def _abstand(hex_a: str, hex_b: str) -> float:
    """Abstand zweier Farben im RGB-Wuerfel, 0 = gleich."""
    a, b = _hex_zu_rgb(hex_a), _hex_zu_rgb(hex_b)
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class TestFarbeWirdWiedergefunden:
    """Die Grundprobe: bekannte Farbe rein, dieselbe Farbe raus."""

    def test_einfarbiges_bild_liefert_genau_diese_farbe(self, tmp_path):
        bild = _bild(tmp_path / "blau.jpg", "blue")

        palette = hole_palette([bild])

        assert palette, "Ein einfarbiges Bild muss mindestens eine Farbe ergeben."
        # JPEG ist verlustbehaftet, exakte Gleichheit waere die falsche Zusage.
        # 40 von 441 moeglichen Einheiten ist eng genug, dass keine andere
        # Grundfarbe hineinpasst.
        assert _abstand(palette[0]["hex"], "#0000ff") < 40, (
            f"Blau erwartet, {palette[0]['hex']} gemessen.")

    def test_der_hexwert_ist_nicht_aufs_buendelraster_gerundet(self, tmp_path):
        """Zurueck kommt der echte Farbmittelwert, nicht die Buendelmitte.

        GEFUNDEN DURCH EINE MUTATIONSPROBE: ersetzt man den Mittelwert durch
        die gerasterte Buendelmitte, blieben alle uebrigen Tests dieser Datei
        gruen -- die Rasterung verschiebt je Kanal um hoechstens 7 Einheiten
        und fiel damit unter jede hier verwendete Toleranz. Der Docstring von
        `hole_palette` behauptete etwas, das nichts nachprueft.

        0x7f = 127 liegt bewusst zwischen zwei Rasterpunkten: gebuendelt
        (>> 3, << 3) waere daraus 120. Wer 120 zurueckgibt, nennt dem Nutzer
        eine Farbe, die im Reel nicht vorkommt.
        """
        bild = _bild(tmp_path / "grau.jpg", "0x7f7f7f")

        palette = hole_palette([bild])

        gemessen = _hex_zu_rgb(palette[0]["hex"])[0]
        assert abs(gemessen - 127) < 4, (
            f"Erwartet ~127 (echter Wert), gemessen {gemessen}. "
            f"120 bedeutet: auf die Buendelmitte gerundet.")

    def test_die_groessere_flaeche_steht_vorn(self, tmp_path):
        """Sortiert wird nach Anteil -- sonst waere die Reihenfolge Zufall."""
        gross = _bild(tmp_path / "rot1.jpg", "red")
        gross2 = _bild(tmp_path / "rot2.jpg", "red")
        klein = _bild(tmp_path / "gruen.jpg", "green")

        palette = hole_palette([gross, gross2, klein])

        assert _abstand(palette[0]["hex"], "#ff0000") < 60, (
            "Zwei von drei Bildern sind rot -- Rot muss vorn stehen.")
        assert palette[0]["anteil"] > palette[-1]["anteil"]


class TestPaletteAusDemVideo:
    """Die Palette muss das ganze Video abbilden, nicht nur seine Schnitte.

    GEFUNDEN IM ERSTEN ECHTEN DURCHSTICH: ein Testvideo aus zwei gleich
    langen Haelften (blau, dann orange) ergab eine Palette mit EINER Farbe zu
    100 Prozent. Grund: `schneide_keyframes` schneidet an Szenenwechseln, und
    bei genau einem Wechsel gibt es genau ein Bild. Fuer die Technik-Analyse
    ist das richtig -- sie will die gezeigten Bildschirme. Fuer eine
    Farbmessung ist es falsch: sie behauptete eine Farbverteilung des Videos
    und zeigte die eines einzelnen Standbilds.
    """

    def _zweifarbig(self, pfad: Path) -> Path:
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0x0000ff:duration=2:size=160x120:rate=25",
            "-f", "lavfi", "-i", "color=c=0xffff00:duration=2:size=160x120:rate=25",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-pix_fmt", "yuv420p", str(pfad),
        ], check=True, capture_output=True)
        return pfad

    def test_beide_haelften_stehen_in_der_palette(self, tmp_path):
        from src.palette import hole_palette_aus_video

        video = self._zweifarbig(tmp_path / "zwei.mp4")

        palette = hole_palette_aus_video(video, farben=4)

        hexwerte = [e["hex"] for e in palette]
        blau = any(_abstand(h, "#0000ff") < 60 for h in hexwerte)
        gelb = any(_abstand(h, "#ffff00") < 60 for h in hexwerte)
        assert blau and gelb, (
            f"Beide Haelften erwartet, gemessen: {hexwerte}")

    def test_gleich_lange_haelften_ergeben_aehnliche_anteile(self, tmp_path):
        from src.palette import hole_palette_aus_video

        video = self._zweifarbig(tmp_path / "zwei.mp4")

        palette = hole_palette_aus_video(video, farben=2)

        for eintrag in palette:
            assert 0.3 <= eintrag["anteil"] <= 0.7, (
                f"Zwei gleich lange Haelften, aber Anteil "
                f"{eintrag['anteil']} -- die Zeit wird nicht gleichmaessig "
                f"abgetastet.")

    def test_kaputtes_video_meldet_sich(self, tmp_path):
        from src.palette import hole_palette_aus_video

        kaputt = tmp_path / "kaputt.mp4"
        kaputt.write_bytes(b"kein video")

        with pytest.raises(PaletteFehler):
            hole_palette_aus_video(kaputt)


class TestAnteileSindEhrlich:
    """Ein Anteil, der nicht aufgeht, ist eine erfundene Zahl."""

    def test_anteile_summieren_sich_auf_eins(self, tmp_path):
        bilder = [_bild(tmp_path / "a.jpg", "blue"),
                  _bild(tmp_path / "b.jpg", "yellow")]

        palette = hole_palette(bilder, farben=8)

        summe = sum(e["anteil"] for e in palette)
        assert 0.99 <= summe <= 1.01, f"Summe {summe}, erwartet 1.0"

    def test_zwei_gleich_grosse_flaechen_teilen_sich_haelftig(self, tmp_path):
        bilder = [_bild(tmp_path / "a.jpg", "blue"),
                  _bild(tmp_path / "b.jpg", "yellow")]

        palette = hole_palette(bilder, farben=2)

        for eintrag in palette:
            assert 0.35 <= eintrag["anteil"] <= 0.65, (
                f"Zwei gleich grosse Bilder, aber Anteil {eintrag['anteil']}.")


class TestGrenzen:
    """Was passiert, wenn nichts oder Kaputtes hereinkommt."""

    def test_obergrenze_wird_eingehalten(self, tmp_path):
        bilder = [_bild(tmp_path / f"{f}.jpg", f)
                  for f in ("red", "green", "blue", "yellow")]

        palette = hole_palette(bilder, farben=2)

        assert len(palette) <= 2

    def test_ohne_bilder_leere_palette_statt_absturz(self):
        """Keine Bilder ist kein Fehler -- es ist eine leere Messung.

        Und eine leere Messung ist niemals ein Fund: der Aufrufer muss
        `[]` bekommen und selbst entscheiden, nicht eine erfundene Farbe.
        """
        assert hole_palette([]) == []

    def test_kaputte_datei_meldet_sich_statt_zu_schweigen(self, tmp_path):
        kaputt = tmp_path / "kaputt.jpg"
        kaputt.write_bytes(b"das ist kein bild")

        with pytest.raises(PaletteFehler):
            hole_palette([kaputt])

    def test_eine_kaputte_datei_unter_guten_kippt_nicht_alles(self, tmp_path):
        """Ein unlesbares Bild darf die Messung der uebrigen nicht wegwerfen.

        Bei einem Reel mit 20 Keyframes ist ein einzelnes kaputtes Bild
        kein Grund, gar keine Palette zu liefern -- wohl aber ein Grund,
        es zu erwaehnen (siehe `uebersprungen` im Rueckgabewert der
        Pipeline).
        """
        gut = _bild(tmp_path / "gut.jpg", "blue")
        kaputt = tmp_path / "kaputt.jpg"
        kaputt.write_bytes(b"kein bild")

        palette = hole_palette([gut, kaputt], nachsichtig=True)

        assert palette, "Das gute Bild allein muss reichen."
        assert _abstand(palette[0]["hex"], "#0000ff") < 40
