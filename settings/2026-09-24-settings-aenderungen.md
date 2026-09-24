# Settings-Aenderungen 2026-09-24

Nur die Aenderungen, nicht die ganze `settings.json` (die enthaelt Projektpfade und Permission-Listen, die hier nichts verloren haben).

## ~/.claude/settings.json

| Key | vorher | nachher | Grund |
|---|---|---|---|
| `model` | `sonnet` | `opus` | Lead-Session auf Opus, Fable nur auf Zuruf. Der Picker in VS Code gewinnt pro Session. |
| `effortLevel` | `xhigh` | `medium` | Ultracode/xhigh auf jedem Turn war der groesste Treiber fuer das gerissene Wochenlimit. |
| `modelSettings` | `xhigh` fuer opus-4-8, fable-5-1, opus-5 | entfernt | Per-Modell-Overrides haetten den globalen Wert ausgehebelt. |
| `skipWorkflowUsageWarning` | `true` | `false` | Die Kostenwarnung vor Multi-Agent-Workflows soll wieder erscheinen. |

## ~/.claude/settings.local.json

| Key | vorher | nachher | Grund |
|---|---|---|---|
| `enabledMcpjsonServers` | `["claude-flow"]` | entfernt | Server war nie erreichbar, 30 Sekunden Timeout bei jedem Start. |

## ~/.mcp.json

Einziger Eintrag war `claude-flow` (`npx @claude-flow/cli@3.42.5 mcp start`). Datei umbenannt zu `.mcp.json.disabled-2026-09-24` statt geloescht.

## Was NICHT geaendert wurde

97 Skills, 116 Agent-Definitionen, 122 Permission-Eintraege. Bewusste Entscheidung, spaeter pruefen. Wirkung der Aenderungen: siehe `lernen/Retro-Log.md`.
