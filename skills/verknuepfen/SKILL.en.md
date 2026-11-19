---
name: verknuepfen
description: >
  Links notes in an Obsidian vault to entities (people, companies, tools, projects): adds wikilinks
  on first mentions and proposes new entities and relations.
  Use when the user says "verknuepfen", "link the note", "link entities", "knowledge graph", "new entities",
  "candidates", "interlink", after writing a vault note, and at session end before the daily note.
version: 1.2.3
user-invocable: true
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

## Vault path

`<VAULT>` in this skill stands for the path of your Obsidian vault. It is stored in `~/.config/claude-skills/einstellungen.json` under `vault`. Read it before the first access:

```bash
python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.config/claude-skills/einstellungen.json")))["vault"]))'
```

If the file or the key is missing or the value is empty, ask for the path. If the file is missing, create it with `{"vault": "<path>"}`. Otherwise set `vault` in the existing file and leave all other keys unchanged.

# Verknuepfen Skill - Knowledge Graph in the vault

You link notes to the vault's entities and propose what is missing. `scripts/verknuepfen.py` (standard library only)
does the counting and writing. You do not write links into the note text by
hand; the exceptions are listed under Rules.

## Vault

- **Path:** `<VAULT>/` (see Vault path above). The scripts read it from the setting `vault`; `--vault` wins. If neither
  is set they stop with a plain message and exit 2.
- **Work folder (optional):** setting `dienst_ordner` in `~/.config/claude-skills/einstellungen.json`, a vault-relative
  folder for work notes (e.g. `"02 Projekte/Dienst"`). Missing or empty means no note counts as work.
- **Entities:** notes with `type:` (types person, firma, werkzeug, projekt) and `aliases:`, as in Lint L1.
  Usually under `04 Ressourcen/Entitäten/`.
- **Sources:** all notes except `memory/`, `06 Archiv/`, `Briefings/`, generated files, files starting with `_`,
  `00 Kontext/Claude.MD/` and the root system files.

## Triggers

- The user says `/verknuepfen`, "link the note" or similar.
- After writing a note in the vault, on request or as the closing step of a task.
- At session end before the daily note.

## Usage

| Input | Behaviour |
|-------|-----------|
| `/verknuepfen NOTE` | Flow for one note (steps 1 to 5) |
| `/verknuepfen` | Notes this session wrote (session end) |
| `/verknuepfen kandidaten` | Step 2 only, for the whole vault: propose new entities, without `--notiz` |
| `/verknuepfen --alle` | All sources. A decision for the user, back up first (see limits) |

## Flow for one note

1. **Link entities.** First unlinked mention per entity (title and aliases), entities only:

   ```bash
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py link "<note>" --dry-run
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py link "<note>"
   ```

   `--json FILE` writes the changes and `not_written` (notes that could not be written).
2. **Candidates.** Names that appear in at least two notes without an entity and look like a company, person or
   tool are proposed as new entities. Report only, never create. `--notiz` shows only candidates that occur in that note
   (repeatable, absolute or relative to the vault); counting stays vault-wide:

   ```bash
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py kandidaten --min 2 --notiz "<note>"
   ```

   Output is at most 30 lines; `--json FILE` lists `alle_notizen` (all locations) per candidate. Use a temp file
   (`mktemp`) for it, never a fixed path. Check each proposal against the notes before naming it.
   **Day-job people** (by context employer, work, colleagues, i.e. coworkers, clients, applicants) are never proposed, even when the script lists them,
   because it filters by path only. When in doubt, leave them out.
3. **Relations.** You set the fields `kunde_von`, `nutzt` and `entschieden_in` in the frontmatter of the entity the
   relation starts from yourself with Edit (value as `[[target]]`, see lint L4), but only where a note proves the
   relation with a sentence; name the sentence and location (file, line). Anything unclear is a proposal, not a
   change. The script sets no relations.
4. **Semantic neighbours.** Notes with similar content, found locally through qmd (vector search, no remote). For each note written:

   ```bash
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py nachbarn --vault <vault> "<note>"
   ```

   Output: up to five lines `Verwandt: [[Name]] (0.xx)` or one line `Schritt 4 übersprungen: <reason>`; exit 0 in both
   cases, exit 1 if the note is not in the vault, exit 2 if the vault or the folder of the `--json` file is missing.
   The command never writes to the note. Suggestions go into the report only; you set no link from them. Links
   stay with step 1 and the reader's judgement. Notes already linked, the note itself and excluded folders do not
   appear. Nothing below the threshold (`graph.schwelle`) is shown; if it is `null`, step 4 is off. Daily notes and
   technical check notes show up often; check that a hit holds up on content before you name it.
5. **Report.** One line per change (`note:line [[link]]`), one line per proposal.

## At session end

The same steps for every note the session wrote, collected once, before the daily note; step 2 with `--notiz` and
all those notes in one call.

Refresh the index after step 1 (`link`), so the freshly linked notes are in it, and before step 4:

```bash
python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py index --vault <vault>
```

This writes `~/.config/qmd/<index>.yml` from the settings, runs `qmd update`, `embed` and `cleanup`, then checks the
index for excluded paths and foreign collections. The first run is slow (about 24 minutes for 1,300 notes); after
that only changed notes are processed (seconds). The first run takes longer than the Bash tool's time limit: start it
in the background or ask the user to start it in a terminal. Then step 4 for each note. If a foreign qmd configuration
already exists under that name (another collection, another `path`, own keys such as `global_context`), `index` stops
with exit 1 and leaves it untouched; choose another `graph.qmd_index` or back the file up yourself.

## Rules

- Candidates are only proposed, never created.
- A relation needs a proving sentence and location, otherwise it is a proposal. It is set with Edit in the
  frontmatter (step 3), in the three relation fields only.
- Work boundary: in notes under the work folder (`dienst_ordner`), entities of type `person` are never linked.
- Do not set links in the note text by hand, use `link`. The script protects frontmatter, code blocks, quotes, inline code, existing
  links, URLs, hashtags, paths, domains and comments, and keeps tables intact.
- Respect the block list: a removed link does not come back (`~/.claude/hooks/auto-link-sperre.json`). Every run
  records all entities linked in the note, hand-set links included; if one is removed later it stays blocked. If the
  user wants it back, they set it by hand. On their explicit word you may set it by hand; the hook does not remove it,
  it just sets no new one. Never edit the block file to force a link.
- The file lock on the state file waits at most 10 seconds (`VERKNUEPFEN_SPERRFRIST`, seconds, capped at 12), then the run aborts with "Sperre belegt" and leaves the note unchanged.
- Privacy for step 4: no remote embedding. Folders from `graph.ausschluss` (default `03 Bereiche/Finanzen/**`,
  `memory/**`; add the work folder yourself, e.g. `02 Projekte/Dienst/**`) plus fixed `.obsidian/**`, `.trash/**`, `07 Anhaenge/**` get no
  vectors; an excluded note is not queried. A qmd configuration with a foreign model (`http(s)` or a model without
  `hf:`) blocks `index` and `nachbarn`. Only the user changes `einstellungen.json` (exclusions, threshold); at most
  you suggest a change.
- Change notes only through `link`, with exactly two exceptions by Edit: the relation fields `kunde_von`, `nutzt`
  and `entschieden_in` in an entity's frontmatter when a note proves the relation (step 3), and a blocked link on the
  user's explicit word (block list). Only the script writes the block file under `~/.claude/hooks/`. Otherwise write
  nothing outside the vault except temp files (`mktemp`); exception `index`: it writes `~/.config/qmd/<index>.yml`
  and the qmd cache under `~/.cache/qmd`.

## Step 4: setup and settings

- Install: `npm install -g @tobilu/qmd@2.8.3` (npm 11 blocks install scripts, qmd works anyway), Python 3.13+,
  Node 22+. The first `index` run downloads the model (embeddinggemma-300M, about 330 MB) once.
- Queries go through `scripts/qmd_vektor.mjs` (qmd SDK `store.searchVector`, embedding model only, about 2 s per
  query), not `qmd vsearch`: that loads a second model for query expansion on every call, and its score is then no
  longer a pure cosine.
- Settings: `~/.config/verknuepfen/einstellungen.json` (path via `VERKNUEPFEN_EINSTELLUNGEN`), read fresh on every
  run. Keys under `graph`: `ausschluss` (list, replaces the default entirely, so list every pattern), `schwelle`
  (a number with a decimal point, e.g. `0.37`; `null` = step 4 off), `max_nachbarn` (5), `qmd_index` (`vault`),
  `qmd_frist` (30 s). A value of the wrong type does not count: the default applies, with a warning.
- Calibrating the threshold: `python3 -I ~/.claude/skills/verknuepfen/scripts/eichen.py --vault <vault> <pairs.md>`
  with lines `- [[A]] | [[B]] | verwandt|nicht`; `--einstellungen <file>` reads another settings file instead of the
  default. Prints scores, threshold and hit rate, writes nothing. The user enters the
  threshold in `einstellungen.json`. The pair list is private and does not belong in the skill.
- Known limit: the top five hits almost always lie above the threshold, so it rarely cuts anything.

## Limits and deviations

- Lint L1 reports every mention outside code, frontmatter, links and URLs. `/verknuepfen` additionally protects
  headings, quotes and callouts, indented code, hashtags, paths, domains, comments, reference links and footnotes, plus
  `00 Kontext/Claude.MD/` and the root system files. `link` also deliberately does not fix: blocked
  entities (block list) and links with an alias in table rows. An L1
  finding therefore does not mean `link` fixes it.
- The hook `~/.claude/hooks/auto-link-entities.py` is active only after the swap. The old `auto-link-notes.py` keeps
  running until then. The user approves the swap; in `~/.claude/settings.json` under `hooks.PostToolUse`
  (matcher `Write|Edit`) the command is replaced by:

  ```json
  "command": "python3 \"$HOME/.claude/hooks/auto-link-entities.py\" 2>/dev/null || true"
  ```

- A full run `link --alle` is a decision for the user, with a vault backup first. The user makes the backup. Or, on
  their word, you copy the vault to the place they name; that is the second exception to "write nothing outside the
  vault" and applies to exactly that place. Show it with `--dry-run` first. The output is about 1,200 lines, so
  write it with `--json` to a temp file and evaluate the file instead of reading the output:

  ```bash
  out="$(mktemp)"
  python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py link --alle --dry-run --json "$out" | tail -n 1
  ```

  While it runs (backup, dry run and `link --alle`), no other session writes to the vault; otherwise its change is
  missing from the backup, and notes changed since they were read stay unwritten.

## Tests

```bash
python3 -I -m unittest discover -s ~/.claude/skills/verknuepfen/scripts
```
