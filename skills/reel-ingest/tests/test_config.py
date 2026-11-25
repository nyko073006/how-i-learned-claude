import json
from pathlib import Path

WURZEL = Path(__file__).parent.parent


def test_config_hat_alle_schalter():
    c = json.loads((WURZEL / "config.json").read_text())
    for schluessel in ("aktiv", "max_zeilen", "max_dateien",
                       "cookies_browser", "max_alter_tage"):
        assert schluessel in c, f"{schluessel} fehlt"


def test_grenzen_entsprechen_der_spec():
    c = json.loads((WURZEL / "config.json").read_text())
    assert c["max_zeilen"] == 150
    assert c["max_dateien"] == 5
    assert c["max_alter_tage"] == 14


def test_registry_beispiel_vollstaendig():
    text = (WURZEL / "references" / "projekte.beispiel.md").read_text()
    assert "| Projekt | Pfad | Wofuer | Passt bei Reels ueber |" in text
    # Die Regel muss in der Registry stehen, weil das Modell nur sie liest.
    assert "kein ausweichziel" in text.lower()
    zeilen = [z for z in text.splitlines() if z.startswith("| ") and "---" not in z]
    assert len(zeilen) == 4  # Kopf plus drei Beispielprojekte
    assert "Terminplaner-App" in text
