---
name: reel-ingest
version: 1.5.4
description: Verarbeitet Reels (Instagram, YouTube Shorts, TikTok) — per Telegram oder direkt im Chat. Zwei Modi: ohne Praefix wird die gezeigte Technik in einem Projekt auf einem eigenen Branch umgesetzt; mit Praefix "design:" wird das Reel nur analysiert (Farbpalette mit Hex-Werten, Schrift-Einschaetzung, Hook-Aufbau, Schnittrhythmus, Transkript) und nichts gebaut. Nutzen, sobald ein Link auf instagram.com/reel, youtube.com/shorts oder tiktok.com kommt, ein Video-Anhang ankommt, oder ein lokaler Videopfad zur Analyse genannt wird. Dritter Modus "Sammeln": viele gespeicherte Reels (Instagram-DMs des Lesekontos, Sammlung, Linkliste) zu wenigen wiederverwendbaren Skills buendeln statt ein Skill je Reel. Nicht nutzen bei Praefix "fyi:".
---

## Vault-Pfad

`<VAULT>` steht in diesem Skill für den Pfad deines Obsidian-Vaults. Er steht in `~/.config/claude-skills/einstellungen.json` unter `vault`. Lies ihn vor dem ersten Zugriff:

```bash
python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.config/claude-skills/einstellungen.json")))["vault"]))'
```

Fehlt die Datei oder der Schlüssel oder ist der Wert leer, frag nach dem Pfad. Fehlt die Datei, lege sie mit `{"vault": "<Pfad>"}` an. Sonst trag den Pfad unter `vault` in die bestehende Datei ein und lass alle anderen Schlüssel unverändert.

# Reel-Ingest

Diese Anweisung setzt ein, sobald ein Dossier vorliegt oder vorliegen muss.
Der Hook (`hooks/reel_guard.sh` -> `cli.py`) hat fuer Reels mit Link bereits
heruntergeladen, Keyframes geschnitten und ein Transkript besorgt; die
Ausgabe des Hooks nennt den Dossier-Ordner. Fuer weitergeleitete Video-
Anhaenge fehlt dieser automatische Schritt — dafuer gilt Abschnitt 0.

## Welcher Modus — zuerst entscheiden, dann arbeiten

| Eingang | Modus | Was passiert |
|---|---|---|
| Praefix `design:` | **Analyse** | Design-Bericht, **kein Code, kein Branch, kein Projekt noetig** |
| kein Praefix | **Umsetzen** | wie bisher: Technik erkennen, Projekt zuordnen, auf Branch bauen |
| Praefix `fyi:` | — | Skill gar nicht nutzen |
| mehrere Reels mit Wunsch nach Skills daraus | **Sammeln** | Abschnitt S: buendeln, abgleichen, bestehende Skills erweitern |

Der Modus wird **nie geraten**. Steht kein Praefix da, gilt „umsetzen" —
auch wenn das Reel nach Design aussieht. Wer im falschen Modus arbeitet,
baut entweder ungefragt Code oder liefert einen Bericht, wo eine Umsetzung
erwartet wurde. Ist der Auftrag unklar, per Telegram nachfragen statt zu
waehlen.

Beide Modi nutzen dieselbe Beschaffung (Abschnitt 0/1). Erst danach trennen
sie sich: Analyse geht zu Abschnitt A, Umsetzung zu Stufe 4.

## Reels direkt im Chat statt ueber Telegram

Nennt der Nutzer im Chat einen lokalen Videopfad (oder legt eine Datei ab),
braucht es weder Telegram noch `download_attachment`: `verarbeite_datei`
nimmt jeden lokalen Pfad. Derselbe Aufruf wie in Abschnitt 0, Schritt 2.
Auch hier gilt die Modus-Tabelle oben: sagt der Nutzer „analysier das",
ist das der Analyse-Modus, auch ohne getipptes `design:`.

## S. Sammelmodus — viele Reels, wenige Skills

Ausloeser: "meine gespeicherten Reels", "die Reels im Chat", "mach Skills aus den Reels",
mehrere Links auf einmal. Ergebnis sind **wenige Skills nach Thema**, nie einer je Reel: Fuenf
Reels, die dasselbe lehren, ergeben eine Fassung, die beste.

**S1. Holen.** Gespeicherte Beitraege des eigenen Kontos (`<reel_konto>` aus der Einstellungsdatei; ist der Wert leer,
frag den Nutzer nach dem Kontonamen) kommen nur ueber den
Instagram-Datenexport: Nutzer fordert in der App „Gespeichert", JSON, Zeitraum ab dem letzten Export
an; die ZIP landet in `~/Downloads`. Dann, mit allen frueheren Sammel-Notizen als `--bekannt`:

```bash
cd ~/.claude/skills/reel-ingest && venv/bin/python scripts/sammle.py export ~/Downloads/instagram-<reel_konto>-<DATUM>-*.zip --bekannt <VAULT>/04\ Ressourcen/Reel-Analysen/*.md > "$TMPDIR/reel-links.txt"
```

Danach weiter mit `hole` wie unten. Muse (Meta) kann das spaeter vielleicht direkt, ist in DE noch
nicht verfuegbar und hat keine CLI.

Erfahrung aus dem Lauf vom 18.11.2026: Die Bereit-Mail kann ausbleiben; dann liegt die Datei in der
App unter „Deine Informationen herunterladen" > „Aktuelle Downloads". Der Export kann mehr liefern als
angefordert (ein ganzes Jahr statt einer Woche, dazu DMs und Storys). Deshalb nie `--seit` als
Abgleich nehmen, sondern `--bekannt`, und die ZIP nach der Auswertung loeschen. Damit `--bekannt`
traegt, muss die Sammel-Notiz die Shortcodes ALLER Beitraege enthalten, auch der nicht ladbaren:
Gegentest nach dem Ablegen ist ein zweiter `export`-Lauf, der 0 Links liefern muss.

Reels aus DMs (Lesekonto = Chrome-Profil `reel_chrome_profil` aus der Einstellungsdatei, OpenCLI; ist es leer, bricht `dm` mit `FEHLER reel_chrome_profil fehlt in <Pfad>` und Exit 2 ab, dann beim Nutzer nachfragen und eintragen):

```bash
cd ~/.claude/skills/reel-ingest && venv/bin/python scripts/sammle.py dm > "$TMPDIR/reel-links.txt"
cd ~/.claude/skills/reel-ingest && venv/bin/python scripts/sammle.py hole $(cat "$TMPDIR/reel-links.txt")
```

`dm` startet Chrome im Profil, falls OpenCLI nicht verbunden ist, und liest den obersten Chat
(`--chat NAME` fuer einen anderen). **Vorher dem Nutzer ansagen: Chrome springt waehrend des Laufs
(10–20 Minuten) immer wieder nach vorn**, weil Chrome einen verdeckten Tab nicht rendert. Nur starten,
wenn er nicht gerade arbeitet. Hintergrund (am 30.10.2026 erst beim dritten Anlauf verstanden, erster
Lauf fand 2 statt 134): Der Verlauf ist umgekehrt (scrollTop 0 = unten), laedt aeltere Nachrichten erst
oben nach und ist virtualisiert; geteilte Reels haben kein href. Das Skript liest die Medien-ID aus
`ig_cache_key` der Vorschaubilder (base64) und rechnet sie in den Shortcode um. Plausibel ist das
Ergebnis nur, wenn der aelteste Fund weit zurueckreicht; die Zeile "Verlauf: ..." auf stderr nennt die
Zahl. `hole` laedt in niedrigster Qualitaet mit Ton (bei Instagram meist 720p), traegt Caption,
Uploader, Dauer und Datum ins Dossier nach und loescht alle Videodateien sofort. Linklisten aus
anderer Quelle gehen direkt an `hole`. Viele Links parallel:
`xargs -P 4 -n 6 venv/bin/python scripts/sammle.py hole < links.txt` (rund 25 s je Reel und Prozess).
Bild- und Karussell-Posts (yt-dlp: "No video formats found") holt `hole` automatisch ueber
gallery-dl mit den Cookies des Lesekontos: Ordner `bild-<shortcode>`, jede Folie ein Frame (auf
1080 x 1350 gebracht), kein Transkript, Video-Folien als `videos_ausgelassen` gezaehlt. Erst wenn
auch das scheitert, kommt eine `FEHLER`-Zeile; diese im Bericht als nicht ausgewertet nennen.

**S2. Verstehen** je Dossier wie Stufe 3: Caption, ganzes Transkript, alle Frames.
`sammle.py steckbrief <ORDNER>...` legt je Dossier `kontaktbogen.jpg` (alle Frames) und
`steckbrief.md` an. Ab etwa 10 Reels auf Sonnet-Sub-Agents verteilen (rund 20 Reels je Agent), Ergebnis
als Datei je Paket. **Sub-Agents lassen Kontaktboegen aus** (am 30.10.2026 vier von fuenf): Im Briefing
je Block die Zeile `Frames: gesehen` verlangen und vor dem Buendeln zaehlen, dass Bloecke und
Frames-Zeilen gleich viele sind. Je Reel eine Liste **atomarer Lehren**: eine Handlung, die man
anders macht, mit Beispiel aus dem Reel.

**S3. Aussieben.** Eine Lehre fliegt raus, wenn sie kein Verhalten aendert ("definiere klar,
was du willst", "sei konsequent") oder ein Profi sie ohne das Reel genauso sagen wuerde. Was
bleibt, hat einen konkreten Kniff, eine Zahl, ein Werkzeug oder eine Reihenfolge.

**S4. Buendeln und abgleichen.** Lehren nach Thema clustern. Je Cluster zuerst gegen bestehende
Skills (`~/.claude/skills/`) und Agenten pruefen: Ist es schon da, nur die fehlende Luecke
ergaenzen (Regel "erweitern statt neu"). Lehren mehrere Reels dasselbe unterschiedlich, bleibt
die Fassung, die Doku oder ein eigener Test bestaetigt (Stufe 4), nicht die lauteste.

**S5. Bauen mit Beleg.** Jede Erweiterung bekommt einen Gegentest, der vorher rot ist. Was eine
Sperre oder einen Schalter verspricht, in einer echten Wegwerf-Sitzung pruefen, nicht aus dem
Code schliessen. Danach Skill-Lifecycle (publish_skill.py, Vault-Doku).

**S6. Aufraeumen und ablegen.** Dossiers loeschen, sobald die Notiz steht:

```bash
cd ~/.claude/skills/reel-ingest && venv/bin/python scripts/sammle.py aufraeumen <ORDNER> <ORDNER>
```

Vault-Notiz nach Abschnitt V, aber **eine je Sammellauf** mit allen Reels, ihren Lehren, was
gestrichen wurde und warum, und welcher Skill was aufgenommen hat.

## 0. Weitergeleitete Videos (Stufe 1 und 2 von Hand)

Hat die Telegram-Nachricht ein `attachment_file_id` statt eines Links,
konnte der Hook nichts tun — `download_attachment` ist ein MCP-Werkzeug,
eine Shell kommt daran nicht heran. Dann selbst uebernehmen:

1. `download_attachment` aufrufen und den zurueckgegebenen Pfad notieren.
2. Diesen Pfad an `verarbeite_datei` uebergeben — woertlich:

```bash
cd ~/.claude/skills/reel-ingest && ~/.claude/skills/reel-ingest/venv/bin/python -c "
from pathlib import Path
from src.pipeline import verarbeite_datei
import json; print(json.dumps(verarbeite_datei(Path('<PFAD>')), ensure_ascii=False))"
```

Das vorangestellte `cd` ist noetig: `python -c` setzt `sys.path[0]` auf das
aktuelle Arbeitsverzeichnis, nicht auf den Ort des Skripts. Der Agent steht
nach `download_attachment` typischerweise nicht im Repo-Wurzelverzeichnis —
ohne das `cd` schlaegt der Import von `src.pipeline` mit
`ModuleNotFoundError` fehl.

3. Mit dem zurueckgegebenen Dossier bei Stufe 3 weitermachen, genau wie bei
   einem per Link automatisch erzeugten Dossier.

Ist der Anhang groesser als 20 MB, lehnt die Bot-API ihn ab. Dann nicht
weiter versuchen — per Telegram um den Link statt der Datei bitten.

## 1. Stufe 3 — Verstehen

Dossier lesen: `dossier.json` im vom Hook genannten Ordner (oder im
`ordner`-Feld des Dossiers aus Abschnitt 0). Danach alle Pfade in `frames`
einzeln per Read ansehen — nicht nur den ersten. Transkript (`transkript`,
`transkript_quelle`) und `caption` mitlesen.

Sind `frames_fehler` oder `transkript_fehler` gesetzt (nicht `None`), ist
das Dossier unvollstaendig: die eine Haelfte hat geliefert, die andere ist
ausgefallen. Das im spaeteren Bericht nennen — ein unvollstaendiges Dossier
darf nie als vollstaendiges gelesen und stillschweigend weiterverarbeitet
werden.

Aus alldem festhalten: welches Tool oder welche Bibliothek gezeigt wird,
welche Technik oder welcher Kniff demonstriert wird, welches Repo aus der
Registry (siehe Stufe 5) dazu passen koennte, und welcher konkrete
Anwendungsfall im Reel vorkommt.

## A. Analyse-Modus (`design:`) — verstehen statt bauen

Gilt **statt** der Stufen 4 bis 6. Kein Projekt, kein Branch, kein Code.
Grundlage ist dasselbe Dossier aus Stufe 3.

### A1. Farbpalette — gemessen, nicht geschaetzt

Steht als `palette` im Dossier: `[{"hex": "#1e3a8a", "anteil": 0.42}, ...]`,
absteigend nach Anteil. Gemessen wird ueber das **ganze Video**, alle 0,5
Sekunden abgetastet — nicht ueber die Keyframes. Der Unterschied ist keine
Feinheit: ein Testvideo aus zwei gleich langen Farbhaelften ergab ueber die
Keyframes eine Palette mit EINER Farbe zu 100 Prozent, weil Keyframes an
Szenenwechseln entstehen. `anteil` ist damit Zeit- mal Flaechenanteil, also
das, was ein Betrachter als „dominante Farbe" wahrnimmt.

Ist `palette_fehler` gesetzt, ist die Palette **leer, weil die Messung
ausfiel** — nicht, weil das Reel farblos waere. Das im Bericht so sagen.

Nuetzlich fuer den Bericht: welche Farbe traegt den Hintergrund, welche ist
Akzent (kleiner Anteil, hoher Kontrast), und ob die Palette ueber die
Laufzeit wechselt (dann Palette je Abschnitt statt global nennen).

### A2. Schrift — Einschaetzung, keine Bestimmung

**Es gibt hier keine zuverlaessige Fonterkennung, und es wird auch keine
behauptet.** Was geliefert wird: die Frames ansehen und die Schrift
BESCHREIBEN (Sans/Serif, geometrisch oder humanistisch, Strichstaerken-
kontrast, x-Hoehe, Besonderheiten wie einstoeckiges `a` oder abgeschnittene
Terminals), daraus **Kandidaten** nennen, und die praktisch brauchbare
kostenlose Entsprechung (Google Fonts), die sich wirklich einsetzen laesst.

Im Bericht immer als Einschaetzung kennzeichnen. Ein behaupteter
Schriftname, der falsch ist, kostet den Nutzer eine Lizenzrecherche fuer
die falsche Schrift. **„Sieht aus wie" ist eine ehrliche Aussage,
„ist" waere geraten.**

### A3. Aufbau — was das Reel tatsaechlich macht

Aus Frames, Transkript und `dauer_sekunden`:

- **Hook**: was in den ersten ~3 Sekunden zu sehen und zu hoeren ist. Der
  erste Frame und die ersten Transkriptzeilen, woertlich zitiert.
- **Schnittrhythmus**: wie viele Keyframes auf welche Laufzeit kommen. Das
  ist eine Naeherung ueber Szenenwechsel, kein Schnittprotokoll — so
  benennen.
- **Text im Bild**: Overlays aus den Frames ablesen und woertlich notieren.
- **Struktur**: welche Abschnitte erkennbar sind (Hook, Aufbau, Kern,
  Schluss/CTA) und wo sie zeitlich liegen.

### A4. Ablage — siehe Abschnitt V

Die Vault-Notiz ist Pflicht, im Analyse-Modus wie im Umsetzungs-Modus. Der
gemeinsame Abschnitt steht unten unter „V. Vault-Notiz".

### A5. Was im Analyse-Modus verboten bleibt

Kein Code, kein Branch, kein Commit, kein Projekt aus der Registry noetig.
Die Umfangsbremse aus Stufe 6 entfaellt, weil nichts gebaut wird — die
Sperre gegen fremde Dateien gilt trotzdem: `kunden.json`, `kontingent.json`,
`AVV_*`, `VERARBEITUNGSVERZEICHNIS*` werden auch im Analyse-Modus nicht
gelesen.

## 2. Stufe 4 — Gegenpruefen

Die echte Dokumentation des gezeigten Tools holen — ueber context7, wenn
dort verfuegbar, sonst per WebSearch. Das Reel selbst ist keine
verlaessliche Quelle fuer Details, Parameter oder Verhalten.

**„Das Reel ist ein Fingerzeig, keine Quelle. Behauptet das Reel etwas, das
die Doku nicht hergibt, gilt die Doku."**

Weicht das Reel von der Doku ab, wird nach der Doku umgesetzt, nicht nach
dem Reel. Laesst sich die im Reel gezeigte Technik in der echten Doku gar
nicht wiederfinden, ist das ein Grund, in Stufe 6 abzubrechen und im
Bericht zu sagen, was nicht bestaetigt werden konnte.

## 3. Stufe 5 — Zuordnen

`~/.config/claude-skills/reel-ingest-projekte.md` lesen; fehlt sie, `references/projekte.beispiel.md` lesen und den Nutzer nach seinen echten Projekten fragen (Beispiel nach `~/.config/claude-skills/reel-ingest-projekte.md` kopieren und anpassen). Die Stichworte je
Registry-Eintrag ("Passt bei Reels ueber") gegen das in Stufe 3
festgehaltene Tool, die Technik und den Anwendungsfall abgleichen.

**Bei Unklarheit oder Gleichstand: nicht umsetzen, per Telegram
nachfragen.** Passt kein Eintrag oder passen mehrere gleich gut, gibt es
kein Ausweichziel — siehe „Kein Ausweichziel" unten. Erst wenn genau ein
Projekt eindeutig passt, geht es weiter zu Stufe 6.

## 4. Stufe 6 — Umsetzen

Die folgenden Regeln gelten fuer **jede** Umsetzung, ohne Ausnahme. Sie
binden diese Anweisung zur Laufzeit, wenn tatsaechlich Code in einem der
Nutzer-Projekte geaendert wird — nicht die Bearbeitung dieser Datei selbst.

- **Branch:** Umsetzung nur auf `reel/<datum>-<kurzname>`, abgezweigt vom
  Standardbranch. `main` wird nie angefasst.
- **Verboten:** kein `git push`, kein Merge, kein PR, kein Deploy.
- **Schmutziger Arbeitsbaum → Abbruch mit Meldung.** Nie stashen, nie
  committen, was der Nutzer angefangen hat.
- **Weitere Abbruchgruende:** neue Abhaengigkeit noetig,
  Schema-/Migrationsaenderung, API-Key noetig, Auth/Zahlung/Sicherheit
  betroffen, Zuordnung unklar.
- **Gesperrte Dateien, auch lesend:** `kunden.json`, `kontingent.json`,
  `AVV_*`, `VERARBEITUNGSVERZEICHNIS*` im Broken-Links-Projekt.
- **Kein Ausweichziel.** Passt ein Reel zu keinem oder zu mehreren
  Registry-Eintraegen gleich gut → Rueckfrage per Telegram.
- **Secrets:** nie Keys in Dateien. Cookie-Datei `chmod 600` und in
  `.gitignore`.
- **Sprache:** Code-Kommentare, Ausgaben und Doku auf Deutsch.

**Umfangsbremse** — vor dem Umsetzen pruefen, danach ggf. nach jedem
Bearbeitungsschritt neu:

| Bedingung | Ueber Schwelle |
|---|---|
| Geaenderte Zeilen | ueber ~150 |
| Geaenderte Dateien | mehr als 5 |

Trifft eine der beiden Zeilen zu: nicht umsetzen, Plan schicken.

## V. Vault-Notiz — in BEIDEN Modi, ohne Ausnahme

**Jedes verarbeitete Reel bekommt eine Notiz im Vault.** Nicht nur im
Analyse-Modus.

DIESER ABSCHNITT ENTSTAND AUS EINEM FEHLER: die Ablage stand zuerst nur im
Analyse-Modus. Ein Reel ueber Payment-Architektur lief im Umsetzungs-Modus
durch, die Erkenntnis wurde ausfuehrlich erklaert — und landete nirgends. Der
Nutzer musste selbst fragen, ob das Wissen im Vault sei. Es war es nicht.
**Der Denkfehler war, die Ablage an den Modus zu haengen statt an das Wissen:**
gerade im Umsetzungs-Modus faellt MEHR Verstaendnis an, weil die Technik
zusaetzlich gegen die echte Doku geprueft wird.

**Ort:** `<VAULT>/04 Ressourcen/Reel-Analysen/`,
Dateiname `JJJJ-MM-TT <sprechender Titel>.md`. Ordner anlegen, falls er fehlt.

**Inhalt, immer:**

- Frontmatter mit `tags` (Thema, nicht nur `reel-analyse`), `quelle`,
  `quelle_datum`, `erfasst`, `status`.
- Worum es geht und **warum es so gebaut ist** — nicht nur was gezeigt wurde.
  Wenn das Reel eine Entwicklung in Stufen zeigt, jede Stufe MIT ihrer
  Bruchstelle festhalten: der Wert liegt fast immer darin, woran die einfachere
  Loesung scheitert.
- Ein Abschnitt **„Offen / nicht geprueft"**. Was die Doku nicht bestaetigt hat,
  was das Reel ausgelassen hat, was ungeklaert blieb. Eine Notiz ohne diesen
  Abschnitt liest sich spaeter wie gesichertes Wissen, obwohl sie ein
  Reel-Referat ist.
- `[[Wikilinks]]` auf verwandte Notizen. Ein Link auf eine noch nicht
  existierende Notiz ist erlaubt und nuetzlich — er markiert die Luecke.

**Im Analyse-Modus zusaetzlich:** Palette als Hex-Liste mit Anteilen, die
Schrift-Einschaetzung samt Vorbehalt, der Aufbau.

**Themenseite mitpflegen:** Passt das Reel zu einem Dauerthema (Zahlungen,
Architektur, iOS, SEO …), gehoert ein Verweis in die zugehoerige Themenseite
unter `04 Ressourcen/Themen/`. Existiert keine, eine anlegen. Ohne diesen
Schritt liegt die Notiz zwar im Vault, wird aber nur gefunden, wer schon weiss,
dass es sie gibt — und dann haette man sie nicht gebraucht.

## 5. Bericht

Immer per `reply` an Telegram antworten — auch bei Fehlschlag oder
Abbruch, auch wenn in Stufe 5 nachgefragt oder in Stufe 6 abgebrochen
wurde. Nie stillschweigend enden.

Inhalt: was das Reel zeigte, welches Projekt zugeordnet wurde (oder warum
keins), was tatsaechlich gebaut wurde, auf welchem Branch, und wie das
Ergebnis zu pruefen ist. War das Dossier unvollstaendig
(`frames_fehler`/`transkript_fehler` gesetzt), das ebenfalls nennen. Lange
Berichte in mehrere `reply`-Nachrichten stueckeln statt eine Nachricht zu
ueberladen. Der Bericht selbst ist auf Deutsch (siehe Sprache-Regel in
Stufe 6), unabhaengig davon, in welcher Sprache das Zielprojekt gehalten
ist.

## 6. Laufende Arbeit hat Vorrang

Kommt ein Reel mitten in einer laufenden Aufgabe an, wird die laufende
Aufgabe zuerst fertig gemacht. Das Reel wird nicht sofort bearbeitet,
sondern als wartend gemeldet — danach folgt diese Anweisung von vorn.

## 7. Bekannte Stolpersteine

**YouTube-Downloads scheitern mit `HTTP 403`.** Symptom im Log:
`Signature solving failed` und `n challenge solving failed`. Ursache: yt-dlp
kann YouTubes JS-Challenges nicht loesen. Eine blosse JavaScript-Runtime
reicht dafuer nicht — die Challenge-Solver-Komponente muss zusaetzlich im
yt-dlp-Cache liegen. Einmaliger Fix: yt-dlp einmal mit
`--remote-components ejs:github` aufrufen; die Komponente landet danach in
`~/.cache/yt-dlp/` und wird von jedem folgenden Aufruf automatisch genutzt,
ohne dass die Option erneut angegeben werden muss.
