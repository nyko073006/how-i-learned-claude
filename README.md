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
| `token-setup/` | Wie ich das Wochenlimit halte: Regeln, Einstellungen, Startkontext-Diaet, Messwerte |
| `skills/` | Meine Claude-Code-Skills, je Ordner ein Skill (Uebersicht und Installation im Abschnitt "Skills") |

## Skills

Elf Skills fuer Claude Code, gespiegelt aus `~/.claude/skills/`. Jeder Ordner hat `SKILL.md` (Anweisung fuer Claude), `README.md` und meist ein Diagramm.

| Skill | Zweck | Abhaengigkeit |
|---|---|---|
| `akquise-vorlagen` | Bauplaene fuer B2B-Akquise: Kaltmail, LinkedIn-Post, Kommentar-Routine, Verkaufsgespraech | Vault in der Einstellungsdatei (liest `<VAULT>/00 Kontext/Schreibstil.md`) |
| `app-store-wachstum` | Handgriffe, damit eine iOS-App nach dem Bau Nutzer und Umsatz bekommt | keine |
| `hoehlenmensch` | Ultrakomprimierter Antwort-Modus fuer deutschsprachige Sessions | keine |
| `ingest` | Verarbeitet Notizen im Obsidian Vault und vernetzt sie mit dem restlichen Wissen | Vault in der Einstellungsdatei; ergaenzt `lint` |
| `launch-check` | Prueft eine KI-gebaute Website oder Web-App vor dem Livegang | `curl`, `dig`, `nc` |
| `lint` | Woechentlicher Gesundheits-Check eines Obsidian-Vaults | Vault in der Einstellungsdatei |
| `reel-ingest` | Verarbeitet Reels (Instagram, YouTube Shorts, TikTok), umsetzen oder nur analysieren | Vault in der Einstellungsdatei; `ffmpeg`/`ffprobe`; Python-Pakete aus `requirements.txt`; Sammelmodus (DMs): `opencli` und `reel_chrome_profil` (`reel_konto`); optional Telegram (Plugin mit Bot) |
| `reload-verlust` | Prueft nach einem Neuladen von Obsidian, was an Claude-Sitzungen verloren ging | nur macOS; Vault in der Einstellungsdatei (`repo_wurzeln` optional); Cockpit-Statuszeile optional |
| `skill-creator` | Veroeffentlicht einen Skill ueber alle Ebenen des Skill-Lifecycles | Einstellungsdatei (`skill_repo`, `oeffentlich_repo`, `sperrliste`) |
| `unbeaufsichtigt` | Laeufe ohne Nutzer am Platz zu Ende bringen | keine |
| `verknuepfen` | Setzt Wikilinks auf Entitaeten in Obsidian-Notizen | braucht `lint` (importiert `vault_lint`); Vault in der Einstellungsdatei; optional qmd und Node fuer `nachbarn` |

### Installation

Repo holen und den Skill-Ordner anlegen:

```bash
git clone https://github.com/nyko073006/how-i-learned-claude.git
cd how-i-learned-claude
mkdir -p ~/.claude/skills
```

Je gewuenschten Skill eine Zeile, hier `lint` (bei `verknuepfen` auch `lint`). Die Zeile kopiert nur, wenn es den Ordner unter `~/.claude/skills/` noch nicht gibt; ein vorhandener Skill gleichen Namens wird nie ueberschrieben:

```bash
test -e ~/.claude/skills/lint && echo "lint existiert schon, nichts kopiert" || cp -R skills/lint ~/.claude/skills/
```

`skill-creator` heisst wie Anthropics offizieller Skill. Meldet die Zeile fuer `skill-creator` einen vorhandenen Ordner, nicht darueberkopieren: entweder auf diesen Skill verzichten oder den vorhandenen Ordner vorher selbst umbenennen. Dieser Skill erwartet sich unter `~/.claude/skills/skill-creator`, seine Befehle nennen diesen Pfad.

Die Einstellungsdatei einmal anlegen, ohne eine vorhandene zu ueberschreiben:

```bash
mkdir -p ~/.config/claude-skills && cp -n skills/einstellungen.beispiel.json ~/.config/claude-skills/einstellungen.json
```

Danach in `~/.config/claude-skills/einstellungen.json` den eigenen `vault` eintragen. In der Vorlage sind die meisten Werte leer (`""` oder `[]`), vorbelegt sind nur `repo_wurzeln` und `sperrliste`; ein leerer Wert wirkt wie ein fehlender. Ist `vault` leer, fragen die Skills beim ersten Aufruf nach dem Pfad und tragen ihn ein. Was das je Schluessel bedeutet:

- `vault`: `lint`, `verknuepfen` und `reload-verlust` brechen mit Klartext und Exit 2 ab, ebenso, wenn der Ordner nicht existiert. `skill-creator` (`publish_skill.py`) warnt nur und laesst den Vault-Doku-Schritt weg. Ist `vault` gesetzt, braucht `publish_skill.py` den Ordner `<VAULT>/03 Bereiche/Skills`; fehlt er, Exit 2, bevor etwas geschrieben wird.
- `dienst_ordner`: leer heisst, die Pruefungen auf dienstliche Notizen entfallen: in `lint` der Dienstteil von Regel L5 und die Ausnahme in L1, in `verknuepfen` die Grenze fuer dienstliche Notizen (keine Notiz gilt als dienstlich).
- `repo_wurzeln`: fehlt der Schluessel, gilt `~/Developer`.
- `skill_repo`: Pflicht fuer `publish_skill.py` (oder `--repo-dir`); fehlt er, Abbruch mit Exit 2.
- `skill_remote`: optional; fehlt er, laeuft der Push ueber ein vorhandenes `origin` weiter. `--create-remote` bricht nur dann mit Exit 2 ab, wenn es noch kein `origin` gibt, und zwar vor dem Versionssprung.
- `oeffentlich`: Liste der Skills (`["lint"]`), die zusaetzlich oeffentlich gespiegelt werden; leer oder fehlend heisst kein oeffentlicher Schritt. Ein String statt einer Liste ist ein Fehler (Exit 2).
- `oeffentlich_repo`: lokale Arbeitskopie des oeffentlichen Repos. Steht der veroeffentlichte Skill in `oeffentlich` und fehlt `oeffentlich_repo`, Exit 2. `--pruefe-oeffentlich` braucht `oeffentlich_repo` immer.
- `sperrliste`: Die Vorlage nennt `~/.config/cockpit/public-denylist.txt`. Steht der veroeffentlichte Skill in `oeffentlich`, bricht `publish_skill.py` mit Exit 2 ab, wenn diese Datei fehlt, keine Begriffe enthaelt oder nicht UTF-8 ist; `--pruefe-oeffentlich` laedt sie immer. Eigene Datei anlegen (ein Begriff je Zeile) oder den Pfad aendern.
- `reel_konto`, `reel_chrome_profil`: nur fuer `reel-ingest`; ist `reel_chrome_profil` leer, bricht der Sammelmodus (`sammle.py dm`) mit Exit 2 ab; ist `reel_konto` leer, fragt der Sammelmodus nach dem Konto.

## Was hier fehlt, mit Absicht

- Handoff-Dateien. Session-Zustand, kein Inhalt. Stehen in der `.gitignore`.
- Screenshots des Skool-Classrooms. Kursmaterial eines bezahlten Kurses und mein Account. Die `![[...]]`-Einbettungen im Lernplan zeigen deshalb hier ins Leere.
- Daily Notes, Memory-Dateien und die vollstaendige `settings.json`. Enthalten Kontext aus anderen Projekten.

## Herkunft

Die Dateien sind Kopien aus meinem Obsidian-Vault und aus `~/.claude/`. Wikilinks im Obsidian-Format (`[[Name]]`) bleiben stehen, sie zeigen auf Dateien in diesem Repo oder im Vault. Kurs: [Skaile Academy - Claude Code](https://www.skool.com/skaile-academy) von Sebastian Kauffmann.
