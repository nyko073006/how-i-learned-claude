#!/usr/bin/env python3
"""Kern des Skills /verknuepfen: verlinkt Erwaehnungen von Entitaeten im Vault.

Regel wie Lint-Pruefung L1 (vault_lint.l1_mentions): Eine Quelle nennt eine
Entitaet beim Titel oder Alias, ohne irgendwo auf sie zu verlinken. Je Entitaet
wird die erste freie Erwaehnung zum Wikilink. Geschuetzte Stellen (Code,
Zitate, Links, Kommentare, Pfade, Domains, Hashtags, Frontmatter) bleiben
unberuehrt. Nur Python-Standardbibliothek.

    python3 -I verknuepfen.py link [--vault P] [--dry-run] [--json DATEI] (NOTIZ... | --alle)
    python3 -I verknuepfen.py kandidaten [--vault P] [--min N] [--notiz NOTIZ...] [--json DATEI]
"""
import argparse
import contextlib
import errno
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    # ASSUMPTION: Ohne fcntl (Windows) laeuft alles ohne Sperre wie vor der Fix-Welle, weil der Skill
    # dort sonst gar nicht ladbar waere; parallele Laeufe koennen dann Eintraege verlieren.
    fcntl = None

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lint" / "scripts"))
import vault_lint as vl  # noqa: E402

TEST_ENV = "VERKNUEPFEN_TEST"

# --- Maske: geschuetzte Stellen ---
QUOTE = re.compile(r"[ \t]*>")
LIST_ITEM = re.compile(r"(?:[-*+]|\d+[.)])(?:[ \t]|$)")
OBS_COMMENT = re.compile(r"%%.*?(?:%%|\Z)", re.S)
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
TOKEN = re.compile(r"\S+")
DOMAIN = re.compile(r"(?<![\w-])(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}(?![\w-])")
HASHTAG = re.compile(r"#\w")
HEADING = re.compile(r"#{1,6}(?:[ \t]|$)")
# Referenzlink [Text][ref], Referenzdefinition [ref]: ziel (ganze Zeile), Fussnote [^x] und [^x]:
REFLINK = re.compile(r"\[[^\]\n]*\]\[[^\]\n]*\]")
REFDEF = re.compile(r"(?m)^[ \t]{0,3}\[(?!\^)[^\]\n]+\]:.*$")
FOOTNOTE = re.compile(r"\[\^[^\]\s]+\]:?")
# Endungen, bis zu denen ein Pfad mit Leerzeichen reicht (Ruling Lead, Fix-Runde 1)
PATH_EXTENSIONS = (".md", ".py", ".json", ".png", ".jpg", ".pdf", ".txt", ".csv", ".ts", ".sh")
TRAILING_PUNCT = ")]}>\"'.,;:!?»«“”„‘’"
SOURCE_EXCLUDED_DIRS = ("00 Kontext/Claude.MD/",)


@dataclass
class Vault:
    root: str
    files: dict
    texts: dict
    resolver: object
    ents: dict


def load_vault(vault):
    root = os.path.abspath(os.path.expanduser(vault))
    files = vl.walk(root)
    texts = {f: vl.read(files[f]) for f in sorted(files)
             if f.endswith(".md") and vl.top(f) != vl.ATTACHMENTS}
    notes = [f for f in texts if vl.top(f) != "memory"]
    return Vault(root, files, texts, vl.Resolver(files.keys()), vl.entities(notes, texts))


def is_source(rel):
    """Quelle wie bei L1 (ausserhalb memory/, 06 Archiv/, Briefings/, nicht generiert, ohne _), dazu
    nie 00 Kontext/Claude.MD/ und nie die Wurzeldateien aus ROOT_SYSTEM_FILES (Ruling Lead)."""
    return (rel.endswith(".md") and vl.top(rel) != vl.ATTACHMENTS
            and not vl.is_underscore_or_excluded(rel) and not vl.is_generated(rel)
            and rel not in vl.ROOT_SYSTEM_FILES
            and not rel.startswith(SOURCE_EXCLUDED_DIRS))


def _blank(s):
    return re.sub(r"[^\n]", " ", s)


def _blank_match(m):
    return _blank(m.group(0))


def _is_indented(line):
    rest = line.lstrip(" \t")
    ws = line[:len(line) - len(rest)]
    return bool(rest) and ("\t" in ws or len(ws) >= 4)


def _indent_width(line):
    """Einzug in Spalten; ein Tab zaehlt als 4."""
    w = 0
    for ch in line:
        if ch == " ":
            w += 1
        elif ch == "\t":
            w += 4
        else:
            break
    return w


def _mask_blocks(text):
    """Zeilenweise: Codebloecke (``` und ~~~), eingerueckter Code, Zitate, Callouts, Ueberschriften.

    Ein Fence zaehlt mit beliebigem Einzug aus Leerzeichen und Tabs, auch in Listen. Er schliesst
    nur mit einer Zeile, die hoechstens 3 Spalten mehr Einzug hat als die oeffnende; eine tiefer
    eingerueckte Fence-Zeile (Codebeispiel im Docstring, Codeblock in einer Liste im Block) ist Inhalt.
    """
    out, fence, fence_indent, prev_blank, prev_code = [], None, 0, True, False
    for line in text.split("\n"):
        code = False
        if fence is not None:
            m = vl.FENCE_CLOSE.match(line.lstrip(" \t"))
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                    and _indent_width(line) <= fence_indent + 3:
                fence = None
            out.append(_blank(line))
        else:
            # ASSUMPTION: Fence auch bei 4+ Zeichen Einzug, weil Codebloecke in Listen so eingerueckt
            # sind; ein frei eingerueckter Fence waere sonst eingerueckter Code und bleibt so ebenfalls maskiert.
            m = vl.FENCE_OPEN.match(line.lstrip(" \t"))
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                fence_indent = _indent_width(line)
                out.append(_blank(line))
            elif _is_indented(line) and not LIST_ITEM.match(line.lstrip(" \t")) and (prev_blank or prev_code):
                code = True
                out.append(_blank(line))
            elif QUOTE.match(line) or HEADING.match(line):
                out.append(_blank(line))
            else:
                out.append(line)
        prev_blank, prev_code = not line.strip(), code
    return "\n".join(out)


def _has_extension(tok):
    t = tok.rstrip(TRAILING_PUNCT).lower()
    return t.endswith(PATH_EXTENSIONS)


def _mask_paths_with_spaces(t):
    """Ab einem Token mit / oder \\ bis zum naechsten Token mit Dateiendung in derselben Zeile."""
    out = list(t)
    for line_m in re.finditer(r"[^\n]+", t):
        toks = [(m.start(), m.end(), m.group(0)) for m in TOKEN.finditer(line_m.group(0))]
        i = 0
        while i < len(toks):
            s0, _e0, tok = toks[i]
            if "/" in tok or "\\" in tok:
                for j in range(i, len(toks)):
                    if _has_extension(toks[j][2]):
                        a, b = line_m.start() + s0, line_m.start() + toks[j][1]
                        out[a:b] = " " * (b - a)
                        i = j
                        break
            i += 1
    return "".join(out)


def _mask_token(m):
    tok = m.group(0)
    if "/" in tok or "\\" in tok or DOMAIN.search(tok) or HASHTAG.match(tok):
        return _blank(tok)
    return tok


def mask(text):
    """Text gleicher Laenge, jede geschuetzte Stelle durch Leerzeichen ersetzt, Umbrueche bleiben."""
    fm = vl.FRONTMATTER.match(text)
    t = (_blank(fm.group(0)) + text[fm.end():]) if fm else text
    t = _mask_blocks(t)
    for pat in (OBS_COMMENT, HTML_COMMENT, vl.INLINE_CODE, vl.WIKILINK, vl.MDLINK, REFLINK, REFDEF,
                FOOTNOTE, vl.URL):
        t = pat.sub(_blank_match, t)
    t = _mask_paths_with_spaces(t)
    # Pfad (Token mit / oder \), Domain ohne Schema, Hashtag am Tokenanfang: ganzes Token
    t = TOKEN.sub(_mask_token, t)
    assert len(t) == len(text)
    return t


# --- Link-Regel ---
_PATS = {}


def _name_pat(name):
    p = _PATS.get(name)
    if p is None:
        # ASSUMPTION: Gross/Klein per re.IGNORECASE statt casefold wie L1, weil casefold die Laenge
        # aendern kann (ß -> ss) und die Fundstelle dann nicht mehr auf den Originaltext passt.
        p = _PATS[name] = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(name), re.I)
    return p


def _target(e, src, ents, resolver):
    title = ents[e]["title"]
    return title if resolver.resolve(title, src) == e else e[:-3]


def link_text(text, src, ents, resolver, linked, sperre):
    """Verlinkt je Entitaet die erste freie Erwaehnung. Gibt (neuer Text in NFC, Aenderungen)."""
    # ASSUMPTION: Text wird vor dem Suchen nach NFC gebracht, das Ergebnis ist NFC, weil die
    # Masken-Positionen sonst verrutschen (Vorgabe aus dem Brief).
    text = vl.nfc(text)
    m_text = mask(text)
    folded = m_text.casefold()
    dienst = vl.is_dienst(src)
    cands = []
    for e in sorted(ents):
        if e == src or e in linked or e in sperre:
            continue
        if dienst and ents[e]["type"] == "person":
            continue
        best = None
        for n in ents[e]["names"]:
            if not n or n.casefold() not in folded:
                continue
            m = _name_pat(n).search(m_text)
            if m and (best is None or m.start() < best[0]
                      or (m.start() == best[0] and m.end() - m.start() > best[1] - best[0])):
                best = (m.start(), m.end(), n)
        if best:
            cands.append((best[0], -(best[1] - best[0]), e, best[1], best[2]))
    cands.sort()
    chosen, taken = [], []
    for start, _neg, e, end, n in cands:
        if any(start < b and a < end for a, b in taken):
            # ASSUMPTION: Ueberlappt die erste Fundstelle einer Entitaet eine schon gewaehlte, entfaellt
            # die Entitaet fuer diese Notiz, weil die Regel nur die erste Fundstelle kennt.
            continue
        found = text[start:end]
        tgt = _target(e, src, ents, resolver)
        link = "[[%s]]" % tgt if found == tgt else "[[%s|%s]]" % (tgt, found)
        ls = text.rfind("\n", 0, start) + 1
        le = text.find("\n", start)
        line_txt = text[ls:le if le >= 0 else len(text)]
        if "|" in link and line_txt.lstrip(" \t").startswith("|"):
            continue
        taken.append((start, end))
        chosen.append((start, end, {"entity": e, "name": n, "line": text.count("\n", 0, start) + 1,
                                    "link": link}))
    chosen.sort(key=lambda c: c[0])
    new = text
    for start, end, ch in reversed(chosen):
        new = new[:start] + ch["link"] + new[end:]
    return new, [c[2] for c in chosen]


def linked_targets(src, text, resolver):
    return {tgt for _raw, tgt, _line in vl.note_links(src, text, resolver) if tgt}


def link_note(v, rel, sperre):
    """Verlinkt eine Notiz. Behalten werden nur Links, die linked_targets (vault_lint.note_links) im
    neuen Text auch sieht; sonst gaelte ein solcher Link beim naechsten Lauf als entfernt und wuerde
    gesperrt (Maske und strip_code erkennen Code verschieden, "[Kappa]" wird "[[[Kappa]]]",
    HTML-Kommentar mit Backtick). Unsichtbare Entitaeten entfallen fuer diese Notiz ganz; danach wird
    der Text ohne sie neu gebaut, bis alle verbleibenden Links sichtbar sind."""
    if not is_source(rel) or rel not in v.texts:
        return None, []
    text = v.texts[rel]
    linked = linked_targets(rel, text, v.resolver)
    aus = set(sperre)
    while True:
        new, changes = link_text(text, rel, v.ents, v.resolver, linked, aus)
        if not changes:
            return None, []
        seen = linked_targets(rel, new, v.resolver)
        unsichtbar = {c["entity"] for c in changes if c["entity"] not in seen}
        if not unsichtbar:
            return new, changes
        # Endet: aus waechst je Runde um mindestens eine Entitaet.
        aus |= unsichtbar


# --- Schreiben ---
def _norm_path(p):
    return unicodedata.normalize("NFC", os.path.realpath(os.path.expanduser(p))).casefold()


def _nutzer_home():
    """Home des angemeldeten Nutzers aus der Passwortdatenbank, unabhaengig von HOME (Tests biegen HOME um)."""
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_dir
    except (ImportError, KeyError, AttributeError):  # pragma: no cover
        return os.path.expanduser("~")


def _gesperrte_vaults():
    """Vaults, die die Testsperre schuetzt: der aus der aktiven Einstellungsdatei und der aus der Datei
    des angemeldeten Nutzers (~ dort ab dessen Home), damit ein umgebogenes HOME oder
    CLAUDE_SKILLS_EINSTELLUNGEN den echten Vault nicht freigibt. None, wenn eine Datei unlesbar ist."""
    home = _nutzer_home()
    quellen = ((None, os.path.expanduser("~")),
               (os.path.join(home, ".config", "claude-skills", "einstellungen.json"), home))
    roots = []
    for pfad, basis in quellen:
        try:
            v = vl.einstellungen(pfad).get("vault")
        except vl.EinstellungsFehler:
            return None
        if isinstance(v, str) and v.strip():
            v = v.strip()
            if v == "~" or v.startswith("~/"):
                v = basis + v[1:]
            roots.append(v)
    return roots


def write_locked(path):
    """Testsperre: Unter VERKNUEPFEN_TEST=1 nie unter dem echten Vault schreiben. Ist eine
    Einstellungsdatei unlesbar, sperrt sie alles (fail closed)."""
    if os.environ.get(TEST_ENV) != "1":
        return False
    roots = _gesperrte_vaults()
    if roots is None:
        return True
    p = _norm_path(path)
    for root in roots:
        r = _norm_path(root)
        if p == r or p.startswith(r.rstrip(os.sep) + os.sep):
            return True
    return False


def _write_all(fh, data):
    """Schreibt alle Bytes ueber einen ungepufferten Deskriptor, auch bei Teilschreibungen."""
    mv = memoryview(data)
    while mv:
        n = fh.write(mv)
        if not n:
            raise OSError("write schrieb 0 Bytes")
        mv = mv[n:]


def _discard(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _fail(path, grund):
    print("verknuepfen: nicht geschrieben (%s): %s" % (grund, path), file=sys.stderr)
    return False


def write_note(path, old_text, new_text):
    """Schreibt in die bestehende Datei, nur wenn sie noch genau old_text enthaelt.

    Liefert False bei jedem Fehler, die Datei bleibt dann unveraendert; je Fehlschlag genau eine
    Zeile auf stderr. Lesen, Vergleichen und Schreiben laufen ueber einen ungepufferten Deskriptor
    (r+b, buffering=0) in die bestehende Datei (Ruling Lead): os.replace setzte eine neue Inode und
    ein neues Erstelldatum, Obsidian zeigte dann ein falsches "Erstellt".
    """
    if write_locked(path):
        return _fail(path, "Testsperre, echter Vault")
    try:
        fh = open(path, "r+b", buffering=0)
    except OSError as exc:
        return _fail(path, exc.__class__.__name__)
    with fh:
        try:
            raw = fh.readall()
        except OSError as exc:
            return _fail(path, exc.__class__.__name__)
        try:
            current = raw.decode("utf-8")
        except UnicodeDecodeError:
            # ASSUMPTION: Datei, die nicht sauber als UTF-8 lesbar ist, wird nie geschrieben, weil
            # vault_lint.read Fehler ersetzt und ein Rueckschreiben Bytes zerstoerte.
            return _fail(path, "kein UTF-8")
        # vault_lint.read liest mit Newline-Uebersetzung (\r\n und \r werden \n), old_text hat also nie
        # \r. Eine Datei durchgehend mit \r\n wird mit \r\n zurueckgeschrieben.
        # ASSUMPTION: Gemischte Zeilenenden oder einzelne \r werden nie geschrieben, weil sie sich aus
        # dem uebersetzten Text nicht verlustfrei wiederherstellen lassen.
        crlf = "\r" in current
        if crlf and current != old_text.replace("\n", "\r\n"):
            norm = current.replace("\r\n", "\n").replace("\r", "\n")
            return _fail(path, "gemischte Zeilenenden" if norm == old_text else "seit dem Lesen geaendert")
        if not crlf and current != old_text:
            return _fail(path, "seit dem Lesen geaendert")
        data = (new_text.replace("\n", "\r\n") if crlf else new_text).encode("utf-8")
        # ASSUMPTION: Vor dem Schreiben eine Kopie der alten Bytes unter $TMPDIR, weil auch das
        # Zurueckschreiben nach einem Schreibfehler scheitern kann (z. B. E/A-Fehler). Nach Erfolg oder
        # gelungenem Zurueckschreiben wird sie entfernt; nur wenn beides scheitert, bleibt sie und ihr
        # Pfad steht in der Meldung. Laesst sich keine Kopie anlegen, wird nicht geschrieben.
        bak = None
        try:
            fd, bak = tempfile.mkstemp(prefix="verknuepfen-sicherung-", suffix=".md")
            with os.fdopen(fd, "wb") as b:
                b.write(raw)
        except OSError as exc:
            if bak:
                _discard(bak)
            return _fail(path, "keine Sicherungskopie moeglich, %s" % exc.__class__.__name__)
        try:
            fh.seek(0)
            _write_all(fh, data)
            fh.truncate()
        except OSError as exc:
            # Ein Link verlaengert den Text, ein Schreibfehler faellt also in die Verlaengerung: alte
            # Bytes zurueck und auf die alte Laenge kuerzen.
            try:
                fh.seek(0)
                _write_all(fh, raw)
                fh.truncate()
            except OSError as exc2:
                return _fail(path, "%s, Zurueckschreiben gescheitert (%s), alte Fassung unter %s"
                             % (exc.__class__.__name__, exc2.__class__.__name__, bak))
            _discard(bak)
            return _fail(path, "%s, alte Fassung zurueckgeschrieben" % exc.__class__.__name__)
    _discard(bak)
    return True


# --- Sperrliste ---
SPERRE_ENV = "AUTO_LINK_SPERRE"
SPERRE_DEFAULT = "~/.claude/hooks/auto-link-sperre.json"


def sperre_path():
    return os.path.expanduser(os.environ.get(SPERRE_ENV) or SPERRE_DEFAULT)


def sperre_load(path=None):
    """Liest die Zustandsdatei fehlertolerant: fehlt sie oder ist sie kaputt, ist der Zustand leer."""
    try:
        with open(path or sperre_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        notes = data["notes"]
        if not isinstance(notes, dict):
            raise ValueError
        clean = {}
        for rel, e in notes.items():
            if isinstance(e, dict):
                clean[rel] = {k: [x for x in e.get(k, []) if isinstance(x, str)]
                              if isinstance(e.get(k, []), list) else [] for k in ("gesetzt", "gesperrt")}
        return {"version": 1, "notes": clean}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"version": 1, "notes": {}}


def sperre_save(state, path=None):
    """Schreibt atomar (Temp-Datei im selben Ordner, dann os.replace). Gibt True bei Erfolg."""
    if not path and os.environ.get(TEST_ENV) == "1" and not os.environ.get(SPERRE_ENV):
        # ASSUMPTION: Unter VERKNUEPFEN_TEST=1 ohne AUTO_LINK_SPERRE wird die echte Zustandsdatei nie
        # geschrieben, weil die bestehenden Tests sie sonst anlegten (Brief: nie anlegen).
        return False
    path = path or sperre_path()
    tmp = None
    try:
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".sperre-", dir=d)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except OSError:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return False


def _entry(state, rel):
    return state.setdefault("notes", {}).setdefault(rel, {"gesetzt": [], "gesperrt": []})


def sperre_pruefen(state, rel, linked_now):
    """Jede gesetzte Entitaet, die nicht mehr verlinkt ist, wird gesperrt. Gibt gesperrt[rel]."""
    e = state.get("notes", {}).get(rel)
    if not e:
        return set()
    weg = [x for x in e["gesetzt"] if x not in linked_now]
    if weg:
        e["gesetzt"] = [x for x in e["gesetzt"] if x in linked_now]
        e["gesperrt"] += [x for x in weg if x not in e["gesperrt"]]
    return set(e["gesperrt"])


def sperre_merken(state, rel, neu):
    if not neu:
        return
    e = _entry(state, rel)
    e["gesetzt"] += [x for x in neu if x not in e["gesetzt"]]


SPERRFRIST_ENV = "VERKNUEPFEN_SPERRFRIST"
SPERRFRIST_VORGABE = 10.0  # Sekunden; unter dem Hook-Timeout von 15 s
SPERRFRIST_MAX = 12.0  # Obergrenze: Vault laden (bis ~1 s) plus Frist bleibt unter dem Hook-Timeout von 15 s
SPERRE_PAUSE = 0.05
SPERRE_BELEGT = object()  # Rueckgabe von _sperre_lock: Frist abgelaufen, Sperre gehoert jemand anderem
GRUND_BELEGT = "Sperre belegt (Frist %s s abgelaufen)"


def _sperrfrist():
    """Frist in Sekunden: VERKNUEPFEN_SPERRFRIST (float >= 0, endlich, hoechstens SPERRFRIST_MAX), sonst
    SPERRFRIST_VORGABE. Gibt nie -0.0 zurueck."""
    try:
        wert = float(os.environ[SPERRFRIST_ENV])
    except (KeyError, ValueError):
        return SPERRFRIST_VORGABE
    if not (0 <= wert < float("inf")):  # auch NaN
        return SPERRFRIST_VORGABE
    return max(0.0, min(wert, SPERRFRIST_MAX))


def _sperre_lock(sperre_pfad, frist=None):
    """Oeffnet <Zustandsdatei>.lock und sperrt sie exklusiv (fcntl.flock, LOCK_NB in einer Schleife mit
    SPERRE_PAUSE) hoechstens frist Sekunden lang (None = _sperrfrist(); 0 = ein Versuch). Gibt das Dateihandle (close() gibt frei),
    None, wenn die Lock-Datei sich nicht anlegen oder sperren laesst, oder SPERRE_BELEGT, wenn die
    Frist ablief (Handle ist dann geschlossen)."""
    if not sperre_pfad and os.environ.get(TEST_ENV) == "1" and not os.environ.get(SPERRE_ENV):
        return None  # wie sperre_save: unter der Testsperre nie neben der echten Zustandsdatei anlegen
    if fcntl is None:  # pragma: no cover
        return contextlib.nullcontext()
    pfad = (sperre_pfad or sperre_path()) + ".lock"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        fh = open(pfad, "a")
    except OSError:
        return None
    if frist is None:
        frist = _sperrfrist()
    ende = time.monotonic() + frist
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh  # close() gibt die Sperre frei
        except OSError as e:
            if not (isinstance(e, BlockingIOError) or e.errno in (errno.EWOULDBLOCK, errno.EAGAIN)):
                fh.close()  # EACCES, ENOLCK usw.: nicht belegt, sondern nicht sperrbar
                return None
            rest = ende - time.monotonic()
            if rest > 0:
                time.sleep(min(SPERRE_PAUSE, rest))
            if time.monotonic() >= ende:  # nach Ablauf kein weiterer Versuch
                fh.close()
                return SPERRE_BELEGT


def link_and_record(v, rel, state, sperre_pfad, dry_run):
    """Gemeinsamer Ablauf von Hook und CLI. Gibt (geschrieben, changes, fehler).

    Die Zustandsaenderung laeuft unter einer exklusiven Sperre auf <Zustandsdatei>.lock: Unter der
    Sperre wird der Zustand neu geladen (state wird ersetzt), nur der Eintrag von rel geaendert und
    gespeichert; die Notiz wird ebenfalls unter der Sperre geschrieben. Sonst verloeren parallele
    Laeufe (Hook aus mehreren Sitzungen) Eintraege. Trockenlauf: keine Sperre, state wie uebergeben.
    Laesst sich die Lock-Datei nicht anlegen, gilt das wie "Zustandsdatei nicht schreibbar": Muesste
    etwas gespeichert werden, bleibt die Notiz unveraendert und es kommt eine Meldung.
    Ist die Sperre nach der Frist (_sperrfrist(), Vorgabe 10 s, hoechstens 12 s) noch belegt, gilt dasselbe mit dem
    Grund "Sperre belegt (Frist N s abgelaufen)" statt "Zustandsdatei nicht schreibbar".
    """
    if dry_run:
        return _link_and_record(v, rel, state, sperre_pfad, True)
    frist = _sperrfrist()
    lk = _sperre_lock(sperre_pfad, frist)
    if lk is None or lk is SPERRE_BELEGT:
        grund = GRUND_BELEGT % ("%g" % frist) if lk is SPERRE_BELEGT else "Zustandsdatei nicht schreibbar"
        frisch = sperre_load(sperre_pfad)
        state.clear()
        state.update(frisch)
        probe = json.loads(json.dumps(frisch))
        vorher = json.dumps(probe, sort_keys=True)
        _ok, changes, _f = _link_and_record(v, rel, probe, sperre_pfad, True)
        if changes or json.dumps(probe, sort_keys=True) != vorher:
            _fail(rel if changes else (sperre_pfad or sperre_path()), grund)
            return False, changes, grund
        return False, [], None
    with lk:
        state.clear()
        state.update(sperre_load(sperre_pfad))
        return _link_and_record(v, rel, state, sperre_pfad, False)


def _link_and_record(v, rel, state, sperre_pfad, dry_run):
    """Ablauf ohne Sperre (link_and_record haelt sie).

    Reihenfolge: Vereinigung gesetzt mit verlinkt, sperre_pruefen, link_note; bei Aenderungen zuerst Zustand speichern
    (scheitert das, wird die Notiz nicht geschrieben), dann write_note (bei False Zustand zurueck);
    ohne Aenderungen nur den Zustand speichern, wenn er sich geaendert hat. Trockenlauf speichert nie.
    Beim Scheitern steht eine Zeile auf stderr (_fail bzw. write_note), fehler ist dann ein Text.
    """
    notes = state.setdefault("notes", {})
    vorher = json.dumps(state, sort_keys=True)
    prev = json.loads(vorher)
    pfad = sperre_pfad or sperre_path()
    existierte = os.path.exists(pfad)
    # Jeder Lauf (Ruling Lead): aktuell verlinkte Entitaeten, auch von Hand oder vom alten Hook
    # gesetzte, gelten als gesetzt (ausser den gesperrten); entfernt der Nutzer sie spaeter, kommen
    # sie nicht zurueck. Ein Eintrag entsteht nur, wenn etwas darin steht.
    linked = linked_targets(rel, v.texts[rel], v.resolver)
    alt = notes.get(rel, {}).get("gesperrt", [])
    sperre_merken(state, rel, sorted(x for x in linked if x not in alt and x in v.ents))
    gesperrt = sperre_pruefen(state, rel, linked)
    new, changes = link_note(v, rel, gesperrt)

    def zurueck():
        # Nur den eigenen Eintrag auf den Stand vom Laufbeginn setzen, den Rest frisch lesen.
        eigen = prev.get("notes", {}).get(rel)
        jetzt = sperre_load(sperre_pfad)
        if eigen is None:
            jetzt["notes"].pop(rel, None)
        else:
            jetzt["notes"][rel] = eigen
        state.clear()
        state.update(jetzt)
        if not existierte and not jetzt["notes"]:
            try:
                os.unlink(pfad)
            except OSError:
                pass
        elif not sperre_save(jetzt, sperre_pfad):
            print("verknuepfen: Zustand nicht zurueckgesetzt: %s" % pfad, file=sys.stderr)

    if new is not None:
        sperre_merken(state, rel, [c["entity"] for c in changes])
    if dry_run:
        return False, changes, None
    if new is None:
        if json.dumps(state, sort_keys=True) != vorher and not sperre_save(state, sperre_pfad):
            _fail(pfad, "Zustandsdatei nicht schreibbar")
            return False, [], "Zustandsdatei nicht schreibbar"
        return False, [], None
    if not sperre_save(state, sperre_pfad):
        state.clear()
        state.update(prev)
        _fail(rel, "Zustandsdatei nicht schreibbar")
        return False, changes, "Zustandsdatei nicht schreibbar"
    if not write_note(v.files[rel], v.texts[rel], new):
        zurueck()
        return False, changes, "nicht geschrieben"
    return True, changes, None


# --- Kandidaten (Schritt 2) ---
_CAP = r"[A-ZÄÖÜ][\w&-]*"
SUFFIX = r"(?:GmbH|AG|UG|KG|SE|e\.V\.|Inc\.|Ltd\.)"
FIRMA = re.compile(r"(?<![\w-])((?:%s[ \t]+){0,3}%s)[ \t]+%s(?!\w)" % (_CAP, _CAP, SUFFIX))
# Titelkette ("Herr Dr. X", "Prof. Dr. X"): alle Titel gehoeren nicht zum Namen, "Dr"/"Prof" ist nie der Name.
PERSON = re.compile(r"(?<![\w-])(?:(?:Herr|Frau|Dr\.|Prof\.)[ \t]+)+(?!(?:Dr|Prof)\b)(%s(?:[ \t]+%s)?)(?![\w-])"
                    % (_CAP, _CAP))
WERKZEUG = re.compile(r"(?<![\w-])(?=[A-Za-z0-9]*[a-z][A-Z])[A-Za-z][A-Za-z0-9]{3,}(?![\w-])")


# ASSUMPTION: Fuehrende Artikel und Fuellwoerter gehoeren nicht zum Firmennamen, weil ein Satzanfang
# ("Die Tau GmbH") sonst jede Schreibweise einzeln zaehlt und die Haeufung verhindert.
FUELLWOERTER = {"der", "die", "das", "dem", "den", "des", "ein", "eine", "einer", "einen", "und", "oder", "mit",
                "von", "bei", "fuer", "für", "im", "am", "zur", "zum", "wir", "auch", "dann", "als", "the", "a", "an"}


def _firma_name(m):
    woerter = m.group(1).split()
    while woerter and woerter[0].casefold() in FUELLWOERTER:
        woerter.pop(0)
    if not woerter:  # "Eine GmbH", "Die AG": nur ein Artikel vor der Rechtsform
        return None
    return " ".join(woerter) + " " + m.group(0).split()[-1]


def _treffer(masked):
    for m in FIRMA.finditer(masked):
        name = _firma_name(m)
        if name:
            yield "firma", name
    for m in PERSON.finditer(masked):
        yield "person", m.group(1)
    for m in WERKZEUG.finditer(masked):
        if m.group(0) != "GmbH":  # Rechtsform, kein Werkzeug
            yield "werkzeug", m.group(0)


def kandidaten(v, minimum=2, notizen=None):
    """Namen, die in mindestens `minimum` Quellnotizen vorkommen und wie Person, Firma oder Werkzeug
    aussehen, aber keine Entitaet sind. Nur Vorschlag, legt nie etwas an."""
    vorhanden = set()
    for e in v.ents.values():
        for n in e["names"]:
            vorhanden.add(vl.name_key(n))
        vorhanden.add(vl.name_key(e["title"]))
    gesehen = {}  # (art, key) -> {"name": Schreibweise, "notizen": []}
    nur = set(notizen) if notizen is not None else None
    for rel in sorted(v.texts):
        if not is_source(rel):
            continue
        dienst = vl.is_dienst(rel)
        for art, name in _treffer(mask(v.texts[rel])):
            if art == "person" and dienst:
                continue
            k = vl.name_key(name)
            if k in vorhanden:
                continue
            if art == "firma":
                # ASSUMPTION: Eine Firma ohne Rechtsform-Zusatz gilt als vorhanden, weil Entitaeten
                # meist ohne Zusatz heissen ("Rho" fuer "Rho GmbH").
                if vl.name_key(re.sub(r"[ \t]+%s$" % SUFFIX, "", name)) in vorhanden:
                    continue
            d = gesehen.setdefault((art, k), {"name": name, "notizen": []})
            if rel not in d["notizen"]:
                d["notizen"].append(rel)
    # Die Zaehlung bleibt vault-weit; `notizen` (Filter) waehlt nur, welche Kandidaten gezeigt werden.
    res = [{"name": d["name"], "art": art, "notizen": len(d["notizen"]), "beispiele": d["notizen"][:2],
            "alle_notizen": d["notizen"]}
           for (art, _), d in gesehen.items()
           if len(d["notizen"]) >= minimum and (nur is None or nur & set(d["notizen"]))]
    res.sort(key=lambda r: (-r["notizen"], r["name"]))
    return res


def cmd_kandidaten(a):
    vault = os.path.expanduser(a.vault)
    if not os.path.isdir(vault):
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    v = load_vault(vault)
    code, nur = 0, None
    if a.notiz:
        nur = []
        for n in a.notiz:
            r = _rel(v, n)
            if r is None:
                print("Notiz nicht im Vault: %s" % n, file=sys.stderr)
                code = 1
            elif r not in nur:
                nur.append(r)
    res = kandidaten(v, a.min, nur)
    for r in res[:29]:
        print("%-9s %-32s %d Notizen  %s" % (r["art"], r["name"], r["notizen"], r["beispiele"][0]))
    if len(res) > 29:
        print("... und %d weitere (siehe --json)" % (len(res) - 29))
    elif not res:
        print("Keine Kandidaten.")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    return code


# --- CLI ---
def _rel(v, note):
    p = os.path.expanduser(note)
    if os.path.isabs(p):
        r = os.path.relpath(os.path.realpath(p), os.path.realpath(v.root))
        if r == ".." or r.startswith(".." + os.sep):
            return None
        p = r
    rel = vl.nfc(p.replace(os.sep, "/"))
    return rel if rel in v.texts else None


def cmd_link(a):
    vault = os.path.expanduser(a.vault)
    if not os.path.isdir(vault):
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    if bool(a.notes) == bool(a.alle):
        print("Entweder NOTIZ... oder --alle angeben.", file=sys.stderr)
        return 2
    v = load_vault(vault)
    code = 0
    if a.alle:
        rels = [r for r in v.texts if is_source(r)]
    else:
        rels = []
        for n in a.notes:
            r = _rel(v, n)
            if r is None:
                print("Notiz nicht im Vault: %s" % n, file=sys.stderr)
                code = 1
            elif r not in rels:
                rels.append(r)
    report, not_written, n_links, n_notes = [], [], 0, 0
    state = sperre_load()
    for rel in rels:
        ok, changes, fehler = link_and_record(v, rel, state, None, a.dry_run)
        if fehler:
            not_written.append(rel)  # Grund steht schon auf stderr
            continue
        if not changes:
            continue
        n_notes += 1
        n_links += len(changes)
        for c in changes:
            print("%s:%d %s" % (rel, c["line"], c["link"]))
            report.append({"note": rel, **c})
    print("%d Links in %d Notizen" % (n_links, n_notes))
    if not_written:
        # ASSUMPTION: Nicht geschriebene Notizen aendern den Exitcode nicht (0), weil der Lauf weitergeht
        # und der Hook (Task 2) nie blockieren darf; sie stehen auf stderr und im JSON.
        print("%d Notizen nicht geschrieben" % len(not_written), file=sys.stderr)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"vault": v.root, "dry_run": a.dry_run, "links": n_links, "notes": n_notes,
                       "changes": report, "not_written": not_written}, fh, ensure_ascii=False, indent=1)
    return code


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verlinkt Erwaehnungen von Entitaeten im Vault.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("link", help="Erwaehnungen verlinken")
    lk.add_argument("--vault", default=None, help="Vorgabe: Einstellung vault")
    lk.add_argument("--dry-run", action="store_true", help="nichts schreiben")
    lk.add_argument("--json", help="Aenderungen als JSON in diese Datei")
    lk.add_argument("--alle", action="store_true", help="alle Quellen im Vault")
    lk.add_argument("notes", nargs="*", metavar="NOTIZ", help="absolut oder relativ zum Vault")
    kd = sub.add_parser("kandidaten", help="neue Entitaeten vorschlagen (nur melden)")
    kd.add_argument("--vault", default=None, help="Vorgabe: Einstellung vault")
    kd.add_argument("--min", type=int, default=2, help="mindestens so viele Notizen")
    kd.add_argument("--notiz", nargs="+", action="extend", metavar="NOTIZ", help="nur Kandidaten dieser Notizen")
    kd.add_argument("--json", help="Kandidaten als JSON in diese Datei")
    nbr = sub.add_parser("nachbarn", help="semantische Nachbarn vorschlagen (nur melden, qmd)")
    nbr.add_argument("--vault", default=None, help="Vorgabe: Einstellung vault")
    nbr.add_argument("--json", help="Nachbarn als JSON in diese Datei")
    nbr.add_argument("note", metavar="NOTIZ", help="absolut oder relativ zum Vault")
    ix = sub.add_parser("index", help="qmd-Konfiguration schreiben, Index bauen und pruefen (qmd, lokal)")
    ix.add_argument("--vault", default=None, help="Vorgabe: Einstellung vault")
    a = ap.parse_args(argv)
    try:
        a.vault = vl.vault_waehlen(a.vault)
        vl.dienst_ordner()  # Einstellungsdatei einmal vorab pruefen: Fehler als Klartext, nicht mitten im Lauf
    except vl.EinstellungsFehler as ex:
        print(ex, file=sys.stderr)
        return 2
    if a.cmd == "index":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nachbarn  # erst hier: nachbarn importiert verknuepfen
        return nachbarn.cmd_index(a)
    if a.cmd == "nachbarn":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I kennt das Skriptverzeichnis nicht
        import nachbarn  # erst hier: nachbarn importiert verknuepfen
        return nachbarn.cmd_nachbarn(a)
    if a.cmd == "kandidaten":
        return cmd_kandidaten(a)
    if a.cmd == "link":
        return cmd_link(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())
