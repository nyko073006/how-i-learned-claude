---
tags:
  - claude-code
  - kurs-notiz
status: aktiv
aktualisiert: 2026-09-29
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
| Handoff und `/clear` | Vorhanden: Kontext-Cap 150k, Skill `handoff` (bis 2026-09-29 `session-uebergabe`), clearable-Regel |
| CLAUDE.md unter 200 Zeilen | Vorhanden: 122 Zeilen |
| .md statt PDF | Neu, als Regel uebernommen (siehe unten) |
| Modell passend zur Aufgabe | Vorhanden: Opus Lead, Sonnet Sub-Agents, Fable auf Zuruf. Das Workshop-Beispiel (Wochenlimit in 8 Stunden weg, alles lief ueber das teuerste Modell) ist meine Ausgangslage vom 2026-09-24. |
| Caveman-Skill | Korrektur 2026-09-29: war installiert (`caveman` plus Varianten und die deutsche Fassung `hoehlenmensch`), aber kaum genutzt. Beim Ausduennen bleibt nur `hoehlenmensch`, die englische Familie ist archiviert. Offen: `hoehlenmensch` besser in den Alltag integrieren. Zahlen (45 bis 87 Prozent kuerzer) vom Presenter bzw. Entwickler. |
| Context Mode | Nicht installiert. Drittanbieter, Installation per kopiertem Prompt von context.scale.de: Prompt vorher lesen. Zahlen (3 Stunden laenger, 98 Prozent weniger Daten) vom Entwickler. |
| Terminal statt App | Offen. Passt zum Retro-Log: In VS Code gewinnt der Picker ueber settings.json. |
| Kontext in Prozent sehen | Eingerichtet am 2026-09-27: Statusline mit k-Tokens, Prozent und HANDOFF ab 150k, siehe `settings/2026-09-27-settings-aenderungen.md`. |

## Was aendert sich an meinem Setup

- Neue Regel in der CLAUDE.md, Abschnitt Kontext-Cap: PDFs vorher mit Markitdown in Markdown umwandeln.
- Statusline mit Kontextanzeige eingerichtet (nur im Terminal sichtbar).
- Kandidaten zum Testen, je einzeln und mit Messung per `/usage`: Terminal statt VS Code, `hoehlenmensch` gezielt einsetzen statt zusaetzlich Context Mode.

## Regel-Kandidat

PDFs nie direkt einlesen, vorher mit Markitdown in Markdown umwandeln. Bestaetigt und uebernommen am 2026-09-27, siehe [[Changelog]].

## Einordnung

- Der Workshop ist auch Verkaufsveranstaltung fuer die Academy.
- Zahlen ungeprueft, Angaben des Presenters: 0,4 Prozent der Weltbevoelkerung nutzen Coding-Agents, rund 1 Prozent zahlen fuer KI (Grafik "Each square is ~3.3 million people", Stand August 2026, Quelle laut Folie Philipp Baldauf); Anthropic-Messung 99,7 Prozent Trefferquote bei kurzem gegen 69 Prozent bei langem Verlauf; 20-seitige PDF mind. 50k Tokens, als .md rund 12k.

## Status

vertieft
