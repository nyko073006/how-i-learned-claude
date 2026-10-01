---
tags:
  - claude-code
  - retro
status: aktiv
aktualisiert: 2026-10-01
source: claude
chat_url: unbekannt
---

# Retro-Log Arbeitsweise Claude Code

Datierte Eintraege, was an Regeln oder Settings geaendert wurde, warum, und ob es gewirkt hat. Neueste Eintraege oben.

## 2026-10-01 Wirkungskontrolle nach einer Woche

### Gemessen

`/usage` am 2026-10-01, 08:40, einen Tag vor dem Reset (2026-10-02, 07:00):

| Zeile | Stand |
|---|---|
| Wochenlimit, alle Modelle | 65 % |
| Wochenlimit, Fable 5.1 | 88 % |
| Anfragen | 804 in 24 h, 6.758 in 7 Tagen |

Angaben des Nutzers: ueberwiegend im Terminal gearbeitet, Kontext seit der Regel nie ueber 300k, Handoff viel genutzt, PDF-Regel noch nicht gebraucht.

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

- Wochenlimit trotz Claude Max 20x regelmaessig gerissen.
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
