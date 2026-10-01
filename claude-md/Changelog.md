---
tags:
  - kontext
  - claude-md
  - changelog
status: aktiv
aktualisiert: 2026-10-01
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
| 2026-09-27 | Kontext-Cap: PDFs vor dem Einlesen mit Markitdown in Markdown umwandeln; scheitert die Umwandlung, sage ich es vorher. | Workshop Skaile Academy: 20-seitige PDF kostet laut Presenter mind. 50k Tokens, als `.md` rund 12k. Vom Nutzer bestaetigt. | [[History/2026-09-27]] |
| 2026-09-27 (2) | Effort: Standard fuer Opus (Lead-Session) von `medium` auf `high`; alle anderen Modelle bleiben auf `medium`. `settings.json` passend: `modelSettings.claude-opus-5-5.effortLevel` von `xhigh` auf `high`, globales `effortLevel` bleibt `medium`. | Nutzer-Entscheidung. Anlass: In `settings.json` stand fuer Opus 5.5 unbemerkt `xhigh`, im Widerspruch zur Regel `medium`. | [[History/2026-09-27-2]] |
| 2026-09-29 | Kontext-Cap: Handoff-Skill `session-uebergabe` durch `handoff` ersetzt. | Skills ausgeduennt (96 auf 47): `session-uebergabe` war doppelt zu `handoff` und ist archiviert, der umfangreichere `handoff` bleibt. Vom Nutzer bestaetigt. | [[History/2026-09-29]] |
| 2026-10-01 | Modell: Jede Session sagt zu Beginn ihr Modell an; bei Fable ohne Zuruf fragt sie einmal nach. Ersetzt "weise nur bei Abweichung hin". | Wirkungskontrolle 01.10.: Fable-Zeile bei 88 % (bewusst genutzt). Nutzer will das Modell jeder Session sehen und bei unbeabsichtigtem Fable gefragt werden. Vom Nutzer bestaetigt. | [[History/2026-10-01]] |
