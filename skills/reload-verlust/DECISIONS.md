# Entscheidungen und Annahmen (reload-verlust)

Gebaut am 2026-10-21 ohne Rueckfragen (Nutzer nicht am Platz). Jede Annahme mit Grund.

- **Neuer Skill statt Erweiterung.** Lokal (202 Skills, Commands, Agenten) und auf skills.sh gibt es
  nichts Vergleichbares: `anthropics/session-report` zaehlt Tokens, `agentmemory/session-history`
  braucht einen eigenen Memory-Server, `agentops/recover` ist im Repo nicht mehr vorhanden.
- **Name `reload-verlust`.** Deutsch wie die anderen eigenen Skills; sagt, was er findet.
- **Zeitpunkt = Start des Obsidian-Prozesses.** Einziger Wert, den das System sicher kennt.
  `plugin:reload` haelt den Prozess am Leben, dafuer gibt es `--zeit`.
- **Statusdatei-Zeitstempel ist kein Beleg.** Die Statuszeile schreibt alle 30 s (`refreshInterval`).
  Am 21.10. galt eine seit 07:19 stille Sitzung sonst als Verlust.
- **Drei Belegarten:** Kontext-Abweichung, Commit-Trailer, Vault-Datei mit Session-URL. Zusammen
  fanden sie am 21.10. alle fuenf Sitzungen, die nachweislich ohne Transkript gearbeitet hatten.
- **10 Minuten Karenz** nach der letzten Nachricht, weil Commit und Handoff einer Antwort oft kurz
  danach auf der Platte landen.
- **Remote-Session gehoert der juengsten Sitzung im Tab**, weil sie `/clear` ueberlebt.
- **„Ohne Zuordnung“ nur, wenn es eine betroffene Sitzung gibt**, sonst listet der Bericht jeden
  Commit des Tages.
- **`git -c core.trustctime=false -c core.checkStat=minimal`**, weil `git status` in iCloud-Repos
  sonst pro Worktree bis ins Zeitlimit haengt (gemessen: 2:10 min statt 6 s).
- **Nur lesen, nur Standardbibliothek**, wie `lint/scripts/vault_lint.py`.
