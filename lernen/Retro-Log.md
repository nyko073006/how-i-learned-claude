---
tags:
  - claude-code
  - retro
status: aktiv
aktualisiert: 2026-11-16
source: claude
chat_url: unbekannt
---

# Retro-Log Arbeitsweise Claude Code

Datierte Eintraege, was an Regeln oder Settings geaendert wurde, warum, und ob es gewirkt hat. Neueste Eintraege oben.

## 2026-11-16 Spec-Gegenprüfung auf Fable außerhalb des Fokus, erster Lauf

### Änderung

- Globale CLAUDE.md vom 16.11.: Außerhalb des Fokusprojekts schreibt Opus die Spec, `skeptiker` mit `model: "fable"` prüft sie gegen, bevor geplant wird.

### Messung

- Erster Lauf: Website-Spec „Bühne Schwarz/Zoom“ (Opus-Lead, Website nicht Fokus), nach einem Builder-Check durch einen frischen Sub-Agent. Der Fable-Skeptiker fand 12 Befunde, davon 1 planblockierend (Regeltest wird mit winzigen Geräten grün, roter Gegentest gelaufen) und 6 mit Rotprobe am Spike-Build. Vier davon hat der Lead nachgeprüft, alle hielten. Daraus wurden Spec-Abschnitt 12 und vier Fragen an den Nutzer.
- Kosten: 234k Sub-Agent-Tokens, 27 Minuten.

### Urteil

- Wirkt: Der Builder-Check vorher hatte zwei Fragen gefunden, der Skeptiker die Lücken, die den Plan entwertet hätten. Weiter so, auf die nächsten zwei Specs beobachten.

## 2026-11-13 Wirkungskontrolle Tagesfokus und Besetzung mit Fable, Trimmrunde

Gemessen nach dem Reset am 13.11., 06:00, wie im Eintrag vom 11.11. angesetzt: Tagesfokus statt Sollkurve (Changelog 10.11.), Besetzung Lead Fable `xhigh`, Sub-Agents Opus `medium`, Recherche Sonnet, Review Fable `xhigh` (Changelog 11.11. (2)), Meldung von Gelb und Rot erst ab Tag 4 (Changelog 11.11.), dazu die Trimmrunde vom 11.11. Die Woche lief gemischt: Limittag 1 bis 4 ohne Fable, am 11.11. bis 21:21 Lead Fable faktisch `medium` (Effort-Wähler des Cockpits), danach `xhigh`.

### Gemessen

Quelle: `~/.claude/cockpit/limit-log.jsonl` (182 Einträge), Transkripte, `Limit-Eichung.py` (`woche`, Eichung, `fenster`), Tagesgrenze 06:00.

- Woche 2 (06.11. bis 13.11.), Stand am Tagesende gegen Soll: 26/13, 28/26, 38/39, 50/52, 56/65, 79/78, 99/90. Das Protokoll endet bei 99 % am 12.11. um 15:04. Das Wochenlimit war am 13.11. um 00:44 erreicht („You've hit your weekly limit“, zwei Meldungen in den Transkripten), 5 Stunden 16 Minuten vor dem Reset. Zwischen 15:04 und 00:44 liefen noch 0,20 Mio. Output-Tokens.
- Verbrauch: 32,40 Mio. Output-Tokens (Sonnet 16,18, Opus 11,35, Fable 4,52, Haiku 0,35), Rohquote 3,06 Punkte je Mio. Woche 1: 2,86.
- Höchster Sechs-Stunden-Anstieg: 16 Punkte (12.11., 07:55 bis 13:44). Woche 1: 30.
- Vor und nach dem Wechsel: Limittag 1 bis 4 (ohne Fable) 50 Punkte auf 23,04 Mio., das sind 2,17 je Mio. Vom 11.11., 06:00 bis 12.11., 15:05 (neue Besetzung) 43 Punkte auf 7,59 Mio., das sind 5,66 je Mio. bei 57 % Fable-Anteil. Limittag 6: 23 Punkte auf 4,23 Mio., Limittag 7: 20 Punkte auf 3,55 Mio. Beide Tage liegen beim Mediantag (4,2 Mio.) oder darunter.
- Lead `medium` gegen `xhigh`: 5,33 je Mio. bei 45 % Fable-Anteil (11.11., 06:00 bis 21:21) gegen 5,71 bei 67 % (danach bis 12.11., 15:04). Der Unterschied folgt dem Fable-Anteil, ein Aufschlag je Token durch `xhigh` ist nicht zu sehen. Ob `xhigh` je Aufgabe mehr Tokens braucht, misst das nicht.
- Schätzung je Modell über 180 Fenster beider Wochen, Punkte je Mio. Output-Tokens: Opus 2,88 (2,6 bis 3,2), Sonnet 2,23 (2,0 bis 2,5), Fable 7,74 (7,1 bis 8,5; Grundlage 4,49 Mio.). Fable getrennt: als Lead 8,6 (7,1 bis 11,4; 1,82 Mio.), im Sub-Agent 7,2 (6,1 bis 8,3; 2,66 Mio.). Spannen: 5. bis 95. Perzentil aus 3.000 Ziehungen der Fenster. Fable kostet je Output-Token rund das 2,7-Fache von Opus.
- Wohin die Fable-Tokens gingen (10.11. bis 13.11., Mio.): `task-reviewer` 2,37, Lead 1,78, `umsetzer` 0,25, `skeptiker` 0,11. Das Review ist der größte Posten.
- Verteilung auf Projekte am Limittag 7 (Fokus laut `fokus.json`: SAIN): SAIN 1,71 von 3,55 Mio. (48 %), Feiern HDH 1,04 (davon 0,79 Fable), [[dienstliche Daten-Admin - PMO HUB|dienstliche Daten-Admin]] 0,34. Limittag 6: SAIN 1,63 und Glasscockpit 1,51 von 4,23 Mio. Der Fokus des 11.11. ist nicht mehr nachzulesen, `fokus.json` hält nur den letzten Tag.
- Trimmrunde 11.11.: Startkontext `holger` 64k auf 39,0k, `task-reviewer` 22,7k, `~/AGENTS.md` aus dem Startkontext. Effort-Wähler des Cockpits auf `aus`, Lead seit 11.11., 21:21 im Transkript `xhigh`.
- Meldung ab Tag 4: `stufe()` des Hooks bleibt mit den geltenden Schwellen an Tag 1 bis 3 auch bei 30, 60 und 80 % still und meldet an Tag 4 Gelb bei 60 % und Rot bei 95 %. Im Betrieb erst in der Woche ab 13.11. zu sehen.

### Hat gewirkt

- Kein Ausreißer mehr: höchstens 16 Punkte in sechs Stunden statt 30, kein Nachtlauf.
- Die Trimmrunde hält. Startkontexte und Effort stehen im Transkript so, wie sie eingestellt sind.

### Nicht gewirkt

- Die Woche lief ins Limit; Woche 1 endete bei 92 % ohne Stopp. Ursache ist kein Ausreißer, sondern zwei gewöhnliche Tage mit der neuen Besetzung: 43 Punkte auf 7,78 Mio. Tokens.
- Der Tagesfokus begrenzt den Verbrauch nicht. Er regelt die Besetzung des Fokusprojekts, Fable sitzt aber als Lead und im Review in jedem Projekt. Am 12.11. lief die Hälfte der Tokens außerhalb des Fokusprojekts.
- Der Planwert 2,6 gilt für diese Besetzung nicht. Gemessen sind 5,5 bis 5,7 je Mio. Ein Mediantag kostet damit rund 24 Punkte, die Woche fasst rund 18 Mio. Output-Tokens. Die letzten beiden Wochen hatten je rund 32 Mio.
- `Limit-Eichung.py` schätzte bis heute zu tief: ungewichtet ergaben die Werte 162 statt 189 gemessener Punkte, für Woche 1 um 21 % zu wenig. Aus diesem Verfahren stammen Opus 2,32 und Sonnet 2,05 im Eintrag vom 11.11. und der Zwischenstand Fable 8,24 vom 12.11. Gewichtet liegt Sonnet rund ein Fünftel unter Opus, nicht gleichauf.

### Geändert

- `Limit-Eichung.py`: Schätzung gewichtet mit 1/Fenstertokens, Gegenprobe je Limitwoche (geschätzt gegen gemessen: 87/90 und 103/99), `woche` liest die Limitmeldung aus den Transkripten. Gegentest mit bekannter Wahrheit (Simulation, 2,6 / 2,2 / 7,5): ungewichtet je nach Beobachtungsverzug 2,32 bis 2,54 / 2,02 bis 2,15 / 5,96 bis 6,98, gewichtet 2,61 / 2,19 / 7,47. Alte Fassung und Rechenskripte: `~/.claude/_archiv/2026-11-13-limit-eichung/`. [[03 Bereiche/Claude Code/Fehlerlog|Fehlerlog]], 13.11.

### Urteil

Die Besetzung bestimmt den Wochenverbrauch, nicht der Tagesfokus. Mit Fable als Lead und im Review ist die Woche nach rund 18 Mio. Output-Tokens voll, das sind gut vier Mediantage.

### Offen

- Entschieden von Nyko am 13.11. („ja wie du gesagt hast fable nur lead und review den rest macht opus“): Fable nur im Fokusprojekt, dort als Lead und im Review; sonst Opus. Umgesetzt mit `~/.claude/hooks/fokus-setzen.py` (Projekteinstellung im Fokus-Repo), Agent-Dateien `task-reviewer` und `skeptiker` auf Opus, Planwert in der CLAUDE.md (Changelog 13.11.). Wirkung prüfen nach dem Reset am 20.11.: Punkte je Mio. erwartet rund 4, die Woche ohne Limit. Grundlage der Wahl, Planwert und Besetzung, gerechnet am Zeitraum 11.11., 06:00 bis 12.11., 15:05 bei gleicher Tokenmenge. Das ist eine Annahme: Opus kann für dieselbe Arbeit mehr oder weniger Tokens und Runden brauchen.
  - Besetzung bleibt: rund 5,7 je Mio., die Woche fasst rund 18 Mio.
  - Review auf Opus, Lead bleibt Fable: rund 4,3 je Mio., rund 23 Mio.
  - Lead auf Opus, Review bleibt Fable: rund 4,4 je Mio., rund 23 Mio.
  - Fable nur im Fokusprojekt (gerechnet am 12.11.): rund 3,9 je Mio., rund 25 Mio.
  - Lead und Review auf Opus: rund 2,9 je Mio., rund 34 Mio.
  - Der Planwert in der CLAUDE.md folgt der Wahl.
- Meldung ab Tag 4 im Betrieb: nach dem 16.11. in den Transkripten ab 13.11., 06:00 nach „Wochenbudget Gelb“ und „Wochenbudget Rot“ suchen. Erwartet: keine vor dem 16.11., 06:00.
- Nächste Messung nach dem Reset am 20.11., 06:00: die erste ganze Woche mit einer einzigen Besetzung.
- Grenze der Messung: Verbrauch ohne Transkript auf dem Mac (claude.ai, Cloud-Sitzungen) steckt, soweit er aufs Wochenlimit zählt, unerkannt in Rohquote und Schätzung.

## 2026-11-11 Wirkungskontrolle Sollkurve (Wochenbudget vom 30.10.)

Regel vom 30.10. (Changelog): am Tag k der Limitwoche höchstens 13 mal k Prozent, insgesamt höchstens 90 %, Stufen Grün, Gelb, Rot mit Gegenmaßnahmen. Ziel: bis zum Reset am 06.11., 06:00 hinkommen, ohne Ausreißertag wie den 27./28.10. Seit 10.11. melden Gelb und Rot nur noch (Changelog 10.11.). Der Eintrag war für den 06.11. geplant und kommt fünf Tage später.

### Gemessen

Quelle: `~/.claude/cockpit/limit-log.jsonl` (140 Einträge), Tagesgrenze jeweils 06:00.

- Woche 1 (30.10. bis 06.11.), Stand am Tagesende gegen Soll: 14/13, 19/26, 21/39, 25/52, 33/65, 41/78, 92/90.
- Woche 1 nach Stufen: 158,6 Stunden Grün, 7,7 Stunden Gelb (30.10. ab 22:16), 0,9 Stunden Rot (06.11. ab 05:04 bei 90 %). Letzter Stand vor dem Reset 92 % um 05:57.
- Tag 7 brachte 51 der 92 Punkte, davon 30 in sechs Stunden (05.11. 21:50 bis 06.11. 03:46). Anlass war Nykos Wunsch vom 05.11. („weit unter Plan, Usage ausnutzen“): Sub-Agent-Schub auf Opus `xhigh` ab 09:50 und zwei Recherche-Workflows über Nacht ([[03 Bereiche/Claude Code/Fehlerlog|Fehlerlog]], 06.11.).
- Woche 2 (ab 06.11.): Tag 1 endete bei 26 % gegen Soll 13. Gelb ab 12:44, Rot ab 21:15. Danach 28/26, 38/39, 50/52, 56/65; am 11.11. um 07:47 58 % bei Soll 78.
- Woche 2 bis zum Regelwechsel: 27,8 Stunden Gelb und 8,7 Stunden Rot, alle in den ersten 48 Stunden.
- Planwert: 148 Punkte auf 55,8 Mio. Output-Tokens, das sind 2,65 Punkte je Mio. (Woche 1: 2,86, Woche 2: 2,38). `Limit-Eichung.py` schätzt über 138 Fenster Opus 2,32 und Sonnet 2,05 Punkte je Mio. (Nachtrag 13.11.: ungewichtet und damit zu tief, gewichtet 2,88 und 2,23, siehe Eintrag vom 13.11.)

### Hat gewirkt

- Der Reset am 06.11. wurde erreicht, ohne dass das Limit die Arbeit stoppte.
- Die Stufen haben in Woche 2 nachweislich gebremst: am 06.11. keine Workflows und Lead auf `medium`, Abschlussreview B1 zunächst angehalten; am 07.11. und 08.11. je ein Lauf verschoben (Daily Notes).
- Das Protokoll des Hooks trägt die Eichung. Sonnet kostet je Output-Token fast so viel wie Opus; der Wechsel auf Sonnet spart also kaum Wochenprozente.

### Nicht gewirkt

- Der Ausreißertag kam trotzdem, nur am Ende statt am Anfang. Die Kurve erlaubt ihn: Wer an Tag 6 bei 41 % steht, hat an Tag 7 49 Punkte in Grün frei. Gebremst hat in der Nacht der Workflow-Wächter bei 86 %, nicht die Kurve; Rot kam 56 Minuten vor dem Reset.
- Die Kurve bestraft einen starken ersten Tag. 26 % an Tag 1 sind zwei Tagesraten und standen neun Stunden auf Rot, obwohl die Woche danach durchgehend unter Soll lief.
- Die Stufe springt an der Tagesgrenze ohne jeden Verbrauch: am 07.11. um 06:00 von Rot auf Grün bei unverändert 26 %.
- Der Planwert 2 je Mio. ist zu niedrig. Die Rohquote liegt bei 2,65, in der Opus-lastigen Woche 1 bei 2,86.
- Das gezielte Sonnet-Fenster (5 Mio. Tokens, Sonnet als Lead, keine parallele Opus-Sitzung) aus [[Output-Kennzahlen]] finde ich in keiner Daily Note. Die Sonnet-Zahl stammt aus Mischfenstern.

### Urteil

Die Sollkurve hat das Limit gehalten, aber zur falschen Zeit gebremst: früh in der Woche, als Luft war, und nicht am letzten Tag, als es eng wurde. Nyko hat sie am 10.11. bei 52 % als Steuerung abgelöst; gesteuert wird seither über den Tagesfokus.

### Offen

- Erledigt 13.11. (Eintrag vom 13.11.): Wirkung des Tagesfokus: Erste Messung nach dem Reset am 13.11., 06:00 (Endstand der Woche, höchster Sechs-Stunden-Anstieg).
- Erledigt 13.11. (Eintrag vom 13.11., Entscheidung zu Planwert und Besetzung dort offen): Entschieden von Nyko am 11.11.: Planwert in der CLAUDE.md auf rund 2,6. Dazu Sub-Agents auf Opus, Recherche Sonnet, Review Fable (Changelog 11.11. (2)). Wirkung prüfen nach dem Reset am 13.11.: Punkte je Mio. und Wochenstand mit der neuen Besetzung.
- Funktion geprüft 13.11., Betrieb offen im Eintrag vom 13.11.: Entschieden von Nyko am 11.11.: Der Hook meldet Gelb und Rot erst ab Tag 4 der Limitwoche (`budget_melden_ab_tag`, Vorgabe 4; Changelog 11.11.). Wirkung prüfen in der Woche ab 13.11.: keine Meldung an Tag 1 bis 3.
- Grenze der Messung: Der Hook schreibt nur bei einem Prompt, und der Wochenstand kommt aus der letzten Antwort irgendeiner Sitzung. Einzelne Sprünge (74 auf 77 %) sind deshalb unscharf.

## 2026-10-28 (2) Limit ausreizen vorzeitig beendet (Notbremse bei 79 % Woche)

### Änderung

- Abschnitt „Limit ausreizen“ aus der CLAUDE.md entfernt; es gelten wieder „Effort“, „Modell“ und „Sub-Agents und Workflows“. `settings.json`: `ultracode` und `env.CLAUDE_CODE_EFFORT_LEVEL` entfernt, `env.CLAUDE_CODE_SUBAGENT_MODEL` = `sonnet` (Sicherung `settings.json.bak-2026-10-28`). Der launchd-Auftrag `de.nyko.limit-zurueck` findet am 30.10. nichts mehr und trägt sich aus.
- `effort: medium` in 13 eigenen Sonnet-Agenten (alle außer `kevin`), weil Sub-Agents sonst den Cockpit-Startwert `--effort xhigh` erben ([[03 Bereiche/Claude Code/Fehlerlog|Fehlerlog]], 28.10.).
- Anlass: Nutzer („wir müssen sofort was anpassen bin bei 78% woche!!“).

### Wirkung des Abschnitts vom 27.10. (offener Punkt aus der Daily vom 27.10.)

- Woche 1–2 % am 27.10. gegen 18 Uhr (nach dem Planwechsel), 60 % am 28.10. gegen 11 Uhr, 79 % um 13:31: rund 77 Punkte in 19,5 Stunden mit Nachtpause, zuletzt 7–8 Punkte je Stunde. 5-Stunden-Fenster um 13:31 bei 81 %.
- Um 13:31 liefen 7 Sessions, in 6 davon Sub-Agents mit Effort `max` auf Opus.
- Urteil: Ausreizen ohne Zielrate verbraucht die Woche in unter einem Tag.

### Offen

- Laufende Sessions behalten bis zum Neustart `max` und Opus-Sub-Agents; `/clear` reicht nicht, die Schalter hängen am Prozess.
- Cockpit-Startwähler steht auf `xhigh`: Für den Lead ist das Standard, `general-purpose`-Sub-Agents erben es aber. „aus“ wählen.
- Vorschlag, nicht beschlossen: Ausreiz-Phasen nur mit Zielrate (Restprozent durch Reststunden) und Prüfung alle 2–3 Stunden.

## 2026-10-28 Ultracode anlassbezogen, Nachprüfung je Workflow, Opus-Effort xhigh

### Änderung

- Befristeter Abschnitt „Limit ausreizen“ (bis 30.10., 06:00): Ultracode nicht mehr für jede substanzielle Aufgabe. Der Schalter `"ultracode": true` bleibt, damit der Lead Workflows selbst starten darf. Vor jeder substanziellen Aufgabe prüft er, ob ein Workflow etwas liefert, das solo oder ein einzelner Sub-Agent nicht liefert, und sagt in einem Satz, ob er läuft und was er liefern soll. Anlass: Breite, Tragweite, die mehr als eine unabhängige Prüfung braucht, oder ein offener Lösungsraum. Planumsetzungen laufen weiter wie bisher, auch per `sdd-aufgabe`.
- Dauerhaft („Sub-Agents und Workflows“): Nach jedem Workflow prüft der Lead, ob er den Output verbessert hat, gemessen am Satz vom Start. Urteil in einem Satz an den Nutzer, eine Zeile in die Bilanz unten.
- Effort: Opus-Standard `xhigh` statt `high`; `settings.json` steht seit 27.10., 06:47, so. Die Ursache der Kipper ist jetzt belegt: `/effort <Stufe>` speichert jede Wahl außer `max` als Standard für neue Sessions (Transkripte: 22.10. um 19:57 und sechsmal am 23.10. `medium`, 27.10. zwischen 06:47 und 06:48 dreimal `xhigh`). Der Nutzer behält `xhigh`, die Regel zieht nach. Der Mechanismus bleibt, der Prüfpunkt vom 22.10. gilt also weiter: Weicht der Wert ab, hat vermutlich ein `/effort` ihn gesetzt.
- `~/.claude/agents/nyko/kevin.md`: „kein `max` oder ultracode ungefragt“ statt „kein xhigh …“, sonst widerspräche Kevins Datei dem neuen Opus-Standard.
- Anlass: Nutzerwunsch („ultracode nur anlassbezogen, aber immer überprüfen ob es den output verbessert“). Wer den Anlass entscheidet, wie lange die Nachprüfung gilt und welcher Opus-Effort gilt, hat der Nutzer per Rückfrage entschieden. Der Wortlaut der Anlass-Regel stammt aus dem Vorschlag des Leads, vom Nutzer per Auswahl bestätigt; nach der Gegenprüfung (erste Bilanzzeile) verschärft, die Messweise korrigiert.

### Erwartung

- Workflows nur dort, wo Breite, mehr als eine unabhängige Prüfung oder ein offener Lösungsraum sie tragen; Kleinkram und einfache Prüfungen solo oder mit einem Sub-Agent. Nach Zuordnung des Prüfers wären von 19 Läufen am 28.10. bis 11 Uhr 18 schon unter die erste, weitere Fassung der Kriterien gefallen.
- Die Bilanz zeigt nach einigen Läufen, bei welchen Aufgabenarten Ultracode den Output verbessert.

### Messung

- Zählweise je Zeile:
  - Maßstab ist der Satz vom Start: was der Workflow liefern soll, das solo oder ein einzelner Sub-Agent nicht liefert. Bei Planumsetzung zählen Umsetzer, `task-reviewer` und `agy` zu solo, weil sie auch ohne Workflow Pflicht sind.
  - Mehrwert ist nur, was darüber hinaus den Output mit Fundstelle geändert hat. Selbst erzeugte und wieder gestrichene Fehlbefunde zählen nicht.
  - Bei parallelen Linsen dazu: wie viele übernommene Funde nur aus einer Linse kamen und wie viele der beste Einzelprüfer allein gebracht hätte. Das zeigt, ob ein Sub-Agent gereicht hätte.
  - Kosten: Output-Tokens der `agent-*.jsonl` im Transcript dir des Laufs, Höchstwert je `message.id`, summiert ([[output-tokens-hoechstwert-je-antwort]]). Nicht `subagent_tokens` aus der Abschlussmeldung, das ist ungefähr der Endkontext (erster Lauf: 656.259 gemeldet, 356.220 Output-Tokens). Auch nicht `budget.spent()`, das zählt die Hauptschleife des Turns mit.
  - Eine Zeile je Aufruf des Workflow-Werkzeugs; `sdd-aufgabe`, auch verschachtelt, eine Zeile je Plan und Session mit summierten Tokens.
- Blind für die Gegenrichtung: Solo erledigte Aufgaben bekommen keine Zeile. Die Auswertung erkennt überflüssige Workflows, aber keine fehlenden.
- Zeilen bis 28.10., 13:31, stammen aus Läufen mit Opus-Sub-Agents und Effort `max`. Die erste Auswertung nach dem Reset gilt nur dafür; nach einigen Läufen mit Sonnet wiederholen. Sie geht zusammen mit dem offenen Punkt aus der Daily vom 27.10. (Wirkung der Woche mit `max` und Ultracode): Zeilen nach Spalte „Art“, „lohnt“ gegen „lohnt nicht“.

### Offen

- Sub-Agents erben einen Session-Effort (`--effort` aus dem Cockpit-Startwähler, steht auf `xhigh`, oder `/effort`) und laufen dann nicht mit `medium`; gemessen mit 13 Wegwerf-Sessions ([[03 Bereiche/Claude Code/Fehlerlog|Fehlerlog]], 28.10.). Ab 30.10., wenn `max` wegfällt, liefen sie im Cockpit mit `xhigh`. Abhilfe: Cockpit-Startwähler auf „aus“, dann gilt `settings.json`; optional `effort: medium` in den eigenen Sonnet-Agenten. Entscheidung beim Nutzer.

### Ultracode-Bilanz

| Datum | Aufgabe | Art | Lauf-ID | Output-Tokens | Mehrwert gegenüber Satz vom Start | Urteil |
|---|---|---|---|---|---|---|
| 2026-10-28 | Entwurf „Ultracode anlassbezogen“ der globalen CLAUDE.md gegenlesen | Regel | wf_2c1def96-b7a | 356.220 (3 Opus-Agenten, Effort max, 27 min) | Erwartung stand nur im Briefing, nicht als Satz vorab: Widersprüche in Text und Messweise, Kostenquelle und Selbstbewertung als offene Fragen. 11 Funde übernommen, 1 widerlegt. Darüber hinaus: falsche Kostenquelle (`subagent_tokens`), Maßstab rechnete Pflicht-Reviews dem Workflow zu, Anlass-Kriterien zu weit, Sub-Agents erben den Lead-Effort, `/effort` als Kipp-Ursache samt falscher Daten im Entwurf, kevin.md, Spalten, Gegenrichtung. 8 der 11 kamen aus nur einer Linse; die Linse Messbarkeit allein hätte 8 gebracht, die beiden anderen 3 weitere, darunter den einzigen hohen Befund. | lohnt, aber teuer für drei Leser |
| 2026-10-28 | Bauprobe Spec B (alter): B1 und B2 in Repo-Kopien bauen, Gegenprüfung B1, Regel-Linse (Vorsitzung) | Spec | wf_4dcffd4b-cc6 | 824.701 (5 Opus-Agenten, 74 min; skeptiker-b2 am Nutzungslimit abgebrochen) | Satz vom Start stand in der Vorsitzung, hier nicht geprüft. Über solo hinaus: gemessene Breite der Bildzeile (Etikett nur an s2), Poolzahlen 36/35/29, Blocker an R37 (Element 1 braucht drei Sätze), vier Mutanten aus B1 überleben die Suite, Altbestand liefert ohne Wächter still falsche Ergebnisse. Die Gegenprüfung von B2 fehlte, nachgeholt in wf_5e77e7a3-8b1. | lohnt; der Abbruch am Limit kostete die Gegenprüfung |
| 2026-10-28 | Gegenprüfung Bauprobe B2 und Kernbehauptungen für Spec B (alter) | Spec | wf_5e77e7a3-8b1 | 1.153.554 (8 Opus-Agenten: 4 Linsen, 4 Nachrechnungen; 104 min) | Satz vom Start (nur als Statussatz): vier Linsen und je Linse eine unabhängige Nachrechnung statt eines Skeptikers laut Handoff. Rund 33 Funde in die Spec übernommen, 2 doppelt; die Nachrechnung widerlegte keinen Befund und präzisierte 4, darunter die Rekursion des vorgeschlagenen Ziehweg-Fixes ohne Pool. Neu: alter-Pool um den 04.01.2027 leer; ein leerer Pool kostet still 38,9 % der Versuche; skriptBefund lässt die Alter der älteren Person, „durch 7 minus 2“, die Teilgröße und Pronomen durch; der einzige Negativtest „Fehlschluss ab Satz 2“ ging in B2 verloren; der Verwurf nach R48 muss auf alter begrenzt sein, weil verworfen ein Endstatus ist. Jeder Fund kam aus genau einer Linse; die stärkste Linse (skript) hätte allein 11 gebracht. | lohnt |
| 2026-10-28 | Spec-Prüfung Spec B (alter) mit den sechs Nachträgen in Spec A | Spec | wf_572cc954-55f | 935.596 (3 Agenten: Skeptiker treue und code auf Sonnet, agy mit Gemini 3.8 Flash; 84 min) | Satz vom Start: zwei unabhängige Linsen und eine andere Modellfamilie lesen die eigene Spec unbefangen; die Befunde prüft der Lead selbst statt einer Verifier-Runde (Woche bei 79 %). Über solo hinaus: 43 Befunde, 28 verschiedene, alle eingearbeitet, keiner widerlegt (drei am Code nachgeprüft); darunter eine falsche Bestandsaussage (`test/cli.test.ts`), die Doppelbedeutung von „Pool“, die falsche Wurf-Annahme der Hörprobe, ein heute roter Wächter, die Reihenfolge der Rotgründe in B2, der Importzyklus des Ziehwegs und fehlende Gegenrichtungstests. agy brachte 3 eigene Befunde (Abnahme-Schritte 1 bis 3), der Rest doppelt. | lohnt |
| 2026-10-28 | Werkzeugkasten Automatisierung aus zehn Handbüchern einer Fachsoftware, nur Herstellerdoku | Recherche | wf_c0b806e4-14c | 5.182.647 (68 Opus-Agenten, ab 10:08; 24 von 25 Auswertern und 3 Sichter am 5-h-Limit um 10:29 abgebrochen, Reset 10:30) | Satz vom Start stand nur im Briefing (alle zehn Handbücher abdecken, jeden Eintrag gegenprüfen). Über solo hinaus: Die Belegprüfung korrigierte 132 von 171 Einträgen (Seite, Pfad, Rolle) und verwarf keinen. Die Versionsprüfung fand 2 entfallene, 1 fraglichen, 4 unklare und 6 neue. Die Lückensuche fand 8 Lücken und 15 Mängel. Abgedeckt sind nur ein Modulpaket und sechs Lückenpakete; sieben Module fehlen. | lohnt so nicht: Die Prüfung ist wertvoll, aber das Skript lief nach dem Ausfall ohne Wächter weiter und lieferte für viel Geld einen Teilstand |
| 2026-10-28 | Patina-Website: erster Prüfbericht (B1 bis B3, Abschluss), Nachbesserung B4 | Planumsetzung | wf_664b28d2-e87, wf_86d1f03a-9b2, wf_7449ee56-12d | nicht gemessen (subagent_tokens rund 3,1 Mio. sind keine Output-Tokens; Lauf 2 am 5-h-Limit um 10:29 abgebrochen, per resume fortgesetzt; B4 endete mit der Sitzung nach dem Umsetzer, Review und agy danach einzeln) | Satz vom Start: Skeptiker-Linsen und ein Abschluss-Skeptiker sollten Lücken finden, die Umsetzer, task-reviewer und agy (solo) nicht finden. Über solo hinaus mit Fundstelle: Gegentests für € neben den Einträgen (B1), Namenskollision, Endungen und toter Aufruf im Wächter (B2), Zeitzonen-Fenster 00:00 bis 01:00 MEZ in der CI und Beleg-Satz auf /pruefberichte/ ungeprüft (Abschluss). Die wichtigste Berichtigung (drittes Netz fängt den toten Link schon, F63) fand der Umsetzer, also solo. | lohnt, aber teuer: die Skeptiker brachten je Lauf zwei bis vier echte Befunde, der Rest waren Minors zum Parken |
| 2026-10-28 | Werkzeugkasten Neuauflage Teil 1 (GF, SV2), Sonnet mit Ausfallwächter | Recherche | wf_5e88c7c1-18c | 439.892 (13 Sonnet-Agenten, 0 Ausfälle) | Satz vom Start: neun parallele Auswertungen über GF und SV2 mit Fundstellenprüfung gegen die seitenmarkierten Texte. Geliefert: 109 Einträge, 59 Fundstellen korrigiert, 0 verworfen. In `wissen/11` steht davon noch nichts, das Zusammenführen kommt erst in Teil 2. | offen bis Teil 2 |
| 2026-10-28 | Rätselmeister: Plan A und B schreiben (Entwurf je Etappe, Gegenprüfung, Überarbeitung) | Plan | wf_0d890eab-c00 | 3.051.487 (9 Sonnet-Agenten bis zum Stopp; Wochenstand 85 → 91 %) | Satz vom Start: je Etappe ein Verfasser mit voller Lektüre von Spec, Code und Vorlagen, dann je Plan Skeptiker und agy gegen Spec und Code, dann ein Überarbeiter; solo hätte den Kontext gesprengt. Bis zum Stopp geliefert: sechs Entwürfe (71 bis 145 KB, drei- bis viermal so lang wie ihr Spec-Abschnitt) und Prüfbefunde zu Plan A; Prüfung B und Überarbeitung fehlen. | offen: am Wochenlimit gestoppt, Urteil nach der Überarbeitung |
| 2026-10-28 | CoreMetrics: PR-Befund der Cloud-Sitzung prüfen, verdächtige PRs aus dem Export, vermisste Features suchen | Analyse | wf_d8d123b8-656 | 1.455.071 (12 Opus-Agenten, Effort max, 58 min; Zusammenführer am Monatslimit abgebrochen, die zwei Feature-Skeptiker nie gestartet) | Satz vom Start: Code-Aussagen mit Skeptiker, verdächtige PRs mit zwei unabhängigen Methoden plus Abgleich, vier Quellen parallel nach Feature-Wünschen. Über solo hinaus mit Fundstelle: zweiter Tippfehler Brustfly 1276 × 6 und das verlorene Banner vom 27.10.; Fehlalarme je Schwelle; „Neuberechnung stellt den Falsch-PR wieder her“ (`tools/abnahme-auswertung.mjs:172-187`); Löschgeste in ScrollView (`TrainingView.swift:422`); `tech-spec-2-5-15.md:190`; `aa986cd`; Spec-Querverweise zu den vier Wünschen und zu den Stufen D/E vom 22.09. Linsen: den Daten-Kern (beide Tippfehler, Schwellen) brachte die Sprung-Methode allein, aus der robusten kamen nur zwei Kandidaten, beide verworfen; die vier TestFlight-Wünsche fand der Lead vorab selbst. | lohnt teilweise: Befund deutlich tiefer als solo, aber Opus für Leseaufgaben zu teuer; 3–4 Sonnet-Agenten (Code-Skeptiker, eine Datenmethode, Repo und Vault) hätten den Kern gebracht |
| 2026-10-28 | Feiern: Post nach Wochentag, zwei Tasks (Planprüfung Skeptiker, je Task sdd-aufgabe mit Skeptiker- und agy-Linse) | Planumsetzung | wf_deb69a36-fa7, wf_b663377d-422, wf_90318aef-8b8 | nicht gemessen (subagent_tokens rund 1,5 Mio. sind keine Output-Tokens) | Satz vom Start fehlte. Über solo hinaus: Planprüfung vorab fand vier Planfehler mit Gegentest (M3 konnte nie rot werden, fehlendes nummeriert=False), die Skeptiker-Linse in Task 1 fünf Testlücken mit Mutanten, die per Fix-Runde Tests wurden (Kürzung nach Rang, Messung ohne Nummern, Tiebreak). Task-2-Linsen durch Sitzungsabbruch ausgefallen | Mehrwert ja (Planprüfung und Task-1-Linse) |
| 2026-10-29 | CoreMetrics: Grundlagen für das PRD PR-Plausibilität (Code-Inventur, Spec-Abgleich, Grenzfälle, Dieper) | Spec | wf_a84275c6-7c7 | 698.307 (4 Sonnet-Agenten, 31 min) | Satz vom Start: vier unabhängige Grundlagen, die solo nur nacheinander im eigenen Kontext gingen; Grenzfälle unabhängig vom Entwurf. Über solo hinaus, mit Fundstelle: Schwellenzahl galt nur für Bezug „ganze Historie“, mit „ab Reset“ ein Fehlalarm bei +20 % (73 × 9, 25.09.) → erneute Rückfrage, Befund § 4 Nachtrag (Grenzfälle F10, Dieper unabhängig); zwei Testläufe ab Stichtag als einzige Bankdrücken-Bestleistung → mitgelöscht (F14); 15 Grenzfälle → Festlegungen L1–L10; Spec-Abgleich lieferte die Schalter-Präzedenz (`prd-gym-logging.md:155`) und `RESET_DIAGNOSE.md:179`. Bester Einzelprüfer: Grenzfälle; Inventur und Spec-Abgleich je mit eigenen Funden. | lohnt |
| 2026-10-29 | CoreMetrics: PRD PR-Plausibilität gegenlesen (Fakten, Vollständigkeit, Zweitmeinung) | Spec | wf_d385593c-c03 | 455.069 (3 Agenten: Skeptiker und task-reviewer auf Sonnet, agy mit Gemini 3.8 Flash; 24 min) | Satz vom Start: drei Gegenlesungen ohne Anker auf meinen Entwurf. Übernommen rund 35 Funde, u. a. Replay-Regel für AK1 (3 statt 4 Rückfragen), Gerätetest scheiterte an L4, Schreibpfad gegen O3, Leerzustand der Detailseite (32 Übungen), Dreizustand am Satz, Zirkel in der Reihenfolge, O1-Empfehlung gedreht. Nur aus einer Linse: Reviewer rund 15, Skeptiker 7, agy 5; der Reviewer allein hätte rund 60 % gebracht. | lohnt |
| 2026-10-30 | Rätselmeister: Plan A und B fertigstellen (B2-Entwurf, Abdeckungsprüfung je Etappe mit Skeptiker, agy für B, Überarbeitung, Köpfe) | Plan | wf_21e1b447-b11 (zwei Läufe, Resume nach Netzaussetzern) | nicht gemessen (subagent_tokens 3,84 Mio. sind keine Output-Tokens) | Satz vom Start fehlte im Chat. Über solo hinaus: sieben Abschnitte parallel geprüft und überarbeitet (62 Befunde angewendet, u. a. A4 legt ffmpegMessung an, A3-Bezüge umgestellt), Schnittstellenabgleich der Köpfe ohne Abweichung; Richtwerte der Länge verfehlt (52 bis 82 KB statt 25 bis 45 KB). Urteil: Mehrwert ja, Kürzungsziel nein. |
| 2026-10-30 | Rätselmeister: Umsetzung Auftrag A und B, rund 55 Läufe sdd-aufgabe (Umsetzer, task-reviewer, codex-Linse) plus Etappen-Reviews und Abschlussreview (Opus) | Planumsetzung | je Task ein wf_ (siehe Sitzung) | nicht gemessen (Wochenstand 3 auf 12 % über den Tag) | Satz vom Start: je Task Umsetzer und Review, das ist solo laut Zählweise. Über solo hinaus: nichts, was die Zählweise wertet; die Etappen-Reviews und Codex fanden je Etappe 2 bis 8 Minors, davon u. a. Doppelrechnung Sperrfilter (B1), Hilfswerte doppelt (B2), Prüfskript ohne Pausenbedingung (Abnahme), afade ungeprüft (Abschluss). Urteil: Ablauf trägt, kein Workflow-Mehrwert im Sinne der Bilanz. | Nachtrag 02.11.2026 (Handyurteil Abnahme 9): K12, K16 und Hook-Liste erfüllt; K9 verletzt, die Fugenpause hörbar. Keins der Reviews hatte sie gefunden, nur das Abnahme-Prüfskript (K11). |
| 2026-10-28 | Fernzugriff: Web-App, um den Mac vom Windows-PC im Browser zu steuern (Dieper, fünf Sweeps, Dossiers, Linsen, Synthese) | Recherche | wf_0b3e7325-d03 (zwei Läufe) | nicht gemessen (Lauf 1: drei Sweeps am 5-h-Limit um 10:29 abgebrochen, Sweep Selbsthost ohne Deckel 2,5 h und rund 250 Web-Aufrufe, gestoppt; Lauf 2 endete mit der Sitzung vor dem Bündeln) | Satz vom Start: belegte Rangfolge mit Einrichtung aus Primärquellen und Skeptiker-Prüfung, auch für den Dienst-PC. Beim Nutzer kam nichts an; er entschied sich am 02.11. selbst für Chrome Remote Desktop („hättest nicht so auffahren müssen“). | kein Mehrwert; für eine Produktfrage zu groß, eine direkte Antwort mit zwei, drei Kandidaten hätte gereicht |
| 2026-11-05 | Sub-Agent-Schub opus/xhigh: drei Proben, welches Modell und welcher Effort bei Workflow-Agents ankommt (ohne/mit agentType, Hook-Sperre, model opus) | Probe | wf_38824af1-a68, wf_c75eb22c-3b8 (dritter Lauf vom Hook abgelehnt) | nicht gemessen (subagent_tokens 0,1 Mio., 3 Agenten) | Satz vom Start: Messung, kein Arbeits-Workflow. Ergebnis: agentType nimmt in laufenden Sitzungen die Agent-Datei vom Sitzungsstart (Sonnet), env-Effort greift sofort; daraufhin agentType-Regel im Hook. | Messmittel, kein Workflow-Mehrwert im Sinne der Bilanz. |
| 2026-11-05 | Patina-Website: Kosten einer Live-3D-Bühne statt Bildfolge (vier Inventuren: alte 3D-Bühne, Blender, heutige Bühne, Blueprint; drei Schätzungen aus verschiedenen Winkeln; Skeptiker) | Entscheidung | wf_de108efc-a15 | 301.862 (8 Opus-Agenten, Effort xhigh wegen Sub-Agent-Schub, 33 min; je Antwort Höchstwert) | Satz vom Start: vier unabhängige Bestandsaufnahmen und drei getrennte Schätzungen mit Skeptiker, damit die Zahl nicht an der Lead-Vermutung hängt. Über solo hinaus mit Fundstelle: Blueprint ist Linienzeichnung ohne Textur und Licht, die Treffer MeshPhysicalMaterial/VideoTexture stammen aus der mitgelieferten Bibliothek (stage.js @394309 und @389935 gegen Szenencode ab @512631, vom Lead nachgeprüft), das korrigierte eine falsche Lead-Aussage an Nyko; Skeptiker hob die Spanne von 2.100 Zeilen/4 Mio. auf 3.300/8 Mio. (abstandsfaktor in allen 998 Dateien 1,0, Gegentest G1; [[Markenplan]]:250 Kadenz); letzter voller 3D-Stand 41bcc69^ statt 34491b6^. | lohnt |
| 2026-11-05 | Nachtrecherche ([[unbeaufsichtigt]]): 6 Unternehmenswege für Patina Southside und 4 Design-Themen. Je Thema Tiefenplan ([[dieper]]), 4 Suchwege, Lückenkritik mit Nachsuche, zwei Prüfer an der Quelle, Ablage; dazu 5 Linsen und 2 Synthesen | Recherche | wf_d472d391-d52, wf_b9177f74-bfc, wf_fee819f9-cdd | 7.799.257 (128 Agenten-Dateien, Opus xhigh). Wochenlimit vor dem Reset von 61 auf 89 %. Im selben Fenster liefen drei andere Sitzungen mit 3,4 Mio. Output-Tokens, zusammen also rund 2,6 Punkte je Mio. Anteil dieses Laufs nach Tokens rund 19 Punkte | Satz vom Start nicht ausdrücklich gesagt, nur den Ablauf beschrieben. Über solo hinaus: Die Prüfer strichen 31 Aussagen als widerlegt aus den Berichten, zum Beispiel Design 01 Z. 426 (Base UI sei in salvyra und nox „direkt genutzt“) und Wege 04 Z. 413 (2 widerlegt, 14 übertrieben von 69 Befunden). Linsen: Nur der Skeptiker legte den Web-Piloten auf den Notenrechner statt auf Salvyra (Salvyras ci.yml Z. 11 verlangt arc-runners-frontend, vom Lead geprüft). Bei den Wegen setzten alle drei Linsen dieselbe Spitze, dafür hätte eine Linse gereicht; die Widersprüche bei Kundenauftrag und Organisationslizenz zeigt erst der Vergleich. | lohnt für Breite und Belegprüfung. Kosten leicht über Plan (rund 20 statt 12 bis 18 Punkte). Weil parallel andere Sitzungen liefen, reichte das Limit nicht, darum zwei Pausen vor dem Vergleich und ein Fortsetzungsskript |
| 2026-11-05 | Website Live-Bühne: Bestandsaufnahme (drei Karten), Umsetzungsplan, Plan-Review mit Linsen und agy, Nachbessern | Plan | wf_b923fc3c-6f3 | nicht gemessen (totalTokens 2,62 Mio. sind keine Output-Tokens; 10 Agenten, Opus wegen Sub-Agent-Schub, 104 min, 0 Ausfälle) | Satz vom Start: Karten zu Laufzeit, Bestand und Tests parallel, damit der Plan auf gezählten Zahlen steht, dann unabhängiges Review gegen die Spec. Über solo hinaus mit Fundstelle: 37 Befunde (22 wichtig), umgesetzt u. a. Anti-Ziele im Live-Weg als Tests (`pruefe_schilder_live`, `test_live_hud_text_liegt_frei`, `test_live_leerflaeche_hoechstens_ein_viertel`, Plan Task 8), Fenster beim Kontextverlust ohne Layoutwechsel (Task 10), Haken `__live.wirkung` für Material, Anisotropie und k; die Karte fand, dass die Kamerawerte nur in `tools/render/film.json` stehen (`_config.yml:30`), daraus Task 2 mit Abgleichtest. | lohnt |
| 2026-11-05 | Website Live-Bühne: Vorabprüfung des Plans vor Task 1 (Tabelle Paare und Tasks) | Planumsetzung | wf_6998c9a7-a56 | nicht gemessen (totalTokens 0,35 Mio.; 1 task-reviewer auf Opus, 24 min) | Satz vom Start: Widersprüche zwischen Tasks finden, bevor ein Umsetzer daran hängt. Geliefert: 61 Zeilen, 3 echte Konflikte (Grenztest in der Suite gegen Ruling R1, Ausblenden bei `null` in Task 8/10, Reihenfolge beim Verstecken in Task 12), daraus Rulings R4 bis R6. Ein einzelner Agent zählt als solo; die Workflow-Hülle brachte nichts dazu. | kein Workflow-Mehrwert; die Prüfung selbst lohnte |
| 2026-11-06 | Website Live-Bühne: Umsetzung Tasks 1 bis 10 in fünf Läufen sdd-aufgabe (Umsetzer, task-reviewer, agy-Linse, Fix-Runden), danach Tasks 11 bis 15 per Einzel-Dispatch (Gelb) | Planumsetzung | wf_f350b768-9bb, wf_38711100-5ce, wf_a48ad29c-2d9, wf_c4ed2387-388, wf_a8a2806d-9b2 | nicht gemessen (totalTokens zusammen 5,62 Mio. sind keine Output-Tokens; 40 Agenten, Opus/xhigh wegen Sub-Agent-Schub bis 08:00; Wochenstand 90 % → Reset → 15 % um 13:30) | Satz vom Start: je Task Umsetzer, Review und agy in fester Schleife bis zum Halt; das ist solo laut Zählweise. Über solo hinaus: nichts, was die Zählweise wertet. Drei Halte zur Entscheidung (Task 2, 5, 8 → R8, R9/R10, R13) hätte solo genauso gebracht. Kosten: Lauf 1 brauchte 5,1 h für 2 Tasks, weil `pruefe_seite.sh` im geteilten WebKit hängt (danach R7); der Einzel-Dispatch ab Task 11 kostete je Task rund 1 Wochenpunkt bei gleichem Ablauf. | kein Workflow-Mehrwert; Einzel-Dispatch reicht für Planumsetzung |

## 2026-10-22 ~/[[AGENTS]].md entfernt, Opus-Effort wieder high

- `~/AGENTS.md` war am 07.10. als Codex-Fassung einer aelteren CLAUDE.md zurueckgekehrt (kaputte Pfade `~/.Codex/...`, `Codex-Projekte/SecondBrain`) und lud in jeder Claude-Session unter `$HOME` als Projektanweisung mit. Herkunft unklar, vermutlich Codex-Import. Verschoben nach `~/.claude/_archiv/2026-10-22-home-agents-md/AGENTS.md.bak` (Prüfsumme gleich, LIESMICH mit Rückweg). Codex nutzt `~/.codex/AGENTS.md`.
- `settings.json`: `modelSettings.claude-opus-5-5.effortLevel` stand seit 12.–19.10. unbemerkt auf `medium` (Sicherung `bak-2026-10-12` noch `high`), vermutlich ueber den Effort-Waehler der App. Zurueck auf `high` gemaess Nutzer-Entscheidung 27.09.; Sicherung `settings.json.bak-2026-10-22`. CLAUDE.md unveraendert.
- Wirkung pruefen: Startkontext ohne `~/AGENTS.md`; taucht die Datei wieder auf oder kippt der Opus-Effort erneut, Ausloeser suchen (Codex-Import, App-Waehler).

## 2026-10-04 Stufe 3: CLAUDE.md und MEMORY.md gestrafft

Session: Session-Link entfernt.
Changelog: [[Changelog]] (Archiv `History/2026-10-04`).

### Startwert nach Stufe 2 (belegt)

Frischer interaktiver Prozess im Home-Ordner (PID 62325, Start 09:34,
Opus, Session `8d535a97`): **61.218** Tokens am ersten Request (27.675
Cache-Lesung, 33.541 Cache-Schreibung). Die Erwartung von rund 61k aus
Stufe 2 ist erfuellt, gegenueber 73.770 vor Stufe 2 sind es 12,5k weniger.
[[Vercel]] fehlt im Deferred-Anhang, Figma und Claude Docs stehen weiter in
den MCP-Anweisungen.

### Geaendert

- `~/.claude/CLAUDE.md`: 11.994 auf 9.115 Bytes. Keine Regel geaendert,
  nur Formulierungen; gestrichen der erledigte claude-flow-Satz.
- `memory/MEMORY.md`: 14.609 auf 11.204 Bytes. Alle 92 Eintraege und Links
  bleiben in gleicher Reihenfolge, nur die Kurzbeschreibungen sind kuerzer.

### Messung (headless, Sonnet, gleiche Flags wie Stufe 2)

| Ort | vorher | nachher |
|---|---|---|
| Home-Ordner | 43.625 | 41.219 (-2.406) |

Der Vorher-Wert liegt 758 unter den 44.383 aus Stufe 2, ohne dass sich
etwas geaendert hat; die Streuung zwischen zwei Laeufen ist also nicht null.
Interaktiv im Home-Ordner sind damit rund 58,8k zu erwarten.

### Offen

- Startwert 58,8k in einem frischen Prozess im Home-Ordner pruefen.
- Projekte interaktiv nachmessen (patina-charts-ios, coremetrics,
  Notenrechner): bis 09:42 gab es seit der Umstellung keinen Start dort.
- Figma und Claude Docs auf claude.ai trennen (Nutzer), danach messen.

## 2026-10-04 Stufe 2: Vercel nur im Notenrechner, Skill-Budget 0.005

Session: Session-Link entfernt.
Settings: [[2026-10-04-settings-aenderungen-stufe-2]].

### Startwert vor der Aenderung

Frischer Prozess im Home-Ordner (Opus, 09:08, kein `/clear`): 73.770 Tokens
am ersten Request. Chrome ist weg (0 Namen im Deferred-Anhang), die
abgeschalteten Plugins `code-review` und `mcp-server-dev` auch. Die
Erwartung von 74 bis 75k ist erfuellt. 120 Skills, 29.942 Zeichen.

### Geaendert

- Vercel global aus, im Notenrechner per `settings.local.json` an (auch in
  den drei Worktrees).
- `skillListingBudgetFraction` 0.005, 13 eingebaute Skills auf `name-only`.

### Messung (headless, Sonnet, gleiche Flags)

| Ort | vorher | nachher |
|---|---|---|
| Home-Ordner | 56.708 | 44.383 (-12.325) |
| Notenberechnung | nicht gemessen | 55.203, Vercel geladen (488 Treffer) |
| Worktree `hygiene` | nicht gemessen | 55.407, Vercel geladen |

Die Simulation per `--settings` (44.381) stimmte mit den echten Dateien
ueberein. Grob aufgeteilt: Skill-Liste rund 15k Zeichen (etwa 3,7k Tokens),
der Rest ist Vercel (Tool-Namen 41,6k auf 16,7k Zeichen, Anweisungen,
Skills). Interaktiv im Home-Ordner sind damit rund 61k statt 73,8k zu
erwarten. Gemessen ist das erst nach einem echten Neustart.

### Lehre

- `skillOverrides` greift nicht bei Plugin-Skills, egal in welcher
  Schreibweise (Code von 2.1.289). Die name-only-Liste aus dem Handoff war
  deshalb zu zwei Dritteln wirkungslos. Fuer Plugin-Skills bleibt nur das
  Budget.
- Bei Budget 0.005 behielten alle 17 eigenen Skills ihre Beschreibung,
  ebenso die genutzten von superpowers. Gekappt wurden ungenutzte Plugin-
  und eingebaute Skills. Die Sorge aus Stufe 1 ("zuerst verlieren eigene
  Skills die Beschreibung") ist mit den Overrides nicht eingetreten.
- `enabledPlugins` wird tief zusammengefuehrt; `true` in der Projektdatei
  schlaegt das globale `false`.
- [[Claude Code]] kopiert `settings.local.json` beim Anlegen eines Worktrees
  mit. Eine lokale Datei reicht also, ein Commit ist nicht noetig.

### Offen

- Startwert im frischen interaktiven Prozess nachmessen: Home rund 61k,
  Notenrechner, patina-charts-ios, coremetrics.
- Figma und Claude Docs auf claude.ai trennen (Nutzer).
- MEMORY.md und CLAUDE.md straffen (eigene Session).
- Alte Prozesse vom 02. und 03.10. laufen noch mit dem alten Stand.

## 2026-10-04 Startkontext von 96k auf rund 77k

Anlass: Sessions starteten vor dem ersten Satz mit rund 95k Tokens, bis zum
Kontext-Cap von 150k blieben damit nur gut 50k fuer die Arbeit.
[Original-Chat](Session-Link entfernt)

### Ausgangslage

Gemessen am ersten Request dieser Session (96.314 Tokens) und an den
Transkript-Anhaengen. Der Startwert ist seit Juli von rund 54k auf 94 bis
96k gewachsen (Tagesmediane aus `~/.claude/projects`). Sub-Agents starten im
Median mit 59k (196 Laeufe in 35 Tagen).

| Block | Groesse | Ballast darin |
|---|---|---|
| Systemprompt + eingebaute Tools | 29k (Cache-Lesung) | keiner; Artifact 31x, Workflow 137x genutzt |
| Memory-Dateien | 17,6k | `~/AGENTS.md` 4,4k: Codex-Vorlage, identisch mit `~/.codex/AGENTS.md`, laedt bei Start im Home-Ordner (61 von 201 Sessions) |
| Agent-Liste | 8,5k | 90 claude-flow-Agents 5,3k, 18 seo-Agents 1,4k |
| Namen der Deferred Tools | 677 Namen, 29k Zeichen | Postproxy 103, Figma 40, Kernel 29, Drive 11, Claude Docs 8, Slack 2: null Aufrufe in 35 Tagen |
| Skill-Liste | 9,9k | 92 claude-flow-Commands, 19 seo-Skills |
| MCP-Anweisungen, Hook-Texte | ca. 5k | Figma, Claude Docs |

### Geaendert

Vom Nutzer gewaehlt: "Ballast raus", "SEO parken", "Chrome auf Abruf".
"Vercel nur im Notenrechner" bewusst nicht, Vercel bleibt global.

- Archiv `~/.claude/_archiv/2026-10-04-kontext-diaet/`: claude-flow (23
  Agent-Ordner, 7 Command-Ordner, 3 Commands, Skill `browser`), SEO (19 Skills
  inkl. `.venv` und Chromium, 18 Agents), `~/AGENTS.md`, dazu
  `settings.json.bak` und `claude.json.bak`.
- Settings im Einzelnen: [[2026-10-04-settings-aenderungen]].

### Messung

Headless `claude -p` mit Sonnet, Telegram aus, identische Flags: 69.182
Tokens vorher, 56.514 nachher. Vorher waren Vercel und Kernel beim ersten
Request noch nicht verbunden, nachher ist Vercel mitgezaehlt (244 Namen, ca.
4,5k). Bereinigt rund 17k weniger.

- Agent-Liste: 123 Agents / 30.656 Zeichen -> 15 / 5.811
- Memory-Dateien: 17,6k -> 13,3k
- Deferred-Namen: sechs Connectoren weg, Gmail und Kalender da
- Skill-Liste: 29.847 -> 29.966 Zeichen, also **keine** Ersparnis (siehe Lehre)

Erwartung interaktiv: Home-Ordner rund 77k statt 96k, Projekte rund 15k
weniger als bisher. Pruefen mit `/context` in der naechsten Session.

### Nachmessung in der Folgesession

Erster Request nach `/clear` im Home-Ordner (Opus, 08:01): 76.088 Tokens.
Die zwei `/clear`-Starts um 07:52 lagen bei 75.918 und 75.846, die sechs
Starts der Nacht bei 96.192 bis 96.465. Die Erwartung von rund 77k ist
erfuellt, gespart sind rund 20k. `~/AGENTS.md` laedt nicht mehr mit, als
Memory-Dateien bleiben `~/.claude/CLAUDE.md` und `MEMORY.md`.

Einschraenkung: Alle drei Werte stammen aus Prozessen, die vor der
Umstellung gestartet wurden (juengster laufender Prozess 01:23). `/clear`
startet keinen neuen Prozess. Deshalb ist Chrome in allen dreien noch
geladen (22 Namen, Anweisungen, Abschnitt im Systemprompt, zusammen rund
1,5k), obwohl `claudeInChromeDefaultEnabled` auf `false` steht. Ein frischer
Prozess muesste entsprechend tiefer starten. Ob der GrowthBook-Schalter
`tengu_chrome_auto_enable: true` in `~/.claude.json` Chrome trotzdem
zuschaltet, ist ungeprueft.

Projekte: Seit 07:50 gab es keinen Start in einem Projektordner, die
Erwartung ist also noch nicht geprueft. Mediane 27.09. bis 03.10. (Opus):
patina-charts-ios 82,2k (22 Starts), coremetrics 85,6k (14),
`03 Bereiche/Claude Code` 92,6k (9). Mit 15k weniger muessten sie bei rund
67k, 71k und 78k landen.

Wo die 76k jetzt stecken (Zeichen der Transkript-Anhaenge): 489
Deferred-Namen mit 20,4k Zeichen, davon Vercel 244 (11,7k) und [[Higgsfield]]
117 (4,3k); Skill-Liste 125 Skills mit 29,9k, am Budget; MCP-Anweisungen
11,5k, davon Figma und Claude Docs 4k ohne ein Tool dahinter; Agent-Liste
16 Agents.

Aufrufe in 30 Tagen (1.333 Transkripte): Playwright 544, Vercel 84 (71 aus
Notenberechnung samt Worktrees, 13 aus dem Home-Ordner: Seitenaufrufe,
Firewall, Logs), Gmail 31, Higgsfield 26, Chrome 10, Kalender 7, context7 1;
Telegram, Figma und Claude Docs 0. 96 von 125 Skills ohne Aufruf, darunter
45 der 46 Vercel-Skills.

### Lehre

- Die Skill-Liste hat ein Budget: `skillListingBudgetFraction` (Standard
  0.01, bei 1M rund 30k Zeichen). Skills entfernen spart dort nichts, der
  freie Platz geht an laengere Beschreibungen der uebrigen. Getestet: 0.005
  ergibt 5k, 0.0035 ergibt 3,5k; dabei verlieren zuerst eigene Skills
  ([[council]], [[reel-ingest]]) ihre Beschreibung, eingebaute wie dataviz nicht.
- `permissions.deny` auf `mcp__<server>` nimmt die Tools restlos raus, die
  Server-Anweisungen bleiben (Figma, Claude Docs, ca. 1,2k). Ganz weg nur per
  `/mcp disable` (pro Projekt) oder Trennen auf claude.ai.
- `claude -p "/context"` laeuft ohne Modellaufruf, zeigt aber nur einen Teil
  (43,8k statt 96k). Den echten Startwert liefert die `usage` des ersten
  Requests im Transkript, die Bloecke stehen dort als `attachment`.

### Offen

- Skill-Budget senken (0.005 spart 5k), sinnvoll nur zusammen mit
  `name-only` fuer ungenutzte eingebaute Skills, damit das Budget bei den
  eigenen landet.
- Figma und Claude Docs auf claude.ai trennen, falls dort auch ungenutzt.
- MEMORY.md (7k) und CLAUDE.md (6,2k) straffen; der claude-flow-Satz in der
  CLAUDE.md ist durch das Archiv erledigt.
- Vercel nur im Notenrechner aktivieren (rund 5k), falls gewuenscht.
- Frischen Prozess messen, im Home-Ordner und in einem Projektordner: erst
  dann sind "Chrome auf Abruf" und die Projekt-Erwartung belegt.
- Entschieden in der Folgesession (Auswahl des Nutzers): Vercel nur im
  Notenrechner, Skill-Budget 0.005 mit name-only fuer ungenutzte Plugin- und
  eingebaute Skills, Figma und Claude Docs trennt er auf claude.ai, Straffen
  in eigener Session. Umsetzung: [[HANDOFF-2026-10-04-kontext-diaet-stufe-2]].

## 2026-10-01 Agent Stefan: erster echter Aufruf (Abend)

Wirkungskontrolle fuer den am selben Tag angelegten Agenten `stefan`
([[HANDOFF-2026-10-01-agent-stefan]]), vor allem fuer die nach dem Probelauf
ergaenzte Regel "Fristart und Rechtsfolgen nur mit Fundstelle".

### Geprueft

Frage: "Stefan, was ist heute Abend dran?" Diesmal als eigener Agent aufgerufen,
nicht mehr als `general-purpose` mit kopiertem Prompt.

| Pruefpunkt | Ergebnis |
|---|---|
| Duzen | Ja, durchgehend. |
| Kalender | Tool kommt im Agenten an, Aufruf fehlerfrei. Die leere Antwort (nur Kontometadaten) hat er als "nicht bestaetigbar" gemeldet statt als leer behauptet. Gegentest: `list_events` 01.–15.10. liefert den Termin am 08.10., die Abfrage findet also Termine; der Abend war wirklich frei. |
| Fristfolgen | "Verliert das Quartal" mit Quelle Wochenplan KW40 (Z. 42–43) und dem Zusatz, dass er keine gesetzliche Grundlage gefunden hat. |

### Hat gewirkt
- Die Regel gegen erfundene Rechtsfolgen: Folge belegt und als nur planseitig gekennzeichnet.
- Die Billogram-Rechnung (im Probelauf uebersehen) nennt er diesmal, ohne neue Regel.
- Kosten rund 42k Tokens statt 87k im Probelauf. Ursache nicht geprueft.

### Unschaerfe, keine Regel
- "Bevor Mahngebuehren entstehen", obwohl das Briefing "Erinnerung ohne Mahngebuehr" sagt. Abgeschwaecht, nicht falsch.
- Die Quellenliste am Ende stand im Auftrag, gehoert nicht zu seinem Standardformat.
- Die Folge "verliert das Quartal" ist nur im Wochenplan belegt; ob sie selbst stimmt, ist offen (vgl. [[frist-herkunft-waechst-beim-kopieren]]).

### Offen
- Weitere Aufrufe beobachten. Keine Regelaenderung.

## 2026-10-01 Wirkungskontrolle nach einer Woche

### Gemessen

`/usage` am 2026-10-01, 08:40, einen Tag vor dem Reset (2026-10-02, 07:00):

| Zeile | Stand |
|---|---|
| Wochenlimit, alle Modelle | 65 % |
| Wochenlimit, Fable 5.1 | 88 % |
| Anfragen | 804 in 24 h, 6.758 in 7 Tagen |

Angaben des Nutzers: ueberwiegend im Terminal gearbeitet, Kontext seit der Regel nie ueber 300k, Handoff viel genutzt, PDF-Regel noch nicht gebraucht.

### Ursachen-Aufschluesselung (zweiter `/usage`-Blick am selben Tag)

Der Lauf um 08:40 hatte nur die Limit-Balken erfasst. Der Abschnitt "What's
contributing to your limits usage?" nennt die Treiber. Datenbasis: letzte 24 h,
und ausdruecklich **nur lokale Sessions auf diesem Mac** — Cloud-Sessions und
claude.ai fehlen darin. Die Posten sind laut Anzeige unabhaengige Merkmale,
keine Aufteilung einer Summe, addieren sich also nicht auf 100 Prozent.

| Treiber | Anteil |
|---|---|
| Verbrauch bei ueber 150k Kontext | 71 % |
| Subagent-schwere Sessions | 39 % |
| davon Subagents unter `coder` | 10 % |
| Skill `/handoff` | 3 % |
| Skill `superpowers:brainstorming` | 1 % |
| MCP `playwright` | 3 % |
| MCP `context-mode` | 3 % |

Zwei dieser Zahlen widersprechen dem, was weiter unten unter "Hat gewirkt" steht:

- **Der Kontext-Cap 150k greift nicht.** Unten steht "kein Kontext mehr ueber
  300k". Das stimmt, ist aber die falsche Schwelle. Die Regel in der CLAUDE.md
  nennt 150k, und 71 Prozent des Verbrauchs lag darueber. Gehaltenes Wochenlimit
  und eingehaltener Cap sind zwei verschiedene Befunde — hier war nur der erste
  wahr. Die Formulierung "Kontext-Cap greift" war zu grosszuegig.
- **`coder` laeuft, die eigenen fuenf nicht.** Das [[2026-09-29 Agenten-Inventar]]
  hatte ueber 30 Tage null Aufrufe fremder Agenten gezaehlt. In den letzten 24 h
  gehen 10 Prozent des Verbrauchs auf Subagents unter `coder`, einen
  claude-flow-Agenten, den die Regel vom 30.09. ausdruecklich ausschliesst.
  Gleichzeitig wurde keiner der fuenf eigenen je ausgefuehrt. **Von Nyko am
  01.10. als bekannt und gewollt bestaetigt** — die Herkunft ist ihm klar, sie
  ist hier nicht protokolliert. Damit ist die Zahl erklaert, aber die Regel vom
  30.09. ("die fremd installierten Agenten aus `claude-flow` nutze ich nicht")
  beschreibt die Praxis nicht vollstaendig. Entweder bekommt sie eine Ausnahme
  fuer `coder`, oder sie bleibt bewusst strenger als die Praxis.

Die Woche ist mit diesem Stand praktisch gelaufen (Reset 2026-10-02, 07:00),
die 65 Prozent sind also ein Endstand, kein Zwischenstand. Der Sonnet-Fallback
aus der Donnerstags-Regel haette hier nichts mehr zu steuern gehabt — ein
weiteres Argument, Schwelle und Zeitpunkt der Regel neu zu fassen.

### Hat gewirkt

- Wochenlimit nicht gerissen, einen Tag vor dem Reset bei 65 %. Vorher regelmaessig gerissen. Fuer den Nutzer ein voller Erfolg.
- Kein Kontext mehr ueber 300k, vorher Sessions bis 90 MB Transkript. Kontext-Cap, Handoff und Statusline greifen.
- Fable 88 % war bewusste Nutzung, kein Ausreisser durch den VS-Code-Picker.

### Nicht messbar oder offen

- PDF-Regel: noch kein Anlass, keine Aussage.
- Skills 96 auf 47 (2026-09-29): erst zwei Tage aktiv, Wirkung naechste Woche.
- Die Regel "Opus-Zeile donnerstags ueber 60 Prozent" passt nicht zu `/usage`: Es gibt keine eigene Opus-Zeile, nur "alle Modelle" und eine Zeile pro Modell wie Fable. Mit 65 % in "alle Modelle" waere die Regel formal gerissen, obwohl die Woche ein Erfolg war. Schwelle und Zeile neu festlegen, Entscheidung offen.
- Diese Cloud-Session lief vom 2026-09-27 bis 2026-10-01 ueber mehrere Auftraege (Workshop, Statusline, Skills, Retro). Stand am 01.10.: 5,1 Mio. Tokens Cache-Read, 22 $. Verstoesst gegen "ein Auftrag pro Session". Lehre: auch Cloud-Sessions nach jedem Auftrag uebergeben.

### Geaendert

- Modell-Regel in der CLAUDE.md: Jede Session sagt zu Beginn ihr Modell an und fragt bei Fable ohne Zuruf einmal nach. Siehe [[Changelog]].

### Naechste Messung

- 2026-10-08 per `/usage`. Fokus: Wirkung der ausgeduennten Skills, Entscheidung zur 60-Prozent-Regel.
- Dabei immer auch "What's contributing" mitlesen, nicht nur die Balken.
  Zielgroesse: der Anteil ueber 150k Kontext soll unter 71 Prozent liegen.
- `coder` ist geklaert (gewollt), braucht keine Messung mehr. Offen bleibt die
  Formulierung der Agenten-Regel in `~/.claude/CLAUDE.md` — Entscheidung bei Nyko,
  nicht eigenstaendig aendern.
- Die fuenf eigenen Agenten sind weiter bei null Ausfuehrungen. Das bleibt die
  eigentliche offene Messung aus dem Eintrag vom 30.09.

## 2026-09-30 Fuenf eigene Sub-Agents statt 116 fremder

Zwei Teile: eine Setup-Aenderung (fuenf neue Agenten) und, am selben Tag
nachgezogen, eine Regel in `~/.claude/CLAUDE.md`, die sie namentlich nennt.
Anlass war das [[2026-09-29 Agenten-Inventar]].

### Ausgangslage

`~/.claude/agents/` enthielt 116 Agenten, alle fremd installiert (mtime
2026-03-30 aus dem claude-flow-Paket, die 18 seo-* vom 2026-07-23).
Keiner davon wurde in 30 Tagen ein einziges Mal aufgerufen. Gestartet
wurden ausschliesslich Built-ins: `general-purpose` (277x), `Explore`
(68x), `Plan` (18x).

Vier gemessene Ursachen: Themen-Mismatch der `description` gegen die
tatsaechliche Arbeit, fehlende MCP-Server (`claude-flow`, `ruv-swarm`,
`agentic-flow` sind nicht konfiguriert, 70 Agenten brauchen sie), falscher
Skill-Einstieg bei den seo-Agenten, und die eigene Regel "Standard ist
linear".

Der eigentliche Befund lag nicht bei den Agenten, sondern bei den Prompts:
**102 von 192 eindeutigen Subagent-Aufrufen beginnen mit einem
handgeschriebenen Rollen-Kopf** ("Rolle: Skeptischer Pruefer. Du aenderst
KEINE Dateien", "Rolle: Belegsucher ... Datei + Zeile + Seite + Zitat").
Die Agenten existierten also laengst — sie wurden jedes Mal neu getippt.

### Geaendert

`~/.claude/agents/nyko/` angelegt mit fuenf Agenten, destilliert aus den
eigenen Rollen-Koepfen: `skeptiker`, `repo-inventur`, `beleg-sucher`,
`web-rechercheur`, `task-reviewer`. Alle auf `model: sonnet`, entsprechend
`subagents-immer-sonnet`.

Die vier read-only Agenten haben **kein** `Write` und **kein** `Edit`. Die
wiederholte Prompt-Bitte "Du aenderst KEINE Dateien" ist damit keine Bitte
mehr, sondern eine fehlende Faehigkeit. Einschraenkung: `Bash` bleibt drin
und koennte theoretisch schreiben — die Sperre ist stark, nicht lueckenlos.

Die 116 alten Agenten und die 8 Duplikate wurden **nicht** angefasst.

### Erwartung

Die handgeschriebenen Rollen-Koepfe entfallen, weil die Rolle in der
Definition steht. Das spart Prompt-Tokens je Aufruf und macht das
Read-only-Versprechen technisch statt rhetorisch.

### Messung

Am 2026-10-01 zusammen mit `/usage`: Wie oft wurde einer der fuenf per
`subagent_type` aufgerufen, und wie oft wurde trotzdem wieder ein
Rollen-Kopf in einen `general-purpose`-Prompt getippt? Die zweite Zahl ist
die interessante — sie zeigt, ob die Definitionen greifen oder nur
herumliegen.

### Offen

- **Teilweise verifiziert.** Am 30.09. in frischer Session bestaetigt: die
  fuenf erscheinen in der geladenen Agentenliste. Ein Testaufruf am 29.09.
  war noch mit "Agent type not found" gescheitert, weil die Liste nur beim
  Session-Start geladen wird. Tatsaechlich *ausgefuehrt* wurde noch keiner.
- **Regel eingetragen am 2026-09-30.** Nach Bestaetigung durch Nyko steht in
  `~/.claude/CLAUDE.md` unter "Sub-Agents und Workflows" eine Zeile, die die
  fuenf namentlich nennt und die `claude-flow`-Agenten ausschliesst.
  Vorversion archiviert als [[History/2026-09-30]], Changelog-Zeile gesetzt,
  Macbook-Kopie abgeglichen. Gegengeprueft: alle fuenf tragen `model: sonnet`,
  die vier read-only haben nur `Read, Bash, Glob, Grep` — `web-rechercheur`
  hat bewusst `Write`, und genau den findet die Suche, sie ist also nicht blind.
- **Katalog unaufgeraeumt.** 116 alte Agenten, davon 8 Duplikate, blaehen
  jeden Systemprompt auf.

## 2026-09-28 Zwei neue Arbeitsregeln aus dem E2-Bau (Abend)

Aufgenommen nach ausdruecklicher Bestaetigung von Nyko am 28.09. Beide
stammen aus dem Bau von E2 (Entnahmeplan individuell, patina-charts-ios,
PR #94), wo sie jeweils erst im Abschluss-Review aufgefallen sind.

### Regel 1: Beim Waechter den Codepfad pruefen, nicht die Farbe

Ein gruener Test beweist nur, dass er gelaufen ist, nicht dass er
hinschaut. Vor dem Berufen auf einen Waechter gilt die Frage: **welchen
Codepfad betritt er, und welchen Fehler wuerde er fangen?**

Anlass: Nach dem Umbau der ETF-Entnahmerechnung blieb
`GoldenNumbersTests` gruen, und das wurde als Beleg gemeldet, dass die
Extraktion nichts verschoben hat. Tatsaechlich laufen alle drei
Golden-Faelle mit `kapitalverzehr = false`, und der Kapitalerhalt-Zweig
kehrt *vor* der umgebauten Schleife zurueck. Die Tests konnten gar nicht
fallen. Die eigens dafuer geschriebene Regression war ebenso blind: sie
prueft `bruttoSumme`, die bei konstanter Rate algebraisch aus `startRate`
folgt.

Praktische Fassung: Die Sabotage-Probe gehoert an den **Anfang**, nicht
ans Ende. Der Beleg war am Ende trivial (Steuersatz verdoppeln, beide
Tests blieben gruen) und haette direkt nach dem Umbau zwei Minuten
gekostet, statt eine falsche Entwarnung zu erzeugen.

Ergaenzt die bestehende Skeptiker-Regel („ein Fund gilt erst, wenn ein
Gegentest rot wird") um die Frage, ob der Test den geaenderten Code
ueberhaupt erreicht.

### Regel 2: Ein Flag, das nur die UI abschaltet, ist kein Kill-Switch

Bei jedem Feature-Flag von Anfang an fragen, was beim **Zurueckschalten**
passiert, nicht nur beim Einschalten. Persistierter Zustand, Cache-
Schluessel und Parameter-Fabriken gehoeren mit unter das Flag, sonst
rechnet die Engine weiter, waehrend das Bedienelement verschwunden ist.

Anlass: `entnahmePlan` und `policeAuszahlungsart` wurden aus `KundenProfil`
und `SessionSnapshot` ohne Flag-Pruefung wiederhergestellt, waehrend die
Karte hinter dem Flag lag. Flag aus haette geheissen: Engine rechnet
weiter den Auszahlplan, Beratungstexte und PDF sagen „Auszahlplan", und
der Berater hat kein Bedienelement, um es zurueckzustellen. Genau der
Fall, fuer den ein Kill-Switch da ist.

### Erwartung

- Weniger falsche Entwarnungen in Zwischenberichten an Nyko.
- Flags bleiben rueckrollbar, ohne dass ein Geraete-Smoke das aufdecken muss.

### Messung

- Naechste Pruefung beim naechsten groesseren Umbau mit Flag (E3 oder E4).
- Bewaehren sich beide, gehoeren sie in `~/.claude/CLAUDE.md` unter
  „Arbeitsregeln Code" - dann mit dem dortigen Versionierungs-Ritual
  (Archiv, Changelog, Kopie).

### Offen

- Noch nicht in `~/.claude/CLAUDE.md` uebernommen, bewusst: erst Wirkung
  abwarten.

## 2026-09-24 Wirkungskontrolle nach dem Umbau (Abend)

### Geprueft

- `~/.claude/settings.json`: Modell opus, Effort medium, keine modelSettings mehr. Die Datei greift.
- claude-flow: `claude mcp list` in einem frischen Prozess zeigt keinen claude-flow mehr. Die laufende VS-Code-Session meldete den 30-Sekunden-Timeout trotzdem noch, weil ihr Prozess vor dem Umbenennen der `~/.mcp.json` gestartet war.
- Rest gefunden: `SecondBrain/.claude/settings.local.json` hatte noch `enabledMcpjsonServers: ["claude-flow"]`. Entfernt.

### Nicht gewirkt

- Die VS-Code-Session lief nach `/clear` weiter auf Fable 5.1 mit Effort Ultracode. Der Picker in VS Code gewinnt pro Session ueber settings.json, und `/clear` startet den Prozess nicht neu.
- Konsequenz: Modell und Effort im Picker von Hand auf Opus und medium stellen, danach die Extension neu starten.

### Naechster Schritt

- Nach dem Neustart pruefen: Modell Opus, Effort medium, keine claude-flow-Meldung.
- Messung am 2026-10-01 per `/usage` bleibt.

## 2026-09-24 CLAUDE.md-Umbau und Effort-Regel

### Ausgangslage

- Wochenlimit trotz Claude Max 20x regelmaessig gerissen. Plan: Claude Max 20x, der groesste Plan. Ursache war das Muster (Punkte unten), nicht das Kontingent.
- Stand 07.10.2026 (Limit-Verlauf): Laut Nyko stoesst er nicht mehr ans Limit; am 07.10. drei angefangene 5h-Fenster, keins ueber 10 %. Die Verlaeufe 23.09.-07.10. enthalten 0 Limit-Abbrueche. Limit ist damit kein vorrangiges Problem mehr. Hohe Tageswerte im Cockpit (07.10.: 1,53 Mio. Output) stimmen und kommen ueberwiegend aus Sub-Agents (62 %). Der damalige Kontext-Cap 150k ist inzwischen 175k (~/.claude/CLAUDE.md).
- Effort-Stufe "ultracode"/"xhigh" dauerhaft aktiv, unabhaengig von der Aufgabengroesse.
- 1M-Kontext-Modell im Einsatz, Sessions liefen bis 90 MB Transkript auf.
- CLAUDE.md-Regel "immer Agenten-Team, nie Solist" erzwang Sub-Agents auch bei kleinen Aufgaben.
- 97 Skills und 116 Agent-Definitionen installiert, davon viele claude-flow-Reste ohne aktuellen Nutzen.

### Geaendert

- Betriebsregeln Claude Code ergaenzt: Kontext-Cap 150k Tokens pro Session.
- Effort-Standard auf medium gesetzt statt dauerhaft ultracode/xhigh.
- Rollenaufteilung festgelegt: Lead auf Opus, Sub-Agents auf Sonnet, Fable nur auf Zuruf.
- Sub-Agents werden erst ab zwei unabhaengigen Teilaufgaben eingesetzt, nicht pauschal.
- Workflows laufen nur noch auf ausdrueckliche Anweisung.
- /usage-Check fest eingeplant: montags und donnerstags, mit Sonnet-Fallback sobald ueber 60 Prozent verbraucht.
- Template-Platzhalter aus der CLAUDE.md entfernt.
- claude-flow-MCP deaktiviert.
- Workflow-Kostenwarnung wieder aktiviert.

### Erwartung

- Wochenlimit haelt unter normaler Nutzung.
- Qualitaet steigt eher, weil der Kontext klein und fokussiert bleibt, statt durch riesige Transkripte zu verwaessern.

### Messung

- Naechste Pruefung: 2026-10-01, donnerstags per `/usage`, Fokus auf die Opus-Zeile.

### Offen

- Skool-Kurs (Name, Anbieter, Module) noch eintragen, siehe [[Lernplan]].
- Skills und Agent-Definitionen ausduennen wurde bewusst NICHT gemacht, steht noch aus.
- Vault-CLAUDE.md hat noch Template-Platzhalter, die bereinigt werden muessten.
