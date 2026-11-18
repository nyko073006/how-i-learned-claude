---
name: app-store-wachstum
description: >
  Konkrete Handgriffe, damit eine iOS-App nach dem Bau Nutzer und Umsatz bekommt: Store-Seite (Header
  3840x1646 ueber die Asset Library), Bewertungsabfrage richtlinienkonform (5.6.1, kein Vorfilter),
  Session Replays ab Tag 1, Probezeitraum fuer 0,99 statt gratis testen, Kaufsignale fuer
  Werbenetzwerke staffeln, Rechtstexte (EULA), Launch-Kanaele. Nutzen bei "App launchen", "mehr
  Downloads", "Bewertungen bekommen", "review prompt", "App Store Seite", "Header-Bild", "Trial",
  "erste Nutzer fuer die App", "App-Marketing", "Paywall testen".
version: 1.0.3
user-invocable: true
---

# app-store-wachstum — iOS-App nach dem Bau

Gebuendelt aus 6 Reels (App-Marketing, dekompilierte Erfolgs-App, Trial-Test, Launch-Kanaele, Stand
10/2026). Wo Reels Apple widersprachen, gilt Apple; die Pruefung steht jeweils dabei.

Vor jeder Aussage ueber die App erst die **Live-Version im Store** nachsehen, nicht das Repo
([[store-version-gegen-repo-stand]]). Was sich per App-Store-Connect-API erledigen laesst, selbst
erledigen ([[asc-schritte-selbst-per-api]]).

## 1. Store-Seite

- **Header ganz oben auf der Produktseite** (seit 05.10.2026): 3840 x 1646 px (21:9), JPEG oder PNG,
  **ohne Transparenz**. Ablauf: in App Store Connect unter Growth & Marketing > Asset Library hochladen,
  Apple gibt frei, dann unter Product Page Information > "Header and Search Results" zuweisen. Einmal
  freigegeben, ohne neue App-Version wiederverwendbar; laesst sich ueber die App-Store-Connect-API
  hochladen. Massangaben vor dem Upload gegen Apples Seite "Creative assets specifications" pruefen.
- Fuer Varianten: Product Page Optimization (A/B) und Custom Product Pages je Zielgruppe oder Anzeige.
- Sammelstelle fuer Vorlagen und Masse: Themenseite [[App Store Asset Best Practices]].

## 2. Bewertungen

- **Nur Apples Abfrage** (`requestReview` / `SKStoreReviewController`). Ein eigener Zwischendialog
  "Gefaellt dir die App?", der Zufriedene zum Store und Unzufriedene zum Feedback schickt, ist
  **Review Gating und verstoesst gegen Richtlinie 5.6.1**. Ein Reel empfahl genau das, ein anderes
  warnte davor; Sekundaerquellen bestaetigen die Warnung. Feedback-Formular ja, aber unabhaengig vom
  Bewertungsfluss (z. B. dauerhaft in den Einstellungen).
- **Zeitpunkt:** direkt nach einem Erfolgsmoment (Level geschafft, Ziel erreicht, Export fertig),
  nie beim Start, nie auf Knopfdruck "Bewerte uns" (das System kann den Aufruf dann ignorieren).
  Das System zeigt den Dialog hoechstens wenige Male im Jahr; die App entscheidet nur, wann sie fragt.
- Direktlink zum Schreiben einer Bewertung: Store-URL plus `?action=write-review`.

## 3. Sehen, wo Nutzer abspringen

PostHog (o. ae.) mit **Session Replay ab der ersten Testversion**, nicht nur Ereigniszaehler: Man sieht,
an welchem Onboarding-Schritt Leute abbrechen und welche Fehler sie treffen. Datenschutz: Eingabefelder
maskieren, in der Datenschutzerklaerung nennen.

## 4. Preis und Probezeit

- **Testidee, kein Gesetz:** Probezeitraum fuer 0,99 statt gratis. Ein Entwickler (Consumer-App, n
  unbekannt) mass: Starts 20 % gratis gegen 15 % bei 0,99; gleich viele Zahlende (~7 von 100);
  Wiederholungskaeufer 46 % gegen 60 %; Umsatz +32 %. Grund laut ihm: Gratis zieht Mitnehmer an, eine
  hinterlegte Karte mit Deckung sortiert aus. Nur als A/B-Test einsetzen, mit eigener Messung.
- Paywall-Aenderungen immer gegen eine Kontrollgruppe, nie nach Gefuehl.

## 5. Werbung: Signale, nicht Klicks

Wer bezahlte Anzeigen schaltet: Das Netzwerk optimiert auf die Ereignisse, die es bekommt. Eine
erfolgreiche Spiele-App (per KI dekompiliert) sendet je Kauf **gestaffelt mehrere Kauf-Ereignisse**:
unter 4 USD 1x, 4–9,99 2x, 10–19,99 3x, 20–39,99 4x, ab 40 USD 5x; dazu eigene Ereignisse fuer "Kauf am
ersten Tag", "Rueckkehr an Tag 2", "zweiter Kauf". So lernt das Netzwerk, wer viel zahlt. Staffel als
Einstellung anlegen, nicht fest verdrahten. Vor Einsatz Datenschutz (ATT, Datenschutzerklaerung) pruefen.

## 6. Rechtliches vor dem ersten Release

- EULA (Apples Standard-EULA reicht oft; eigene bei Abo- oder Sonderbedingungen), Datenschutzerklaerung,
  bei Nutzer-Uploads eine Regel fuer Urheberrechtsbeschwerden.
- App mit anonymer Anmeldung: Kontoloeschung in der App anbieten ([[apple-loeschpflicht-gastkonten]]).
- Abo: Kuendigung so einfach wie Abschluss.

## 7. Erste Nutzer ohne Budget

Reddit r/SideProject; Hacker News mit Titel "Show HN: ..."; Product Hunt (Reel-Tipp: Di bis Do);
Indie Hackers; kleine App-Verzeichnisse, die auf die Website zurueckverlinken. Je Kanal ein eigener Text,
kein Kreuzposting.

## Ausgabe

Bei "was fehlt fuer den Launch": Liste der Abschnitte 1 bis 7 mit `erledigt | offen | nicht noetig`
und Beleg (Screenshot-Pfad, ASC-Status, Code-Fundstelle). Bei Einzelfragen nur den passenden Abschnitt.

## Quellen

Reel-Notiz [[2026-10-30 Reel-Sammlung 134 Reels zu Skills]]. Geprueft am 30.10.2026: Header-Mass und
Asset Library (Apple Help "Creative assets specifications", "Manage your App Store assets"),
Review Gating 5.6.1 (Sekundaerquellen; Apples Richtlinientext vor Release selbst lesen).
