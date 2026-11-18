# app-store-wachstum

Handgriffe fuer eine iOS-App nach dem Bau: Store-Seite, Bewertungen, Abbruchanalyse, Probezeitraum, Werbesignale, Rechtstexte, erste Nutzer. Wo Reels Apple widersprachen (Bewertungs-Vorfilter), gilt Apple.

![app-store-wachstum Ablauf](app-store-wachstum-overview.png)

> Quelle des Diagramms: [`app-store-wachstum-overview.excalidraw`](app-store-wachstum-overview.excalidraw)

## Installation

Ordner nach `~/.claude/skills/app-store-wachstum/` kopieren. Keine Abhaengigkeiten.

## Nutzung

```text
/app-store-wachstum was fehlt fuer den Launch von <App>
/app-store-wachstum wie frage ich nach Bewertungen
```

## Umfang

- Header 3840 x 1646 ueber die Asset Library
- Bewertung nur per requestReview nach Erfolgsmoment, kein Gating (5.6.1)
- Session Replay ab Tag 1
- Trial 0,99 statt gratis als A/B-Test
- gestaffelte Kaufsignale
- EULA, Loeschpflicht, Kuendigung
- Launch-Kanaele

## Hintergrund

Aus 6 Instagram-Reels (Stand 10/2026). Header-Mass und Asset Library sowie Review Gating am 30.10.2026 gegen Apple-Hilfe bzw. Sekundaerquellen geprueft.

## Dateistruktur

```
app-store-wachstum/
├── SKILL.md
├── README.md
├── app-store-wachstum-overview.excalidraw
└── app-store-wachstum-overview.png
```
