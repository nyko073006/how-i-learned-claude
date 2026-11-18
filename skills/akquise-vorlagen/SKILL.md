---
name: akquise-vorlagen
description: >
  Fertige Bauplaene fuer B2B-Akquise und Kundenstart: Demo fuer genau diesen Betrieb als Aufhaenger
  des Erstkontakts (Bauweg je Lead, Kanal nach UWG), Kaltmail (Aufbau Zeile fuer Zeile, drei
  Einstiege), LinkedIn-Post pruefen und bauen, taegliche Kommentar-Routine statt Posten,
  Verkaufsgespraech (Demo vorher, schweigen nach dem Preis), Onboarding in der ersten Stunde nach der
  Zusage und ein Quiz-Funnel nach Kaeufertypen aus dem CRM. Nutzen bei "Kaltakquise", "cold email",
  "schreib eine Akquise-Mail", "LinkedIn-Post", "LinkedIn Strategie", "wie kommentiere ich",
  "Kunde hat zugesagt, was jetzt", "Onboarding", "Verkaufsgespraech", "Funnel", "Quiz",
  "Erstkontakt", "Neukunden gewinnen", "Demo vorab bauen", "Probescan", "Leads ansprechen".
version: 1.2.0
user-invocable: true
---

## Vault-Pfad

`<VAULT>` steht in diesem Skill für den Pfad deines Obsidian-Vaults. Er steht in `~/.config/claude-skills/einstellungen.json` unter `vault`. Lies ihn vor dem ersten Zugriff:

```bash
python3 -c 'import json,os;print(os.path.expanduser(json.load(open(os.path.expanduser("~/.config/claude-skills/einstellungen.json")))["vault"]))'
```

Fehlt die Datei oder der Schlüssel, frag nach dem Pfad. Fehlt die Datei, lege sie mit `{"vault": "<Pfad>"}` an. Fehlt nur der Schlüssel, ergänze ihn in der bestehenden Datei und lass alle anderen Schlüssel unverändert.

# akquise-vorlagen — Demo vorab, Kaltmail, LinkedIn, Gespraech, Onboarding

Gebuendelt aus 22 Reels (Demo vorab, Kaltmail-Vorlagen, LinkedIn-Ghostwriter, Agentur-Erfahrungen,
Onboarding, Stand 11/2026). Reels sind US-gepraegt; Ton und Recht passt der Skill auf DE an.

Immer zuerst lesen: `<VAULT>/00 Kontext/Schreibstil.md`. Fuer die eigene Firma zusaetzlich `ICP.md` und `Angebot.md`;
fuer andere Projekte Zielgruppe beim Nutzer erfragen.
Preise, Kanalwahl und Netzwerken: ein Finanz-/Steuer-Agent, falls eingerichtet, sonst der Nutzer. Dieser Skill liefert Texte und Ablaeufe, keine
Strategie. **Nichts wird gesendet oder gepostet**; Ergebnis ist ein Entwurf.

## Recht DE, gilt fuer Abschnitt 1 und 2

Nach § 7 UWG, Stand der Rechtsprechung 11/2025, keine Rechtsberatung:
- **E-Mail und Direktnachrichten** in sozialen Netzwerken (LinkedIn, Xing, Instagram, WhatsApp) gelten
  als elektronische Post. Werbung darueber braucht die vorherige ausdrueckliche Einwilligung, auch bei
  Unternehmen. Eine Vernetzung oder ein Like ist keine Einwilligung (AG Duesseldorf 23 C 120/25;
  BGH I ZR 25/19; OLG Nuernberg 3 U 724/18).
- **Anruf bei Unternehmen** nur bei mutmasslicher Einwilligung, also konkretem, erkennbarem Bedarf
  des Betriebs. Blosse Branchenzugehoerigkeit reicht nicht.
- **Brief** ist zulaessig, solange der Empfaenger nicht widersprochen hat.
- **Warmer Kontakt:** Hat der Empfaenger selbst angefragt, um etwas gebeten oder im Gespraech zugestimmt
  ("schicken Sie mir das gern"), ist die Nachricht keine unverlangte Werbung. Zustimmung festhalten.
Bei Zweifel rechtlichen Rat holen; der Skill entscheidet das nicht.

## 1. Demo als Aufhaenger des Erstkontakts

Nicht pitchen, sondern beim ersten Kontakt etwas Fertiges fuer genau diesen Betrieb zeigen. Sechs Reels
von fuenf Konten zeigen das unabhaengig voneinander; der Interessent sieht sein eigenes Ergebnis statt
eines Versprechens.

Was vorab gebaut wird, je nach Angebot:
- **Website-Entwurf** fuer einen Betrieb ohne oder mit schwacher Seite.
- **Demo-Chatbot**, dessen Wissen aus der Website des Betriebs stammt.
- **Probeanruf** bei einem Telefonassistenten mit der Website als Wissensbasis.
- **Kurzanalyse oder Probescan**: drei bis fuenf konkrete Befunde zu Website, Kanaelen oder Ablauf des
  Betriebs, jeder mit Fundstelle.

Kanal (siehe Recht DE): Die US-Reels schicken die Demo per Kaltanruf oder Kaltnachricht. In DE die Demo
per **Brief** mit Kurzlink oder QR-Code schicken, oder sie **nach einem warmen Kontakt** anbieten
(Kommentar-Routine aus Abschnitt 4, Empfehlung, Messe, Anfrage): "Ich habe mir erlaubt, [Demo] fuer Sie
zu skizzieren. Darf ich Ihnen den Link schicken?" Erst nach dem Ja den Link senden. Die Frage faellt im
Gespraech oder in einem Austausch, den der Betrieb begonnen hat, nie als erste Direktnachricht: Auch
eine Bitte um Einwilligung per E-Mail oder DM werten Gerichte als Werbung.

Bauweg je Lead, damit es fuer viele Betriebe geht:
1. **Liste als CSV:** Firma, Domain, Ansprechpartner, Quelle, Kanal, Status. Firmen von Hand oder aus
   Quellen mit erlaubter Nutzung sammeln; Google Maps nicht automatisiert abgreifen
   (Nutzungsbedingungen). Personendaten nur, soweit fuer die Ansprache noetig (DSGVO).
2. **Ein fester Prompt je Domain**, als eigene Datei im Projekt: Website des Betriebs lesen, daraus
   Leistungen, Ort, Ton, Farben und haeufige Kundenfragen ziehen, daraus die Demo bauen (eine HTML-Datei
   oder ein Agent-Prompt). Der Prompt bleibt fuer alle Leads gleich, nur die Domain wechselt.
3. **Jede Demo vor dem Versand selbst ansehen.** Ein falscher Ort oder eine falsche Leistung verbrennt
   den Lead. Fehler fliessen in den Prompt zurueck, nicht in Handkorrekturen.
4. **Kennzeichnen und privat halten:** Sichtbar "Unverbindlicher Entwurf fuer [Firma]". Nur per nicht
   erratbarem Link, `noindex`, nicht oeffentlich verlinkt; Logo und Texte des Betriebs nicht als
   Referenz nutzen. Nach Absage oder 30 Tagen ohne Antwort loeschen.
5. **Nachricht oder Brief:** Zeile 1 ueber den Betrieb, Zeile 2 die Demo mit einem Satz, was sie zeigt,
   Zeile 3 Interesse erfragen ("Waere das fuer Sie interessant?"). Link statt Anhang.

Aufwand vorher rechnen: Leads je Abschluss mal Minuten je Demo (Bauen plus Ansehen). Einziger Richtwert
aus den Reels, US-Kaltanruf und Eigenangabe: ueber 100 Anrufe, 3 Termine, 1 Abschluss. Mit eigenen Werten
nach den ersten 20 Leads ersetzen und in der CSV mitzaehlen.

## 2. Kaltmail

Nur mit Einwilligung oder nach warmem Kontakt (siehe Recht DE); sonst denselben Aufbau als Brief.

Aufbau, jede Zeile eine Aufgabe:
1. **Betreff** 2–3 Woerter, klein, mit Vornamen: "frage, tobias".
2. **Erste Zeile ueber den Empfaenger**, nicht ueber dich: neue Rolle, Stellenanzeige, Zitat, Event.
3. **Ein Problem**, das daraus folgt.
4. **Eine Zeile Beleg:** aehnliche Firma, was sich messbar aenderte ("von 3 auf 5,9 Mio. in einem Jahr,
   ohne zusaetzliche Vollzeitstelle").
5. **Interesse erfragen statt Termin:** "Waere es abwegig, wenn ich Ihnen zeige, wie?" Ein CTA, keiner mehr.

Drei Einstiege, je nach Stand:
- **Fallbeispiel:** Ergebnis bei aehnlicher Firma, kostenlose Aufschluesselung anbieten. Einstieg
  "Passt vielleicht gerade nicht, aber ...".
- **Event:** Messe oder Konferenz, die die Zielgruppe in 3–6 Monaten besucht, als Anlass in Zeile 1.
  Aussteller- und Rednerlisten nicht automatisiert abgreifen.
- **Freie Ressource:** fuer den Anfang ohne Fallbeispiele (Checkliste, Kurzanalyse).
- **Direkt an Entscheider** statt Portal oder Info-Adresse; Inhalt eine eigene kurze Analyse ihres
  letzten Projekts. Versandzeitpunkt (Reel: Sonntagnachmittag) testen, nicht glauben.

## 3. LinkedIn-Post

**Pruefung vor jedem Post**, mindestens eins muss drinstecken, sonst nicht posten: eigene Erfahrung,
eigene Zahlen, eigener Ablauf, eigene Meinung. Das ist zugleich der Filter fuer KI-Entwuerfe.

Themenart, eine von fuenf: Geschichte mit Lehre, unbequeme Meinung der Zielgruppe, Branchenkommentar mit
Haltung, Ablauf zum Nachmachen, Ergebnis. Aufbau fuer kalte Leser: Hook (Neugierluecke, Zahl, kuehne
Aussage), Kontext (wer, worum), Kern, Lehre oder CTA. Ein enges Thema besetzen; Reel-Richtwert 4 Posts
pro Woche, 80 % Anleitung, 20 % Geschichten. Profil vorab: Headline in einer Zeile "wen ich wie
unterstuetze", ergaenzt um Suchbegriffe (Branche | Leistung | Werkzeug); Info-Abschnitt in der
ersten Person (was ich tue, zwei bis drei Belege, wohin); Bereich "Im Fokus" mit Fallbeispiel;
die ersten drei Kenntnisse genau das, wofuer man gefunden werden will.

Hook-Schablonen zum Fuellen mit eigenen Zahlen (nie erfundenen):
- "Ich habe [Handlung] [X] Tage lang jeden Tag gemacht. Das ist passiert."
- "Wenn Sie als [Rolle] mit [Problem] kaempfen: Das ist fuer Sie."
- "Wollen Sie wirklich [verbreiteter Wunsch], oder eigentlich [wahrer Wunsch]?"

## 4. Kommentar-Routine (wirkt frueher als Posten)

- Tabelle mit drei Listen zu je 25 Konten: Konten, mit denen die Zielgruppe interagiert; Gleichrangige;
  Branchengroessen. Daraus einen eigenen Feed, sortiert nach "Neueste", als Lesezeichen.
- Zweimal taeglich 3–5 Kommentare, rund 30 Minuten. Jeder Kommentar ein Mini-Post (Beispiel, Anekdote,
  Gegenposition), nie "Toller Beitrag".
- Vorlage: Tabelle als Markdown im Projektordner, Spalten Liste | Konto | Link | zuletzt kommentiert.

## 5. Verkaufsgespraech

- **Vorher eine Demo fuer genau diesen Interessenten bauen** und zeigen (Bauweg in Abschnitt 1);
  Agentur-Erfahrung: macht den Abschluss deutlich leichter.
- Vorstellung als Mini-Geschichte aus drei bis vier Stationen ("wie ich dazu kam"), nicht Name, Alter,
  Hobby.
- Gespraech am Laufen halten: die letzten drei Woerter des Gegenuebers als Frage wiederholen
  ("... am meisten Zeit?"); fragen "Wie sind Sie dazu gekommen?".
- Erst das Problem vollstaendig verstehen, dann anbieten; der Kunde redet den Grossteil.
- **Nach der Preisnennung schweigen.**
- Formulierungen (aus einem deutschen Karussell): Bedarf mit "Was bremst Sie gerade am meisten
  aus?" statt "Was ist Ihr groesstes Problem?"; Termin als Wahl ("Donnerstag oder Freitag?");
  Abschluss als Startfrage ("Wann wollen wir starten?"); bei Verspaetung "Danke fuer Ihre Geduld."
- Der erste Einwand ist selten der echte; nachfragen.
- Lieber 50 warme Kontakte als 1000 kalte. Ergebnis und Betreuung verkaufen, nicht ein einzelnes
  KI-Werkzeug (das kann der Anbieter morgen selbst).

## 6. Onboarding: erste Stunde nach der Zusage

Innerhalb einer Stunde vier Dinge senden:
1. Vertrag,
2. Rechnung mit Ueberweisung **und** Zahlungslink (Stripe o. ae.),
3. Willkommensdokument: Projektueberblick, naechste Schritte, Link zum Kundenportal, wie und wann
   kommuniziert wird,
4. Buchungslink fuer den Kickoff (Kreativrichtung, Zeitplan, Logistik; Meet oder Zoom).
Siehe [[2026-08-15 Client-Onboarding nach der Zusage]].

## 7. Quiz-Funnel nach Kaeufertypen

1. Aus dem CRM alle Kontakte samt Verlauf und Ausgang (gewonnen/verloren) ziehen und in Kaeufertypen
   clustern lassen. Jeden Typ mit **Originalwortlaut** der Kunden beschreiben (z. B. "Mach es einfach
   fertig", "Gib mir die Vorlagen", "Beweis es erst").
2. Quiz, dessen Antworten einen Typ bestimmen; ein Freitextfeld ("Was frisst gerade am meisten Zeit?")
   wird klassifiziert, mit Wahrscheinlichkeit je Typ und Entscheidung automatisch/pruefen.
3. Je Typ eigene Folgefragen und eigene Landingpage. Jede Antwort mit den Typ-Wahrscheinlichkeiten
   speichern, um zu sehen, welche Fragen wirklich trennen.
Kundendaten aus dem CRM nur mit Claude, nie an Fremdmodelle; DSGVO-Grundlage vorher klaeren.

## Ausgabe

Entwurf als Markdown im Projektordner oder im Chat, mit Platzhaltern in `[eckigen Klammern]` fuer alles,
was nur der Nutzer weiss (Zahlen, Namen, Fallbeispiele). Nie Zahlen oder Kundennamen erfinden.

## Quellen

Reel-Notiz [[2026-10-30 Reel-Sammlung 134 Reels zu Skills]]; Vorgaenger
[[2026-08-15 Akquise-Lehren aus einem Jahr KI-Agentur]]; Themenseite [[Vertrieb und Positionierung]].
Abschnitt 1 und die Gespraechskniffe: Reel-Sammlung vom 18.11.2026 (sechs Reels zur Demo vorab,
zwei zum Gespraech); Recht DE: Urteile oben, Stand 11/2025.
