# Settings-Aenderungen 2026-09-27

Nur die Aenderungen, nicht die ganze `settings.json`.

## ~/.claude/settings.json

| Key | vorher | nachher | Grund |
|---|---|---|---|
| `statusLine` | nicht gesetzt | `{"type": "command", "command": "bash ~/.claude/statusline-command.sh"}` | Kontextfuellung sichtbar machen, damit der Kontext-Cap von 150k nicht geschaetzt werden muss. Aus dem Workshop, siehe [[Kurs-Notizen/Workshop - Claude Setup]]. |

Angelegt ueber `/statusline` im Terminal. Die Statusline gibt es nur im Terminal-CLI, in der VS-Code-Extension ist sie laut Doku nicht vorgesehen.

## ~/.claude/statusline-command.sh (neu)

Zeigt gedimmt Modell, Kontext in k-Tokens und Prozent, ab 150.000 Tokens rot und fett `HANDOFF`.

```bash
#!/bin/bash
# Claude Code Statusline: Modell, Kontext in k-Tokens und Prozent, HANDOFF ab 150k
input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name')
# Kontext = aktueller Prompt inkl. Cache aus current_usage, nicht total_input_tokens
tokens=$(echo "$input" | jq -r '.context_window.current_usage | (.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0)')
# Runden in jq statt printf: printf scheitert unter deutscher Locale an "1.5"
pct_int=$(echo "$input" | jq -r '(.context_window.used_percentage // 0) | round')

ktok=$(( tokens / 1000 ))

DIM='\033[2m'
RESET='\033[0m'
BOLD_RED='\033[1;31m'

if [ "$tokens" -ge 150000 ]; then
  printf "${DIM}%s | %dk tokens (%d%%)${RESET} ${BOLD_RED}HANDOFF${RESET}" "$model" "$ktok" "$pct_int"
else
  printf "${DIM}%s | %dk tokens (%d%%)${RESET}" "$model" "$ktok" "$pct_int"
fi
```

### Korrektur nach dem ersten Test

Die von `/statusline` erzeugte Fassung las die Tokens aus `.context_window.total_input_tokens`. Im Test mit 160k Tokens unter `current_usage` zeigte sie `0k` und kein `HANDOFF`, die Warnung waere nie gekommen. Jetzt summiert das Script die drei Felder aus `current_usage`. Ausserdem `chmod +x` gesetzt.

Tests nach der Korrektur:

| Eingabe | Ausgabe |
|---|---|
| 160.000 Tokens | `Opus \| 160k tokens (80%) HANDOFF` |
| 149.999 | `Opus \| 149k tokens (75%)` |
| 150.000 | `Opus \| 150k tokens (75%) HANDOFF` |
| `current_usage` fehlt oder null | `Opus \| 0k tokens (0%)` |

Lehre: Von Claude erzeugte Scripts mit einem Grenzfall testen, bevor man sich darauf verlaesst.

## Wirkung

Noch offen. Pruefung beim `/usage`-Check am 2026-10-01, Eintrag dann im `lernen/Retro-Log.md`.
