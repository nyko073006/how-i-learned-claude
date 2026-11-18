---
name: lint
description: >
  Woechentlicher Gesundheits-Check eines Obsidian-Vaults. Findet verwaiste Notizen,
  fehlende Verknuepfungen, volle Inbox, veraltete Projekte und Projekt-Compliance-Drift
  (Whitelist-Verstoesse, kaputte Wikilinks, Naming-Konventionen) und Luecken im Knowledge Graph
  (unverlinkte Erwaehnungen von Entitaeten, fehlende Rueckverweise, Widersprueche in Beziehungen,
  Grenze Dienstliches) und schlaegt Korrekturen vor.
  Verwenden wenn der Nutzer "lint", "vault check", "pruefe das vault", "gesundheitscheck",
  "verwaiste notizen", "orphans", "projekt-compliance", "projekt-check", "graph-check",
  "unverlinkte erwaehnungen", "entitaeten pruefen" sagt.
version: 1.7.3
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

## Vault-Pfad

`<VAULT>` steht in diesem Skill für den Pfad deines Obsidian-Vaults. Er steht in `~/.config/claude-skills/einstellungen.json` unter `vault`. Lies ihn vor dem ersten Zugriff:

```bash
python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.config/claude-skills/einstellungen.json")))["vault"]))'
```

Fehlt die Datei oder der Schlüssel, frag nach dem Pfad. Fehlt die Datei, lege sie mit `{"vault": "<Pfad>"}` an. Fehlt nur der Schlüssel, ergänze ihn in der bestehenden Datei und lass alle anderen Schlüssel unverändert.

# Lint Skill — Vault Gesundheits-Check

Du pruefst den Vault auf Gesundheit und schlaegst Verbesserungen vor.
Komplementaer zum `/ingest` Skill: Waehrend Ingest einzelne Notizen verarbeitet,
pruefst du das gesamte Vault systematisch.

## Vault

- **Pfad:** `<VAULT>/` (siehe Vault-Pfad oben)
- **Struktur:** PARA (00 Kontext, 01 Inbox, 02 Projekte, 03 Bereiche, 04 Ressourcen, 05 Daily Notes, 06 Archiv, 07 Anhaenge)
- **Log:** `<VAULT>/log.md`
- **Reports:** `<VAULT>/Lint-Reports/`
- **Dienstordner (optional):** Einstellung `dienst_ordner` in `~/.config/claude-skills/einstellungen.json`,
  ein Vault-relativer Ordner fuer dienstliche Notizen (z. B. `"02 Projekte/Dienst"`). Fehlt er oder ist
  er leer, laufen alle Pruefungen auf dienstliche Notizen nicht (L1-Ausnahme und L5 entfallen).

## Aufruf

| Input | Verhalten |
|-------|-----------|
| `/lint` | Vollstaendiger Vault-Check (alle 6 Schritte) |
| `/lint orphans` | Nur verwaiste Notizen suchen (Schritt 1) |
| `/lint inbox` | Nur Inbox pruefen (Teil von Schritt 3) |
| `/lint projekte` | Nur Projekt-Compliance-Sektion (Schritt 4) |
| `/lint graph` | Nur Knowledge-Graph-Pruefungen L1 bis L5 (Schritt 4b) |
| `/lint index` | Nur Vault-Index regenerieren (Schritt 6) |

## Pruefskript (seit 1.5.0)

Die Zaehlarbeit der Schritte 1, 3 und 4 und die Daten fuer Schritt 6 macht
`scripts/vault_lint.py` (nur Python-Standardbibliothek, aendert nichts). Immer zuerst
laufen lassen, statt selbst zu globben und zu greppen; die volle Ausgabe gehoert in eine
Datei im Scratchpad, nicht in den Kontext:

```bash
python3 -I ~/.claude/skills/lint/scripts/vault_lint.py --json <scratchpad>/lint.json
```

- **stdout:** kurze Zusammenfassung, nach Ordnern gruppiert. **JSON:** alle Funde mit Pfad
  und Zeile, unter `index` die Daten fuer Schritt 6, unter `counts` die Zahlen.
- **Optionen:** `--teil orphans|inbox|projekte|graph|index` passend zum Aufruf, `--vault <pfad>`
  (Vorgabe: Einstellung `vault`; fehlt beides, bricht das Skript mit Klartext und Exit 2 ab),
  `--heute JJJJ-MM-TT` (Stichtag fuer Altersangaben).
- **Links wie Obsidian:** `[[Name]]`, `[[Ordner/Name|Alias]]`, `#Abschnitt`, `^Block`,
  Einbettungen, Markdown-Links (auch `[Text](url)` ohne Endung) und Links im Frontmatter;
  Gross/Klein egal. Links in Codebloecken und Inline-Code zaehlen nicht. Ein Punkt im Namen
  (`… 1.4.0`, `terminplaner-app.de`) ist keine Dateiendung. Abgeglichen am 15.10.2026 gegen
  Obsidians `app.metadataCache`: Waisen, Notizzahl und offene Links deckungsgleich.
- **Links aus `Index.md` und `Lint-Reports/` zaehlen nicht als eingehend:** beide schreibt
  der Lint selbst, sonst rettete der eigene Report die Waisen, die er meldet.
- **Schritt 2 bleibt Handarbeit.** Das Skript liefert je Waise unter `mentions` die Stellen,
  an denen sie als Text oder Pfad erwaehnt, aber nicht verlinkt ist. Das sind die
  naheliegenden Stellen fuer einen Link.
- **Knowledge Graph (seit 1.6.0):** Unter `graph` stehen Register (`entities`) und die Funde
  `L1` bis `L5` (Schritt 4b). Regeln aus der Spec
  `03 Bereiche/Claude Code/2026-11-15 Spec Knowledge Graph.md`; jede Pruefung hat einen
  Fehler- und einen sauberen Testvault unter `scripts/testdaten/L<n>/`.
- **Nach Korrekturen erneut laufen lassen.** Zahlen „nach Korrekturen“ kommen aus dem
  zweiten Lauf, nicht aus dem Kopf.
- **Tests:** `python3 -I -m unittest discover -s ~/.claude/skills/lint/scripts`

## Workflow

### Schritt 1: Verwaiste Notizen finden

1. **Alle Notizen auflisten** — alle `*.md` im Vault ausser `07 Anhaenge/` (Pruefskript)
2. **Fuer jede Notiz pruefen** — Wird sie von mindestens einer anderen Notiz verlinkt?
   Links aus `Index.md` und `Lint-Reports/` zaehlen nicht (siehe Pruefskript)
3. **Ausnahmen** — Diese Dateien sind KEINE Orphans, auch ohne eingehende Links:
   - Daily Notes (`05 Daily Notes/`)
   - `CLAUDE.md`, `AGENTS.md`, `log.md`, `OTHER_AI.md`, `Index.md` in der Vault-Wurzel
   - Start-Dateien die gleich heissen wie ihr Ordner (z.B. `Claude Code/Claude Code.md`)
   - Dateien in `00 Kontext/`
   - `memory/` (eigener Einstieg `memory/MEMORY.md`) und `06 Archiv/`
   - Maschinen-geschriebene Dateien: `Briefings/` (Morgenbriefings) und `* Tasks.md` direkt
     in der Vault-Wurzel (Aufgabenlisten von Obsidian-Plugins)
   - `frag_*.md` ueberall: Tabellenstuecke, die ein Montageskript einsetzt (z. B. ein
     Finanzmodell). Ohne Unterstrich gilt die Ausnahme nicht
4. **Ergebnis zeigen:**
   ```
   Verwaiste Notizen (keine eingehenden Links):
   - Setup Web Clipper.md (04 Ressourcen/Werkzeuge/Recherche/)
   - Brain Dump.md (01 Inbox/)
   
   3 von 28 Notizen sind verwaist.
   ```

### Schritt 2: Fehlende Verknuepfungen vorschlagen

1. **Fuer jede verwaiste Notiz** — Kernthemen extrahieren und Vault nach Treffern durchsuchen
2. **Auch gut vernetzte Notizen stichprobenartig pruefen** — Gibt es offensichtliche
   thematische Ueberlappungen ohne bestehenden Link?
3. **Vorschlaege praesentieren:**
   ```
   Fehlende Links:
   - [[Setup Web Clipper]] koennte verlinkt werden von [[Obsidian Einrichtung]]
     (beide erwaehnen Obsidian Web Clipper)
   - [[Memory-Architektur]] koennte verlinkt werden von [[Checkliste v14]]
     (beide erwaehnen CLAUDE.md und Auto Memory)
   ```
4. **Fuer jeden Vorschlag fragen** — "Soll ich diesen Link setzen? (ja/nein)"

### Schritt 3: Vault-Hygiene pruefen

Fuehre diese Checks durch und sammle die Ergebnisse:

**3a) Inbox-Check:**
- Zaehle Notizen in `01 Inbox/`
- Warnung wenn > 5 Notizen (Inbox sollte regelmaessig geleert werden)

**3b) Projekt-Status:**
- Alle PMO HUBs in `02 Projekte/` mit `status: abgeschlossen` im Frontmatter finden
- Vorschlagen: "Diese Projekte koennten nach 06 Archiv/ verschoben werden"

**3c) Frontmatter-Check:**
- Notizen ohne YAML-Frontmatter (`---`) identifizieren
- Notizen ohne `tags` im Frontmatter identifizieren
- Ausgenommen sind die Maschinen-geschriebenen Dateien aus Schritt 1 (`Briefings/`, `* Tasks.md` in der Vault-Wurzel),
  `memory/` (Memory-Dateien tragen `name`/`description` statt `tags`), `06 Archiv/` (Sicherungen
  bleiben bytegleich) und `frag_*.md` (ein Frontmatter wanderte mit in die Montage)

**3d) Synthese-Seiten-Check:**
- Alle Unterordner in `04 Ressourcen/` auflisten
- Pruefen ob jeder Ordner eine gleichnamige Start-Datei hat
- Fehlende Start-Dateien melden

**3e) Wurzel und Bereiche (Info):**
- Dateien in der Vault-Wurzel ausser den Systemdateien und `* Tasks.md` (z.B. liegengebliebene
  Handoffs, Bilder, leere `.base`-Dateien)
- Ordner in der Vault-Wurzel ausser PARA, `Briefings/`, `Lint-Reports/` und `memory/`
- Bereiche in `03 Bereiche/` ohne Start-Datei (`<Bereich>.md` oder `<Bereich> - Uebersicht.md`)

**Ergebnis zeigen:**
```
Vault-Hygiene:
  ✓ Inbox: 2 Notizen (OK)
  ⚠ Projekte: 1 abgeschlossenes Projekt nicht archiviert
  ✗ Frontmatter: 3 Notizen ohne Tags
  ✓ Synthese-Seiten: Alle Ressourcen-Ordner haben Start-Dateien
```

### Schritt 4: Projekt-Compliance pruefen

Iteriere ueber alle echten Projekt-Ordner und pruefe gegen die Governance
aus `00 Kontext/Projekt-Struktur.md` (File-Whitelist + Naming-Konventionen + Templates).

**Container-Ordner-Erkennung (Pflicht vor 4a-4g):**

Ordner in `02 Projekte/` deren Name mit Underscore beginnt (z.B. `_Beispiel-Container/`, `_Kunde-X/`)
sind **Container** — Sammelordner fuer mehrere zusammengehoerende Sub-Projekte (z.B. alle
Kundenprojekte eines Mandanten). Container haben selbst KEINEN PMO HUB und KEINE Governance.

Logik:

1. Pro Eintrag in `02 Projekte/*/`:
   - Wenn Ordnername mit `_` beginnt → **Container**: ueberspringe Pflicht-Dateien-Pruefung
     fuer den Container selbst. Iteriere stattdessen ueber `<Container>/*/` und behandle
     jeden direkten Sub-Ordner als eigenes Projekt (rekursiv NUR diese eine Ebene).
   - Sonst → **Projekt**: pruefe wie bisher.
2. Container-Ordner werden im Report unter "Container" ausgewiesen, nicht unter
   "Compliance-Verstoesse".
3. Sub-Projekte im Container muessen die volle Struktur haben (PMO HUB + Governance +
   Subordner) — die Konvention vererbt sich nicht abwaerts.
4. Zusaetzliche Container-spezifische Warnung: Wenn ein Container leer ist oder nur
   eine Ebene hat (also ein einziges Sub-Projekt), Hinweis "Container `_X` enthaelt
   nur Y Sub-Projekte — ist die Container-Ebene noch noetig?"

**4a) Whitelist-Check Projektwurzel**

Erlaubte Files im Projekt-Wurzelordner:
- `<Projekt> - PMO HUB.md` (Pflicht)
- `Projekt-Governance.md` (Pflicht)
- `Financials.md` (opt-in)
- `Fehlerlog.md` (erlaubt, aber keine Pflichtdatei: fehlt sie, gibt es keine Warnung)

Files im Wurzel die diesem Muster nicht entsprechen → Warnung.
Spezialfall: `README.md` im Projektwurzel ist explizit verboten — Hinweis "PMO HUB ist die Landing Page".

**4b) Pflicht-Dateien existieren**

Pruefe pro Projekt:
- Existiert `* - PMO HUB.md`? Falls nicht → Error
- Existiert `Projekt-Governance.md`? Falls nicht → Error
- Existieren Subordner `Meetings/`, `Decisions/`, `Research/`, `assets/`? Falls nicht → Warnung
- `Fehlerlog.md` hier NICHT pruefen: fehlt sie, kein Fund (bestehende Projekte bekommen sie beim ersten Eintrag)

**4c) Naming-Konvention Hub-Datei**

Hub-Datei MUSS auf `- PMO HUB.md` enden. Andere Hub-Namen (alte `- Hub.md`, oder einfach `<Projektname>.md`)
→ Warnung mit Vorschlag fuer Umbenennung.

**4d) Markdown im falschen Ordner**

`*/Research/assets/*.md` finden — Markdown-Dateien sollten direkt in `Research/` liegen,
nur Bilder/SVG/PDF in `Research/assets/`. Markdown in anderen `assets/`-Ordnern des Projekts
meldet das Pruefskript als Hinweis (vor einem Umzug pruefen, ob ein Skript die Datei als
Quelle liest).

**4e) Kaputte Wikilinks im PMO HUB**

Aus jedem PMO HUB alle `[[...]]` extrahieren und pruefen ob die Ziel-Datei existiert
(via Glob `**/<Treffer>.md`). Tote Links → Warnung mit Pfad-Angabe.

**4f) Decisions-Frontmatter-Konsistenz**

Pruefe alle Files in `*/Decisions/` auf:
- `status: entschieden` aber `entschieden_am` leer → Warnung
- `type` fehlt oder nicht "entscheidung" → Warnung

**4g) Pre-Backlog-Items aelter als 30 Tage**

In jedem PMO HUB die Sektion "Pre-Backlog Action Items" pruefen (als Ueberschrift oder als
Absatz; gezaehlt werden offene `- [ ]` bis zur naechsten Ueberschrift).
Wenn Items vorhanden und der Hub `aktualisiert:` Datum > 30 Tage alt → Hinweis
"Backlog-Tool aktivieren oder Items pflegen?"

**Ergebnis zeigen:**

```
Projekt-Compliance:
  ✓ Whitelist: 5/6 Projekte sauber
  ✗ Whitelist: Beispiel-Projekt — README.md im Wurzel
  ✓ Pflicht-Dateien: Alle Projekte haben PMO HUB + Governance
  ⚠ Naming: 1 Projekt hat Hub ohne "- PMO HUB" Suffix
  ⚠ Markdown in assets/: 4 Files in 1 Projekt
  ✗ Kaputte Wikilinks: 5 Links in 1 PMO HUB
  ✓ Decisions-Frontmatter: alle konsistent
  ⚠ Pre-Backlog: 1 Projekt mit Items > 30 Tage alt
```

### Schritt 4b: Knowledge Graph pruefen (L1 bis L5)

Entitaet = Notiz mit Frontmatter `type:` genau `person`, `firma`, `projekt` oder `werkzeug`
(Ablage `04 Ressourcen/Entitäten/`, Projekte sind ihr PMO HUB). Nicht im Register: Dateien mit
`_` am Anfang, `06 Archiv/`, `Briefings/`, `memory/`. Namen sind Titel, Aliase und beim Hub der
Projektname ohne ` - PMO HUB`.

| Nr | Pruefung | Fund |
|---|---|---|
| L1 | Unverlinkte Erwaehnungen | Notiz nennt eine Entitaet (Gross/Klein egal, ganzes Wort, Bindestrich gehoert zum Wort), verlinkt sie aber nirgends. Ein Fund je Notiz und Entitaet, erste Stelle. Personen in Notizen aus dem Dienstordner (Einstellung `dienst_ordner`) zaehlen nicht. Nicht in Code, Links, URLs, Frontmatter, `memory/`, `06 Archiv/`, `Briefings/`, generierten Dateien |
| L2 | Entitaeten ohne eingehenden Link | auch wenn die Waisen-Ausnahmen greifen |
| L3 | Fehlende Rueckverweise | Entitaet A verlinkt B im Text, B verlinkt A weder im Text noch im Frontmatter |
| L4 | Widersprueche | Feld passt nicht zum Typ (`kunde_von` nur person/firma nach projekt, `nutzt` nur projekt nach werkzeug, `entschieden_in` auf eine Notiz, die keine Entitaet ist), Ziel fehlt, Wert ohne `[[…]]`, gleicher Name bei zwei Entitaeten |
| L5 | Grenze Dienstliches | Entitaet vom Typ `person` mit Link in oder aus dem Dienstordner (`dienst_ordner`) oder dort abgelegt; ohne Einstellung keine Funde |

**Umgang mit Funden:**
- L4 und L5 zuerst, einzeln mit dem Nutzer klaeren. L5 heisst: Person aus dem Dienst hat im
  Graph nichts verloren, Entitaet oder Link entfernen (nur nach Rueckfrage).
- L1 ist lang, solange der Bestand nicht verknuepft ist. Im Report je Entitaet die Anzahl und
  die erste Stelle, nicht jeden Fund. Links setzen nicht von Hand im Lint, das macht der
  Skill `/verknuepfen` (Etappe 3 der Spec), sobald es ihn gibt.
- L2 und L3: Link oder Beziehung vorschlagen, einzeln bestaetigen lassen.

### Schritt 5: Report erstellen und Log aktualisieren

1. **Report als Notiz** in `Lint-Reports/` (Vault-Wurzel) ablegen, Ordner anlegen falls er
   fehlt. Nicht in `01 Inbox/`: dort zaehlt der Report als unsortierte Notiz, und beim
   Einsortieren verliert der Index seine Liste der letzten Reports.

```markdown
---
tags: [system, lint-report]
date: YYYY-MM-DD
---

# Vault Lint Report — YYYY-MM-DD

## Zusammenfassung

X von Y Notizen sind verwaist | Z fehlende Links vorgeschlagen |
Inbox: N Notizen | M Notizen ohne Frontmatter |
Projekt-Compliance: K Verstoesse in J Projekten

## Verwaiste Notizen
- ...

## Fehlende Verknuepfungen
- ...

## Vault-Hygiene
- ...

## Projekt-Compliance

### Whitelist-Verstoesse
- [Projekt X] `README.md` im Wurzel — sollte geloescht oder verschoben werden
- [Projekt Y] `notes.md` im Wurzel — gehoert in einen Subordner

### Pflicht-Dateien fehlen
- [Projekt Z] `Projekt-Governance.md` fehlt

### Naming-Konvention
- [Projekt A] Hub heisst `<Projekt>.md` statt `<Projekt> - PMO HUB.md`

### Kaputte Wikilinks
- [Projekt B, PMO HUB Zeile 88] `[[04 Ressourcen/Research/...]]` zeigt ins Leere

### Markdown in falschem Ordner
- [Projekt C] `Research/assets/01-...md` — sollte ein Level hoeher liegen

### Pre-Backlog veraltet
- [Projekt D] 5 Items aelter als 30 Tage — Backlog-Tool aktivieren?

## Knowledge Graph

N Entitaeten (person a, firma b, projekt c, werkzeug d)

- **L4 Widersprueche / L5 Grenze Dienstliches:** jeder Fund einzeln
- **L1 Unverlinkte Erwaehnungen:** n in m Notizen; je Entitaet Anzahl und erste Stelle
- **L2 Entitaeten ohne eingehenden Link:** Liste
- **L3 Fehlende Rueckverweise:** `A -> B (Z. n)`

## Empfohlene Aktionen
1. ...
```

2. **Log-Eintrag** in `log.md` ergaenzen:

```markdown
## [YYYY-MM-DD] lint | Vault Gesundheits-Check

- **Orphans:** X verwaiste Notizen gefunden
- **Fehlende Links:** Y Vorschlaege
- **Projekt-Compliance:** K Verstoesse in J Projekten
- **Korrekturen:** Z Links gesetzt, W Notizen angepasst
- **Report:** [[YYYY-MM-DD Vault Lint Report]]
```

3. **Korrekturen anbieten** — Fuer jeden Finding fragen ob korrigiert werden soll.
   Einzeln abarbeiten, nicht alles auf einmal.

### Schritt 6: Vault-Index regenerieren

Erzeuge eine vorkompilierte `Index.md` im Vault-Wurzelverzeichnis. Sie ist **das
Wiki-Cover des Vaults** — Claude liest sie beim Session-Start, statt das ganze Vault
zu durchsuchen. Token-Effizienz statt Echtzeit-Suche (Karpathy LLM Wiki Pattern).

**Pfad:** `<VAULT>/Index.md`

**Wichtig:** Datei wird bei jedem Lauf vollstaendig **ueberschrieben** — keine
Dataview-Queries, sondern statische Wikilinks (Claude rendert kein Dataview).

**Inhalt der Index.md:**

```markdown
---
tags: [system, vault-index]
auto_generated: true
generated_at: YYYY-MM-DD HH:MM
generated_by: /lint
source: claude
chat_url: unbekannt
---

> [!warning] Auto-generiert von `/lint`
> Diese Datei wird bei jedem Lint-Lauf neu erzeugt. Manuelle Aenderungen gehen verloren.
> Quelle der Wahrheit sind die einzelnen Notizen, nicht dieser Index.

# Vault Index

Cover-Seite des Vaults. Claude liest diese Seite beim Session-Start, um das Vault
ohne Volltextsuche zu navigieren.

## Aktive Projekte (`02 Projekte/`)

Glob `02 Projekte/*/` — pro Ordner ein Eintrag mit Wikilink zur PMO HUB Datei plus
`status` und `phase` aus dem Hub-Frontmatter.

- [[<Projekt> - PMO HUB]] — `aktiv` | `umsetzung` | aktualisiert YYYY-MM-DD
- ...

## Bereiche (`03 Bereiche/`)

Glob `03 Bereiche/*/` — pro Ordner ein Eintrag mit Wikilink zur gleichnamigen Start-Datei
(falls vorhanden) oder Ordnerverweis.

- [[Skills]] — Claude Code Skill Doku
- [[Lifelong Learning]]
- ...

## Synthese-Seiten (`04 Ressourcen/`)

Glob `04 Ressourcen/*/` — pro Themenordner die gleichnamige Start-Datei (Synthese-Seite
nach Variante B des LLM Wiki Patterns).

- [[Claude Code]] — Synthese aller Claude-Code-Notizen
- [[Perplexity]]
- ...

## Kontext (`00 Kontext/`)

Alle Markdown-Dateien direkt in `00 Kontext/` (rekursiv ohne Subordner-Inhalte).

- [[Über mich]]
- [[Branding]]
- [[Schreibstil]]
- [[ICP]]
- [[Angebot]]
- [[Projekt-Struktur]]

## Letzte Daily Notes

Letzte 5 Dateien aus `05 Daily Notes/`, sortiert absteigend nach Dateiname.

- [[2026-05-01]]
- [[2026-04-30]]
- ...

## Letzte Lint-Reports

Letzte 3 Dateien `* Vault Lint Report*` aus `Lint-Reports/`, sortiert absteigend.

- [[YYYY-MM-DD Vault Lint Report]]
- ...

## Vault-Statistik

- Notizen gesamt: N
- Verwaiste Notizen (letzter Lint): X
- Aktive Projekte: K
- Inbox-Stand: N Eintraege
```

**Generierungs-Regeln:**

1. **Pro Sektion:** Glob laufen lassen, Frontmatter lesen wo relevant (`status`, `phase`,
   `aktualisiert` aus PMO HUB-Files), als Wikilink-Liste schreiben.
2. **Wikilink-Form:** Nur den Notiz-Namen ohne Ordner-Pfad in `[[ ]]` — Obsidian-Konvention.
3. **Sortierung:** Aktive Projekte: nach `aktualisiert` absteigend. Daily Notes/Lint-Reports:
   nach Dateiname absteigend. Bereiche/Synthese/Kontext: alphabetisch.
4. **Filter:** Nur PMO HUB-Files mit `status: aktiv` listen — abgeschlossene/pausierte ueberspringen
   (sie sind im Archiv oder im Hub-Frontmatter sichtbar).
5. **Statistik-Werte:** aus Schritt 1 (Orphans) und 3 (Inbox) wiederverwenden, nicht neu zaehlen
   (`counts` und `index` im JSON des Pruefskripts; nach Korrekturen aus dem zweiten Lauf).
6. **Atomic Write:** Erst kompletten Inhalt aufbauen, dann mit `Write` ueberschreiben — keine
   inkrementellen Edits. Index ist immer ein Snapshot.
7. **Bei `/lint index`:** Nur Schritt 6 ausfuehren (Statistik-Werte dann aus letztem Report ziehen
   oder als "—" markieren wenn nicht vorhanden).

**Log-Eintrag fuer Schritt 6** (in den bestehenden Log-Block aus Schritt 5 einbetten):

```markdown
- **Index:** Index.md regeneriert (K aktive Projekte, M Synthese-Seiten)
```

## Regeln

1. **IMMER fragen** bevor Notizen veraendert werden
2. **NIE loeschen** — bestehende Inhalte werden nur ergaenzt
3. **07 Anhaenge/ komplett ignorieren** — keine Bilder/PDFs durchsuchen
4. **Daily Notes sind keine Orphans** — sie stehen fuer sich
5. **Report ist sachlich** — keine Wertungen, nur Fakten und Vorschlaege
6. **Log ist append-only** — nie bestehende Eintraege aendern
7. **Sprache: Deutsch** — alle Ausgaben auf Deutsch
