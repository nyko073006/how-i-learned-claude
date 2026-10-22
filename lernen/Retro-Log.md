---
tags:
  - claude-code
  - retro
status: aktiv
aktualisiert: 2026-10-22
source: claude
chat_url: unbekannt
---

# Retro-Log Arbeitsweise Claude Code

Datierte Eintraege, was an Regeln oder Settings geaendert wurde, warum, und ob es gewirkt hat. Neueste Eintraege oben.

## 2026-10-22 ~/AGENTS.md entfernt, Opus-Effort wieder high

- `~/AGENTS.md` war am 07.10. als Codex-Fassung einer aelteren CLAUDE.md zurueckgekehrt (kaputte Pfade `~/.Codex/...`, `Codex-Projekte/SecondBrain`) und lud in jeder Claude-Session unter `$HOME` als Projektanweisung mit. Herkunft unklar, vermutlich Codex-Import. Verschoben nach `~/.claude/_archiv/2026-10-22-home-agents-md/AGENTS.md.bak` (Prüfsumme gleich, LIESMICH mit Rückweg). Codex nutzt `~/.codex/AGENTS.md`.
- `settings.json`: `modelSettings.claude-opus-5-5.effortLevel` stand seit 12.–19.10. unbemerkt auf `medium` (Sicherung `bak-2026-10-12` noch `high`), vermutlich ueber den Effort-Waehler der App. Zurueck auf `high` gemaess Nutzer-Entscheidung 27.09.; Sicherung `settings.json.bak-2026-10-22`. CLAUDE.md unveraendert.
- Wirkung pruefen: Startkontext ohne `~/AGENTS.md`; taucht die Datei wieder auf oder kippt der Opus-Effort erneut, Ausloeser suchen (Codex-Import, App-Waehler).

## 2026-10-04 Stufe 3: CLAUDE.md und MEMORY.md gestrafft

Session: Session-Link entfernt.
Changelog: [[Changelog]] (Archiv `History/2026-10-04`).

### Startwert nach Stufe 2 (belegt)

Frischer interaktiver Prozess im Home-Ordner (PID 62325, Start 09:34,
Opus, Session `8d535a97`): **61.218** Tokens am ersten Request (27.675
Cache-Lesung, 33.541 Cache-Schreibung). Die Erwartung von rund 61k aus
Stufe 2 ist erfuellt, gegenueber 73.770 vor Stufe 2 sind es 12,5k weniger.
Vercel fehlt im Deferred-Anhang, Figma und Claude Docs stehen weiter in
den MCP-Anweisungen.

### Geaendert

- `~/.claude/CLAUDE.md`: 11.994 auf 9.115 Bytes. Keine Regel geaendert,
  nur Formulierungen; gestrichen der erledigte claude-flow-Satz.
- `memory/MEMORY.md`: 14.609 auf 11.204 Bytes. Alle 92 Eintraege und Links
  bleiben in gleicher Reihenfolge, nur die Kurzbeschreibungen sind kuerzer.

### Messung (headless, Sonnet, gleiche Flags wie Stufe 2)

| Ort | vorher | nachher |
|---|---|---|
| Home-Ordner | 43.625 | 41.219 (-2.406) |

Der Vorher-Wert liegt 758 unter den 44.383 aus Stufe 2, ohne dass sich
etwas geaendert hat; die Streuung zwischen zwei Laeufen ist also nicht null.
Interaktiv im Home-Ordner sind damit rund 58,8k zu erwarten.

### Offen

- Startwert 58,8k in einem frischen Prozess im Home-Ordner pruefen.
- Projekte interaktiv nachmessen (patina-charts-ios, coremetrics,
  Notenrechner): bis 09:42 gab es seit der Umstellung keinen Start dort.
- Figma und Claude Docs auf claude.ai trennen (Nutzer), danach messen.

## 2026-10-04 Stufe 2: Vercel nur im Notenrechner, Skill-Budget 0.005

Session: Session-Link entfernt.
Settings: [[2026-10-04-settings-aenderungen-stufe-2]].

### Startwert vor der Aenderung

Frischer Prozess im Home-Ordner (Opus, 09:08, kein `/clear`): 73.770 Tokens
am ersten Request. Chrome ist weg (0 Namen im Deferred-Anhang), die
abgeschalteten Plugins `code-review` und `mcp-server-dev` auch. Die
Erwartung von 74 bis 75k ist erfuellt. 120 Skills, 29.942 Zeichen.

### Geaendert

- Vercel global aus, im Notenrechner per `settings.local.json` an (auch in
  den drei Worktrees).
- `skillListingBudgetFraction` 0.005, 13 eingebaute Skills auf `name-only`.

### Messung (headless, Sonnet, gleiche Flags)

| Ort | vorher | nachher |
|---|---|---|
| Home-Ordner | 56.708 | 44.383 (-12.325) |
| Notenberechnung | nicht gemessen | 55.203, Vercel geladen (488 Treffer) |
| Worktree `hygiene` | nicht gemessen | 55.407, Vercel geladen |

Die Simulation per `--settings` (44.381) stimmte mit den echten Dateien
ueberein. Grob aufgeteilt: Skill-Liste rund 15k Zeichen (etwa 3,7k Tokens),
der Rest ist Vercel (Tool-Namen 41,6k auf 16,7k Zeichen, Anweisungen,
Skills). Interaktiv im Home-Ordner sind damit rund 61k statt 73,8k zu
erwarten. Gemessen ist das erst nach einem echten Neustart.

### Lehre

- `skillOverrides` greift nicht bei Plugin-Skills, egal in welcher
  Schreibweise (Code von 2.1.289). Die name-only-Liste aus dem Handoff war
  deshalb zu zwei Dritteln wirkungslos. Fuer Plugin-Skills bleibt nur das
  Budget.
- Bei Budget 0.005 behielten alle 17 eigenen Skills ihre Beschreibung,
  ebenso die genutzten von superpowers. Gekappt wurden ungenutzte Plugin-
  und eingebaute Skills. Die Sorge aus Stufe 1 ("zuerst verlieren eigene
  Skills die Beschreibung") ist mit den Overrides nicht eingetreten.
- `enabledPlugins` wird tief zusammengefuehrt; `true` in der Projektdatei
  schlaegt das globale `false`.
- Claude Code kopiert `settings.local.json` beim Anlegen eines Worktrees
  mit. Eine lokale Datei reicht also, ein Commit ist nicht noetig.

### Offen

- Startwert im frischen interaktiven Prozess nachmessen: Home rund 61k,
  Notenrechner, patina-charts-ios, coremetrics.
- Figma und Claude Docs auf claude.ai trennen (Nutzer).
- MEMORY.md und CLAUDE.md straffen (eigene Session).
- Alte Prozesse vom 02. und 03.10. laufen noch mit dem alten Stand.

## 2026-10-04 Startkontext von 96k auf rund 77k

Anlass: Sessions starteten vor dem ersten Satz mit rund 95k Tokens, bis zum
Kontext-Cap von 150k blieben damit nur gut 50k fuer die Arbeit.
[Original-Chat](Session-Link entfernt)

### Ausgangslage

Gemessen am ersten Request dieser Session (96.314 Tokens) und an den
Transkript-Anhaengen. Der Startwert ist seit Juli von rund 54k auf 94 bis
96k gewachsen (Tagesmediane aus `~/.claude/projects`). Sub-Agents starten im
Median mit 59k (196 Laeufe in 35 Tagen).

| Block | Groesse | Ballast darin |
|---|---|---|
| Systemprompt + eingebaute Tools | 29k (Cache-Lesung) | keiner; Artifact 31x, Workflow 137x genutzt |
| Memory-Dateien | 17,6k | `~/AGENTS.md` 4,4k: Codex-Vorlage, identisch mit `~/.codex/AGENTS.md`, laedt bei Start im Home-Ordner (61 von 201 Sessions) |
| Agent-Liste | 8,5k | 90 claude-flow-Agents 5,3k, 18 seo-Agents 1,4k |
| Namen der Deferred Tools | 677 Namen, 29k Zeichen | Postproxy 103, Figma 40, Kernel 29, Drive 11, Claude Docs 8, Slack 2: null Aufrufe in 35 Tagen |
| Skill-Liste | 9,9k | 92 claude-flow-Commands, 19 seo-Skills |
| MCP-Anweisungen, Hook-Texte | ca. 5k | Figma, Claude Docs |

### Geaendert

Vom Nutzer gewaehlt: "Ballast raus", "SEO parken", "Chrome auf Abruf".
"Vercel nur im Notenrechner" bewusst nicht, Vercel bleibt global.

- Archiv `~/.claude/_archiv/2026-10-04-kontext-diaet/`: claude-flow (23
  Agent-Ordner, 7 Command-Ordner, 3 Commands, Skill `browser`), SEO (19 Skills
  inkl. `.venv` und Chromium, 18 Agents), `~/AGENTS.md`, dazu
  `settings.json.bak` und `claude.json.bak`.
- Settings im Einzelnen: [[2026-10-04-settings-aenderungen]].

### Messung

Headless `claude -p` mit Sonnet, Telegram aus, identische Flags: 69.182
Tokens vorher, 56.514 nachher. Vorher waren Vercel und Kernel beim ersten
Request noch nicht verbunden, nachher ist Vercel mitgezaehlt (244 Namen, ca.
4,5k). Bereinigt rund 17k weniger.

- Agent-Liste: 123 Agents / 30.656 Zeichen -> 15 / 5.811
- Memory-Dateien: 17,6k -> 13,3k
- Deferred-Namen: sechs Connectoren weg, Gmail und Kalender da
- Skill-Liste: 29.847 -> 29.966 Zeichen, also **keine** Ersparnis (siehe Lehre)

Erwartung interaktiv: Home-Ordner rund 77k statt 96k, Projekte rund 15k
weniger als bisher. Pruefen mit `/context` in der naechsten Session.

### Nachmessung in der Folgesession

Erster Request nach `/clear` im Home-Ordner (Opus, 08:01): 76.088 Tokens.
Die zwei `/clear`-Starts um 07:52 lagen bei 75.918 und 75.846, die sechs
Starts der Nacht bei 96.192 bis 96.465. Die Erwartung von rund 77k ist
erfuellt, gespart sind rund 20k. `~/AGENTS.md` laedt nicht mehr mit, als
Memory-Dateien bleiben `~/.claude/CLAUDE.md` und `MEMORY.md`.

Einschraenkung: Alle drei Werte stammen aus Prozessen, die vor der
Umstellung gestartet wurden (juengster laufender Prozess 01:23). `/clear`
startet keinen neuen Prozess. Deshalb ist Chrome in allen dreien noch
geladen (22 Namen, Anweisungen, Abschnitt im Systemprompt, zusammen rund
1,5k), obwohl `claudeInChromeDefaultEnabled` auf `false` steht. Ein frischer
Prozess muesste entsprechend tiefer starten. Ob der GrowthBook-Schalter
`tengu_chrome_auto_enable: true` in `~/.claude.json` Chrome trotzdem
zuschaltet, ist ungeprueft.

Projekte: Seit 07:50 gab es keinen Start in einem Projektordner, die
Erwartung ist also noch nicht geprueft. Mediane 27.09. bis 03.10. (Opus):
patina-charts-ios 82,2k (22 Starts), coremetrics 85,6k (14),
`03 Bereiche/Claude Code` 92,6k (9). Mit 15k weniger muessten sie bei rund
67k, 71k und 78k landen.

Wo die 76k jetzt stecken (Zeichen der Transkript-Anhaenge): 489
Deferred-Namen mit 20,4k Zeichen, davon Vercel 244 (11,7k) und Higgsfield
117 (4,3k); Skill-Liste 125 Skills mit 29,9k, am Budget; MCP-Anweisungen
11,5k, davon Figma und Claude Docs 4k ohne ein Tool dahinter; Agent-Liste
16 Agents.

Aufrufe in 30 Tagen (1.333 Transkripte): Playwright 544, Vercel 84 (71 aus
Notenberechnung samt Worktrees, 13 aus dem Home-Ordner: Seitenaufrufe,
Firewall, Logs), Gmail 31, Higgsfield 26, Chrome 10, Kalender 7, context7 1;
Telegram, Figma und Claude Docs 0. 96 von 125 Skills ohne Aufruf, darunter
45 der 46 Vercel-Skills.

### Lehre

- Die Skill-Liste hat ein Budget: `skillListingBudgetFraction` (Standard
  0.01, bei 1M rund 30k Zeichen). Skills entfernen spart dort nichts, der
  freie Platz geht an laengere Beschreibungen der uebrigen. Getestet: 0.005
  ergibt 5k, 0.0035 ergibt 3,5k; dabei verlieren zuerst eigene Skills
  (council, reel-ingest) ihre Beschreibung, eingebaute wie dataviz nicht.
- `permissions.deny` auf `mcp__<server>` nimmt die Tools restlos raus, die
  Server-Anweisungen bleiben (Figma, Claude Docs, ca. 1,2k). Ganz weg nur per
  `/mcp disable` (pro Projekt) oder Trennen auf claude.ai.
- `claude -p "/context"` laeuft ohne Modellaufruf, zeigt aber nur einen Teil
  (43,8k statt 96k). Den echten Startwert liefert die `usage` des ersten
  Requests im Transkript, die Bloecke stehen dort als `attachment`.

### Offen

- Skill-Budget senken (0.005 spart 5k), sinnvoll nur zusammen mit
  `name-only` fuer ungenutzte eingebaute Skills, damit das Budget bei den
  eigenen landet.
- Figma und Claude Docs auf claude.ai trennen, falls dort auch ungenutzt.
- MEMORY.md (7k) und CLAUDE.md (6,2k) straffen; der claude-flow-Satz in der
  CLAUDE.md ist durch das Archiv erledigt.
- Vercel nur im Notenrechner aktivieren (rund 5k), falls gewuenscht.
- Frischen Prozess messen, im Home-Ordner und in einem Projektordner: erst
  dann sind "Chrome auf Abruf" und die Projekt-Erwartung belegt.
- Entschieden in der Folgesession (Auswahl des Nutzers): Vercel nur im
  Notenrechner, Skill-Budget 0.005 mit name-only fuer ungenutzte Plugin- und
  eingebaute Skills, Figma und Claude Docs trennt er auf claude.ai, Straffen
  in eigener Session. Umsetzung: [[HANDOFF-2026-10-04-kontext-diaet-stufe-2]].

## 2026-10-01 Agent Stefan: erster echter Aufruf (Abend)

Wirkungskontrolle fuer den am selben Tag angelegten Agenten `stefan`
([[HANDOFF-2026-10-01-agent-stefan]]), vor allem fuer die nach dem Probelauf
ergaenzte Regel "Fristart und Rechtsfolgen nur mit Fundstelle".

### Geprueft

Frage: "Stefan, was ist heute Abend dran?" Diesmal als eigener Agent aufgerufen,
nicht mehr als `general-purpose` mit kopiertem Prompt.

| Pruefpunkt | Ergebnis |
|---|---|
| Duzen | Ja, durchgehend. |
| Kalender | Tool kommt im Agenten an, Aufruf fehlerfrei. Die leere Antwort (nur Kontometadaten) hat er als "nicht bestaetigbar" gemeldet statt als leer behauptet. Gegentest: `list_events` 01.–15.10. liefert den Termin am 08.10., die Abfrage findet also Termine; der Abend war wirklich frei. |
| Fristfolgen | "Verliert das Quartal" mit Quelle Wochenplan KW40 (Z. 42–43) und dem Zusatz, dass er keine gesetzliche Grundlage gefunden hat. |

### Hat gewirkt
- Die Regel gegen erfundene Rechtsfolgen: Folge belegt und als nur planseitig gekennzeichnet.
- Die Billogram-Rechnung (im Probelauf uebersehen) nennt er diesmal, ohne neue Regel.
- Kosten rund 42k Tokens statt 87k im Probelauf. Ursache nicht geprueft.

### Unschaerfe, keine Regel
- "Bevor Mahngebuehren entstehen", obwohl das Briefing "Erinnerung ohne Mahngebuehr" sagt. Abgeschwaecht, nicht falsch.
- Die Quellenliste am Ende stand im Auftrag, gehoert nicht zu seinem Standardformat.
- Die Folge "verliert das Quartal" ist nur im Wochenplan belegt; ob sie selbst stimmt, ist offen (vgl. [[frist-herkunft-waechst-beim-kopieren]]).

### Offen
- Weitere Aufrufe beobachten. Keine Regelaenderung.

## 2026-10-01 Wirkungskontrolle nach einer Woche

### Gemessen

`/usage` am 2026-10-01, 08:40, einen Tag vor dem Reset (2026-10-02, 07:00):

| Zeile | Stand |
|---|---|
| Wochenlimit, alle Modelle | 65 % |
| Wochenlimit, Fable 5.1 | 88 % |
| Anfragen | 804 in 24 h, 6.758 in 7 Tagen |

Angaben des Nutzers: ueberwiegend im Terminal gearbeitet, Kontext seit der Regel nie ueber 300k, Handoff viel genutzt, PDF-Regel noch nicht gebraucht.

### Ursachen-Aufschluesselung (zweiter `/usage`-Blick am selben Tag)

Der Lauf um 08:40 hatte nur die Limit-Balken erfasst. Der Abschnitt "What's
contributing to your limits usage?" nennt die Treiber. Datenbasis: letzte 24 h,
und ausdruecklich **nur lokale Sessions auf diesem Mac** — Cloud-Sessions und
claude.ai fehlen darin. Die Posten sind laut Anzeige unabhaengige Merkmale,
keine Aufteilung einer Summe, addieren sich also nicht auf 100 Prozent.

| Treiber | Anteil |
|---|---|
| Verbrauch bei ueber 150k Kontext | 71 % |
| Subagent-schwere Sessions | 39 % |
| davon Subagents unter `coder` | 10 % |
| Skill `/handoff` | 3 % |
| Skill `superpowers:brainstorming` | 1 % |
| MCP `playwright` | 3 % |
| MCP `context-mode` | 3 % |

Zwei dieser Zahlen widersprechen dem, was weiter unten unter "Hat gewirkt" steht:

- **Der Kontext-Cap 150k greift nicht.** Unten steht "kein Kontext mehr ueber
  300k". Das stimmt, ist aber die falsche Schwelle. Die Regel in der CLAUDE.md
  nennt 150k, und 71 Prozent des Verbrauchs lag darueber. Gehaltenes Wochenlimit
  und eingehaltener Cap sind zwei verschiedene Befunde — hier war nur der erste
  wahr. Die Formulierung "Kontext-Cap greift" war zu grosszuegig.
- **`coder` laeuft, die eigenen fuenf nicht.** Das [[2026-09-29 Agenten-Inventar]]
  hatte ueber 30 Tage null Aufrufe fremder Agenten gezaehlt. In den letzten 24 h
  gehen 10 Prozent des Verbrauchs auf Subagents unter `coder`, einen
  claude-flow-Agenten, den die Regel vom 30.09. ausdruecklich ausschliesst.
  Gleichzeitig wurde keiner der fuenf eigenen je ausgefuehrt. **Von Nyko am
  01.10. als bekannt und gewollt bestaetigt** — die Herkunft ist ihm klar, sie
  ist hier nicht protokolliert. Damit ist die Zahl erklaert, aber die Regel vom
  30.09. ("die fremd installierten Agenten aus `claude-flow` nutze ich nicht")
  beschreibt die Praxis nicht vollstaendig. Entweder bekommt sie eine Ausnahme
  fuer `coder`, oder sie bleibt bewusst strenger als die Praxis.

Die Woche ist mit diesem Stand praktisch gelaufen (Reset 2026-10-02, 07:00),
die 65 Prozent sind also ein Endstand, kein Zwischenstand. Der Sonnet-Fallback
aus der Donnerstags-Regel haette hier nichts mehr zu steuern gehabt — ein
weiteres Argument, Schwelle und Zeitpunkt der Regel neu zu fassen.

### Hat gewirkt

- Wochenlimit nicht gerissen, einen Tag vor dem Reset bei 65 %. Vorher regelmaessig gerissen. Fuer den Nutzer ein voller Erfolg.
- Kein Kontext mehr ueber 300k, vorher Sessions bis 90 MB Transkript. Kontext-Cap, Handoff und Statusline greifen.
- Fable 88 % war bewusste Nutzung, kein Ausreisser durch den VS-Code-Picker.

### Nicht messbar oder offen

- PDF-Regel: noch kein Anlass, keine Aussage.
- Skills 96 auf 47 (2026-09-29): erst zwei Tage aktiv, Wirkung naechste Woche.
- Die Regel "Opus-Zeile donnerstags ueber 60 Prozent" passt nicht zu `/usage`: Es gibt keine eigene Opus-Zeile, nur "alle Modelle" und eine Zeile pro Modell wie Fable. Mit 65 % in "alle Modelle" waere die Regel formal gerissen, obwohl die Woche ein Erfolg war. Schwelle und Zeile neu festlegen, Entscheidung offen.
- Diese Cloud-Session lief vom 2026-09-27 bis 2026-10-01 ueber mehrere Auftraege (Workshop, Statusline, Skills, Retro). Stand am 01.10.: 5,1 Mio. Tokens Cache-Read, 22 $. Verstoesst gegen "ein Auftrag pro Session". Lehre: auch Cloud-Sessions nach jedem Auftrag uebergeben.

### Geaendert

- Modell-Regel in der CLAUDE.md: Jede Session sagt zu Beginn ihr Modell an und fragt bei Fable ohne Zuruf einmal nach. Siehe [[Changelog]].

### Naechste Messung

- 2026-10-08 per `/usage`. Fokus: Wirkung der ausgeduennten Skills, Entscheidung zur 60-Prozent-Regel.
- Dabei immer auch "What's contributing" mitlesen, nicht nur die Balken.
  Zielgroesse: der Anteil ueber 150k Kontext soll unter 71 Prozent liegen.
- `coder` ist geklaert (gewollt), braucht keine Messung mehr. Offen bleibt die
  Formulierung der Agenten-Regel in `~/.claude/CLAUDE.md` — Entscheidung bei Nyko,
  nicht eigenstaendig aendern.
- Die fuenf eigenen Agenten sind weiter bei null Ausfuehrungen. Das bleibt die
  eigentliche offene Messung aus dem Eintrag vom 30.09.

## 2026-09-30 Fuenf eigene Sub-Agents statt 116 fremder

Zwei Teile: eine Setup-Aenderung (fuenf neue Agenten) und, am selben Tag
nachgezogen, eine Regel in `~/.claude/CLAUDE.md`, die sie namentlich nennt.
Anlass war das [[2026-09-29 Agenten-Inventar]].

### Ausgangslage

`~/.claude/agents/` enthielt 116 Agenten, alle fremd installiert (mtime
2026-03-30 aus dem claude-flow-Paket, die 18 seo-* vom 2026-07-23).
Keiner davon wurde in 30 Tagen ein einziges Mal aufgerufen. Gestartet
wurden ausschliesslich Built-ins: `general-purpose` (277x), `Explore`
(68x), `Plan` (18x).

Vier gemessene Ursachen: Themen-Mismatch der `description` gegen die
tatsaechliche Arbeit, fehlende MCP-Server (`claude-flow`, `ruv-swarm`,
`agentic-flow` sind nicht konfiguriert, 70 Agenten brauchen sie), falscher
Skill-Einstieg bei den seo-Agenten, und die eigene Regel "Standard ist
linear".

Der eigentliche Befund lag nicht bei den Agenten, sondern bei den Prompts:
**102 von 192 eindeutigen Subagent-Aufrufen beginnen mit einem
handgeschriebenen Rollen-Kopf** ("Rolle: Skeptischer Pruefer. Du aenderst
KEINE Dateien", "Rolle: Belegsucher ... Datei + Zeile + Seite + Zitat").
Die Agenten existierten also laengst — sie wurden jedes Mal neu getippt.

### Geaendert

`~/.claude/agents/nyko/` angelegt mit fuenf Agenten, destilliert aus den
eigenen Rollen-Koepfen: `skeptiker`, `repo-inventur`, `beleg-sucher`,
`web-rechercheur`, `task-reviewer`. Alle auf `model: sonnet`, entsprechend
`subagents-immer-sonnet`.

Die vier read-only Agenten haben **kein** `Write` und **kein** `Edit`. Die
wiederholte Prompt-Bitte "Du aenderst KEINE Dateien" ist damit keine Bitte
mehr, sondern eine fehlende Faehigkeit. Einschraenkung: `Bash` bleibt drin
und koennte theoretisch schreiben — die Sperre ist stark, nicht lueckenlos.

Die 116 alten Agenten und die 8 Duplikate wurden **nicht** angefasst.

### Erwartung

Die handgeschriebenen Rollen-Koepfe entfallen, weil die Rolle in der
Definition steht. Das spart Prompt-Tokens je Aufruf und macht das
Read-only-Versprechen technisch statt rhetorisch.

### Messung

Am 2026-10-01 zusammen mit `/usage`: Wie oft wurde einer der fuenf per
`subagent_type` aufgerufen, und wie oft wurde trotzdem wieder ein
Rollen-Kopf in einen `general-purpose`-Prompt getippt? Die zweite Zahl ist
die interessante — sie zeigt, ob die Definitionen greifen oder nur
herumliegen.

### Offen

- **Teilweise verifiziert.** Am 30.09. in frischer Session bestaetigt: die
  fuenf erscheinen in der geladenen Agentenliste. Ein Testaufruf am 29.09.
  war noch mit "Agent type not found" gescheitert, weil die Liste nur beim
  Session-Start geladen wird. Tatsaechlich *ausgefuehrt* wurde noch keiner.
- **Regel eingetragen am 2026-09-30.** Nach Bestaetigung durch Nyko steht in
  `~/.claude/CLAUDE.md` unter "Sub-Agents und Workflows" eine Zeile, die die
  fuenf namentlich nennt und die `claude-flow`-Agenten ausschliesst.
  Vorversion archiviert als [[History/2026-09-30]], Changelog-Zeile gesetzt,
  Macbook-Kopie abgeglichen. Gegengeprueft: alle fuenf tragen `model: sonnet`,
  die vier read-only haben nur `Read, Bash, Glob, Grep` — `web-rechercheur`
  hat bewusst `Write`, und genau den findet die Suche, sie ist also nicht blind.
- **Katalog unaufgeraeumt.** 116 alte Agenten, davon 8 Duplikate, blaehen
  jeden Systemprompt auf.

## 2026-09-28 Zwei neue Arbeitsregeln aus dem E2-Bau (Abend)

Aufgenommen nach ausdruecklicher Bestaetigung von Nyko am 28.09. Beide
stammen aus dem Bau von E2 (Entnahmeplan individuell, patina-charts-ios,
PR #94), wo sie jeweils erst im Abschluss-Review aufgefallen sind.

### Regel 1: Beim Waechter den Codepfad pruefen, nicht die Farbe

Ein gruener Test beweist nur, dass er gelaufen ist, nicht dass er
hinschaut. Vor dem Berufen auf einen Waechter gilt die Frage: **welchen
Codepfad betritt er, und welchen Fehler wuerde er fangen?**

Anlass: Nach dem Umbau der ETF-Entnahmerechnung blieb
`GoldenNumbersTests` gruen, und das wurde als Beleg gemeldet, dass die
Extraktion nichts verschoben hat. Tatsaechlich laufen alle drei
Golden-Faelle mit `kapitalverzehr = false`, und der Kapitalerhalt-Zweig
kehrt *vor* der umgebauten Schleife zurueck. Die Tests konnten gar nicht
fallen. Die eigens dafuer geschriebene Regression war ebenso blind: sie
prueft `bruttoSumme`, die bei konstanter Rate algebraisch aus `startRate`
folgt.

Praktische Fassung: Die Sabotage-Probe gehoert an den **Anfang**, nicht
ans Ende. Der Beleg war am Ende trivial (Steuersatz verdoppeln, beide
Tests blieben gruen) und haette direkt nach dem Umbau zwei Minuten
gekostet, statt eine falsche Entwarnung zu erzeugen.

Ergaenzt die bestehende Skeptiker-Regel („ein Fund gilt erst, wenn ein
Gegentest rot wird") um die Frage, ob der Test den geaenderten Code
ueberhaupt erreicht.

### Regel 2: Ein Flag, das nur die UI abschaltet, ist kein Kill-Switch

Bei jedem Feature-Flag von Anfang an fragen, was beim **Zurueckschalten**
passiert, nicht nur beim Einschalten. Persistierter Zustand, Cache-
Schluessel und Parameter-Fabriken gehoeren mit unter das Flag, sonst
rechnet die Engine weiter, waehrend das Bedienelement verschwunden ist.

Anlass: `entnahmePlan` und `policeAuszahlungsart` wurden aus `KundenProfil`
und `SessionSnapshot` ohne Flag-Pruefung wiederhergestellt, waehrend die
Karte hinter dem Flag lag. Flag aus haette geheissen: Engine rechnet
weiter den Auszahlplan, Beratungstexte und PDF sagen „Auszahlplan", und
der Berater hat kein Bedienelement, um es zurueckzustellen. Genau der
Fall, fuer den ein Kill-Switch da ist.

### Erwartung

- Weniger falsche Entwarnungen in Zwischenberichten an Nyko.
- Flags bleiben rueckrollbar, ohne dass ein Geraete-Smoke das aufdecken muss.

### Messung

- Naechste Pruefung beim naechsten groesseren Umbau mit Flag (E3 oder E4).
- Bewaehren sich beide, gehoeren sie in `~/.claude/CLAUDE.md` unter
  „Arbeitsregeln Code" - dann mit dem dortigen Versionierungs-Ritual
  (Archiv, Changelog, Kopie).

### Offen

- Noch nicht in `~/.claude/CLAUDE.md` uebernommen, bewusst: erst Wirkung
  abwarten.

## 2026-09-24 Wirkungskontrolle nach dem Umbau (Abend)

### Geprueft

- `~/.claude/settings.json`: Modell opus, Effort medium, keine modelSettings mehr. Die Datei greift.
- claude-flow: `claude mcp list` in einem frischen Prozess zeigt keinen claude-flow mehr. Die laufende VS-Code-Session meldete den 30-Sekunden-Timeout trotzdem noch, weil ihr Prozess vor dem Umbenennen der `~/.mcp.json` gestartet war.
- Rest gefunden: `SecondBrain/.claude/settings.local.json` hatte noch `enabledMcpjsonServers: ["claude-flow"]`. Entfernt.

### Nicht gewirkt

- Die VS-Code-Session lief nach `/clear` weiter auf Fable 5.1 mit Effort Ultracode. Der Picker in VS Code gewinnt pro Session ueber settings.json, und `/clear` startet den Prozess nicht neu.
- Konsequenz: Modell und Effort im Picker von Hand auf Opus und medium stellen, danach die Extension neu starten.

### Naechster Schritt

- Nach dem Neustart pruefen: Modell Opus, Effort medium, keine claude-flow-Meldung.
- Messung am 2026-10-01 per `/usage` bleibt.

## 2026-09-24 CLAUDE.md-Umbau und Effort-Regel

### Ausgangslage

- Wochenlimit trotz Claude Max 20x regelmaessig gerissen.
- Effort-Stufe "ultracode"/"xhigh" dauerhaft aktiv, unabhaengig von der Aufgabengroesse.
- 1M-Kontext-Modell im Einsatz, Sessions liefen bis 90 MB Transkript auf.
- CLAUDE.md-Regel "immer Agenten-Team, nie Solist" erzwang Sub-Agents auch bei kleinen Aufgaben.
- 97 Skills und 116 Agent-Definitionen installiert, davon viele claude-flow-Reste ohne aktuellen Nutzen.

### Geaendert

- Betriebsregeln Claude Code ergaenzt: Kontext-Cap 150k Tokens pro Session.
- Effort-Standard auf medium gesetzt statt dauerhaft ultracode/xhigh.
- Rollenaufteilung festgelegt: Lead auf Opus, Sub-Agents auf Sonnet, Fable nur auf Zuruf.
- Sub-Agents werden erst ab zwei unabhaengigen Teilaufgaben eingesetzt, nicht pauschal.
- Workflows laufen nur noch auf ausdrueckliche Anweisung.
- /usage-Check fest eingeplant: montags und donnerstags, mit Sonnet-Fallback sobald ueber 60 Prozent verbraucht.
- Template-Platzhalter aus der CLAUDE.md entfernt.
- claude-flow-MCP deaktiviert.
- Workflow-Kostenwarnung wieder aktiviert.

### Erwartung

- Wochenlimit haelt unter normaler Nutzung.
- Qualitaet steigt eher, weil der Kontext klein und fokussiert bleibt, statt durch riesige Transkripte zu verwaessern.

### Messung

- Naechste Pruefung: 2026-10-01, donnerstags per `/usage`, Fokus auf die Opus-Zeile.

### Offen

- Skool-Kurs (Name, Anbieter, Module) noch eintragen, siehe [[Lernplan]].
- Skills und Agent-Definitionen ausduennen wurde bewusst NICHT gemacht, steht noch aus.
- Vault-CLAUDE.md hat noch Template-Platzhalter, die bereinigt werden muessten.
