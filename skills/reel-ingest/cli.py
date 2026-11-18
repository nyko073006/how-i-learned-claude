"""Einstiegspunkt fuer den Hook. Liest die Nutzlast von stdin."""
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).parent
sys.path.insert(0, str(WURZEL))
from src.detect import detect_reel          # noqa: E402
from src.pipeline import verarbeite, raeume_auf  # noqa: E402

STANDARD_CONFIG = {"aktiv": True, "cookies_browser": None, "max_alter_tage": 14}

# Telegram-Nachrichten kommen als "<channel source=\"telegram\" ...> Text"
# beim Hook an. Das "fyi:"-Praefix in src.detect.SKIP_PRAEFIX bezieht sich
# laut Spec auf die Nachricht, nicht auf dieses Metadaten-Tag (^-verankert) —
# das Tag muss vor detect_reel() weg, sonst greift "fyi:" nie bei
# Telegram-Nachrichten und die Kette laedt trotzdem herunter.
CHANNEL_TAG = re.compile(r"^\s*<channel\b[^>]*>\s*")


def lade_config() -> dict:
    """Fehlende oder kaputte Config darf die Kette nicht umbringen."""
    try:
        return {**STANDARD_CONFIG, **json.loads((WURZEL / "config.json").read_text())}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(STANDARD_CONFIG)


def main() -> int:
    roh = sys.stdin.read()
    try:
        prompt = json.loads(roh).get("prompt", "")
    except (json.JSONDecodeError, AttributeError):
        return 0                      # Muell rein, nichts raus — nie blockieren

    config = lade_config()
    if not config["aktiv"]:
        return 0                      # Der Aus-Schalter

    if "source=\"telegram\"" not in prompt and "source=\\\"telegram\\\"" not in prompt:
        return 0

    nachricht = CHANNEL_TAG.sub("", prompt, count=1)
    treffer = detect_reel(nachricht)
    if not treffer:
        return 0

    plattform, url = treffer
    raeume_auf(max_alter_tage=config["max_alter_tage"])
    try:
        dossier = verarbeite(url, plattform,
                             cookies_browser=config["cookies_browser"])
    except Exception as fehler:                       # noqa: BLE001
        print(f"reel-ingest: Verarbeitung fehlgeschlagen — {fehler}")
        return 0

    if dossier["bereits_verarbeitet"]:
        print(f"reel-ingest: Dieses Reel wurde schon verarbeitet "
              f"({dossier['ordner']}). Kein zweiter Durchlauf.")
        return 0

    def _palette_zeile(d: dict) -> str:
        """Die Palette in einer Zeile -- oder warum es keine gibt.

        `—` steht ausdruecklich fuer "nicht gemessen" und nicht fuer "keine
        Farben": den Grund nennt die Hinweiszeile darunter. Ein leeres Feld
        ohne beides waere die Verwechslung, gegen die dieser Skill gebaut ist.
        """
        palette = d.get("palette") or []
        if not palette:
            return "—"
        return "  ".join(f"{e['hex']} {round(e['anteil'] * 100)}%"
                         for e in palette)

    print(
        "reel-ingest: Dossier liegt bereit. Folge jetzt der Anweisung in "
        f"{Path(__file__).parent / 'SKILL.md'} ab Stufe 3.\n"
        f"  Ordner:     {dossier['ordner']}\n"
        f"  Titel:      {dossier['titel']}\n"
        f"  Uploader:   {dossier['uploader']}\n"
        f"  Transkript: {dossier['transkript_quelle']}, "
        f"{len(dossier['transkript'])} Zeichen\n"
        f"  Frames:     {len(dossier['frames'])}\n"
        f"  Palette:    {_palette_zeile(dossier)}\n"
        f"  Caption:    {dossier['caption'][:400]}"
    )
    if dossier.get("frames_fehler"):
        print(f"  Hinweis:    Bilder unvollstaendig — {dossier['frames_fehler']}")
    if dossier.get("palette_fehler"):
        # Dieselbe Linie wie untertitel_fehler unten (Task 11a): ein
        # Teil-Ausfall, den die Zusammenfassung verschweigt, laesst ein halbes
        # Dossier wie ein volles aussehen. Ohne diese Zeile saehe eine
        # ausgefallene Farbmessung genauso aus wie ein Reel ohne Farben.
        print(f"  Hinweis:    Farbpalette nicht gemessen — {dossier['palette_fehler']}")
    if dossier.get("transkript_fehler"):
        print(f"  Hinweis:    Transkript unvollstaendig — {dossier['transkript_fehler']}")
    if dossier.get("untertitel_fehler"):
        # Fund 3 (Fix-Runde 1, Task 11a): ohne diese Zeile war im
        # Drosselungsfall nicht zu unterscheiden, ob Untertitel schlicht
        # fehlten oder aktiv verweigert wurden — das Transkript kam trotzdem
        # per Whisper zustande (siehe transkript_quelle oben).
        print(f"  Hinweis:    Untertitel nicht verfuegbar (Transkript ggf. "
              f"per Whisper) — {dossier['untertitel_fehler']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
