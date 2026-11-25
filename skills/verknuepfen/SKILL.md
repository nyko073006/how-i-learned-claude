---
name: verknuepfen
description: >
  Verknuepft Notizen in einem Obsidian-Vault mit Entitaeten (Personen, Firmen, Werkzeuge, Projekte):
  setzt Wikilinks auf erste Erwaehnungen, schlaegt neue Entitaeten und Beziehungen vor.
  Verwenden wenn der Nutzer "verknuepfen", "verlinke die notiz", "entitaeten verlinken", "link entities",
  "knowledge graph", "neue entitaeten", "kandidaten", "link note", "interlink" sagt, nach dem Schreiben
  einer Vault-Notiz und am Session-Ende vor der Daily Note.
version: 1.2.4
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

Fehlt die Datei oder der Schlüssel oder ist der Wert leer, frag nach dem Pfad. Fehlt die Datei, lege sie mit `{"vault": "<Pfad>"}` an. Sonst trag den Pfad unter `vault` in die bestehende Datei ein und lass alle anderen Schlüssel unverändert.

# Verknuepfen Skill - Knowledge Graph im Vault

Du verlinkst Notizen mit den Entitaeten des Vaults und schlaegst vor, was fehlt. Die Zaehl- und Schreibarbeit macht
`scripts/verknuepfen.py` (nur Standardbibliothek). Links im Notiztext schreibst du nicht von Hand; die Ausnahmen
stehen unter Regeln.

## Vault

- **Pfad:** `<VAULT>/` (siehe Vault-Pfad oben). Die Skripte lesen ihn selbst aus der Einstellung `vault`; `--vault` geht vor.
  Fehlt beides, brechen sie mit Klartext und Exit 2 ab.
- **Dienstordner (optional):** Einstellung `dienst_ordner` in `~/.config/claude-skills/einstellungen.json`, ein
  Vault-relativer Ordner fuer dienstliche Notizen (z. B. `"02 Projekte/Dienst"`). Fehlt er oder ist er leer, gilt keine
  Notiz als dienstlich.
- **Entitaeten:** Notizen mit `type:` (Typen person, firma, werkzeug, projekt) und `aliases:`, siehe Lint L1.
  Ablage meist `04 Ressourcen/Entitäten/`.
- **Quellen:** alle Notizen ausser `memory/`, `06 Archiv/`, `Briefings/`, generierten Dateien, Dateien mit `_` am Anfang,
  `00 Kontext/Claude.MD/` und den Wurzel-Systemdateien.

## Ausloeser

- Nutzer sagt `/verknuepfen`, "verlinke die Notiz" oder aehnlich.
- Nach dem Schreiben einer Notiz im Vault, auf Wunsch oder als Abschluss des Auftrags.
- Am Session-Ende vor der Daily Note.

## Aufruf

| Input | Verhalten |
|-------|-----------|
| `/verknuepfen NOTIZ` | Ablauf fuer eine Notiz (Schritte 1 bis 5) |
| `/verknuepfen` | Notizen, die diese Session geschrieben hat (Session-Ende) |
| `/verknuepfen kandidaten` | Nur Schritt 2 fuer den ganzen Vault: neue Entitaeten vorschlagen, ohne `--notiz` |
| `/verknuepfen --alle` | Alle Quellen. Eine Entscheidung des Nutzers, vorher Sicherung (siehe Grenzen) |

## Ablauf fuer eine Notiz

1. **Entitaeten verlinken.** Erste unverlinkte Erwaehnung je Entitaet (Titel und Aliase), nur Entitaeten:

   ```bash
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py link "<Notiz>" --dry-run
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py link "<Notiz>"
   ```

   Option `--json DATEI` schreibt Aenderungen und `not_written` (Notizen, die nicht geschrieben werden konnten).
2. **Kandidaten.** Namen, die in mindestens zwei Notizen ohne Entitaet vorkommen und wie Firma, Person oder Werkzeug
   aussehen, als neue Entitaet vorschlagen. Nur melden, nie anlegen. `--notiz` zeigt nur Kandidaten, die in dieser Notiz
   (mehrfach moeglich, absolut oder relativ zum Vault) vorkommen; gezaehlt wird weiter im ganzen Vault:

   ```bash
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py kandidaten --min 2 --notiz "<Notiz>"
   ```

   Ausgabe hoechstens 30 Zeilen; `--json DATEI` fuehrt je Kandidat `alle_notizen` mit allen Fundstellen. Fuer die Datei
   eine Temp-Datei (`mktemp`) nehmen, nie einen festen Pfad. Pruefe jeden Vorschlag mit Blick in die Notizen, bevor du ihn nennst.
   **Personen aus dem Dienst** (nach Kontext Arbeitgeber, Kollegium, also Kollegen, Klienten, Antragsteller) schlaegst du nie vor, auch wenn das Skript sie
   nennt, weil es nur nach Pfad filtert. Im Zweifel weglassen.
3. **Beziehungen.** Die Felder `kunde_von`, `nutzt` und `entschieden_in` im Frontmatter der Entitaet, von der die
   Beziehung ausgeht, setzt du selbst per Edit (Wert als `[[Ziel]]`, siehe Lint L4), aber nur, wo eine Notiz die
   Beziehung mit einem Satz belegt; Satz und Fundstelle (Datei, Zeile) nennen. Unklares ist ein Vorschlag, keine
   Aenderung. Das Skript setzt keine Beziehungen.
4. **Semantische Nachbarn.** Notizen mit aehnlichem Inhalt, lokal ueber qmd (Vektorsuche, kein Remote). Je geschriebener Notiz:

   ```bash
   python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py nachbarn --vault <Vault> "<Notiz>"
   ```

   Ausgabe: bis zu fuenf Zeilen `Verwandt: [[Name]] (0.xx)` oder eine Zeile `Schritt 4 übersprungen: <Grund>`; Exit 0
   in beiden Faellen, Exit 1, wenn die Notiz nicht im Vault liegt, Exit 2, wenn der Vault oder der Ordner der
   `--json`-Datei fehlt. Der Befehl schreibt nie in die Notiz. Die Vorschlaege kommen nur in den Bericht, du setzt daraus
   keinen Link. Links bleiben Schritt 1 und dem Urteil des Lesers. Schon verlinkte Notizen, die Notiz selbst und
   ausgeschlossene Ordner erscheinen nicht. Unter der Schwelle (`graph.schwelle`) kommt nichts; ist sie `null`, ist
   Schritt 4 aus. Daily Notes und technische Pruefnotizen tauchen oft auf; pruefe, ob der Treffer inhaltlich traegt,
   bevor du ihn nennst.
5. **Bericht.** Eine Zeile je Aenderung (`Notiz:Zeile [[Link]]`), eine Zeile je Vorschlag.

## Am Session-Ende

Dieselben Schritte fuer alle Notizen, die die Session geschrieben hat, einmal gesammelt, vor der Daily Note;
Schritt 2 mit `--notiz` und allen diesen Notizen in einem Aufruf.

Den Index nach Schritt 1 (`link`) auffrischen, damit die frisch verlinkten Notizen drin sind, und vor Schritt 4:

```bash
python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py index --vault <Vault>
```

Das schreibt `~/.config/qmd/<index>.yml` aus den Einstellungen, ruft `qmd update`, `cleanup` und `embed` und prueft den
Index danach auf ausgeschlossene Pfade und fremde Collections. Der erste Lauf dauert lange (rund 24 Minuten fuer 1.300
Notizen), laenger als die Frist des Bash-Werkzeugs: den ersten Lauf im Hintergrund starten oder den Nutzer bitten, ihn
im Terminal zu starten. Danach nur geaenderte Notizen (Sekunden). Erst dann Schritt 4 je Notiz. Liegt unter dem Namen
schon eine fremde qmd-Konfiguration (andere Collection, anderer `path`, eigene Schluessel wie `global_context`), bricht
`index` mit Exit 1 ab und laesst sie unveraendert; dann einen anderen `graph.qmd_index` waehlen oder die Datei selbst
sichern.

## Regeln

- Kandidaten nur vorschlagen, nie anlegen.
- Beziehung nur mit belegendem Satz und Fundstelle, sonst Vorschlag. Gesetzt wird sie per Edit im Frontmatter
  (Schritt 3), nur in den drei Beziehungsfeldern.
- Grenze Dienstliches: In Notizen unter dem Dienstordner (`dienst_ordner`) werden Entitaeten vom Typ `person` nie verlinkt.
- Links im Notiztext nicht von Hand setzen, sondern per `link`. Das Skript schuetzt Frontmatter, Codebloecke, Zitate, Inline-Code,
  bestehende Links, URLs, Hashtags, Pfade, Domains und Kommentare, und es haelt Tabellen heil.
- Sperrliste respektieren: Ein entfernter Link kommt nicht zurueck (`~/.claude/hooks/auto-link-sperre.json`). Jeder Lauf
  merkt sich alle in der Notiz verlinkten Entitaeten, also auch von Hand gesetzte Links; wird einer spaeter entfernt,
  bleibt er gesperrt. Will der Nutzer ihn zurueck, setzt er ihn selbst von Hand. Auf sein ausdrueckliches Wort darfst
  du ihn von Hand setzen; der Hook entfernt ihn nicht, er setzt nur keinen neuen. Nie die Sperrdatei bearbeiten, um einen Link zu erzwingen.
- Die Dateisperre auf der Zustandsdatei wartet hoechstens 10 Sekunden (`VERKNUEPFEN_SPERRFRIST`, Sekunden, auf 12 gekappt), danach bricht der Lauf mit "Sperre belegt" ab und laesst die Notiz unveraendert.
- Datenschutz Schritt 4: kein Remote-Embedding. Ordner aus `graph.ausschluss` (Vorgabe `03 Bereiche/Finanzen/**`,
  `memory/**`; den Dienstordner dort selbst eintragen, z. B. `02 Projekte/Dienst/**`) plus fest `.obsidian/**`, `.trash/**`, `07 Anhaenge/**` bekommen keine
  Vektoren; eine ausgeschlossene Notiz wird nicht abgefragt. Eine qmd-Konfiguration mit Fremdmodell (`http(s)` oder
  ein Modell ohne `hf:`) sperrt `index` und `nachbarn`. `einstellungen.json` (Ausschluss, Schwelle) aendert nur der
  Nutzer; du schlaegst hoechstens vor.
- Notizen aenderst du nur ueber `link`, mit genau zwei Ausnahmen per Edit: die Beziehungsfelder `kunde_von`,
  `nutzt` und `entschieden_in` im Frontmatter einer Entitaet, wenn eine Notiz die Beziehung belegt (Schritt 3), und
  ein gesperrter Link auf ausdrueckliches Wort des Nutzers (Sperrliste). Die Sperrdatei unter `~/.claude/hooks/` schreibt nur das Skript. Sonst nichts
  ausserhalb des Vaults schreiben ausser Temp-Dateien (`mktemp`); Ausnahme `index`: Es schreibt
  `~/.config/qmd/<index>.yml` und den qmd-Cache unter `~/.cache/qmd`.

## Schritt 4: Einrichtung und Einstellungen

- Installation: `npm install -g @tobilu/qmd@2.8.3` (npm 11 sperrt Install-Skripte, qmd laeuft trotzdem), Python ab 3.13,
  Node ab 22. Das Modell (embeddinggemma-300M, rund 330 MB) laedt der erste `index`-Lauf einmal herunter.
- Abfrage ueber `scripts/qmd_vektor.mjs` (qmd-SDK `store.searchVector`, nur das Embedding-Modell, rund 2 s je Abfrage),
  nicht ueber `qmd vsearch`: Das laedt je Abfrage ein zweites Modell zur Erweiterung, und sein Score ist dann kein
  reiner Kosinus.
- Einstellungen: `~/.config/verknuepfen/einstellungen.json` (Pfad ueber `VERKNUEPFEN_EINSTELLUNGEN`), bei jedem Lauf
  frisch gelesen. Schluessel unter `graph`: `ausschluss` (Liste, ersetzt die Vorgabe ganz, also alle Muster eintragen),
  `schwelle` (Zahl mit Punkt, z. B. `0.37`; `null` = Schritt 4 aus), `max_nachbarn` (5), `qmd_index` (`vault`),
  `qmd_frist` (30 s). Ein Wert mit falschem Typ gilt nicht: Dann greift die Vorgabe, mit Warnung.
- Eichung der Schwelle: `python3 -I ~/.claude/skills/verknuepfen/scripts/eichen.py --vault <Vault> <Paarliste.md>`
  mit Zeilen `- [[A]] | [[B]] | verwandt|nicht`; `--einstellungen <Datei>` liest eine andere Einstellungsdatei statt
  der Vorgabe. Druckt Scores, Schwelle und Trefferquote, schreibt nichts. Die Schwelle traegt der
  Nutzer in `einstellungen.json` ein. Die Paarliste ist privat und gehoert nicht in den Skill.
- Bekannte Grenze: Die fuenf besten Treffer liegen fast immer ueber der Schwelle, sie schneidet also selten etwas ab.

## Grenzen und Abweichungen

- Lint L1 meldet jede Erwaehnung ausserhalb von Code, Frontmatter, Links und URLs. `/verknuepfen` schuetzt zusaetzlich
  Ueberschriften, Zitate und Callouts, eingerueckten Code, Hashtags, Pfade, Domains, Kommentare, Referenzlinks und
  Fussnoten sowie `00 Kontext/Claude.MD/` und die Wurzel-Systemdateien. Ausserdem behebt `link` absichtlich nicht:
  gesperrte Entitaeten (Sperrliste) und Links mit Alias in Tabellenzeilen. Eine L1-Meldung heisst deshalb nicht, dass `link` sie behebt.
- Der Hook `~/.claude/hooks/auto-link-entities.py` wird nicht mit dem Skill ausgeliefert. Fehlt die Datei, ist der
  Eintrag unten wirkungslos (der Befehl endet still mit `|| true`); der Skill selbst laeuft ohne Hook. Ist er
  vorhanden, wird er erst nach dem Tausch aktiv. Der alte `auto-link-notes.py` laeuft bis dahin weiter. Den Tausch gibt der Nutzer selbst frei; in `~/.claude/settings.json` unter `hooks.PostToolUse`
  (Matcher `Write|Edit`) wird der Befehl durch diesen ersetzt:

  ```json
  "command": "python3 \"$HOME/.claude/hooks/auto-link-entities.py\" 2>/dev/null || true"
  ```

- Ein voller Lauf `link --alle` ist eine Entscheidung des Nutzers, mit Sicherung des Vaults vorher. Die Sicherung legt
  der Nutzer an. Oder du legst auf sein Wort eine Kopie des Vaults an dem Ort an, den er nennt; das ist die zweite
  Ausnahme von "nichts ausserhalb des Vaults schreiben" und gilt nur fuer genau diesen Ort. Erst mit `--dry-run` zeigen.
  Die Ausgabe hat rund 1.200 Zeilen; deshalb mit `--json` in eine Temp-Datei schreiben und die Datei auswerten, statt
  die Ausgabe zu lesen:

  ```bash
  out="$(mktemp)"
  python3 -I ~/.claude/skills/verknuepfen/scripts/verknuepfen.py link --alle --dry-run --json "$out" | tail -n 1
  ```

  Waehrend des Laufs (Sicherung, Trockenlauf und `link --alle`) schreibt keine andere Sitzung in den Vault; sonst
  fehlt deren Aenderung in der Sicherung, und Notizen, die sich seit dem Lesen geaendert haben, bleiben ungeschrieben.

## Tests

```bash
python3 -I -m unittest discover -s ~/.claude/skills/verknuepfen/scripts
```
