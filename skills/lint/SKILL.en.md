---
name: lint
description: >
  Weekly health check for an Obsidian vault. Finds orphaned notes,
  missing wikilinks, full inbox, stale projects, and project compliance drift
  (whitelist violations, broken wikilinks, naming conventions) and gaps in the knowledge graph
  (unlinked mentions of entities, missing backlinks, contradicting relations, work boundary)
  and suggests fixes.
  Use when the user says "lint", "vault check", "check the vault", "health check",
  "orphans", "project-compliance", "project-check", "graph check", "unlinked mentions".
version: 1.7.4
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

# Lint Skill — Vault Health Check

Check the vault for health and suggest improvements.
Complementary to the `/ingest` skill: while ingest processes individual notes,
this skill checks the entire vault systematically.

German version: [SKILL.md](SKILL.md)

## Vault

- **Path:** `<VAULT>/` (see Vault path above)
- **Structure:** PARA (00 Kontext, 01 Inbox, 02 Projekte, 03 Bereiche, 04 Ressourcen, 05 Daily Notes, 06 Archiv, 07 Anhaenge)
- **Log:** `<VAULT>/log.md`
- **Work folder (optional):** setting `dienst_ordner` in `~/.config/claude-skills/einstellungen.json`, a vault-relative folder for work notes (e.g. `"02 Projekte/Dienst"`). Missing or empty means every check on work notes is off (the L1 exception and L5).

## Invocation

| Input | Behavior |
|-------|----------|
| `/lint` | Full vault check (all 6 phases) |
| `/lint orphans` | Only find orphans (phase 1) |
| `/lint inbox` | Only check inbox (part of phase 3) |
| `/lint projekte` | Only project-compliance section (phase 4) |
| `/lint graph` | Only knowledge-graph checks L1 to L5 (phase 4b) |
| `/lint index` | Only regenerate vault index (phase 6) |

## Checker script (since 1.5.0)

`scripts/vault_lint.py` (Python standard library only, read-only) does the counting for phases 1, 3 and 4 and collects the data for phase 6. Always run it first instead of globbing and grepping by hand, and send the full output to a scratchpad file:

```bash
python3 -I ~/.claude/skills/lint/scripts/vault_lint.py --json <scratchpad>/lint.json
```

- stdout is a short summary grouped by folder; the JSON holds every finding with path and line, `index` for phase 6 and `counts`.
- Options: `--teil orphans|inbox|projekte|graph|index`, `--vault <path>` (default: setting `vault`; if neither is set the script stops with a plain message and exit 2), `--heute YYYY-MM-DD`.
- Links resolve the way Obsidian resolves them: `[[Name]]`, `[[Folder/Name|Alias]]`, headings, blocks, embeds, Markdown links (including `[text](url)` without an extension) and frontmatter links, case-insensitive. Links inside code blocks and inline code do not count; a dot in a name (`… 1.4.0`) is not a file extension. Cross-checked on 2026-10-15 against Obsidian's `app.metadataCache`: orphans, note count and unresolved links matched.
- Links from `Index.md` and `Lint-Reports/` do not count as incoming, because lint writes both itself; otherwise its own report would rescue the orphans it reports.
- Phase 2 stays manual. For each orphan the script lists, under `mentions`, the places that name it as text or path without linking it.
- Knowledge graph (since 1.6.0): `graph` holds the entity register and findings `L1` to `L5` (phase 4b). Rules come from the spec `03 Bereiche/Claude Code/2026-11-15 Spec Knowledge Graph.md`; every check has a faulty and a clean test vault under `scripts/testdaten/L<n>/`.
- Run it again after fixes; numbers "after fixes" come from the second run.
- Tests: `python3 -I -m unittest discover -s ~/.claude/skills/lint/scripts`

## Workflow (6 phases plus 4b)

1. **Find orphans** — Notes without incoming links (exceptions: Daily Notes, `CLAUDE.md`, `AGENTS.md`, `log.md`, `OTHER_AI.md`, `Index.md`, folder start files, `00 Kontext/`, `memory/`, `06 Archiv/` and machine-written files: `Briefings/`, `* Tasks.md` in the vault root)
2. **Suggest missing links** — Theme matching between notes, individual confirmation instead of auto-apply
3. **Vault hygiene** — Inbox count, closed projects (`status: abgeschlossen` in the PMO HUB), frontmatter (machine-written files and `memory/` excluded), synthesis pages, plus info on stray files in the vault root and areas without a start file
4. **Project compliance** (since v1.2.0):
   - Whitelist project root (only PMO HUB, Governance, Financials, Fehlerlog allowed; `Fehlerlog.md` is allowed but not required, no warning when it is missing)
   - `README.md` in project root forbidden
   - Required files exist (PMO HUB, Projekt-Governance.md; `Fehlerlog.md` is not checked)
   - Naming convention `* - PMO HUB.md`
   - Markdown in `*/Research/assets/` (should be one level higher); Markdown in other `assets/` folders is reported as a hint
   - Broken wikilinks in PMO HUB
   - Decisions frontmatter consistency
   - Pre-Backlog items older than 30 days (section as heading or paragraph, open `- [ ]` up to the next heading)
4b. **Knowledge graph** (since v1.6.0). An entity is a note whose frontmatter `type:` is exactly `person`, `firma`, `projekt` or `werkzeug` (projects are their PMO HUB; not `_*` files, `06 Archiv/`, `Briefings/`, `memory/`). Names are title, aliases and, for a hub, the project name without ` - PMO HUB`.
   - L1 Unlinked mentions: a note names an entity (case-insensitive, whole word, a hyphen belongs to the word) and never links it; one finding per note and entity; persons in notes from the work folder (setting `dienst_ordner`) do not count. Code, links, URLs, frontmatter, `memory/`, `06 Archiv/`, `Briefings/` and generated files are skipped
   - L2 Entities without an incoming link, regardless of orphan exceptions
   - L3 Missing backlinks: entity A links B in the body, B links A neither in body nor frontmatter
   - L4 Contradictions: field does not fit the type (`kunde_von` person/firma to projekt, `nutzt` projekt to werkzeug, `entschieden_in` to a note that is no entity), missing target, value without `[[…]]`, same name on two entities
   - L5 Work boundary: entity of type `person` linked to or from the work folder (`dienst_ordner`) or stored there; no findings without the setting
   - Handle L4 and L5 first, one by one. L1 stays long until the vault is linked; report count and first place per entity. Linking is the job of the `/verknuepfen` skill (stage 3 of the spec)
5. **Report + log** — Markdown report in `Lint-Reports/` at the vault root (since v1.4.0; not the inbox, where it would count as an unsorted note), append-only log entry in `log.md`
6. **Regenerate vault index** (since v1.3.0) — Pre-compiles `Index.md` at the vault root: active projects, areas, synthesis pages, context files, last 5 daily notes, last 3 lint reports, vault stats. Claude reads this page on session start instead of full-text searching the vault (Karpathy LLM Wiki Pattern: pre-processing over real-time search). File is overwritten on every run — no Dataview, only static wikilinks. See German [SKILL.md](SKILL.md) phase 6 for the full template and generation rules.

## Rules

1. **ALWAYS ask** before changing notes
2. **NEVER delete** — only augment existing content
3. **Ignore 07 Anhaenge/ completely** — no images/PDFs searched
4. **Daily Notes are not orphans** — they stand alone
5. **Report is factual** — no judgments, only facts and suggestions
6. **Log is append-only** — never change existing entries
7. **Language: German default** (skill output and report)
