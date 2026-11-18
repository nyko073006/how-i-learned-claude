# launch-check

Prueft eine KI-gebaute Website oder Web-App vor dem Livegang. Fuenf Creator lieferten je eine eigene 20-Punkte-Liste; dieser Skill fuehrt sie zusammen und gibt jedem Punkt einen Pruefweg (Befehl, Handgriff oder Code-Fundstelle), damit am Ende eine Rot/Gruen-Liste mit Beleg steht statt eines Bauchgefuehls.

![launch-check Ablauf](launch-check-overview.png)

> Quelle des Diagramms: [`launch-check-overview.excalidraw`](launch-check-overview.excalidraw)

## Installation

Ordner nach `~/.claude/skills/launch-check/` kopieren (Befehle im Abschnitt "Skills" des Haupt-README von [how-i-learned-claude](https://github.com/nyko073006/how-i-learned-claude#installation)). Abhaengigkeiten: `curl`, `dig` und `nc` fuer die Pruefungen von aussen.

## Nutzung

```text
/launch-check https://meine-seite.de
/launch-check vorher   (Design-Vorgaben fuer ein neues Projekt)
```

## Umfang

- **Vorher:** Styleguide-PDF, Stil beim Namen, eine Aktionsfarbe, Komponentenbasis, Muster fuer Loeschen.
- **Pruefen:** A von aussen (curl, dig, nc), B von Hand (Wegwerf-Mail, zweites Konto), C Code-Audit (Secrets auch im Git-Verlauf, Rechte serverseitig, Zahlungen, Uploads), D KI-Spuren, E Auffindbarkeit, F Konversion und Recht (DE).

## Hintergrund

Aus rund 20 Instagram-Reels (Stand 10/2026), gebuendelt im Sammelmodus von reel-ingest. Befehlsblock am 30.10.2026 gegen example.com getestet; H1-Zaehlung mit Gegentest (zwei H1 in einer Zeile).

## Dateistruktur

```
launch-check/
├── SKILL.md
├── README.md
├── launch-check-overview.excalidraw
└── launch-check-overview.png
```
