# how i learned claude

Lernjournal zu Claude Code. Hier liegen meine Regeln, ihre Versionsgeschichte, der Lernplan zur Skaile Academy und ein Retro-Log, das festhaelt, was ich geaendert habe und ob es gewirkt hat.

Ausgangspunkt am 2026-09-24: Wochenlimit trotz Claude Max 20x regelmaessig gerissen. Ursache war nicht das Kontingent, sondern das Muster: Effort-Stufe Ultracode dauerhaft aktiv, 1M-Kontext-Sessions mit Transkripten bis 90 MB, und eine CLAUDE.md-Regel, die Sub-Agents zur Pflicht machte. Die Antwort darauf steht in `claude-md/CLAUDE.md`, Abschnitt "Betriebsregeln Claude Code".

## Struktur

| Ordner | Inhalt |
|---|---|
| `claude-md/CLAUDE.md` | Globale Regeln (`~/.claude/CLAUDE.md`), aktuelle Fassung |
| `claude-md/Changelog.md` | Was sich wann geaendert hat und warum |
| `claude-md/history/` | Archivierte Vorfassungen, je Aenderung eine Datei |
| `vault/CLAUDE.md` | KI-agnostische Regeln fuer das Obsidian-Vault (Struktur, Daily-Note-Pattern, Projekte, Research) |
| `lernen/Lernplan.md` | Module der Skaile Academy, auf Abende verteilt, mit 20-Minuten-Minimalfassung |
| `lernen/Retro-Log.md` | Datierte Eintraege: Aenderung, Grund, Erwartung, Messung |
| `lernen/kurs-notizen/` | Eine Notiz pro Kursmodul, aus der Vorlage |
| `settings/` | Aenderungen an `settings.json` und Co., nur die Diffs |

## Was hier fehlt, mit Absicht

- Handoff-Dateien. Session-Zustand, kein Inhalt. Stehen in der `.gitignore`.
- Screenshots des Skool-Classrooms. Kursmaterial eines bezahlten Kurses und mein Account. Die `![[...]]`-Einbettungen im Lernplan zeigen deshalb hier ins Leere.
- Daily Notes, Memory-Dateien und die vollstaendige `settings.json`. Enthalten Kontext aus anderen Projekten.

## Herkunft

Die Dateien sind Kopien aus meinem Obsidian-Vault und aus `~/.claude/`. Wikilinks im Obsidian-Format (`[[Name]]`) bleiben stehen, sie zeigen auf Dateien in diesem Repo oder im Vault. Kurs: [Skaile Academy - Claude Code](https://www.skool.com/skaile-academy) von Sebastian Kauffmann.
