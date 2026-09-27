---
tags:
  - claude-code
  - kurs-notiz
status: aktiv
aktualisiert: 2026-09-27
source: claude
chat_url: unbekannt
---

# Workshop - Claude Setup (Skaile Academy)

Kein Kursmodul, sondern der 90-Minuten-Live-Workshop des Kursanbieters. Inhaltlich deckt Teil 1 den Stoff von Modul 5 (Optimierung) ab, Teil 2 und 3 den von Modul 6 und 7. Plan: [[Lernplan]]. Quelle: Notion-Zusammenfassung mit Transkript, zwei Folien-Screenshots.

## Modul

- Nr: Workshop, kein Modul
- Titel: Warum Claude duemmer wird, Agenten aufsetzen, System bauen (Agentic OS)
- Datum angesehen: vor 2026-09-27

## Drei Stichpunkte

- Contextrot: Je voller der Kontext, desto schlechter die Antworten und desto schneller ist das Limit weg. Beides hat dieselbe Ursache. Handoff ab 70 bis 80 Prozent, dann `/clear`; nicht auf das automatische Zusammenfassen warten, das traegt die Fehler weiter.
- Agent = Chef (kennt den Aufgabenbereich), Skill = Rezept (Anleitung fuer eine Teilaufgabe), MCP = Steckdose (Anbindung an Tools). Aufgabe finden mit drei Fragen: Laeuft der Prozess schon sauber? Lohnt es sich (Haeufigkeit, Dauer, Nervfaktor)? Wie einfach ist es (klarer Input und Output, wenige Tools)? Komplexes nur zu 80 bis 90 Prozent abgeben, Ausgabe so bauen, dass der Rest von Hand geht.
- System statt Einzelaufgaben: Routinen ueber `/schedule` (laufen auch bei zugeklapptem Laptop), Kommandozentrale mit einem Tab pro Agent.

### Folie "Zum Mitnehmen aus Teil eins"

1. Handoff schreiben lassen, neues Gespraech. Im Terminal ab 70 bis 80 Prozent mit `/clear`
2. Im Chat ein Projekt, im Terminal eine CLAUDE.md unter 200 Zeilen
3. .md-Dateien statt PDFs
4. Das Modell passend zur Aufgabe
5. Der Caveman-Skill
6. Context Mode

## Abgleich mit meinem Setup (2026-09-27)

| Tipp | Stand |
|---|---|
| Handoff und `/clear` | Vorhanden: Kontext-Cap 150k, Skill `session-uebergabe`, clearable-Regel |
| CLAUDE.md unter 200 Zeilen | Vorhanden: 122 Zeilen |
| .md statt PDF | Neu, als Regel uebernommen (siehe unten) |
| Modell passend zur Aufgabe | Vorhanden: Opus Lead, Sonnet Sub-Agents, Fable auf Zuruf. Das Workshop-Beispiel (Wochenlimit in 8 Stunden weg, alles lief ueber das teuerste Modell) ist meine Ausgangslage vom 2026-09-24. |
| Caveman-Skill | Nicht installiert. Drittanbieter, Zahlen (45 bis 87 Prozent kuerzer) vom Presenter bzw. Entwickler. Steht gegen den offenen Punkt "Skills ausduennen". |
| Context Mode | Nicht installiert. Drittanbieter, Installation per kopiertem Prompt von context.scale.de: Prompt vorher lesen. Zahlen (3 Stunden laenger, 98 Prozent weniger Daten) vom Entwickler. |
| Terminal statt App | Offen. Passt zum Retro-Log: In VS Code gewinnt der Picker ueber settings.json. |
| Kontext in Prozent sehen | Offen: `/statusline` einrichten, dann ist der 150k-Cap sichtbar statt geschaetzt. |

## Was aendert sich an meinem Setup

- Neue Regel in der CLAUDE.md, Abschnitt Kontext-Cap: PDFs vorher mit Markitdown in Markdown umwandeln.
- Kandidaten zum Testen, je einzeln und mit Messung per `/usage`: Statusline mit Kontext-Prozent, Terminal statt VS Code, hoechstens eins von Caveman oder Context Mode.

## Regel-Kandidat

PDFs nie direkt einlesen, vorher mit Markitdown in Markdown umwandeln. Bestaetigt und uebernommen am 2026-09-27, siehe [[Changelog]].

## Einordnung

- Der Workshop ist auch Verkaufsveranstaltung fuer die Academy.
- Zahlen ungeprueft, Angaben des Presenters: 0,4 Prozent der Weltbevoelkerung nutzen Coding-Agents, rund 1 Prozent zahlen fuer KI (Grafik "Each square is ~3.3 million people", Stand August 2026, Quelle laut Folie Philipp Baldauf); Anthropic-Messung 99,7 Prozent Trefferquote bei kurzem gegen 69 Prozent bei langem Verlauf; 20-seitige PDF mind. 50k Tokens, als .md rund 12k.

## Status

vertieft
