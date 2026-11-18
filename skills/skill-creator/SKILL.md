---
name: skill-creator
version: 1.3.0
description: >
  Veroeffentlicht einen Claude-Skill in einem Durchgang ueber alle Ebenen des
  Skill-Lifecycles: lokal (Version bumpen), GitHub (spiegeln und committen), Vault
  (Doku-Frontmatter und Versionshistorie aktualisieren) und, fuer freigegebene Skills,
  oeffentlich (Sperrlisten-Pruefung, dann Spiegel ins oeffentliche Repo). Verwenden nach
  JEDER Skill-Erstellung oder -Aenderung, sowie wenn der Nutzer "publish skill",
  "skill veroeffentlichen", "skill releasen", "skill dokumentieren", "version bumpen"
  oder "publish_skill" sagt.
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
---

# skill-creator — Publish-Pipeline fuer Claude-Skills

Dieser Skill stellt das Publish-Tooling bereit, das der globale Skill-Lifecycle-Workflow
in `~/.claude/CLAUDE.md` vorschreibt. Er buendelt die Ebenen in einem Befehl.

## Der Lifecycle

| Ebene | Was passiert | Ort |
|-------|--------------|-----|
| 1. Lokal | SKILL.md validieren, SemVer-Version lesen und erhoehen | `~/.claude/skills/<name>/` |
| 2. GitHub | Skill-Ordner ins Repo spiegeln, committen, ggf. pushen | `<skill_repo>/<name>/` |
| 3. Vault | Doku-Frontmatter und Versionshistorie fortschreiben | `<vault>/03 Bereiche/Skills/<name>.md` |
| 4. Oeffentlich | nur Skills in `oeffentlich`: Sperrliste pruefen, spiegeln, committen (nie pushen) | `<oeffentlich_repo>/skills/<name>/` |

## Einstellungen

Pfade und Namen stehen nicht im Code, sondern in einer JSON-Datei: Env
`CLAUDE_SKILLS_EINSTELLUNGEN`, sonst `~/.config/claude-skills/einstellungen.json`.
`~` in Pfaden wird aufgeloest. Fehlt die Datei, gelten keine Vorgaben.

| Schluessel | Bedeutung |
|------------|-----------|
| `skill_repo` | Pflicht (oder `--repo-dir`). Privates Skill-Repo, Ziel von Ebene 2 |
| `skill_remote` | GitHub-Slug `besitzer/repo`, fuer Hinweise und `--create-remote` |
| `vault` | Vault-Wurzel fuer Ebene 3. Fehlt er, gibt es eine Warnung und keinen Doku-Schritt |
| `oeffentlich` | Liste der Skills, die zusaetzlich oeffentlich gespiegelt werden. Muss eine JSON-Liste sein (`["lint"]`), sonst Exit 2 |
| `oeffentlich_repo` | Lokale Arbeitskopie des oeffentlichen Repos |
| `sperrliste` | Datei mit Sperrbegriffen: ein Begriff je Zeile, `#` Kommentar, `!` vorn eine Ausnahme (gilt nur mit Wortgrenze beiderseits). Vorgabe ohne Schluessel: `~/.config/cockpit/public-denylist.txt`; fehlt auch diese Datei oder ist sie leer, Exit 2 |

Verglichen wird in Normalform (NFKD, ohne Akzente und unsichtbare Formatzeichen,
klein); Treffer zaehlen auch im Dateipfad und in Binaerdateien. Ausgegeben werden nur
Pfad (Treffer als `***` maskiert) und Zeile, nie der Treffertext. Nutzerpfade und
Links auf Claude-Sitzungen sind immer gesperrt. Eine `.publicignore` im Skill-Ordner
(ein Glob je Zeile, `ordner/` fuer ganze Ordner) nimmt Dateien vom oeffentlichen
Spiegel aus; sie selbst wird nie gespiegelt.

## Standardbefehl

```bash
python3 ~/.claude/skills/skill-creator/scripts/publish_skill.py <skill-name> -m "Was wurde geaendert"
```

Nach JEDER Skill-Erstellung oder -Aenderung ausfuehren. Vorher immer einmal mit
`--dry-run` pruefen, wenn du dir bei einem Skill unsicher bist.

## Flags

| Flag | Bedeutung |
|------|-----------|
| `<skill-name>` | Pflicht. Ordnername unter `~/.claude/skills/` |
| `-m`, `--message` | Pflicht. Beschreibung der Aenderung. Wird Commit-Message und Zeile in der Versionshistorie |
| `--bump patch\|minor\|major` | SemVer-Sprung. Default: `patch` |
| `--no-version-bump` | Version bleibt unveraendert — fuer die Erstveroeffentlichung |
| `--dry-run` | Zeigt alle geplanten Aenderungen, schreibt nichts. Kein Commit, kein Push, keine Datei |
| `--create-remote` | Legt das GitHub-Repo per `gh repo create` an. Default: AUS. Nur mit expliziter Zustimmung des Nutzers setzen |
| `--pruefe-oeffentlich` | Ohne Skill und `-m`: prueft alle Dateien unter `<oeffentlich_repo>/skills/` (ohne Ausschluesse, auch Logs und Caches) gegen die Sperrliste und meldet Ordner, die nicht in `oeffentlich` stehen, als verwaist. Dazu die noch nicht gepushten Commits (`@{u}..HEAD`): Ordner unter `skills/` ("verwaist in Historie"), jede dort geaenderte Datei und jede Commit-Nachricht. Ohne Upstream nur der Arbeitsbaum, mit Hinweis. Exit 0 sauber, 2 bei Treffern oder fehlender Einstellung |
| `--skills-dir`, `--repo-dir`, `--vault-dir` | Pfade ueberschreiben (Default: `~/.claude/skills`, `skill_repo`, `vault`) |

## Tests

```bash
cd ~/.claude/skills/skill-creator/scripts && python3 -m unittest test_publish_skill -v
```

## Ablauf im Detail

1. **Validieren** — Skill-Ordner vorhanden? `SKILL.md` vorhanden und mit gueltigem
   YAML-Frontmatter? Weicht `name:` vom Ordnernamen ab, gibt es eine Warnung.
2. **Version** — `version:` aus dem Frontmatter lesen und nach `--bump` erhoehen.
   Steht kein Top-Level-Feld da, wird `metadata.version` geprueft (so machen es die
   ~31 `seo-*`-Skills) und auch dort wieder zurueckgeschrieben. Fehlt das Feld ganz
   oder ist es kein SemVer (z.B. `unbekannt`), startet der Skill bei `1.0.0` und
   ergaenzt das Feld. Mit `--no-version-bump` bleibt alles wie es ist.
3. **Spiegeln** — Der Skill-Ordner wird nach `<repo>/<skill-name>/` gespiegelt.
   Dauerhaft ausgeschlossen: `.git/`, `venv/`, `.venv/`, `node_modules/`,
   `__pycache__/`, `ms-playwright/`, `.DS_Store` — dazu `*.pyc`, `*.log` und
   `.env*` (Secrets-Policy). Ohne diese Ausschluesse wuerden einzelne Skills
   ueber 27.000 Dateien ins Repo ziehen. Dateien, die im Skill geloescht wurden,
   verschwinden auch im Repo.
4. **Git** — Existiert das Repo nicht, wird `git init -b main` ausgefuehrt und eine
   `.gitignore` mit denselben Mustern angelegt. Dann `git add` und `git commit`.
   **Gepusht wird nur, wenn ein Remote `origin` konfiguriert ist.** Sonst gibt das
   Skript den fertigen Befehl aus, mit dem der Nutzer das Remote nachtraegt.
   Ein Repo auf GitHub legt das Skript **nie von selbst** an — nur mit `--create-remote`.
5. **Vault** — Doku unter `03 Bereiche/Skills/<skill-name>.md` fortschreiben.
6. **Oeffentlich** (nur fuer Skills in `oeffentlich`) — Geprueft wird alles, was in
   den Commit gelangt: der oeffentliche Umfang (Spiegelumfang ohne
   `.publicignore`-Treffer), der Skillname und die Nachricht `-m`. Das geschieht
   schon vor Schritt 1 und noch einmal direkt vor dem Kopieren; ein Treffer bricht
   ab, ohne etwas zu kopieren. Nach `git add` wird zusaetzlich der Index geprueft,
   damit fremde Dateien im Ziel (Logs, Caches) nicht ungeprueft mitkommen; bei einem
   Treffer wird nur der Index zurueckgesetzt, die Dateien bleiben liegen. Loeschungen
   blockieren nie, damit ein Pfad, dessen Begriff spaeter auf die Liste kam, sich
   entfernen laesst. Symlinks gelten immer als Treffer `(symlink)`: Der Spiegel kopiert
   Inhalte und legt nie selbst Links an, ein Link im Ziel ist also fremd. Ist das
   Spiegelziel, ein Elternordner bis zum Repo oder ein Eintrag darin ein Symlink, bricht
   der Spiegel (privat wie oeffentlich) vor jedem Schreiben ab. Sonst Spiegel nach `<oeffentlich_repo>/skills/<name>/`
   (Veraltetes wird geloescht) und Commit `skills/<name>: <nachricht>`. Gepusht wird
   nie; das bleibt eine bewusste Handlung. Fehlt die Sperrliste oder ist sie leer,
   endet das Skript mit Exit 2.
7. **Zusammenfassung** — Version alt/neu, gespiegelte Dateien, Commit-Hash oder
   Push-Hinweis, Pfad der Doku-Datei, oeffentlicher Commit.

## Sicherheitsregel: bestehende Doku wird nie ueberschrieben

Die Dateien in `03 Bereiche/Skills/` sind handgeschrieben und die eigentliche
Wissensbasis. Existiert die Doku bereits, sind **genau zwei Eingriffe erlaubt**:

- im Frontmatter `version:` und `aktualisiert:` aktualisieren
- in der Tabelle "Versionshistorie" eine Zeile `| <datum> | <version> | <nachricht> |` anhaengen

Alles andere bleibt Zeichen fuer Zeichen so, wie es war. Hat die Datei kein gueltiges
Frontmatter, bricht das Skript ab, statt zu raten.

Existiert die Doku **nicht**, legt das Skript sie nach dem Vault-Format an —
Frontmatter (`tags: [ki-skill]`, `skill`, `version`, `aktualisiert`, `status`,
`source: claude`, `chat_url: unbekannt`) plus die Sektionen Ueberblick, Trigger,
Funktionsumfang, Nutzungsbeispiele, Voraussetzungen, Dateistruktur, Verwandt,
Versionshistorie. Offene Stellen stehen als sichtbares `TODO` drin.

**Nach dem Anlegen einer neuen Doku IMMER die TODO-Platzhalter durch echten Inhalt
ersetzen** — Ueberblick (2 bis 3 Saetze), Funktionsumfang (alle Funktionen als
Bullet-Points) und mindestens zwei Nutzungsbeispiele mit Ausloeser und Ergebnis.
Das Skript kann die Struktur liefern, nicht das Wissen.

## Weitere Regeln

- Das Datum kommt immer aus dem Systemdatum, nie aus einer Schaetzung.
- Keine Secrets in Repo oder Doku — `.env`-Dateien werden beim Spiegeln uebersprungen.
- Fehler werden als klare Meldung ausgegeben, nicht als Traceback. Exit-Code `1` im
  Fehlerfall, `2` bei fehlender oder kaputter Einstellung oder ungueltigem Skillnamen
  (erlaubt: Buchstaben, Ziffern, `.`, `_`, `-`, vorn Buchstabe oder Ziffer).
- Vorbedingungen werden vor dem ersten Schreiben geprueft: Doku-Ordner
  `<vault>/03 Bereiche/Skills` (wenn `vault` gesetzt), `skill_repo` ist ein git-Repo oder
  existiert noch nicht (dann `git init`), `oeffentlich_repo` ist ein git-Repo. Fehlt
  etwas, Exit 2 ohne Versionssprung und ohne Commit.
- Nur Python-Standardbibliothek, keine externen Pakete.

## Beispiele

```bash
# Standardfall: Patch-Bump nach einer kleinen Aenderung
python3 ~/.claude/skills/skill-creator/scripts/publish_skill.py lint -m "Projekt-Compliance-Check ergaenzt"

# Erstveroeffentlichung, Version soll bleiben
python3 ~/.claude/skills/skill-creator/scripts/publish_skill.py mein-skill -m "Erstveroeffentlichung" --no-version-bump

# Groessere Erweiterung, vorher trocken pruefen
python3 ~/.claude/skills/skill-creator/scripts/publish_skill.py mein-skill -m "Neue Sub-Skills" --bump minor --dry-run

# Oeffentliches Repo pruefen (Treffer, verwaiste Ordner)
python3 ~/.claude/skills/skill-creator/scripts/publish_skill.py --pruefe-oeffentlich
```

## Diagramm als PNG rendern

Der Lifecycle verlangt pro Skill ein Diagramm als `.excalidraw` und `.png`. Das PNG
erzeugt `export_excalidraw.cjs` mit der offiziellen Excalidraw-Exportfunktion
(`@excalidraw/utils` 0.1.5) in Headless-Chromium. Vor `publish_skill.py` ausfuehren,
damit das PNG mitgespiegelt wird.

```bash
# PNG neben die Quelle legen (Default-Skalierung 4, ~4.000 px Breite)
node ~/.claude/skills/skill-creator/scripts/export_excalidraw.cjs ~/.claude/skills/lint/lint-overview.excalidraw

# Ziel und Skalierung selbst setzen
node ~/.claude/skills/skill-creator/scripts/export_excalidraw.cjs quelle.excalidraw ziel.png --scale 2
```

Braucht Node, Playwright mit Chromium (global oder lokal) und Netz zu
`cdn.jsdelivr.net`. Das Ergebnis immer einmal ansehen: Schrift und Texte pruefen,
und ob Linien durch Beschriftungen laufen.

## Dateistruktur

```
~/.claude/skills/skill-creator/
├── SKILL.md
└── scripts/
    ├── publish_skill.py
    ├── test_publish_skill.py
    └── export_excalidraw.cjs
```

## Verwandt

- `lint` — prueft das Vault, in dem die Skill-Doku liegt
- `skill-builder` — archiviert am 2026-09-29 (`_archiv/skill-builder`), enthielt Aufbau und Inhalt eines Skills
