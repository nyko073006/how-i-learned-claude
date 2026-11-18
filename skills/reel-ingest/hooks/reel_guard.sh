#!/usr/bin/env bash
# Feuert bei JEDEM Prompt. Muss deshalb in Millisekunden aussteigen, wenn
# nichts zu tun ist — darum Bash und nicht Python.
# Ein Fehler hier wuerde jede Eingabe blockieren, also: niemals ungleich 0 enden.
set -uo pipefail

NUTZLAST=$(cat)
WURZEL="$HOME/.claude/skills/reel-ingest"

# Schnellablehnung: kein Telegram oder kein Reel-Link -> raus.
case "$NUTZLAST" in
  *'source=\"telegram\"'*|*'source="telegram"'*) ;;
  *) exit 0 ;;
esac
case "$NUTZLAST" in
  *instagram.com/reel*|*youtube.com/shorts*|*tiktok.com/*) ;;
  *) exit 0 ;;
esac

# AEUSSERES Zeitlimit fuer den kompletten Python-Prozess (Task 11c).
# Frueher 90s -- das war der bindende Engpass, nicht mehr nur ein Backstop:
# src/fetch.py, src/frames.py und src/transcript.py setzen jetzt eigene
# timeout=-Werte auf ihre subprocess.run()-Aufrufe (yt-dlp Video 180s +
# yt-dlp Untertitel 60s + ffmpeg Keyframes bis zu 2x30s + ffmpeg
# Tonspur-Extraktion 30s = 330s innere Zeitlimits), dazu Whisper (kein
# subprocess, daher nicht per timeout= zu begrenzen; grob geschaetztes
# Worst-Case fuer ein volles Reel bei schwacher Messgrundlage: bis zu ~300s,
# siehe Task-11c-Report). In Summe kann ein echter, aber sehr langsamer
# Durchlauf legitim ueber 90s dauern -- ein 90s-Aussenlimit wuerde dann VOR
# den inneren Limits feuern und genau das Verwaisungsproblem wieder
# einfuehren, das die inneren Limits beheben sollen (der aeussere Waechter
# killt nur den Python-Prozess, nicht die Kindprozesse). 900s (15 Min) liegt
# klar ueber der Summe der inneren Zeitlimits (~630s inkl. Whisper-Schaetzung)
# und wirkt jetzt nur noch als echter Rueckfall gegen einen haengenden
# Python-Prozess selbst (z.B. Bug jenseits der subprocess-Aufrufe).
AEUSSERES_ZEITLIMIT_SEKUNDEN=900

# "timeout" ist unter GNU/Linux Standard. macOS ohne coreutils hat weder
# "timeout" noch "gtimeout" — ohne Rueckfall wuerde die Kette dort bei JEDEM
# Reel sofort mit "command not found" abbrechen, statt je zu verarbeiten.
# Portabler Ersatz nur fuer diesen Fall, das Zeitlimit bleibt identisch.
_mit_zeitlimit() {
  if command -v timeout >/dev/null 2>&1; then
    printf '%s' "$NUTZLAST" | timeout "$AEUSSERES_ZEITLIMIT_SEKUNDEN" "$@"
    return $?
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    printf '%s' "$NUTZLAST" | gtimeout "$AEUSSERES_ZEITLIMIT_SEKUNDEN" "$@"
    return $?
  fi
  "$@" <<< "$NUTZLAST" &
  local pid=$!
  # stdout/stderr des Waechters selbst auf /dev/null: sonst haelt ein
  # ueberlebender "sleep" nach dem Kill die geerbten Pipe-Fds offen, und ein
  # Aufrufer, der auf EOF wartet (z.B. subprocess.run), haengt bis zum
  # Ablauf von AEUSSERES_ZEITLIMIT_SEKUNDEN.
  # Der "sleep" kann nach dem Kill kurz als Waise weiterlaufen (eine Subshell
  # kann ihr eigenes Kind nicht "vererben" fuer den Kill) — harmlos, da seine
  # Ausgabe schon auf /dev/null zeigt und er nur einen laengst toten Pid killt.
  ( sleep "$AEUSSERES_ZEITLIMIT_SEKUNDEN"; kill -TERM "$pid" 2>/dev/null ) >/dev/null 2>&1 &
  local waechter=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  kill "$waechter" 2>/dev/null
  wait "$waechter" 2>/dev/null
  return $rc
}

# Ab hier lohnt sich Python. Zeitlimit, damit die Session nicht haengt.
_mit_zeitlimit "$WURZEL/venv/bin/python" "$WURZEL/cli.py" 2>/dev/null \
  || echo "reel-ingest: Verarbeitung abgebrochen oder Zeitlimit erreicht — Dossier ggf. unvollstaendig."
exit 0
