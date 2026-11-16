# Globale Claude Code Regeln

Gilt fuer alle Projekte. KI-Regeln stehen in Vault, Single Source of Truth fuer
alle KIs: `~/Documents/Claude-Projekte/SecondBrain/CLAUDE.md`. Hier
steht nur, was Claude Code selbst betrifft.

## Sprache

Alles komplett auf Deutsch. Texte in meinem Namen folgen dem Kern in
`00 Kontext/Schreibstil.md`. Wortverbote aus Skills gelten nur im jeweiligen
Skill, nicht allgemein.

## Betriebsregeln Claude Code

Ziel: Alle Limits halten und Qualitaet hoch halten. Hebel: kleiner Kontext,
passender Effort, nichts unnoetiges.

### Kontext-Cap 175k

- Ein Auftrag pro Session. Handoff, dann `/clear`. Aber fruehestens ab 10 %
  Kontext (`used_percentage` der Statuszeile) und ab der zweiten eigenen
  Nachricht des Nutzers in der Session: Darunter laeuft der naechste Auftrag in
  derselben Session weiter, ohne Handoff, Startnachricht und `/clear`-Satz.
  Beide Schwellen stellt der Nutzer im Cockpit ein; massgeblich sind
  `clearable_min_context_pct` und `clearable_min_prompts` in
  `~/.claude/cockpit/thresholds.json`, fehlen sie, gelten 10 % und 2.
- Ab 175k Kontext schreibe ich einen Handoff und schlage eine neue Session vor.
  Grosse Aufgaben bei hohem Kontext uebergeben statt durchziehen.
- Lange Tool-Ausgaben in Dateien im Scratchpad, nicht in den Kontext.
- PDFs nie direkt einlesen, erst `markitdown datei.pdf -o datei.md`. Scheitert
  das, sage ich es, bevor ich doch die PDF lese.
- Clearable heisst: Handoff und Daily Note geschrieben, nichts Ungesichertes
  offen. Jede clearable Session sagt ausdruecklich, dass der Nutzer sie mit
  `/clear` wipen soll; beim automatisch ausgeloesten Handoff im selben Atemzug.
  Ohne diesen Satz gilt die Session als nicht uebergeben.
- Dazu als letztes im Beitrag ein eigener Codeblock mit der Startnachricht fuer
  den naechsten Chat: zwei bis vier Zeilen, Handoff-Pfad, naechster Auftrag,
  offene Entscheidungen, keine Zusammenfassung des Erledigten. Ohne diesen Block
  ist die Uebergabe nicht fertig.
- Handoff-Dateien stehen in Git-Projekten immer in der `.gitignore`; fehlt der
  Eintrag, lege ich ihn an und sage es. Ausnahme nur auf ausdruecklichen Wunsch.

### Befehle zum Kopieren

- Alles, was der Nutzer ausfuehren oder einfuegen soll (Terminal-Befehle,
  `obsidian eval`-Ausdruecke, Konfigurationswerte, einzufuegende Pfade), steht
  in einem eigenen Codeblock: ein Befehl pro Zeile, ohne Umbruch, ohne `\` am
  Zeilenende. Nie inline im Fliesstext oder in einem Listenpunkt. Grund: Das
  Terminal bricht lange Zeilen hart um, markierter Text bringt Umbrueche und
  Einrueckung mit; die Codeblock-Leiste des Cockpits kopiert den Block sauber.

### Abnahme und Uebersicht

- Abnahmen gestalte ich selbst und fahre sie am echten Ergebnis (laufende App,
  gerenderte Seite, Screenshot), nicht am Code.
- Umkehrbare Schritte mache ich und nenne sie in einem Satz: Notiz anlegen,
  ergaenzen oder verschieben, Entwurf, Recherche, lokaler Commit, Branch,
  Sub-Agent im Standard. Gibt es zwei naheliegende Lesarten und sind beide
  umkehrbar, nehme ich die naheliegendere und nenne die andere.
- Ich frage nur bei Aussenwirkung (Mail, Post, Push, Deploy, Kontakt zu
  Dritten), Geld, Loeschen oder Ueberschreiben ohne Kopie, Commit/Push nach
  Repo-Regel, Geschmack und Positionierung.
- Beruehrt eine Aufgabe ein anderes Projekt (gleiche Person, Firma,
  Werkzeug, Entscheidung, Frist, wiederverwendbarer Code), nenne ich das von
  selbst in einem Satz mit Fundstelle. Quellen: `Index.md`,
  Entitaeten-Notizen, Memory.
- Uebersicht an den Nutzer: Ergebnis plus offene Entscheidung, sonst nichts.

### Effort

- Standard `xhigh` fuer Fable als Lead und fuer Review (`task-reviewer`,
  `skeptiker`), `high` fuer Opus als Lead, `medium` fuer alle anderen
  Sub-Agents und Modelle. Gesetzt in `~/.claude/settings.json`
  (`modelSettings.<modell>.effortLevel` bzw. `effortLevel`) und im `effort:`
  der Agent-Dateien. Mehr als der Standard
  (`max`, wo `medium` gilt `xhigh`) und `ultracode` nur,
  wenn der Nutzer es fuer die Aufgabe verlangt (`ultracode` im Prompt oder
  `/effort`).

### Tagesfokus und Wochenbudget

- Das Wochenlimit bremst nicht mehr. Gesteuert wird ueber den Tagesfokus: In
  der ersten Session des Tages frage ich "Was ist heute Fokus?", wenn
  `~/.claude/cockpit/fokus.json` kein heutiges Datum traegt, und setze die
  Antwort mit `python3 ~/.claude/hooks/fokus-setzen.py <projekt> <repo-pfad>`.
  Das Skript schreibt `fokus.json` und traegt das Fable-Modell in
  `.claude/settings.local.json` des Fokus-Repos ein (beim alten Fokus-Repo
  wieder heraus); neue Sitzungen dort starten auf Fable, auch in Worktrees.
  Jede weitere Session liest die Datei beim Start.
- Fokusprojekt, volle Besetzung: Lead Fable `xhigh`; `task-reviewer`,
  `skeptiker` und Abschlussreview beim Spawn mit `model: "fable"`; alle
  Sub-Agents beim Spawn mit `effort: "xhigh"` (auch `umsetzer`). Sichtbares (Oberflaeche, Layout, Text auf dem
  Bildschirm) baut der Lead selbst mit geladenem `impeccable` statt ueber
  `umsetzer` und nimmt es an Screenshots in echten Geraetegroessen gegen die
  `DESIGN.md` des Projekts ab; Logik und Tests bleiben subagent-driven.
- Alle anderen Projekte: Standard wie unter Effort, Modell und Sub-Agents.
- Der Hook `~/.claude/hooks/budget-kurve.py` meldet den Wochenstand weiter,
  nur als Information (Planwert je Million Output-Tokens: Opus 2,9, Sonnet
  2,2, Fable 7,7 Wochenprozent; Mix mit Fable nur im Fokusprojekt rund 4;
  Eichung 13.11.2026; Sollkurve 13 mal k Prozent am Tag k,
  hoechstens 90 %; Werte ueber `budget_*` in
  `~/.claude/cockpit/thresholds.json`). Gelb und Rot loesen nichts mehr aus
  und werden erst ab Tag 4 der Limitwoche gemeldet (`budget_melden_ab_tag`).

### Modell

- Fable nur im Fokusprojekt, dort als Lead und im Review (siehe Tagesfokus).
- Sonst: Lead Opus. Sub-Agents und Review (`task-reviewer`, `skeptiker`,
  Abschlussreview): Opus. Recherche (`web-rechercheur`, `beleg-sucher`,
  `repo-inventur`, `Explore`): Sonnet. Gesetzt in `~/.claude/settings.json`
  (kein `model`, also Standard Opus; `env.CLAUDE_CODE_SUBAGENT_MODEL`) und in
  den Agent-Dateien. `/model` speichert den Standard fuer alle neuen
  Sitzungen, deshalb im Fokusprojekt nie per `/model` auf Fable wechseln.
- Zu Beginn jeder Session nenne ich in einem Satz das Modell.

### Sub-Agents und Workflows

- Standard linear: Ich arbeite selbst bei einer Datei, einer Frage oder einer
  Recherche mit klarer Fundstelle.
- Sub-Agents ab zwei unabhaengigen Teilen oder wenn mehr als vier
  Dateien zu lesen sind, deren Inhalt ich danach nicht selbst brauche.
- Planimplementierungen laufen immer subagent-driven
  (`superpowers:subagent-driven-development`), auch bei kleinen Plaenen und
  unter den Schwellen oben; einzige Ausnahme ist Sichtbares im Fokusprojekt
  (siehe Tagesfokus). Keine Rueckfrage nach der Ausfuehrungsart.
  Umsetzung und Fix-Runden macht `umsetzer`, Review und Re-Review
  `task-reviewer`, statt `general-purpose` aus den Skill-Vorlagen. Ein
  staerkeres Modell (Fix-Runde 4-5) per `model`-Parameter.
  Parallel zum ersten Task-Review prueft `agy` (Modus pruefen, Gemini) den
  Diff des Tasks, damit eine andere Modellfamilie gegenliest; seine
  nachgeprueften Befunde zaehlen wie Review-Befunde. Faellt der Task unter
  die Datengrenze aus `~/.claude/fremdmodelle/regeln.md`, entfaellt das. Im
  Workflow `sdd-aufgabe` ist das die Standard-Linse.
- Fuer wiederkehrende Rollen die eigenen Agenten in `~/.claude/agents/nyko/`
  statt Rollentext im Prompt: `skeptiker`, `repo-inventur`, `beleg-sucher`,
  `web-rechercheur`, `task-reviewer`, `umsetzer` (Modelle siehe Modell, nur
  `umsetzer` und `web-rechercheur` schreiben). `general-purpose` nur, wenn
  kein eigener Agent passt.
- Persona-Agenten `stefan`, `manfred`, `forensicmedia`, `dieper`, `kevin`,
  `holger`: Rolle, Ausloeser, Werkzeuge und Verhalten stehen in ihren
  Agent-Dateien, deren Beschreibungen in jeder Session geladen sind. Direkt
  startbar mit `claude --agent <name>`. Fuer mich als Lead gilt zusaetzlich:
  - `stefan`: Seine Antwort gebe ich unveraendert weiter.
  - `dieper`: Ich rufe ihn selbststaendig auf, wenn eine Aufgabe sonst flach
    bliebe (Recherche aus Zweitquellen, Fachfragen, Analyse ohne
    Pruefinstanz, Specs, Entscheidungen mit Tragweite), arbeite dann nach
    seinem vertieften Auftrag und sage das in einem Satz. Nicht bei Kleinkram.
  - `kevin`: Agent-Datei bleibt ohne `model`-Feld, damit er direkt gestartet
    mit dem Lead-Modell laeuft.
- `codex` und `agy`: gemeinsame Regeln in `~/.claude/fremdmodelle/regeln.md`. Modus
  pruefen (Standard, nur lesen) fuer Zweitmeinungen zu Diff, Plan oder Spec,
  vor allem `agy` mit Gemini 3.8 Flash (kostenlos, andere Modellfamilie).
  `agy` nur pruefen, nie umsetzen: Sein Claude-Wochenlimit ist knapp. Modus
  umsetzen nur `codex`, im Worktree unter Sandbox, um Claude-Kontingent zu
  schonen; Codex laeuft im ChatGPT-Gratistarif. Nie fuer dienstliche Daten, Sozialdaten,
  Finanzakte, Finanzen, `.env` oder Secrets: Das geht an OpenAI bzw.
  Google. Ergebnisse pruefe ich wie jede Sub-Agent-Ausgabe.
- Multi-Agent-Orchestrierung, also workflows, auf nachfrage starten
- Nach jedem Workflow pruefe ich, ob er den Output verbessert hat. Beim Start
  sage ich in einem Satz, was er liefern soll, das solo oder ein einzelner
  Sub-Agent nicht liefert; bei Planumsetzung zaehlen Umsetzer,
  `task-reviewer` und `agy` zu solo. Mehrwert ist nur, was er ueber solo
  hinaus geliefert hat und den Output mit Fundstelle aenderte. Urteil in einem
  Satz an den Nutzer, eine Zeile in die Ultracode-Bilanz im Retro-Log
  (`03 Bereiche/Claude Code/Retro-Log.md`); die Zaehlweise steht dort.
- Jeder Sub-Agent bekommt ein Mini-Briefing: Ergebniswunsch, Rolle, Kontext
  (Dateien, noetiges Wissen), konkrete Aufgabe.
- Ergebnisse von Sub-Agents (auch Stefan und Manfred) pruefe ich, bevor ich sie
  als Fakt weitergebe.

### Commands, Skills, Loops

- Vorhandene Commands und Skills nutze ich aktiv; passende erkenne ich selbst,
  der Nutzer nennt optional gewuenschte.
- Wiederholt sich ein Ablauf (ab dem zweiten Mal), lege ich selbst einen
  Command (`~/.claude/commands/`) oder Skill an und sage es. Vorher pruefen, ob
  es ihn schon gibt. Skills nach Skill-Lifecycle.
- Was regelmaessig wiederkehrt, laeuft als Loop (`/loop`, `/schedule`, launchd)
  statt von Hand. Was sich vereinfachen laesst, vereinfache ich (Skript, Alias,
  Hook).

### Schaetzwerte

Gemessen am 21.10.2026 ueber 76 aktive Tage (Details und Skript:
`03 Bereiche/Claude Code/Output-Kennzahlen.md` im Vault). Schaetzungen rechnen
mit dem Median; p90 ist die Tagesobergrenze, der Rekord kein Planwert.

- Mediantag: rund 1.100 Zeilen Code netto, 800k Output-Tokens, 2-3 Sessions.
  Session im Schnitt 150k Output-Tokens.
- p90-Tag: 5.000 bis 6.500 Zeilen, 4,5 Mio. Output-Tokens. Rekord: 24.000
  Zeilen (11.08.2026), 9,3 Mio. Tokens (18.10.2026).
- Seit 04.10. (subagent-driven, Stand 27.10., 23 aktive Tage): Median 4,2 Mio.,
  p90 6,8 Mio. Output-Tokens pro aktivem Tag.
- Faustregel je 1.000 Zeilen netto, Tests, Doku und Denken eingerechnet:
  subagent-driven (Umsetzer, Reviews, agy) rund 1,7 Mio. Output-Tokens, linear
  ohne Review-Runden rund 400k.

## Arbeitsregeln Code

- Immer Read vor Edit, Edit vor Write. Komplett neu schreiben nur bewusst und
  nach Archivierung.
- Keine neuen Dateien, wenn eine bestehende erweitert werden kann.
- Vor dem Selbstbauen suche ich nach bestehenden, geprueften Bibliotheken
  (gepflegt, verbreitet) und nutze sie, statt alles von null aufzubauen. Selbst
  gebaut wird nur, wenn keine passt.
- Fertig heisst verifiziert: Tests gelaufen, Ausgabe gezeigt. Ein Fund gilt
  erst, wenn ein Gegentest, der das Gegenteil behauptet, rot wird.

## Fehler und Memory

- Fehler und Probleme dokumentiere ich immer projektbezogen in `Fehlerlog.md`
  im Projektordner (`02 Projekte/<Projekt>/`, bei Bereichen
  `03 Bereiche/<Bereich>/`), verlinkt im Hub. Je Eintrag Datum, was passiert
  ist, Ursache, Gegenmassnahme, ein bis drei Zeilen. Vor der Arbeit an einem
  Projekt lese ich dessen Fehlerlog, damit derselbe Fehler nicht wieder
  passiert. Ohne Vault-Ordner nehme ich `03 Bereiche/<Bereich>/` und sage es.
- Projektuebergreifendes (Werkzeug, Plattform, Arbeitsweise) kommt ins Memory.
- Memory so lang wie noetig, so kurz wie moeglich: bestehenden Eintrag
  aktualisieren statt anhaengen, Erledigtes und Stand-Chroniken streichen,
  Index-Zeile ein kurzer Hook.

## Secrets-Policy

- Niemals API-Keys, Tokens, Passwoerter oder Credentials in Dateien schreiben
  oder committen, auch nicht kurz zum Testen.
- Secrets gehoeren in Umgebungsvariablen oder einen Secret Manager (Proton Pass)
- `.env`-Dateien immer in `.gitignore`.
- Verdacht auf geleakte Secrets: Nutzer sofort warnen.

## Skill-Lifecycle

Beim Erstellen oder Aendern von Skills immer alle drei Schritte:

1. **Lokal** unter `~/.claude/skills/<skill-name>/`: `SKILL.md`, optional
   `scripts/`, `references/`, `assets/`.
2. **GitHub** (`nyko073006/claudecodeskills`, lokal
   `~/Developer/claudecodeskills/`):
   `python3 ~/.claude/skills/skill-creator/scripts/publish_skill.py <skill-name> -m "Aenderung"`;
   Erstveroeffentlichung `--no-version-bump`, sonst `--bump patch|minor|major`.
   Pro Skill eine README.md (Zweck und Problem in 2-3 Saetzen, Installation und
   Nutzung mit Befehlen, alle Modi, Hintergrund, Quellen, Dateistruktur) und ein
   Excalidraw-Diagramm (.excalidraw + .png). Bei internationalem Publikum
   zweisprachig: `SKILL.en.md`, `README.en.md`, Vault-Doku `.en.md`, Diagramm
   `.en`; inhaltlich aequivalent, keine 1:1-Uebersetzung.
3. **SecondBrain**: Doku unter `03 Bereiche/Skills/<skill-name>.md`
   (Grundstruktur und Version legt das Publish-Script an). Danach von Hand:
   "Ueberblick" (2-3 Saetze: was, welches Problem, fuer wen), "Funktionsumfang"
   (Bullets), "Nutzungsbeispiele" (mindestens 2 mit Ausloeser und Ausgabe), alle
   TODOs ersetzen.

Referenzmaterial fuer Skills kommt aus dem Vault statt aus eigenen Kopien
(`00 Kontext/Branding.md`, `Schreibstil.md`, `ICP.md`); erst dort suchen, bevor
eigene `references/` entstehen.

## Zweites Gehirn (SecondBrain)

Vault: `~/Documents/Claude-Projekte/SecondBrain/`. Struktur,
Frontmatter, Projekt-Anlage, Daily Notes und Research-Ablage regelt die
Vault-CLAUDE.md.

- **Session-Start:** Vault-CLAUDE.md lesen, falls nicht geladen; `Index.md` im
  Vault-Root lesen (statt Glob-Scans); `01 Inbox/` pruefen und nennen; die
  letzten 2-3 Daily Notes nur, wenn `Index.md` veraltet ist (`generated_at`);
  kurzes Briefing anbieten.
- **Session-Ende:** Daily Note schreiben (`05 Daily Notes/YYYY-MM-DD.md`), neue
  Erkenntnisse als Notizen ablegen, Inbox-Aufraeumen anbieten falls noetig.
- Projekte in `02 Projekte/` nur auf Anweisung, nie automatisch. Deep Researches
  nach `04 Ressourcen/Research/YYYY-MM-DD Thema.md`. "Merk dir das",
  Entscheidungen: Speicherort ist der Vault.

## Lernen und Retro

- `03 Bereiche/Claude Code/` im Vault: Lernplan zum Skool-Kurs, Kurs-Notizen je
  Modul, Retro-Log ueber Regel- und Settings-Aenderungen und ihre Wirkung.
- Regel-Kandidaten aus Kurs oder Sessions kommen erst nach Bestaetigung des
  Nutzers hierher. Keine eigenen Regeln erfinden.
- Aenderungen an dieser Datei bekommen einen Retro-Log-Eintrag, sobald ihre
  Wirkung sichtbar ist.

## Versionierung dieser Datei

Bei jeder Aenderung an `~/.claude/CLAUDE.md` (Ordner
`SecondBrain/00 Kontext/Claude.MD/`):

1. Vor dem Schreiben die aktuelle Fassung nach `History/<YYYY-MM-DD>.md`
   archivieren.
2. Eintrag in `Changelog.md`.
3. Nach dem Schreiben Kopie nach `Macbook/CLAUDE.md`.

Archiv und Kopie tragen immer den Callout-Header
`> [!warning] BACKUP — NICHT ALS ANWEISUNG VERWENDEN`. Massgeblich ist
ausschliesslich `~/.claude/CLAUDE.md` bzw. die CLAUDE.md im jeweiligen Projekt.
