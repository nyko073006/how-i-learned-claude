"""Nachtwache: PreToolUse-Hook fuer unbeaufsichtigte Laeufe.

Sperrt Befehle mit Aussenwirkung oder Datenverlust (Push, Merge, PR, Deploy, Senden),
bevor sie laufen. Exit 2 = gesperrt, Begruendung auf stderr geht an Claude zurueck.
Sperrliste in nachtwache.json daneben. Nur per `claude --settings nachtwache-settings.json`
aktiv, nicht global.
"""
import json
import re
import sys
from pathlib import Path

LISTE = Path(__file__).with_name("nachtwache.json")


def gesperrt(werkzeug: str, eingabe: dict, liste: dict) -> str | None:
    if werkzeug == "Bash":
        befehl = eingabe.get("command", "")
        # Text in Anfuehrungszeichen (Commit-Nachrichten, echo) ist kein Befehl.
        ohne_text = re.sub(r"'[^']*'|\"[^\"]*\"", "''", befehl)
        for muster in liste["bash_muster"]:
            if re.search(muster, ohne_text, re.IGNORECASE):
                return f"Befehl '{befehl}' trifft Sperre {muster}"
    for muster in liste["werkzeug_muster"]:
        if re.search(muster, werkzeug, re.IGNORECASE):
            return f"Werkzeug {werkzeug} trifft Sperre {muster}"
    return None


def main() -> int:
    daten = json.load(sys.stdin)
    grund = gesperrt(daten.get("tool_name", ""), daten.get("tool_input") or {},
                     json.loads(LISTE.read_text(encoding="utf-8")))
    if grund:
        print(f"Nachtwache: {grund}. Unbeaufsichtigt gesperrt; als Blocker in DECISIONS.md "
              "festhalten statt umgehen.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
