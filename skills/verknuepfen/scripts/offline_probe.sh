#!/bin/bash
# Offline-Beleg fuer Schritt 4 (Spec 6): Die Sandbox sperrt das Netz, qmd baut und befragt darin einen Index,
# und ein Fremdmodell erzeugt darin keinen Vektor. Laeuft nur mit VERKNUEPFEN_QMD_PROBE=1 (startet das echte
# qmd und node).
#
#     VERKNUEPFEN_QMD_PROBE=1 bash offline_probe.sh
#
# Jeder Schritt druckt eine Zeile "OK ..." oder "FEHLER ...", dazu die letzten 3 Zeilen der Ausgabe.
# Exit 0 nur, wenn alle Schritte OK sind. Der Modell-Cache (XDG-Cache) bleibt unveraendert.
# Jeder qmd- und node-Aufruf hat eine Frist (Abbruch der ganzen Prozessgruppe); fuer Tests lassen sich alle
# Fristen mit VERKNUEPFEN_PROBE_FRIST_FAKTOR verkuerzen.
set -u

if [ "${VERKNUEPFEN_QMD_PROBE:-}" != "1" ]; then
  echo "Offline-Probe übersprungen: startet das echte qmd und node, nur mit VERKNUEPFEN_QMD_PROBE=1."
  exit 0
fi

D=$(cd "$(dirname "$0")" && pwd)
SB='(version 1)(allow default)(deny network*)'
FRIST_BAU=300
FRIST_ABFRAGE=60
FRIST_FREMD=60
FRIST_ABGELAUFEN=124
FEHLT=0
W=$(mktemp -d) || { echo "FEHLER mktemp"; exit 1; }
[ -n "$W" ] && [ -d "$W" ] || { echo "FEHLER mktemp"; exit 1; }

aufraeumen() {
  rm -rf -- "$W"
}
trap aufraeumen EXIT

# mit_frist <sekunden> <befehl ...>: eigene Prozessgruppe, nach Fristablauf SIGKILL an die ganze Gruppe,
# Exit 124. Standardein- und -ausgabe gehen durch.
FRIST_PY='import os, signal, subprocess, sys
try:
    frist = float(sys.argv[1]) * float(os.environ.get("VERKNUEPFEN_PROBE_FRIST_FAKTOR") or 1)
except ValueError:
    print("VERKNUEPFEN_PROBE_FRIST_FAKTOR ist keine Zahl", file=sys.stderr)
    sys.exit(2)
try:
    p = subprocess.Popen(sys.argv[2:], start_new_session=True)
except OSError as ex:
    print("nicht startbar: %s" % ex, file=sys.stderr)
    sys.exit(127)
def gruppe_beenden():
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    p.wait()
try:
    rc = p.wait(timeout=frist)
except subprocess.TimeoutExpired:
    gruppe_beenden()
    sys.exit(124)
except BaseException:
    gruppe_beenden()
    raise
sys.exit(rc if rc >= 0 else 128 - rc)'

mit_frist() {
  python3 -I -c "$FRIST_PY" "$@"
}

wie() {  # Text zum Exitcode
  if [ "$1" = "$FRIST_ABGELAUFEN" ]; then echo "Frist abgelaufen"; else echo "Exit $1"; fi
}

ausgabe() {  # letzte 3 Zeilen eines Protokolls, eingerueckt
  tail -n 3 "$1" | sed 's/^/    /'
}

ergebnis() {  # ergebnis <ok 0|1> <Text> <Protokoll>
  if [ "$1" = "0" ]; then echo "OK $2"; else echo "FEHLER $2"; FEHLT=1; fi
  ausgabe "$3"
}

treffer_da() {  # JSON-Datei: nicht leeres Array; kaputtes JSON ist kein Treffer, kein Traceback
  python3 -I -c 'import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        d = json.load(fh)
except (OSError, ValueError) as ex:
    print("Ausgabe nicht lesbar: %s" % ex)
    sys.exit(1)
print("%d Treffer" % len(d) if isinstance(d, list) else "keine Liste")
sys.exit(0 if isinstance(d, list) and d else 1)' "$1"
}

vektoren() {  # Zeilen in content_vectors; druckt die Zahl, Exit 1 wenn nicht pruefbar
  python3 -I -c 'import os, sqlite3, sys
from pathlib import Path
if not os.path.isfile(sys.argv[1]):
    print("Index fehlt"); sys.exit(1)
try:
    con = sqlite3.connect(Path(sys.argv[1]).as_uri() + "?mode=ro", uri=True)
    print(con.execute("select count(*) from content_vectors").fetchone()[0])
except sqlite3.Error as ex:
    print("nicht prüfbar: %s" % ex); sys.exit(1)' "$1"
}

# a. Mini-Vault mit erfundenen Notizen, eigene Konfiguration und eigener Index
mkdir -p "$W/vault" "$W/cfg" "$W/cfg-remote"
cat > "$W/vault/Kappa.md" <<'EOF'
# Kappa
Kappa ist ein Projekt der Rho GmbH. Es plant Etappen fuer einen Umzug von Akten.
Im Projekt Kappa entstehen Listen, Fristen und ein Zeitplan fuer das Team.
EOF
cat > "$W/vault/Rho GmbH.md" <<'EOF'
# Rho GmbH
Die Rho GmbH ist eine erfundene Firma. Sie beauftragt das Projekt Kappa.
Ansprechpartner sitzen in einem Buero am Hafen und schreiben Berichte.
EOF
cat > "$W/vault/Omega.md" <<'EOF'
# Omega
Omega ist ein Bereich fuer Gartenarbeit. Hier stehen Notizen zu Tomaten und Kompost.
Im Herbst werden Beete abgedeckt und Samen sortiert.
EOF
printf 'collections:\n  vault:\n    path: "%s"\n    pattern: "**/*.md"\n' "$W/vault" > "$W/cfg/probe.yml"
cp "$W/cfg/probe.yml" "$W/cfg-remote/probe.yml"
printf 'models:\n  embed: "https://api.openai.com/v1#text-embedding-3-small"\n' >> "$W/cfg-remote/probe.yml"
echo "OK Wegwerf-Vault und Konfiguration in $W"

# Netz. Listener auf 127.0.0.1 ausserhalb der Sandbox; Verbindung von innen muss scheitern, von aussen
# gelingen. Kein Kontakt nach aussen.
python3 -I -c 'import socket, subprocess, sys, threading
sb = sys.argv[1]
srv = socket.socket()
srv.bind(("127.0.0.1", 0))
srv.listen(5)
port = srv.getsockname()[1]
def annehmen():
    while True:
        try:
            srv.accept()[0].close()
        except OSError:
            return
threading.Thread(target=annehmen, daemon=True).start()
code = ("import socket, sys\n"
        "try:\n"
        "    socket.create_connection((\"127.0.0.1\", %d), timeout=3).close()\n"
        "except OSError as e:\n"
        "    print(\"gesperrt:\", type(e).__name__, e.errno)\n"
        "    sys.exit(3)\n"
        "print(\"verbunden\")\n" % port)
def versuch(vorne):
    try:
        r = subprocess.run(vorne + [sys.executable, "-I", "-c", code], capture_output=True, text=True,
                           timeout=20)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return None, str(ex)
    return r.returncode, (r.stdout + r.stderr).strip()
innen = versuch(["sandbox-exec", "-p", sb])
aussen = versuch([])
print("in der Sandbox: rc=%s %s" % innen)
print("ohne Sandbox: rc=%s %s" % aussen)
sys.exit(0 if innen[0] == 3 and aussen[0] == 0 else 1)' "$SB" > "$W/netz.log" 2>&1
ergebnis $? "Sandbox sperrt Netz (127.0.0.1 innen gesperrt, außen erreichbar)" "$W/netz.log"

# b. Index bauen ohne Netz
for schritt in update embed; do
  mit_frist "$FRIST_BAU" env QMD_CONFIG_DIR="$W/cfg" INDEX_PATH="$W/probe.sqlite" \
    sandbox-exec -p "$SB" qmd --index probe "$schritt" > "$W/b-$schritt.log" 2>&1
  rc=$?
  [ "$rc" = "0" ]; ergebnis $? "qmd $schritt ohne Netz ($(wie "$rc"))" "$W/b-$schritt.log"
done

# c. Wegwerf-Index abfragen ohne Netz
printf 'Kappa' | mit_frist "$FRIST_ABFRAGE" env QMD_CONFIG_DIR="$W/cfg" INDEX_PATH="$W/probe.sqlite" \
  sandbox-exec -p "$SB" node "$D/qmd_vektor.mjs" "$W/probe.sqlite" 3 > "$W/c.json" 2> "$W/c.log"
rc=$?
cat "$W/c.json" >> "$W/c.log"
[ "$rc" = "0" ] && treffer_da "$W/c.json" >> "$W/c.log"
ergebnis $? "Wegwerf-Index ohne Netz abgefragt ($(wie "$rc"))" "$W/c.log"

# d. echten Index abfragen ohne Netz (Indexname aus den Einstellungen, Pfad nach den Regeln von nachbarn.py,
# beides aus der Umgebung)
DB=$(python3 -I -c 'import sys
sys.path.insert(0, sys.argv[1])
import nachbarn
print(nachbarn.qmd_db_pfad(nachbarn.einstellungen_laden()["graph"]["qmd_index"]))' "$D")
printf 'Testabfrage' | mit_frist "$FRIST_ABFRAGE" sandbox-exec -p "$SB" node "$D/qmd_vektor.mjs" "$DB" 3 \
  > "$W/d.json" 2> "$W/d.log"
rc=$?
[ "$rc" = "0" ] && treffer_da "$W/d.json" >> "$W/d.log"
ergebnis $? "echter Index $DB ohne Netz abgefragt ($(wie "$rc"))" "$W/d.log"

# e. Gegentest: ein Fremdmodell per Adresse erzeugt in derselben Sandbox keinen Vektor. qmd 2.8.3 haengt
# hier (die Adresse geht als Download an node-llama-cpp), deshalb zaehlt Fristablauf wie Scheitern.
mit_frist "$FRIST_BAU" env QMD_CONFIG_DIR="$W/cfg-remote" INDEX_PATH="$W/remote.sqlite" \
  sandbox-exec -p "$SB" qmd --index probe update > "$W/e-update.log" 2>&1
rc=$?
[ "$rc" = "0" ]; ergebnis $? "Gegentest: qmd update mit Fremdmodell ($(wie "$rc"))" "$W/e-update.log"
mit_frist "$FRIST_FREMD" env QMD_CONFIG_DIR="$W/cfg-remote" INDEX_PATH="$W/remote.sqlite" \
  sandbox-exec -p "$SB" qmd --index probe embed > "$W/e-embed.log" 2>&1
rc=$?
anzahl=$(vektoren "$W/remote.sqlite")
gezaehlt=$?
echo "content_vectors: $anzahl" >> "$W/e-embed.log"
[ "$rc" != "0" ] && [ "$gezaehlt" = "0" ] && [ "$anzahl" = "0" ]
ergebnis $? "Gegentest: Fremdmodell erzeugt ohne Netz keinen Vektor (embed $(wie "$rc"), $anzahl Vektoren)" \
  "$W/e-embed.log"

# f. Aufraeumen per trap (nur der mktemp-Ordner)
if [ "$FEHLT" = "0" ]; then
  echo "Offline-Beleg: alle Schritte OK"
  exit 0
fi
echo "Offline-Beleg: mindestens ein Schritt FEHLER"
exit 1
