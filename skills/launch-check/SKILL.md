---
name: launch-check
description: >
  Prueft eine KI-gebaute Website oder Web-App vor dem Livegang: von aussen per Befehl (Header, offene
  Ports, leerer Quelltext, robots/sitemap/llms.txt, Mail-Faelschungsschutz), per Hand (Registrierung mit
  Wegwerf-Mail), als Code-Audit (Secrets auch im Git-Verlauf, serverseitige Rechte, Zahlungen, Uploads)
  und auf KI-Spuren, SEO (auch ueber alle Seiten: verwaiste, duenne und konkurrierende Seiten) und
  Konversion. Liefert eine Rot/Gruen-Liste mit Beleg je Punkt. Ausserdem
  Vorgaben vor dem Bauen gegen generisches KI-Design. Nutzen bei "launch check", "vor dem Livegang",
  "ist die Seite fertig", "Website pruefen", "vibe-coded app absichern", "go-live", "bevor wir launchen",
  "sieht das nach KI aus", "Design-Vorgaben fuer die neue Seite", "verwaiste Seiten",
  "Keyword-Kannibalisierung".
version: 1.3.0
user-invocable: true
---

# launch-check — Website oder Web-App vor dem Livegang

Gebuendelt aus rund 20 Reels (Sicherheits-, SEO- und Launch-Listen verschiedener Creator, Stand 10/2026).
Fuenf davon lieferten je eine "20-Punkte-Liste"; hier steht die zusammengefuehrte Fassung, und zu jedem
Punkt der **Pruefweg**. Eine Liste ohne Pruefweg ist eine Bitte, keine Pruefung.

Zwei Modi:
- **Vorher** (neues Projekt, Redesign): Abschnitt V, dann bauen.
- **Pruefen** (Standard): Abschnitte A bis F, Ergebnis nach "Bericht".

Fremde Seiten nur mit Auftrag des Betreibers scannen (Port-Scan, Header-Abruf). Eigene Seiten: frei.

## V. Vor dem Bauen: Vorgaben statt "mach es modern"

1. **Styleguide als Datei mitgeben.** Moodboard (Pinterest o. ae., bewusst mutig oder texturlastig),
   Schriften, Hauptfarbe plus zweite und dritte aus einem Palettentool, alles in einem Board, als PDF
   exportiert. Dieses PDF geht in jeden Bau-Prompt. Ohne Datei raet das Modell und landet beim Durchschnitt.
2. **Stil beim Namen nennen**, nie "modern" oder "clean": Swiss design, Editorial, Bento-Grid,
   Neo-Brutalism, Glassmorphism, Neumorphism, Claymorphism, Y2K, Synthwave, Scrapbook, Maximalism,
   Wabi-sabi.
3. **Neutrale Palette plus genau eine unerwartete Aktionsfarbe** (z. B. Blau/Weiss mit Pink oder
   Orange fuer CTAs). Rot ist fuer Zerstoerung reserviert, nicht fuer Logout oder Hervorhebung.
   Werte statt Absicht (aus Karussells, 10/2026):
   - Kein reines `#000000` und kein `#ffffff`: getoente Dunkelwerte (`#161616`, `#1A0706`,
     `#112532`) und getoentes Weiss (`#f5f4f2`, `#FFFAED`, `#F1ECE6`).
   - Gesaettigte Grundfarben (`#ff0000`, `#0000ff`) durch eine abgedunkelte Stufe ersetzen, z. B.
     Blau `#1c47c6`, Rot `#8e0300`, Gruen `#395b39`.
   - Palette aus einem Referenzfoto ziehen und auf **drei benannte Hex-Werte** festlegen
     (kraeftige Hauptfarbe, Kontrastakzent, heller Neutralton), z. B. `#0147BA` / `#E34F33` /
     `#F3E6CE`. Text auf einer Farbflaeche in einer dunklen Palettenfarbe statt Schwarz;
     Kontrast pruefen (WCAG AA 4,5:1).
   - Palette vor dem Festlegen auf Mockups ansehen (colors-visualizer.vercel.app), nicht nur
     als Farbfelder.
4. **Ein Schriftpaar, immer dasselbe:** laute Display-Schrift plus ruhige Textschrift (Beispiele
   aus einem Karussell: Archivo + Abril, Athelas + Vanguard). Bezahlte Display-Schrift mit
   freiem Ersatz hinterlegen. Pruefen auf der echten Seite (Chrome-Erweiterung typeface.fyi:
   Schrift, Groesse, Zeilenhoehe, Laufweite per Regler).
5. **Komponentenbasis vom ersten Commit an** (shadcn o. ae.), damit nicht jede Seite die UI neu erfindet.
6. **Zerstoererische Aktionen** (Loeschen, Konto aufloesen):
   - Buttons nennen die Aktion: "Projekt loeschen" / "Projekt behalten", nie "Sind Sie sicher? Ja/Nein".
   - Loeschen nie auf der Position des Bestaetigungsbuttons; Primaerposition hat der sichere Weg.
   - Am Seitenende in einer umrandeten Gefahrenzone; fuer Konto und Projekt Karenzzeit (z. B. 14 Tage).
   - Statt Dialog: Gedrueckt-halten mit fuellendem Ring (Haltezeit einstellbar, Reel: 300 ms).
7. Interne Werkzeuge: mit fuenf Screens anfangen (Dashboard mit "braucht Aufmerksamkeit", Aufgaben,
   Kunden/Projekte, durchsuchbares Wissen, Rollen und Rechte), nicht mit zwanzig.

## A. Von aussen (Befehle, keine Annahmen)

Mit `URL` = Startseite, `HOST` = Domain:

```bash
curl -s "$URL" | grep -o '<title>[^<]*</title>'
curl -s "$URL" | grep -i -o '<h1' | wc -l
curl -sI "$URL" | grep -i -E 'strict-transport|content-security|x-frame|referrer-policy|permissions-policy|^server:|x-powered-by'
curl -s -o /dev/null -w '%{http_code}\n' "$URL/gibt-es-nicht-$RANDOM"
for p in robots.txt sitemap.xml llms.txt; do curl -s -o /dev/null -w "$p %{http_code}\n" "$URL/$p"; done
dig +short TXT "_dmarc.$HOST"
dig +short DS "$HOST"
for p in 21 22 3306 5432 6379 27017; do nc -z -G 3 "$HOST" $p 2>/dev/null && echo "Port $p OFFEN" || echo "Port $p zu"; done
```

`nmap` und `gitleaks` sind auf dem Mac nicht installiert (Stand 30.10.2026); `nc` reicht fuer die
Portpruefung. In Sitzungen mit context-mode leitet ein Hook `curl` um: den Block dann ueber
`ctx_execute` (Sprache shell) ausfuehren. Gegentest am 30.10.2026 gegen example.com: alle Befehle liefen.

| Befund | Rot, wenn |
|---|---|
| Titel / H1 | Titel "Vite App" oder auf jeder Seite gleich; H1-Zaehler 0 (Quelltext leer: SPA ohne Vorrendern, Suchmaschinen und KI-Crawler sehen nichts) oder groesser 1 |
| Header | HSTS, CSP, X-Frame-Options, Referrer-Policy oder Permissions-Policy fehlt; `Server`/`X-Powered-By` mit Versionsnummer |
| 404 | Statuscode 200 (Soft-404) oder Standardseite des Hosters |
| robots.txt | fehlt, oder sperrt KI-Crawler ungewollt; sitemap.xml fehlt |
| DMARC / DNSSEC | leer: Mails im Namen der Domain faelschbar |
| Ports | Datenbank-Port (3306, 5432, 6379, 27017) offen; FTP offen |

Dazu: `curl -s "$URL" | grep -o 'src="[^"]*\.js"'`, Bundle laden, nach `sourceMappingURL` suchen
(Source Maps gehoeren nicht in Produktion) und Groesse notieren. WordPress: Autorennamen nicht ueber
RSS/`?author=1` auslesbar, Login nicht offen und unbegrenzt.

## B. Von Hand (fuenf Minuten, findet, was kein Scanner findet)

1. Registrieren mit einer Wegwerf-Adresse (10-Minute-Mail) und Passwort `123456`. Geht beides durch:
   rot (keine Bestaetigungsmail, keine Passwortregel). Bei Clerk: Wegwerf-Mails per Einstellung sperren.
2. Den Platzhalter aus dem eigenen Eingabefeld auf der Live-URL abschicken. Laedt es endlos: haengt an
   lokaler Umgebung (localhost-URL, fehlende Umgebungsvariable).
3. Auf einem echten Telefon durchklicken, Konsole am Desktop ohne Fehler.
4. Zweites Konto: Kann es Datensaetze des ersten sehen oder aendern, indem man die ID in URL oder
   Anfrage tauscht? Dann rot (fehlende serverseitige Rechtepruefung).
5. **8-Sekunden-Test** mit jemandem, der die Seite nie sah: 8 Sekunden zeigen, schliessen, fragen
   "Was biete ich an? Was merkst du dir? Was habe ich konkret gemacht?" Kann die Person es
   nicht wiedergeben: rot (Darstellung unklar, nicht die Arbeit).

## C. Code-Audit (Auftrag an einen Sub-Agent, Ergebnis mit Fundstelle)

Zuerst die **Zugriffsmatrix** (Rolle, darf lesen, darf schreiben) in die CLAUDE.md des Projekts.
Sicherheitsfehler entstehen meist aus fehlendem Kontext, nicht aus schlechtem Code. Dann pruefen:

- **Secrets:** keine `.env` im Repo, keine Schluessel im Frontend-Bundle, **auch nicht im Git-Verlauf**
  (`git log -p --all | grep -n -E 'sk_live|sk-ant|AKIA|service_role|PRIVATE KEY'`; die Ausgabe nie in
  Bericht oder Chat kopieren, nur Commit und Datei nennen). Kurzlebige Zugangsdaten statt langlebiger Schluessel, wo moeglich.
- **Rechte nur serverseitig:** jede Route prueft Anmeldung und Besitz; Row Level Security an; Preis,
  Rolle, Rabatt und Besitzer-ID nie aus dem Client uebernehmen.
- **Mandantentrennung:** `enable row level security` in den Migrationen ist kein Beleg. Gruen erst
  mit pgTAP-Test je Tabelle unter `supabase/tests/`, der Erlauben und Verweigern fuer `anon` und
  `authenticated` prueft (`supabase test db`), oder mit der Zwei-Konten-Gegenprobe (B4). Am echten
  Projekt muss `select tablename from pg_tables where schemaname = 'public' and not rowsecurity;`
  leer sein (Security Advisor, Lint `0013_rls_disabled_in_public`). Sonst `ungeprueft`.
- **Rate Limiting:** oeffentliche Endpunkte (Login, Registrierung, Passwort-Reset, Formulare) per IP,
  denn dort ist noch niemand angemeldet; angemeldete Endpunkte zusaetzlich per Nutzer. Antwort 429.
- **Eingaben:** serverseitig validieren; SQL nur parametrisiert; Nutzerinhalt nie als rohes HTML.
- **Sitzungen:** Cookies HttpOnly, Secure, SameSite; CSRF-Schutz; alle Sitzungen beenden bei
  Passwortwechsel; Reset-Links laufen ab; Login verraet nicht, ob eine Adresse existiert.
- **Uploads:** Dateityp-Whitelist, Groessenlimit, Storage-Bucket nicht oeffentlich lesbar.
- **Zahlungen:** Idempotency-Key je Zahlungsversuch (Client erzeugt UUID, Server speichert zuerst und
  gibt bei Wiederholung das gespeicherte Ergebnis zurueck); Status als angehaengte Ledger-Zeilen, nie
  ueberschrieben; Absicht vor dem Anbieter-Aufruf ins Ledger; Webhooks: Signatur pruefen, Event-ID gegen
  Doppelverarbeitung, dann anhaengen. Siehe [[2026-08-15 Payment-Architektur — Idempotenz, Ledger, Webhooks]].
- **KI-Funktionen:** Nutzereingaben gegen Prompt-Injection filtern, personenbezogene Daten in
  Ausgaben maskieren, Werkzeugrechte je Aufgabe (lesen/schreiben/ausfuehren getrennt).
- **Pakete:** `npm audit` findet nur bekannte Luecken, keine erfundenen Pakete. Jede Abhaengigkeit
  gegen die Registry pruefen: `npm view <paket> name time.created repository.url`. 404 heisst: von
  der KI erfunden, nie installieren, denn Angreifer registrieren solche Namen (Slopsquatting). Wenige
  Wochen alt oder ohne Repo: verdaechtig. Installieren mit `npm ci` aus dem Lockfile,
  `ignore-scripts=true` in `.npmrc` (OWASP NPM Security Cheat Sheet).
- **Backup:** Supabase sichert taeglich erst ab dem Pro-Plan (7 Tage), Free gar nicht; dort
  regelmaessig `supabase db dump` an einen anderen Ort. Dateien im Storage stecken in keinem
  Datenbank-Backup. Gruen erst nach einer Rueckspielprobe (Backup in ein neues Projekt oder eine
  lokale Datenbank, Zeilen zaehlen); ohne Probe `ungeprueft`.
- **Betrieb:** Fehler-Tracking, Audit-Log fuer Rechte- und Zahlungsaenderungen, Loeschkonzept, das
  wirklich loescht.

Die Liste ersetzt keinen Pentest; bei Zahlungen und Gesundheits- oder Sozialdaten einen anbieten.

## D. KI-Spuren (Abnahme der Optik)

Rot ist jeder dieser Punkte: Emojis als Icons; lila Verlauf im Hero; KI-Standardueberschrift ("Unlock
the power of ..."), Fuellsaetze; erfundene Testimonials oder Logos; Live-Adresse `*.vercel.app`,
`*.netlify.app` statt eigener Domain; Stockfotos statt echter Fotos; ueberall gleicher Seitentitel.

## E. Auffindbarkeit (je Seite und ueber alle Seiten)

Je Seite: eigener Titel, Meta-Description, OG-Bild, Canonical, genau ein H1, `lang`, Alt-Texte, Favicon,
strukturierte Daten (Organisation, Leistung, FAQ). Google Search Console eingerichtet.
**Wortwahl aus ChatGPT abschauen:** Frage zum eigenen Angebot in ChatGPT mit Websuche stellen,
Chat-ID aus der URL (nach `/c/`) kopieren, DevTools > Netzwerk, ID als Filter, neu laden, Eintrag
anklicken, Reiter Response, nach `queries` suchen. Diese Suchbegriffe in Titel, Slug, H1 und erste
Saetze. (Interne Schnittstelle, kann sich jederzeit aendern.)

**Ueber alle Seiten** (Seiten aus der Sitemap laut robots.txt, sonst `/sitemap.xml`, nicht nur die Startseite). Skript neben dieser
Datei, nur Standardbibliothek; liest, was ein Crawler ohne JavaScript sieht:

```bash
python3 scripts/seitenstruktur.py "$URL"
```

Es listet je Seite Woerter im Hauptinhalt, eingehende interne Links, Titel und H1 und meldet
`VERWAIST`, `NICHT IN SITEMAP`, `DUENN` und die aehnlichsten Seitenpaare (`AEHNLICH`). Das sind
Kandidaten; das Urteil faellt nach Lesen der Seiten.

| Befund | Rot, wenn |
|---|---|
| Verwaiste Seite | `VERWAIST`: Seite steht in der Sitemap, keine andere Seite verlinkt sie. Google: "Every page you care about should have a link from at least one other page on your site." `NICHT IN SITEMAP` allein ist nicht rot, aber zu nennen; noindex-Seiten (Danke, Warenkorb) fehlen dort zu Recht |
| Keyword-Kannibalisierung | Zwei Seiten zielen auf dieselbe Suchanfrage, auch umformuliert ("Steuerberater Ulm" und "Steuerberatung in Ulm beauftragen"). Je Seite den Hauptsuchbegriff in einer Zeile aus Titel, H1 und erstem Absatz notieren und vergleichen; ein `AEHNLICH`-Paar deutlich ueber den uebrigen ist ein starker Hinweis. Verschiedene Suchabsichten (Leistungsseite und Kosten-Ratgeber) sind keine Kannibalisierung. Nach dem Livegang belegen: Search Console > Leistung > Suchanfrage filtern > Reiter Seiten, mehr als eine URL mit Impressionen |
| Duenne Seite | `DUENN` und die Seite beantwortet die Frage ihres Suchbegriffs nicht selbst (Leistungsseite mit zwei Saetzen). Impressum, Datenschutz, Kontakt und reine Uebersichtsseiten sind kurz und richtig: nicht rot. Eine Mindestwortzahl gibt es bei Google nicht ("No, we don't"); die Schwelle `--duenn` (Vorgabe ein Drittel des Medians) sucht nur Kandidaten |

Abhilfe in den Bericht schreiben, nicht ungefragt umsetzen: Ueberlappende Seiten zusammenlegen, also
die staerkere URL behalten, den Inhalt der schwaecheren einarbeiten, 301 von alt auf neu, interne
Links umbiegen, alte URL aus der Sitemap. Duenne Seite mit eigenem Suchbegriff ausbauen, sonst
einarbeiten. Verwaiste Seite verlinken oder entfernen. Bei SPA ohne Vorrendern zeigt das Skript
ueberall 0 Woerter; dann gilt der rote Befund aus A.

## F. Konversion

CTA im ersten Bildschirm; auf dem Telefon ein haftender CTA; Telefonnummer antippbar; Formular mit
verstaendlichen Fehlermeldungen und einer Dankesseite; Antwortzeit-Versprechen ("Antwort in 24 h");
eine Seite je Leistung; Fallbeispiele mit Zahlen; fuenf echte FAQs; Ueber-uns mit Geschichte.
Shops (Testideen aus einem Reel, Zahlen unbelegt): Newsletter-Popup erst nach 6–10 s; ab rund 50
Produkten Filter; Produktfotos am Menschen statt flach gelegt.

**Recht (DE):** Impressum; Datenschutzerklaerung nennt Datenerhebung, KI-Nutzung und Drittanbieter;
bei Abos Kuendigungsbutton (§ 312k BGB) und Kuendigung nicht schwerer als Abschluss. Fachfragen nicht
aus Reels beantworten, siehe [[Recht und Vertraege]].

## Bericht

Je Punkt eine Zeile: `rot | gruen | ungeprueft` — Punkt — Beleg (Befehl und Ausgabe, Fundstelle
`datei:zeile`, oder was von Hand passiert ist). Oben die Zahl `N rot, M gruen, K ungeprueft`.
"Ungeprueft" nie als gruen zaehlen. Rote Punkte nicht ungefragt beheben, wenn der Auftrag "pruefen" war.

## Quellen

Reel-Notiz [[2026-10-30 Reel-Sammlung 134 Reels zu Skills]]; Vorgaengernotizen
[[2026-08-15 Stehende Sicherheitsregeln und Zugriffsmatrix]], Themenseite [[Sicherheit und KI-Agenten]].
Pruefwege in C (Stand 11/2026): Supabase-Doku Row Level Security, Database Advisors und Database
Backups; OWASP NPM Security Cheat Sheet. Pruefwege in E, ueber alle Seiten: Google Search Central,
Link best practices, Creating helpful content, Consolidate duplicate URLs.
