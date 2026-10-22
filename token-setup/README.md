# Token-Setup: wie ich das Wochenlimit halte

Stand 22.10.2026, Claude Code 2.1.x, Plan Claude Max 20x.

Bis zum 24.09.2026 habe ich das Wochenlimit regelmäßig gerissen. Seit dem Umbau ist das nicht mehr passiert: In der ersten Woche lag ich einen Tag vor dem Reset bei 65 %, Anfang Oktober bei höchstens 10 % je Fenster. Mehr Kontingent hatte ich nicht. Geändert hat sich, wie ich arbeite.

Hier steht, was ich eingestellt habe, was es gebracht hat und was es kostet. Die Messungen stehen ausführlich in [`../lernen/Retro-Log.md`](../lernen/Retro-Log.md), die Regeln im Wortlaut in [`../claude-md/CLAUDE.md`](../claude-md/CLAUDE.md).

## Die drei großen Hebel

1. **Kleiner Kontext.** Jede Anfrage schickt den ganzen bisherigen Kontext mit. Eine Session mit 300k Kontext kostet pro Antwort ein Vielfaches einer Session mit 60k. Bei mir lagen 71 % des Verbrauchs über 150k Kontext. Das war der größte Einzelposten (`/usage`, Abschnitt "What's contributing").
2. **Passender Effort.** Ultracode lief dauerhaft. Heute bekommt Opus als Lead `high` und alle anderen Modelle `medium`. `xhigh` und Ultracode gibt es nur, wenn ich es für eine Aufgabe ausdrücklich verlange.
3. **Nichts Unnötiges im Startkontext.** Jedes installierte Plugin, jeder MCP-Server, jeder Agent und jeder Skill kostet Tokens, bevor ich den ersten Satz schreibe. Der Startkontext war von 54k auf 96k gewachsen.

## Regeln in der CLAUDE.md

Auszug aus "Betriebsregeln Claude Code":

- **Ein Auftrag pro Session.** Danach kommt ein Handoff (Skill `/handoff`), dann `/clear` und eine neue Session mit einer kurzen Startnachricht. Bei sehr kleinem Kontext darf der nächste Auftrag in derselben Session weiterlaufen. Die Schwellen dafür stehen in einer Datei (siehe unten).
- **Kontext-Cap 175k.** Ab da schreibt Claude einen Handoff und schlägt eine neue Session vor. Große Aufgaben bei hohem Kontext werden übergeben, nicht durchgezogen.
- **Lange Tool-Ausgaben gehen in Dateien im Scratchpad**, nicht in den Kontext.
- **PDFs nie direkt einlesen**, sondern erst mit `markitdown datei.pdf -o datei.md` umwandeln.
- **Lead Opus, Sub-Agents Sonnet.** Fable nur auf Zuruf.
- **Sub-Agents ab zwei unabhängigen Teilen**, oder wenn mehr als vier Dateien zu lesen sind, deren Inhalt der Lead danach nicht selbst braucht. Darunter arbeitet der Lead selbst.
- **Zweitmeinungen über kostenlose Fremdmodelle** (Gemini über Antigravity, GPT über den Codex-Gratistarif). Das schont das Claude-Kontingent. Nie mit sensiblen Daten.

## Einstellungen (`~/.claude/settings.json`)

Nur die Schlüssel, die für Tokens zählen:

```json
{
  "effortLevel": "medium",
  "modelSettings": { "claude-opus-5-5": { "effortLevel": "high" } },
  "env": { "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet" },
  "skillListingBudgetFraction": 0.005,
  "cleanupPeriodDays": 3650,
  "statusLine": { "type": "command", "command": "bash ~/.claude/statusline-command.sh", "refreshInterval": 30 }
}
```

- `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` sorgt dafür, dass Sub-Agents auch dann auf Sonnet laufen, wenn ein Skill oder eine Agent-Datei etwas anderes vorschlägt.
- `skillListingBudgetFraction` begrenzt, wie viele Zeichen die Skill-Liste im Startkontext belegt. Der Standard 0.01 ergibt bei 1M Kontext rund 30k Zeichen. Achtung: Skills löschen spart dort nichts, weil der frei gewordene Platz an längere Beschreibungen der übrigen Skills geht. Nur das Budget wirkt. Ungenutzte eingebaute Skills stelle ich zusätzlich per `skillOverrides` auf `name-only`. Das greift allerdings nicht bei Plugin-Skills.
- `cleanupPeriodDays` hat mit dem Verbrauch nichts zu tun. Ohne diesen Wert löscht Claude Code Transkripte nach 30 Tagen, und dann lässt sich nichts mehr messen.
- Die **Statuszeile** zeigt Kontext in Prozent und Tokens. Ohne diese Zahl merke ich nicht, wann der Cap naht.

Schwellen für Warnung und Handoff (`~/.claude/cockpit/thresholds.json`):

```json
{ "context_warn": 150000, "context_handoff": 175000, "clearable_min_context_pct": 10, "clearable_min_prompts": 3 }
```

## Startkontext-Diät

Gemessen habe ich jeweils die `usage` des ersten Requests im Transkript (`~/.claude/projects/**/*.jsonl`). `/context` zeigt nur einen Teil davon.

| Stufe | Was raus ist | Startkontext Home-Ordner |
|---|---|---|
| Ausgang | | 96k |
| 1 | 90 ungenutzte Fremd-Agents (claude-flow), SEO-Skills und -Agents, eine doppelte `~/AGENTS.md`, sechs MCP-Connectoren ohne einen Aufruf in 35 Tagen | 76k |
| 2 | Vercel-Plugin nur noch im Projekt, das es braucht (`settings.local.json`), Skill-Budget 0.005 | 61k |
| 3 | CLAUDE.md und MEMORY.md gestrafft, ohne eine Regel zu ändern | rund 59k |

Was ich dabei gelernt habe:

- **Erst zählen, dann löschen.** Ich habe die Aufrufe je Tool, Agent und Skill aus 30 Tagen Transkripten gezählt. 96 von 125 Skills und mehrere Connectoren hatten null Aufrufe.
- **`permissions.deny` auf `mcp__<server>`** entfernt die Tools, aber nicht die Anweisungen des Servers. Die verschwinden erst mit `/mcp disable` oder wenn man den Connector auf claude.ai trennt.
- **`enabledPlugins` wird tief zusammengeführt.** `true` in der Projektdatei schlägt `false` in der globalen Datei. So bleibt ein Plugin global aus und ist im Projekt an. Beim Anlegen eines Worktrees kopiert Claude Code `settings.local.json` mit.
- **Der Index der Memory-Datei lädt in jeder Session.** Eine Zeile pro Eintrag, Details stehen in der Einzeldatei.

## context-mode

Das Plugin [context-mode](https://github.com/mksglu/context-mode) hält große Tool-Ausgaben aus dem Kontext heraus. Befehle laufen in einer Sandbox, die Ausgabe wird indiziert, und in den Kontext kommt nur, was ich gezielt abfrage. Das lohnt sich bei Logs, Testläufen und großen Dateien, die ich auswerten, aber nicht editieren will. Es braucht Node 22.

## Was es kostet

Seit dem 04.10. setze ich Pläne immer subagent-driven um: Ein Sonnet-Agent baut, ein zweiter reviewt, dazu Fix-Runden und eine Gegenprüfung durch ein anderes Modell. Das spart **keine** Tokens. Pro 1.000 Zeilen Code brauche ich damit rund 1,7 Mio. Output-Tokens statt 400.000 bei linearer Arbeit, also gut das Vierfache. Trotzdem bleibe ich im Limit, weil diese Tokens auf Sonnet laufen, jeder Agent mit kleinem Kontext startet und der Lead seinen Kontext nicht mit Dateiinhalten füllt.

Kurz gesagt: Sparen kommt hier von kleinem Kontext und dem richtigen Modell an der richtigen Stelle, nicht von weniger Output.

## Selbst nachmachen, in dieser Reihenfolge

1. Statuszeile mit Kontextanzeige einrichten, damit man überhaupt sieht, wo man steht.
2. Mit `/usage` den Abschnitt "What's contributing to your limits usage?" lesen, nicht nur die Balken.
3. Effort herunter auf `medium`, für den Lead `high`, Sub-Agents auf Sonnet.
4. Ein Auftrag pro Session, Handoff und `/clear`.
5. Startkontext am ersten Request messen, Aufrufe zählen, Ungenutztes abschalten.
6. Nach einer Woche wieder `/usage` lesen und die Wirkung im Retro-Log festhalten.
