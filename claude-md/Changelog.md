---
tags:
  - kontext
  - claude-md
  - changelog
status: aktiv
aktualisiert: 2026-09-24
source: claude
chat_url: unbekannt
---

# Changelog globale CLAUDE.md

Massgeblich ist ausschliesslich `~/.claude/CLAUDE.md`. Hier steht nur, was sich wann geaendert hat und warum. Archivierte Fassungen liegen in `History/`, die aktuelle Kopie in `Macbook/CLAUDE.md`.

| Datum | Aenderung | Grund | Archiv der Vorversion |
|---|---|---|---|
| 2026-09-24 | Template-Charakter entfernt (Platzhalter, Vorspann). Neuer Abschnitt "Betriebsregeln Claude Code": Kontext-Cap 150k, Effort-Standard medium, Modell-Regel Opus/Sonnet/Fable, Sub-Agent-Schwelle statt Agenten-Pflicht, Wochenlimit-Check. "Optional: Geraete-Setup" gestrichen. Versionierung von optional auf Pflicht. Neuer Abschnitt "Lernen und Retro". | Wochenlimit trotz Max 20x gerissen. Ursachen: Ultracode-Effort dauerhaft aktiv, 1M-Kontext-Sessions bis 90 MB, Regel "immer Agenten-Team, nie Solist". | [[History/2026-09-24]] |
| 2026-09-24 (2) | Kontext-Cap: Bei automatisch ausgeloestem Handoff sagt die Session, dass sie clearable ist; jede clearable Session fordert ausdruecklich zum `/clear` auf. Definition von clearable ergaenzt. | Nutzer will ein eindeutiges Signal, wann eine Session gewiped werden kann. | [[History/2026-09-24-2]] |
| 2026-09-24 (3) | Kontext-Cap: Handoff-Dateien stehen in Git-Projekten immer in der `.gitignore`; fehlender Eintrag wird beim Handoff angelegt. | Handoffs sind Session-Zustand, kein Projektinhalt; sollen nicht ins Repo. | [[History/2026-09-24-3]] |
