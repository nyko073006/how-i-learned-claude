---
tags:
  - claude-code
  - retro
status: aktiv
aktualisiert: 2026-09-24
source: claude
chat_url: unbekannt
---

# Retro-Log Arbeitsweise Claude Code

Datierte Eintraege, was an Regeln oder Settings geaendert wurde, warum, und ob es gewirkt hat. Neueste Eintraege oben.

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
