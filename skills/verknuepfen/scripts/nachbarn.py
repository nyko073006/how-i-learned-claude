"""Schritt 4: semantische Nachbarn ueber qmd (nur lokal, nur Vorschlaege "Verwandt", schreibt nie in Notizen).

    verknuepfen.py nachbarn [--vault V] [--json DATEI] NOTIZ
"""
import copy
import json
import math
import os
import re
import signal
import sqlite3
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verknuepfen as vk  # noqa: E402

ABFRAGE_ZEICHEN = 2000
EINSTELLUNGEN_ENV = "VERKNUEPFEN_EINSTELLUNGEN"
EINSTELLUNGEN_PFAD = "~/.config/verknuepfen/einstellungen.json"
VORGABEN = {"graph": {
    "ausschluss": ["03 Bereiche/Finanzen/**", "memory/**"],
    "schwelle": None,
    "max_nachbarn": 5,
    "qmd_index": "vault",
    "qmd_frist": 30,
}}
NODE = "node"
QMD = "qmd"
COLLECTION = "vault"  # Name in qmd_yaml; jede andere Collection im Index ist ein Befund
YAML_OBEN = ("collections", "models")  # collections schreibt qmd_yaml, models haengt qmd selbst an
VEKTOR_SKRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qmd_vektor.mjs")
STDERR_ZEICHEN = 200
NODE_VERSION = re.compile(r"Node\.js v\d")  # letzte Zeile jedes Node-Absturzes, sagt nichts
FESTE_MUSTER = [".obsidian/**", ".trash/**", "07 Anhaenge/**"]  # nicht abschaltbar
FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


class NachbarnFehler(Exception):
    """Schritt 4 laeuft nicht; str(e) ist der Grund fuer die Zeile "Schritt 4 uebersprungen"."""


@dataclass
class Nachbar:
    rel: str
    score: float
    titel: str


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _zusammen(basis, extra):
    for k, w in extra.items():
        if isinstance(w, dict) and isinstance(basis.get(k), dict):
            _zusammen(basis[k], w)
        else:
            basis[k] = w
    return basis


def _zahl(w):
    return isinstance(w, (int, float)) and not isinstance(w, bool) and math.isfinite(w)


# Typpruefung je Schluessel (ausschluss eigens unten); falscher Typ: Vorgabe plus Warnung.
TYPEN = [
    ("schwelle", lambda w: w is None or _zahl(w), "keine Zahl"),
    ("max_nachbarn", lambda w: isinstance(w, int) and not isinstance(w, bool) and w >= 0, "keine ganze Zahl ab 0"),
    ("qmd_frist", lambda w: _zahl(w) and w > 0, "keine Zahl über 0"),
    ("qmd_index", lambda w: isinstance(w, str) and w != "" and "/" not in w, "kein Name ohne /"),
]


def einstellungen_laden(pfad=None):
    """VORGABEN tief zusammengefuehrt mit der Datei; bei jedem Aufruf frisch gelesen."""
    if pfad is None:
        pfad = os.environ.get(EINSTELLUNGEN_ENV) or EINSTELLUNGEN_PFAD
    e = copy.deepcopy(VORGABEN)
    e["warnungen"] = []
    pfad = os.path.expanduser(pfad)
    try:
        with open(pfad, encoding="utf-8") as fh:
            roh = json.load(fh)
        if not isinstance(roh, dict):
            raise ValueError("kein Objekt")
    except FileNotFoundError:
        return e
    except (OSError, ValueError) as ex:
        e["warnungen"].append("Einstellungen nicht lesbar (%s): %s" % (pfad, ex))
        return e
    if "graph" in roh and not isinstance(roh["graph"], dict):
        roh = {k: w for k, w in roh.items() if k != "graph"}
        e["warnungen"].append("graph ist kein Objekt, Vorgaben gelten (%s)" % pfad)
    _zusammen(e, roh)
    g = e["graph"]
    for schluessel, gueltig, soll in TYPEN:
        if not gueltig(g.get(schluessel)):
            g[schluessel] = copy.deepcopy(VORGABEN["graph"][schluessel])
            e["warnungen"].append("graph.%s ist %s, Vorgabe gilt (%s)" % (schluessel, soll, pfad))
    a = e["graph"].get("ausschluss")
    if not isinstance(a, list) or not all(isinstance(m, str) for m in a):
        # Datenschutz: ein Text wie "memory/**" wuerde sonst Zeichen fuer Zeichen als Muster gelten.
        e["graph"]["ausschluss"] = copy.deepcopy(VORGABEN["graph"]["ausschluss"])
        e["warnungen"].append("graph.ausschluss ist keine Liste von Texten, Vorgabe gilt (%s)" % pfad)
    return e


def python_grund():
    """Grund, warum Schritt 4 auf diesem Python nicht laeuft (PurePosixPath.full_match gibt es ab 3.13), sonst
    None. Einzige Stelle dieser Pruefung: nachbarn(), cmd_index und eichen.py nutzen sie."""
    return None if hasattr(PurePosixPath, "full_match") else "Python ab 3.13 nötig"


def _yaml_text(roh):
    """Skalar aus einer YAML-Zeile: "..." als JSON-String (so schreibt qmd_yaml), '...' mit '' als ', sonst
    der Text ohne Kommentar. None, wenn nicht lesbar."""
    w = roh.strip()
    if w.startswith('"'):
        try:
            w = json.loads(w)
        except ValueError:
            return None
        return w if isinstance(w, str) else None
    if w.startswith("'"):
        return w[1:-1].replace("''", "'") if len(w) >= 2 and w.endswith("'") else None
    return re.sub(r"[ \t]+#.*$", "", w)


def yaml_fremd(text, vault):
    """Gruende, warum eine bestehende qmd-Konfiguration nicht die eigene ist (leer = eigene): Schluessel oben
    ausser collections und models, eine andere Collection als vault, ein anderer path als der Vault (Realpfad,
    NFC) oder eine Form, die diese Pruefung nicht lesen kann. Ohne YAML-Bibliothek, im Zweifel fremd."""
    gruende = []
    ziel = _nfc(os.path.realpath(os.path.expanduser(vault)))
    oben = coll = None
    coll_einzug = feld_einzug = None
    pfad = False  # False: kein path unter vault; None: nicht lesbar
    schluessel = re.compile(r"\ufeff?[\"']?([^:\"'#]+?)[\"']?[ \t]*:(?:[ \t]+(.*))?$")
    for nr, zeile in enumerate(text.splitlines(), 1):
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        einzug = len(zeile) - len(zeile.lstrip(" "))
        m = schluessel.match(zeile[einzug:])
        wert = m.group(2).strip() if m and m.group(2) else ""
        if wert.startswith("#"):
            wert = ""
        if zeile[einzug] == "\t":
            gruende.append("Zeile %d: Tabulator im Einzug" % nr)
            continue
        if einzug == 0:
            oben, coll, coll_einzug = (m.group(1).strip() if m else None), None, None
            if oben not in YAML_OBEN:
                gruende.append("Zeile %d: Schlüssel %s" % (nr, zeile.strip()))
            elif oben == "collections" and wert:
                gruende.append("Zeile %d: Form nicht lesbar: %s" % (nr, zeile.strip()))
            continue
        if oben != "collections":
            continue  # unter models prueft pruefe_yaml
        if coll_einzug is None:
            coll_einzug = einzug
        if einzug == coll_einzug:
            coll, feld_einzug = (m.group(1).strip() if m and not wert else None), None
            if coll != COLLECTION:
                gruende.append("Zeile %d: Collection %s" % (nr, zeile.strip()))
            continue
        if einzug < coll_einzug:
            gruende.append("Zeile %d: Form nicht lesbar: %s" % (nr, zeile.strip()))
            continue
        if coll != COLLECTION:
            continue
        if feld_einzug is None:
            feld_einzug = einzug
        if einzug == feld_einzug and m and m.group(1).strip() == "path":
            pfad = _yaml_text(wert) if wert else None
    if pfad is None:
        gruende.append("path unter %s nicht lesbar" % COLLECTION)
    elif pfad and _nfc(os.path.realpath(os.path.expanduser(pfad))) != ziel:
        gruende.append("path %s statt %s" % (pfad, ziel))
    return gruende


def ist_ausgeschlossen(rel, muster):
    p = PurePosixPath(_nfc(rel))
    return any(p.full_match(_nfc(m)) for m in list(muster) + FESTE_MUSTER)


def _env(env):
    return os.environ if env is None else env


def _home(env):
    return env.get("HOME") or os.path.expanduser("~")


def qmd_db_pfad(index, env=None):
    """Datenbank des qmd-Index nach den Pfadregeln von qmd (2.8.3): $INDEX_PATH, sonst
    ($XDG_CACHE_HOME oder ~/.cache)/qmd/<index>.sqlite. Leere Variablen gelten als nicht gesetzt."""
    env = _env(env)
    if env.get("INDEX_PATH"):
        return env["INDEX_PATH"]
    cache = env.get("XDG_CACHE_HOME") or os.path.join(_home(env), ".cache")
    return os.path.join(cache, "qmd", index + ".sqlite")


def qmd_yaml_pfad(index, env=None):
    """Konfiguration des qmd-Index: $QMD_CONFIG_DIR/<index>.yml, sonst $XDG_CONFIG_HOME/qmd/<index>.yml,
    sonst ~/.config/qmd/<index>.yml."""
    env = _env(env)
    if env.get("QMD_CONFIG_DIR"):
        return os.path.join(env["QMD_CONFIG_DIR"], index + ".yml")
    conf = env.get("XDG_CONFIG_HOME") or os.path.join(_home(env), ".config")
    return os.path.join(conf, "qmd", index + ".yml")


def qmd_yaml(vault, einst):
    """qmd-Konfiguration in fester Form, ohne YAML-Bibliothek. Nie ein Schluessel models, nie global_context."""
    muster = []
    for m in list(einst["graph"]["ausschluss"]) + FESTE_MUSTER:
        # qmd normalisiert nicht, macOS-Pfade koennen NFD sein: Nicht-ASCII-Muster in beiden Formen
        formen = [m] if m.isascii() else [_nfc(m), unicodedata.normalize("NFD", m)]
        for f in formen:
            if f not in muster:
                muster.append(f)
    q = lambda t: json.dumps(t, ensure_ascii=False)  # noqa: E731  (JSON-String ist gueltiges YAML)
    zeilen = ["collections:", "  %s:" % COLLECTION, "    path: " + q(os.path.realpath(os.path.expanduser(vault))),
              "    pattern: " + q("**/*.md"), "    ignore:"]
    zeilen += ["      - " + q(m) for m in muster]
    zeilen.append("    includeByDefault: true")
    return "\n".join(zeilen) + "\n"


def _wert(roh):
    w = roh.strip()
    if len(w) >= 2 and w[0] == w[-1] and w[0] in "\"'":
        w = w[1:-1]
    return w.strip()


def pruefe_yaml(text):
    """Befunde: jede Zeile mit http:// oder https://; jeder Wert unter models:, der nicht mit hf: beginnt
    (qmd schreibt selbst einen Block models: mit lokalen hf:-Modellen, die Zeile allein ist kein Befund)."""
    befunde = []
    im_block = False
    for nr, zeile in enumerate(text.splitlines(), 1):
        if "http://" in zeile.lower() or "https://" in zeile.lower():
            befunde.append("Zeile %d: Adresse: %s" % (nr, zeile.strip()))
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        if not zeile[0].isspace():
            if re.match(r"\ufeff?(\{|\? )", zeile):
                befunde.append("Zeile %d: YAML-Form nicht erlaubt: %s" % (nr, zeile.strip()))
            m = re.match(r"\ufeff?[\"']?models[\"']?[ \t]*:[ \t]*(.*)$", zeile)
            im_block = bool(m)
            if m and _wert(m.group(1)):
                befunde.append("Zeile %d: models mit Wert: %s" % (nr, zeile.strip()))
            continue
        if im_block:
            m = re.match(r"\s+(?:-\s+)?[^:#]*:[ \t]*(.*)$", zeile)
            w = _wert(m.group(1)) if m else _wert(zeile.lstrip("- \t"))
            if w and not w.startswith("hf:"):
                befunde.append("Zeile %d: models-Wert ohne hf: %s" % (nr, zeile.strip()))
    return befunde


def pruefe_index(db_pfad, vault, muster):
    """Pfade aller Zeilen von documents (auch active=0), die unter den Ausschluss fallen; die DB wird
    schreibgeschuetzt geoeffnet. DB-Probleme sind ein Befund, keine Ausnahme. Die Pfade in documents sind
    relativ zum Ordner der Collection (= Vault), vault wird daher nicht gebraucht."""
    if not os.path.isfile(db_pfad):
        return ["Index-Datenbank fehlt: %s" % db_pfad]
    uri = Path(os.path.abspath(db_pfad)).as_uri() + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
        try:
            zeilen = list(con.execute("SELECT collection, path FROM documents ORDER BY path"))
        finally:
            con.close()
    except sqlite3.Error as ex:
        return ["Index-Datenbank nicht lesbar: %s (%s)" % (db_pfad, ex)]
    befunde = []
    for coll, p in zeilen:
        if coll != COLLECTION:
            befunde.append("fremde Collection %s: %s" % (coll, p))
        elif isinstance(p, str) and ist_ausgeschlossen(p, muster):
            befunde.append(p)
    return befunde


def qmd_aufruf(index, schritt):
    """Ein qmd-Schritt (update, embed, cleanup); Ausgabe geht durch, keine Frist (embed braucht beim
    ersten Mal ueber 20 Minuten). Rueckgabe ist der Exitcode."""
    try:
        return subprocess.run([QMD, "--index", index, schritt], cwd="/").returncode
    except FileNotFoundError:
        raise NachbarnFehler("qmd nicht gefunden")
    except OSError as ex:
        raise NachbarnFehler("qmd nicht startbar: %s" % ex)


def _yaml_schreiben(pfad, text):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = pfad + ".tmp.%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, pfad)


def _yaml_nach_lauf(yaml_pfad, wann):
    """True (und Meldung), wenn die von qmd umgeschriebene Datei Befunde hat."""
    try:
        with open(yaml_pfad, encoding="utf-8") as fh:
            befunde = pruefe_yaml(fh.read())
    except (OSError, ValueError) as ex:
        befunde = ["qmd-Konfiguration nicht lesbar: %s" % ex]
    if befunde:
        print("qmd-Konfiguration %s abgelehnt (%s):" % (wann, yaml_pfad), file=sys.stderr)
        for b in befunde:
            print("  " + b, file=sys.stderr)
    return bool(befunde)


def _index_befund(index, vault, einst, wann):
    """True (und Meldung), wenn der Index ausgeschlossene Pfade enthaelt oder nicht pruefbar ist."""
    befunde = pruefe_index(qmd_db_pfad(index), vault, einst["graph"]["ausschluss"])
    if befunde:
        print("Index enthält ausgeschlossene Pfade oder ist nicht prüfbar (%s):" % wann, file=sys.stderr)
        for b in befunde:
            print("  " + b, file=sys.stderr)
        print("Index neu bauen: die Datenbank %s samt -wal und -shm sichern und entfernen, dann verknuepfen.py index "
              "erneut starten." % qmd_db_pfad(index), file=sys.stderr)
    return bool(befunde)


def cmd_index(a, aufruf=None):
    vault = os.path.expanduser(a.vault)
    if not os.path.isdir(vault):
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    grund = python_grund()
    if grund:
        print("Index nicht gebaut: %s" % grund, file=sys.stderr)
        return 1
    einst = einstellungen_laden()
    for w in einst["warnungen"]:
        print("Warnung: %s" % w, file=sys.stderr)
    index = einst["graph"]["qmd_index"]
    yaml_pfad = qmd_yaml_pfad(index)
    try:
        with open(yaml_pfad, encoding="utf-8") as fh:
            fremd = yaml_fremd(fh.read(), vault)
    except FileNotFoundError:
        fremd = []
    except (OSError, ValueError) as ex:
        fremd = ["nicht lesbar: %s" % ex]
    if fremd:  # nie ohne Kopie ueberschreiben: Datei bleibt, kein qmd-Aufruf
        print("fremde qmd-Konfiguration in %s, anderen graph.qmd_index wählen oder Datei selbst sichern:"
              % yaml_pfad, file=sys.stderr)
        for b in fremd:
            print("  " + b, file=sys.stderr)
        return 1
    text = qmd_yaml(vault, einst)
    _yaml_schreiben(yaml_pfad, text)  # immer: qmd schreibt die Datei bei update selbst um
    befunde = pruefe_yaml(text)
    if befunde:
        print("qmd-Konfiguration abgelehnt (%s):" % yaml_pfad, file=sys.stderr)
        for b in befunde:
            print("  " + b, file=sys.stderr)
        return 1
    aufruf = aufruf or qmd_aufruf
    for schritt in ("update", "embed", "cleanup"):
        try:
            rc = aufruf(index, schritt)
        except NachbarnFehler as ex:
            print("qmd %s fehlgeschlagen: %s" % (schritt, ex), file=sys.stderr)
            return 1
        if rc != 0:
            print("qmd %s fehlgeschlagen (Exitcode %s)" % (schritt, rc), file=sys.stderr)
            return 1
        if schritt == "update":  # qmd schreibt das Modell bei update zurueck: vor embed pruefen
            if _yaml_nach_lauf(yaml_pfad, "nach update"):
                return 1
            if _index_befund(index, vault, einst, "nach update"):  # nichts Ausgeschlossenes einbetten
                return 1
    if _yaml_nach_lauf(yaml_pfad, "nach dem Lauf"):
        return 1
    if _index_befund(index, vault, einst, "nach dem Lauf"):
        return 1
    print("Index %s gebaut, Prüfung ohne Befund." % index)
    return 0


def abfrage_text(text):
    text = FRONTMATTER.sub("", text, count=1)
    return " ".join(vk.mask(text).split())[:ABFRAGE_ZEICHEN].strip()


def _kill_gruppe(p):
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        p.kill()


def qmd_runner(index, abfrage, frist, n=20):
    """Startet qmd_vektor.mjs (Abfrage per stdin) in eigener Prozessgruppe; bei Fristablauf stirbt die Gruppe."""
    cmd = [NODE, VEKTOR_SKRIPT, qmd_db_pfad(index), str(n)]
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", errors="replace", cwd="/", start_new_session=True)
    except FileNotFoundError:
        raise NachbarnFehler("node nicht gefunden")
    except OSError as ex:
        raise NachbarnFehler("node nicht startbar: %s" % ex)
    try:
        out, err = p.communicate(abfrage, timeout=frist)
    except subprocess.TimeoutExpired:
        _kill_gruppe(p)
        p.communicate()
        raise NachbarnFehler("qmd antwortet nicht (Frist %s s)" % frist)
    except BaseException:
        _kill_gruppe(p)
        raise
    if p.returncode != 0:
        zeilen = [z for z in (err or "").splitlines() if z.strip() and not NODE_VERSION.match(z.strip())]
        grund = "qmd Exitcode %d" % p.returncode
        if zeilen:
            grund += ": " + zeilen[-1].strip()[:STDERR_ZEICHEN]
        raise NachbarnFehler(grund)
    return out


def vsearch_lesen(stdout, vault_root):
    """Je Treffer (rel, score, titel). Nur Dateien unter dem Vault (absoluter Realpfad); qmd://, ./ und
    Fremdpfade fallen weg. titel ist der Dateiname ohne .md, das Ziel des Wikilinks."""
    fehler = NachbarnFehler("Ausgabe von qmd nicht lesbar")
    try:
        daten = json.loads(stdout)
    except ValueError:
        raise fehler
    if not isinstance(daten, list):
        raise fehler
    wurzel = _nfc(os.path.realpath(vault_root)).rstrip("/") + "/"
    res = []
    for t in daten:
        if not isinstance(t, dict):
            raise fehler
        score, datei = t.get("score"), t.get("file")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not isinstance(datei, str):
            raise fehler
        datei = _nfc(datei)
        if not datei.startswith(wurzel):
            continue
        rel = datei[len(wurzel):]
        name = rel.rsplit("/", 1)[-1]
        res.append((rel, float(score), name[:-3] if name.endswith(".md") else name))
    return res


def yaml_grund(einst, env=None):
    """Grund, warum der qmd-Index nicht befragt werden darf (Konfiguration fehlt, unlesbar, Fremdmodell),
    sonst None. Einzige Stelle dieser Pruefung: nachbarn() und eichen.py nutzen sie."""
    try:
        with open(qmd_yaml_pfad(einst["graph"]["qmd_index"], env), encoding="utf-8") as fh:
            yaml_text = fh.read()
    except FileNotFoundError:
        return "qmd-Index nicht gebaut (verknuepfen.py index)"
    except (OSError, ValueError) as ex:
        return "qmd-Konfiguration nicht lesbar: %s" % ex
    if pruefe_yaml(yaml_text):
        return "qmd-Konfiguration mit Fremdmodell"
    return None


def ueber_schwelle(score, schwelle):
    """Ein Treffer zaehlt als verwandt ab der Schwelle (score == schwelle zaehlt mit). Einzige Stelle der Regel."""
    return score >= schwelle


def nachbarn(v, rel, einst, runner=qmd_runner):
    g = einst["graph"]
    if g.get("schwelle") is None:
        return [], "Schwelle nicht geeicht"
    grund = python_grund()
    if grund:
        return [], grund
    muster = g.get("ausschluss", [])
    if ist_ausgeschlossen(rel, muster):
        return [], "Notiz vom Vektorindex ausgeschlossen"
    if rel not in v.texts:
        return [], "Notiz nicht im Vault"
    abfrage = abfrage_text(v.texts[rel])
    if not abfrage:
        return [], "Notiz ohne Text"
    grund = yaml_grund(einst)
    if grund:
        return [], grund
    try:
        out = runner(g["qmd_index"], abfrage, g["qmd_frist"])
        treffer = vsearch_lesen(out, v.root)
    except NachbarnFehler as ex:
        return [], str(ex)
    verlinkt = vk.linked_targets(rel, v.texts[rel], v.resolver)
    bester = {}
    for r, score, titel in treffer:
        if r not in v.texts or r == rel or r in verlinkt or ist_ausgeschlossen(r, muster):
            continue
        if not ueber_schwelle(score, g["schwelle"]):
            continue
        if r not in bester or score > bester[r].score:
            # Wie _target: Dateiname, bei mehrdeutigem Namen der Pfad ohne .md.
            ziel = titel if v.resolver.resolve(titel, rel) == r else r[:-3]
            bester[r] = Nachbar(r, score, ziel)
    res = sorted(bester.values(), key=lambda n: (-n.score, n.rel))
    return res[:g["max_nachbarn"]], None


def cmd_nachbarn(a):
    vault = os.path.expanduser(a.vault)
    if not os.path.isdir(vault):
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    v = vk.load_vault(vault)
    rel = vk._rel(v, a.note)
    if rel is None:
        print("Notiz nicht im Vault: %s" % a.note, file=sys.stderr)
        return 1
    einst = einstellungen_laden()
    for w in einst["warnungen"]:
        print("Warnung: %s" % w, file=sys.stderr)
    res, grund = nachbarn(v, rel, einst, qmd_runner)
    if grund:
        print("Schritt 4 übersprungen: %s" % grund)
    for n in res:
        print("Verwandt: [[%s]] (%.2f)" % (n.titel, n.score))
    if a.json:
        try:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump({"vault": v.root, "note": rel, "uebersprungen": grund,
                           "nachbarn": [n.__dict__ for n in res]}, fh, ensure_ascii=False, indent=1)
        except OSError as ex:
            print("JSON-Datei nicht schreibbar: %s (%s)" % (a.json, ex.strerror or ex), file=sys.stderr)
            return 2
    return 0
