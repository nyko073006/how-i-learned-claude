---
name: reload-verlust
description: >
  Prueft nach einem Neuladen oder Neustart von Obsidian (Glasscockpit, agentic-os), was an
  Claude-Sitzungen verloren ging: welche Tabs gearbeitet haben, ohne dass ihr Transkript es
  festhielt, welche Belege (Commits, Vault-Dateien, Kontextstand) das zeigen, was ungesichert in
  Worktrees liegt und ob Obsidian die Markierung CLAUDE_CODE_CHILD_SESSION geerbt hat. Liest nur.
  Verwenden bei "was ist beim reload verloren gegangen", "was hat der neustart zerschossen",
  "wo waren wir", "reload-verlust", "welche sitzungen sind weg", "tabs nach neustart pruefen".
version: 1.1.4
user-invocable: true
allowed-tools:
  - Bash
  - Read
---

## Vault-Pfad

`<VAULT>` steht in diesem Skill für den Pfad deines Obsidian-Vaults. Er steht in `~/.config/claude-skills/einstellungen.json` unter `vault`. Lies ihn vor dem ersten Zugriff:

```bash
python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.config/claude-skills/einstellungen.json")))["vault"]))'
```

Fehlt die Datei oder der Schlüssel oder ist der Wert leer, frag nach dem Pfad. Fehlt die Datei, lege sie mit `{"vault": "<Pfad>"}` an. Sonst trag den Pfad unter `vault` in die bestehende Datei ein und lass alle anderen Schlüssel unverändert.

# reload-verlust — Was ging beim letzten Neuladen verloren?

Beim Neuladen des Cockpits oder einem Neustart von Obsidian brechen alle Cockpit-Tabs ab.
Fortgesetzte Tabs (`--resume`) landen beim letzten gespeicherten Stand. Hat Obsidian vorher
`CLAUDE_CODE_CHILD_SESSION=1` geerbt (aus einer Claude-Sitzung gestartet), haben die Tabs schon
lange davor nichts mehr ins Transkript geschrieben. Dann fehlen Stunden.

## Ablauf

1. **Skript laufen lassen** (liest nur, rund 5 bis 10 Sekunden):

   ```bash
   python3 -I ~/.claude/skills/reload-verlust/scripts/reload_verlust.py > <scratchpad>/reload-verlust.md
   ```

   Ausgabe in eine Datei im Scratchpad, dann lesen. Zeitpunkt: Vorgabe ist der Start des
   Obsidian-Prozesses. Bei `plugin:reload` laeuft der Prozess weiter, dann `--zeit HH:MM` angeben
   (Zeit des Neuladens, notfalls aus der Frage des Nutzers oder dem ersten Eintrag nach der Luecke).

2. **Bericht deuten.** Je Sitzung ein Urteil:
   - `KEIN TRANSKRIPT`: Tab mit Kontext, aber ohne jede Transkriptdatei. Ganze Sitzung weg.
   - `VERLUST`: belegt gearbeitet nach der letzten gespeicherten Nachricht. Belege: Kontextstand
     der Statuszeile weicht vom Transkript ab, Commit mit dem `Claude-Session`-Trailer der Sitzung,
     Vault-Datei mit ihrer Session-URL.
   - `OFFENER AUFRUF`: letzter Werkzeugaufruf ohne Ergebnis, Ausgang unbekannt.
   - `OK`: kein Beleg fuer spaetere Arbeit.
   - Abschnitt „Ohne Zuordnung“: Commits ohne Trailer (meist Sub-Agents) und Worktrees mit
     ungesicherten Aenderungen aus dem Verlustfenster.

3. **Nachpruefen, bevor es Fakt wird.** Fuer jede `VERLUST`-Sitzung den juengsten Beleg ansehen
   (Handoff, Plan-Kaestchen, `git log` im Worktree), um zu sagen, wo die Arbeit stand. Belege
   zeigen, *dass* gearbeitet wurde, nicht *was*. Commits ohne Trailer nur als „wahrscheinlich“
   zuordnen (gleicher Repo, passende Zeit).

4. **Antwort an den Nutzer**, kurz, je betroffener Sitzung: Thema, letzter gespeicherter Stand,
   was auf der Platte gesichert ist, was wirklich offen ist (laufender Sub-Agent, ungeprueftes
   Review, ungesicherte Dateien), naechster Schritt mit Handoff-Pfad. Sitzungen mit `OK` nur in
   einem Satz. Steht die Child-Markierung auf JA: sagen, dass gerade weiter Transkripte fehlen,
   und Cmd+Q plus Neustart aus dem Dock empfehlen.

## Grenzen

- Die Statuszeile schreibt ihre Datei auch im Leerlauf (`refreshInterval`). Ihr Zeitstempel zeigt
  nur „Tab war offen“, nie Arbeit. Ein wieder geoeffneter Tab ueberschreibt ihn.
- Belege gibt es nur, wenn die Sitzung etwas mit Trailer committet oder ihre Session-URL in den
  Vault geschrieben hat. Reine Gespraeche ohne Datei bleiben unsichtbar.
- Die Remote-Session (`cse_…`) ueberlebt `/clear`. Belege gehen an die juengste Sitzung im Tab.

## Optionen

| Option | Bedeutung |
|--------|-----------|
| `--zeit HH:MM` oder `--zeit "JJJJ-MM-TT HH:MM"` | Zeitpunkt des Neuladens; Vorgabe: Start des Obsidian-Prozesses |
| `--stunden N` | Rueckblick vor dem Neustart, Vorgabe 12 |
| `--repos ORDNER` | Ordner mit Git-Repos (eine Ebene tief), mehrfach; Vorgabe `repo_wurzeln` aus der Einstellungsdatei, sonst `~/Developer` (nur wenn der Schlüssel fehlt oder `null` ist; ein falscher Wert, `[]` oder ein leerer Pfad endet mit Exit 2) |
| `--projects`, `--cockpit` | Pfade zu Transkripten, Cockpit-Statusdateien |
| `--vault` | Pfad `<VAULT>`; Vorgabe `vault` aus der Einstellungsdatei, fehlt beides oder gibt es den Ordner nicht: Exit 2 mit Klartext |

## Verwandt

- Memory `obsidian-neuladen-beendet-sitzung`, `obsidian-erbt-child-session`
- `handoff` — damit beim naechsten Mal weniger verloren geht
