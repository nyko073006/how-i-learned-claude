#!/usr/bin/env python3
"""Pruefskript des Lint-Skills.

Zaehlt die Schritte 1, 3 und 4 und sammelt die Daten fuer Schritt 6 (Index).
Schritt 2 (Link-Vorschlaege) bleibt Handarbeit; dafuer liefert das Skript je
Waise die Stellen, an denen sie als Text oder Pfad erwaehnt, aber nicht verlinkt
ist. Aendert nichts im Vault, nur Python-Standardbibliothek.

    python3 -I vault_lint.py [--vault PFAD] [--heute JJJJ-MM-TT] [--json DATEI]
                             [--teil alles|orphans|inbox|projekte|index|graph]

Ausgabe: kurze Zusammenfassung auf stdout, volle Daten in der JSON-Datei.
"""
import argparse
import datetime
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict
from urllib.parse import unquote

# Gemeinsame Einstellungsdatei der Skills; der Pfad ist per Env ueberschreibbar (Tests).
# Eigene Kopie der Lese-Logik, damit der Skill einzeln installierbar bleibt.
EINSTELLUNGEN_ENV = "CLAUDE_SKILLS_EINSTELLUNGEN"
EINSTELLUNGEN_PFAD = "~/.config/claude-skills/einstellungen.json"


class EinstellungsFehler(Exception):
    """Einstellungsdatei unlesbar oder Pflichtwert fehlt; der Text ist die Meldung fuer stderr."""


def einstellungen_pfad(pfad=None):
    """Ausdruecklicher Pfad, sonst Env CLAUDE_SKILLS_EINSTELLUNGEN, sonst die Vorgabe."""
    return os.path.expanduser(pfad or os.environ.get(EINSTELLUNGEN_ENV, "").strip() or EINSTELLUNGEN_PFAD)


def einstellungen(pfad=None):
    """Einstellungen als dict, bei jedem Aufruf frisch gelesen; fehlt die Datei, {}.
    Kaputtes JSON oder kein Objekt: EinstellungsFehler mit Pfad."""
    ziel = einstellungen_pfad(pfad)
    try:
        with open(ziel, encoding="utf-8") as fh:
            daten = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as ex:
        raise EinstellungsFehler("Einstellungsdatei %s ist nicht lesbar: %s" % (ziel, ex))
    if not isinstance(daten, dict):
        raise EinstellungsFehler("Einstellungsdatei %s muss ein JSON-Objekt sein." % ziel)
    return daten


def vault_vorgabe():
    """Wert vault aus den Einstellungen oder None."""
    v = einstellungen().get("vault")
    return v if isinstance(v, str) and v.strip() else None


def vault_waehlen(arg):
    """--vault, sonst die Einstellung vault, jeweils mit ~ aufgeloest. Fehlt beides: EinstellungsFehler."""
    v = arg or vault_vorgabe()
    if not v:
        raise EinstellungsFehler("Vault-Pfad fehlt: --vault angeben oder `vault` in %s setzen"
                                 % einstellungen_pfad())
    return os.path.expanduser(v)
SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules", "__pycache__"}
ATTACHMENTS = "07 Anhaenge"
PARA_DIRS = ["00 Kontext", "01 Inbox", "02 Projekte", "03 Bereiche", "04 Ressourcen",
             "05 Daily Notes", "06 Archiv", ATTACHMENTS]
EXTRA_ROOT_DIRS = {"Briefings", "Lint-Reports", "memory"}
ROOT_SYSTEM_FILES = {"CLAUDE.md", "AGENTS.md", "OTHER_AI.md", "log.md", "Index.md"}
# Links aus diesen Quellen zaehlen nicht als eingehend: der Lint schreibt sie
# selbst, sonst rettete der eigene Report die Waisen, die er meldet.
GENERATED_ROOT_FILES = {"Index.md"}
GENERATED_DIRS = {"Lint-Reports"}
ORPHAN_EXEMPT_DIRS = {"05 Daily Notes", "00 Kontext", "memory", "06 Archiv", "Briefings"}
# 06 Archiv/: Sicherungen sollen bytegleich bleiben (Entscheidung 15.10.2026)
FRONTMATTER_SKIP_DIRS = {"memory", "Briefings", "06 Archiv"}
# Tabellenstuecke, die ein Montageskript per swap_table einsetzt; ein Frontmatter
# wanderte mit in die Montage (Entscheidung 15.10.2026)
FRAGMENT_PREFIX = "frag_"
PROJECT_ALLOWED = {"Projekt-Governance.md", "Financials.md", "Fehlerlog.md"}
PROJECT_SUBDIRS = ["Meetings", "Decisions", "Research", "assets"]
HUB_SUFFIX = " - PMO HUB.md"
START_PATTERNS = ["{n}", "{n} - Uebersicht", "{n}-Uebersicht", "{n} - Übersicht", "{n}-Übersicht"]
GENERIC_STEMS = {"readme", "index", "notes", "notizen", "briefing"}
MENTIONS_MAX = 3
PRE_BACKLOG_MAX_DAYS = 30
INBOX_WARN = 5

WIKILINK = re.compile(r"!?\[\[([^\]\n]+?)\]\]")
MDLINK = re.compile(r"\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^)\s]+))(?:\s+\"[^\"\n]*\")?\s*\)")
FENCE_OPEN = re.compile(r"(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"(`{3,}|~{3,})[ \t]*$")
# Inline-Code wie CommonMark: eine Backtick-Folge schliesst nur mit einer gleich langen.
INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|\Z)", re.S)
HEADING = re.compile(r"(?m)^#{1,6}\s")
OPEN_ITEM = re.compile(r"(?m)^\s*[-*]\s+\[ \]")
DAILY = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,6}$")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def top(rel):
    return rel.split("/", 1)[0]


def stem(rel):
    name = rel.rsplit("/", 1)[-1]
    return name[:-3] if name.endswith(".md") else name


def parent(rel):
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def walk(vault):
    """Alle Dateien als NFC-Pfad relativ zum Vault -> echter Pfad."""
    out = {}
    for root, dirs, files in os.walk(vault):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        rel = os.path.relpath(root, vault)
        for f in files:
            if f == ".DS_Store":
                continue
            r = f if rel == "." else os.path.join(rel, f)
            out[nfc(r.replace(os.sep, "/"))] = os.path.join(root, f)
    return out


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def strip_code(text):
    """Code entfernen, Zeilennummern bleiben gleich.

    Codebloecke wie CommonMark und Obsidian: Ein Block endet nur an einer Zeile
    aus mindestens so vielen gleichen Zeichen ohne Info-String (```dataview
    schliesst keinen ```markdown-Block), ein offener Block laeuft bis zum Ende.
    """
    out, fence = [], None
    for line in text.split("\n"):
        s = line.lstrip(" ")
        indented = len(line) - len(s) > 3
        if fence is None:
            m = None if indented else FENCE_OPEN.match(s)
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                out.append("")
            else:
                out.append(INLINE_CODE.sub("", line))
        else:
            m = None if indented else FENCE_CLOSE.match(s)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            out.append("")
    return "\n".join(out)


def frontmatter(text):
    m = FRONTMATTER.match(text)
    return m.group(1) if m else None


def fm_value(fm, key):
    if fm is None:
        return None
    m = re.search(r"(?m)^%s[ \t]*:[ \t]*(.*)$" % re.escape(key), fm)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'") or None


def days_since(value, today):
    try:
        return (today - datetime.date.fromisoformat(str(value)[:10])).days
    except (TypeError, ValueError):
        return None


class Resolver:
    """Loest Link-Ziele auf wie Obsidian: Name, Pfad-Ende, Gross/Klein egal."""

    def __init__(self, files):
        self.files = sorted(files)
        self.lower = [(f.lower(), f) for f in self.files]
        self.by_stem, self.by_name = {}, {}
        for f in self.files:
            name = f.rsplit("/", 1)[-1].lower()
            self.by_name.setdefault(name, []).append(f)
            if name.endswith(".md"):
                self.by_stem.setdefault(name[:-3], []).append(f)

    @staticmethod
    def _pick(candidates, src):
        same = [c for c in candidates if parent(c) == parent(src)]
        return sorted(same or candidates, key=lambda c: (len(c), c))[0]

    def resolve(self, target, src):
        t = nfc(target).split("|", 1)[0]
        t = re.split(r"[#^]", t, maxsplit=1)[0].strip()
        if not t:
            return src
        tl = t.lower().lstrip("/")
        if tl.endswith(".md"):
            tl = tl[:-3]
        if "/" in tl:
            hits = []
            for fl, f in self.lower:
                base = fl[:-3] if fl.endswith(".md") else fl
                if base == tl or base.endswith("/" + tl) or fl == tl or fl.endswith("/" + tl):
                    hits.append(f)
            return self._pick(hits, src) if hits else None
        # Ein Punkt im Namen ("Build 1.4.0") ist nur dann eine Endung, wenn es
        # die Datei mit genau diesem Namen gibt.
        if EXTENSION.search(tl) and tl in self.by_name:
            return self._pick(self.by_name[tl], src)
        if tl in self.by_stem:
            return self._pick(self.by_stem[tl], src)
        if tl in self.by_name:
            return self._pick(self.by_name[tl], src)
        return None

    def resolve_markdown(self, target, src):
        """Wie Obsidian: jedes Ziel ohne Schema ist ein Notizlink, auch `[Text](url)`."""
        t = target.strip()
        if re.match(r"^[a-z][a-z0-9+.-]*:", t, re.I):
            return "extern"
        t = nfc(unquote(t.split("#", 1)[0]))
        if not t:
            return src
        rel = os.path.normpath(os.path.join(parent(src), t)).replace(os.sep, "/")
        for cand in (rel, rel + ".md"):
            if cand in self.by_name.get(cand.rsplit("/", 1)[-1].lower(), []):
                return cand
        return self.resolve(t, src)


def is_generated(rel):
    return rel in GENERATED_ROOT_FILES or top(rel) in GENERATED_DIRS


def is_fragment(rel):
    return rel.rsplit("/", 1)[-1].startswith(FRAGMENT_PREFIX)


def orphan_exempt(rel):
    parts = rel.split("/")
    if parts[0] in ORPHAN_EXEMPT_DIRS or is_fragment(rel):
        return True
    if len(parts) == 1 and (parts[0] in ROOT_SYSTEM_FILES or parts[0].endswith(" Tasks.md")):
        return True
    return len(parts) >= 2 and stem(rel) == parts[-2]


def frontmatter_skip(rel):
    return (top(rel) in FRONTMATTER_SKIP_DIRS or is_fragment(rel)
            or ("/" not in rel and rel.endswith(" Tasks.md")))


def start_file(folder_rel, name, md_set):
    for pat in START_PATTERNS:
        cand = "%s/%s.md" % (folder_rel, pat.format(n=name))
        if cand in md_set:
            return stem(cand)
    return None


def subdirs(vault, rel):
    path = os.path.join(vault, rel)
    if not os.path.isdir(path):
        return []
    return sorted(nfc(d) for d in os.listdir(path)
                  if not d.startswith(".") and d not in SKIP_DIRS and os.path.isdir(os.path.join(path, d)))


def direct_files(files, folder_rel):
    pre = folder_rel + "/"
    return sorted(f[len(pre):] for f in files
                  if f.startswith(pre) and "/" not in f[len(pre):] and not f[len(pre):].startswith("."))


def find_mentions(orphan, texts, sources):
    name = stem(orphan)
    needle = name
    if name.lower() in GENERIC_STEMS or len(name) < 5:
        needle = parent(orphan).rsplit("/", 1)[-1] or name
    hits = []
    for src in sources:
        if src == orphan or is_generated(src):
            continue
        text = texts[src]
        pos = text.find(needle)
        while pos >= 0 and len(hits) < MENTIONS_MAX:
            line = text.count("\n", 0, pos) + 1
            start = text.rfind("\n", 0, pos) + 1
            end = text.find("\n", pos)
            snippet = text[start:end if end >= 0 else len(text)].strip()
            hits.append({"source": src, "line": line, "text": snippet[:160]})
            pos = text.find(needle, end if end >= 0 else len(text))
        if len(hits) >= MENTIONS_MAX:
            break
    return hits


def pre_backlog(text):
    m = re.search(r"Pre-Backlog Action Items", text)
    if not m:
        return None
    nxt = HEADING.search(text, m.end())
    return len(OPEN_ITEM.findall(text[m.end():nxt.start() if nxt else len(text)]))


# --- Graph (Spec Knowledge Graph, Abschnitt 6) ---
ENTITY_TYPES = ("person", "firma", "projekt", "werkzeug")
RELATIONS = ("kunde_von", "nutzt", "entschieden_in")


def dienst_ordner():
    """Einstellung dienst_ordner (Vault-relativ) ohne / am Ende; Vorgabe "", dann ist nichts dienstlich."""
    d = einstellungen().get("dienst_ordner")
    return nfc(d.strip()).rstrip("/") if isinstance(d, str) else ""


def is_dienst(rel):
    """Liegt rel (Vault-relativ, mit /) unter dienst_ordner()? Einzige Stelle fuer diese Bedingung."""
    d = dienst_ordner()
    return bool(d) and rel.startswith(d + "/")


WIKI_VALUE = re.compile(r"\[\[([^\]\n]+?)\]\]")


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s.strip()


def _split_top(s):
    """Trennt an Kommas, ausser in Anfuehrungszeichen oder in [[...]]."""
    parts, cur, quote, depth, i = [], [], None, 0, 0
    while i < len(s):
        ch = s[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'" and not "".join(cur).strip():
            quote = ch
        elif s.startswith("[[", i):
            depth += 1
            cur.append("[[")
            i += 2
            continue
        elif s.startswith("]]", i) and depth:
            depth -= 1
            cur.append("]]")
            i += 2
            continue
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return [v for v in (_unquote(p) for p in parts) if v]


def fm_list(fm, key):
    """Liste aus dem Frontmatter: None ohne Schluessel, sonst die Werte ohne Anfuehrungszeichen."""
    if fm is None:
        return None
    lines = fm.split("\n")
    pat = re.compile(r"^%s[ \t]*:(.*)$" % re.escape(key))
    for n, line in enumerate(lines):
        m = pat.match(line.rstrip("\r"))
        if not m:
            continue
        rest = m.group(1).strip()
        if not rest:
            out = []
            for nxt in lines[n + 1:]:
                b = re.match(r"^[ \t]*-[ \t]+(.*)$", nxt.rstrip("\r"))
                if not b:
                    break
                v = _unquote(b.group(1))
                if v:
                    out.append(v)
            return out
        # "[a, b]" ist eine Liste, "[[X]]" ein unzitierter Link, "[[[X]], b]" wieder eine Liste
        if rest.startswith("[") and (not rest.startswith("[[") or rest.startswith("[[[")) and rest.endswith("]"):
            return _split_top(rest[1:-1])
        return _split_top(rest)
    return None


def fm_end_line(text):
    """Zeile (1-basiert) der schliessenden --- des Frontmatters, 0 ohne Frontmatter."""
    m = FRONTMATTER.match(text)
    return text.count("\n", 0, m.end(1)) + 2 if m else 0


def name_key(s):
    """Vergleichsschluessel fuer Namen: NFC, ohne Raender, casefold."""
    return nfc(s).strip().casefold()


NOT_ENTITY_DIRS = ("06 Archiv", "Briefings", "memory")


def is_underscore_or_excluded(rel):
    """Datei mit _-Praefix oder in Archiv/Briefings/memory: weder Entitaet noch L1-Quelle."""
    return rel.rsplit("/", 1)[-1].startswith("_") or top(rel) in NOT_ENTITY_DIRS


URL = re.compile(r"https?://\S+")


def _blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def mention_text(text):
    """Text fuer L1: ohne Code, Frontmatter, Links und URLs; Zeilennummern bleiben gleich."""
    lines = strip_code(text).split("\n")
    for i in range(min(fm_end_line(text), len(lines))):
        lines[i] = ""
    t = "\n".join(lines)
    for pat in (WIKILINK, MDLINK, URL):
        t = pat.sub(_blank, t)
    return nfc(t)


def l1_mentions(ents, sources, texts, links):
    """L1: Notiz nennt eine Entitaet beim Namen, ohne irgendwo auf sie zu verlinken."""
    pats = {}
    for e, info in ents.items():
        pats[e] = [(n, re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(name_key(n))))
                   for n in sorted(info["names"], key=lambda n: -len(n)) if name_key(n)]
    found = []
    for src in sources:
        linked = {tgt for _, tgt, _ in links.get(src, []) if tgt}
        whole = "\n".join(name_key(l) for l in mention_text(texts.get(src, "")).split("\n"))
        raw = texts.get(src, "").split("\n")
        dienst = is_dienst(src)
        for e in sorted(ents):
            if e == src or e in linked:
                continue
            if dienst and ents[e]["type"] == "person":
                continue  # Personen in Dienstnotizen werden nie verlinkt (wie /verknuepfen)
            hit = None
            for n, pat in pats[e]:
                # Teilstring-Vorpruefung spart die Regex-Suche; Zeile ueber die Zaehlung der Umbrueche
                m = pat.search(whole) if name_key(n) in whole else None
                if m:
                    i = whole.count("\n", 0, m.start())
                    if hit is None or i < hit[1]:
                        hit = (n, i)
            if hit:
                found.append({"note": src, "entity": e, "name": hit[0], "line": hit[1] + 1,
                              "text": raw[hit[1]][:160] if hit[1] < len(raw) else ""})
    return found


def l2_entity_orphans(ents, incoming):
    """L2: Entitaeten ohne eingehenden Link (unabhaengig von orphan_exempt)."""
    return sorted(e for e in ents if not incoming.get(e))


def entities(notes, texts):
    """Register: Notizen mit type person/firma/projekt/werkzeug im Frontmatter."""
    out = {}
    for f in notes:
        if is_underscore_or_excluded(f):
            continue
        fm = frontmatter(texts.get(f, ""))
        typ = fm_value(fm, "type")
        if typ not in ENTITY_TYPES:
            continue
        title = stem(f)
        cand = [title]
        if f.endswith(HUB_SUFFIX):
            cand.append(title[:-len(HUB_SUFFIX[:-3])])
        cand += fm_list(fm, "aliases") or []
        names, seen = [], set()
        for c in cand:
            k = name_key(c)
            if k and k not in seen:
                seen.add(k)
                names.append(nfc(c).strip())
        out[f] = {"type": typ, "title": title, "names": names,
                  "rel": {r: fm_list(fm, r) or [] for r in RELATIONS}}
    return out


L4_SOURCE = {"kunde_von": ("person", "firma"), "nutzt": ("projekt",)}
L4_TARGET = {"kunde_von": "projekt", "nutzt": "werkzeug", "entschieden_in": "keine Entität"}


def l4_conflicts(ents, resolver):
    """L4: Beziehung passt nicht zum Typ, Ziel fehlt, Wert ohne Link, Name doppelt."""
    found = []
    for a in sorted(ents):
        e = ents[a]
        for feld in RELATIONS:
            vals = e["rel"].get(feld) or []
            if not vals:
                continue
            if feld in L4_SOURCE and e["type"] not in L4_SOURCE[feld]:
                found.append({"kind": "typ", "entity": a, "feld": feld, "seite": "quelle", "ist": e["type"]})
                continue
            for roh in vals:
                m = WIKI_VALUE.fullmatch(roh.strip())
                if not m:
                    found.append({"kind": "kein_link", "entity": a, "feld": feld, "wert": roh})
                    continue
                tgt = resolver.resolve(m.group(1), a)
                if tgt is None:
                    found.append({"kind": "fehlt", "entity": a, "feld": feld, "ziel": roh})
                    continue
                if not tgt.endswith(".md"):
                    ist = "keine Notiz"
                else:
                    ist = ents[tgt]["type"] if tgt in ents else "keine Entität"
                if ist != L4_TARGET[feld]:
                    found.append({"kind": "typ", "entity": a, "feld": feld, "seite": "ziel", "ziel": tgt,
                                  "ist": ist, "erwartet": L4_TARGET[feld]})
    owners = OrderedDict()
    for a in sorted(ents):
        for n in ents[a]["names"]:
            owners.setdefault(name_key(n), [])
            if a not in owners[name_key(n)]:
                owners[name_key(n)].append(a)
    for name, who in owners.items():
        if len(who) > 1:
            found.append({"kind": "doppelt", "name": name, "entities": who})
    return found


def l4_text(f):
    if f["kind"] == "typ" and f["seite"] == "quelle":
        return "%s: %s passt nicht zu type %s" % (f["entity"], f["feld"], f["ist"])
    if f["kind"] == "typ":
        return "%s: %s -> %s ist %s, erwartet %s" % (f["entity"], f["feld"], f["ziel"], f["ist"], f["erwartet"])
    if f["kind"] == "fehlt":
        return "%s: %s -> %s loest nicht auf" % (f["entity"], f["feld"], f["ziel"])
    if f["kind"] == "kein_link":
        return "%s: %s-Wert ohne [[...]]: %s" % (f["entity"], f["feld"], f["wert"])
    return "Name \"%s\" doppelt: %s" % (f["name"], ", ".join(f["entities"]))


def l3_backlinks(ents, links, texts):
    """L3: Entitaet A verlinkt im Koerper Entitaet B, B verlinkt weder im Koerper noch im Frontmatter auf A."""
    found = []
    for a in sorted(ents):
        ende = fm_end_line(texts.get(a, ""))
        first = OrderedDict()
        for _raw, tgt, line in links.get(a, []):
            if line > ende and tgt in ents and tgt != a \
                    and (tgt not in first or line < first[tgt]):
                first[tgt] = line
        for b, line in first.items():
            if not any(t == a for _r, t, _l in links.get(b, [])):
                found.append({"from": a, "to": b, "line": line})
    return found


def l5_dienst(ents, links):
    """L5: Personen und Dienstliches (dienst_ordner) duerfen sich nicht verlinken oder dort liegen.
    Ohne dienst_ordner bleibt die Liste leer."""
    found, seen = [], set()

    def add(person, andere, richtung):
        k = (person, andere, richtung)
        if k not in seen:
            seen.add(k)
            found.append({"person": person, "andere": andere, "richtung": richtung})

    persons = sorted(p for p in ents if ents[p]["type"] == "person")
    pset = set(persons)
    for p in persons:
        if is_dienst(p):
            add(p, p, "liegt_in")
        for _raw, tgt, _line in links.get(p, []):
            if tgt and is_dienst(tgt):
                add(p, tgt, "aus")
    for src in sorted(links):
        if is_dienst(src):
            for _raw, tgt, _line in links[src]:
                if tgt in pset:
                    add(tgt, src, "in")
    return found


def note_links(src, text, resolver):
    """Links einer Notiz ausserhalb von Code: (Rohziel, aufgeloestes Ziel oder None, Zeile).

    Erst alle Wikilinks, dann alle Markdown-Links; externe Markdown-Links fehlen.
    """
    body = strip_code(text)
    out = []
    for m in WIKILINK.finditer(body):
        tgt = resolver.resolve(m.group(1), src)
        out.append((m.group(1), tgt, body.count("\n", 0, m.start()) + 1))
    for m in MDLINK.finditer(body):
        raw = m.group(1) or m.group(2)
        tgt = resolver.resolve_markdown(raw, src)
        if tgt != "extern":
            out.append((raw, tgt, body.count("\n", 0, m.start()) + 1))
    return out


def analyse(vault, today):
    vault = os.path.abspath(os.path.expanduser(vault))
    files = walk(vault)
    md_all = sorted(f for f in files if f.endswith(".md") and top(f) != ATTACHMENTS)
    md_set = set(md_all)
    notes = [f for f in md_all if top(f) != "memory"]
    texts = {f: read(files[f]) for f in md_all}
    resolver = Resolver(files.keys())

    links = {}
    incoming = {f: set() for f in md_all}
    for src in md_all:
        out = note_links(src, texts[src], resolver)
        links[src] = out
        if is_generated(src):
            continue
        for _, tgt, _ in out:
            if tgt and tgt != src and tgt in incoming:
                incoming[tgt].add(src)

    orphans = [f for f in notes if not orphan_exempt(f) and not incoming[f]]
    mentions = {o: find_mentions(o, texts, md_all) for o in orphans}

    fms = {f: frontmatter(texts[f]) for f in notes}
    no_fm = [f for f in notes if not frontmatter_skip(f) and fms[f] is None]
    no_tags = [f for f in notes if not frontmatter_skip(f) and fms[f] is not None
               and not re.search(r"(?m)^tags[ \t]*:", fms[f])]

    inbox = [f for f in files if top(f) == "01 Inbox" and not f.rsplit("/", 1)[-1].startswith(".")]

    ressourcen = []
    for d in subdirs(vault, "04 Ressourcen"):
        rel = "04 Ressourcen/" + d
        ressourcen.append({
            "name": d,
            "start": d if rel + "/" + d + ".md" in md_set else None,
            "md": sum(1 for f in md_all if f.startswith(rel + "/")),
            "pages": [stem(f) for f in direct_files(md_set, rel) if f.endswith(".md")],
            "subdirs": subdirs(vault, rel),
        })
    bereiche = [{"name": b, "start": start_file("03 Bereiche/" + b, b, md_set),
                 "md": sum(1 for f in md_all if f.startswith("03 Bereiche/%s/" % b))}
                for b in subdirs(vault, "03 Bereiche")]

    root_strays = sorted(f for f in files if "/" not in f and not f.startswith(".")
                         and f not in ROOT_SYSTEM_FILES and not f.endswith(" Tasks.md"))
    root_dirs = [d for d in subdirs(vault, ".") if d not in PARA_DIRS and d not in EXTRA_ROOT_DIRS]

    containers, project_dirs = [], []
    for d in subdirs(vault, "02 Projekte"):
        if d.startswith("_"):
            subs = subdirs(vault, "02 Projekte/" + d)
            containers.append({"name": d, "subprojects": subs})
            project_dirs += ["02 Projekte/%s/%s" % (d, s) for s in subs]
        else:
            project_dirs.append("02 Projekte/" + d)
    projects_root_files = direct_files(files, "02 Projekte")

    projects, closed, active = OrderedDict(), [], []
    for pd in project_dirs:
        name = pd.rsplit("/", 1)[-1]
        rootfiles = direct_files(files, pd)
        hubs = [f for f in rootfiles if f.endswith(HUB_SUFFIX)]
        naming = []
        if not hubs:
            naming = [{"file": f, "suggest": name + HUB_SUFFIX} for f in rootfiles
                      if f.endswith(" - Hub.md") or f == name + ".md"]
        skip = set(hubs) | PROJECT_ALLOWED | {n["file"] for n in naming}
        missing = ([] if hubs else ["PMO HUB"]) + \
                  ([] if "Projekt-Governance.md" in rootfiles else ["Projekt-Governance.md"])
        md_assets = []
        for f in md_all:
            if f.startswith(pd + "/"):
                segs = f[len(pd) + 1:].split("/")[:-1]
                if "assets" in segs:
                    md_assets.append({"path": f, "research": "Research" in segs[:segs.index("assets")]})
        hubinfo = OrderedDict()
        for h in hubs:
            hp = pd + "/" + h
            fm = frontmatter(texts.get(hp, ""))
            age = days_since(fm_value(fm, "aktualisiert"), today)
            pb = pre_backlog(texts.get(hp, ""))
            info = {
                "status": fm_value(fm, "status"), "phase": fm_value(fm, "phase"),
                "aktualisiert": fm_value(fm, "aktualisiert"), "age_days": age,
                "broken": [{"link": raw, "line": line} for raw, tgt, line in links.get(hp, []) if tgt is None],
                "pre_backlog_open": pb,
                "pre_backlog_stale": bool(pb) and age is not None and age > PRE_BACKLOG_MAX_DAYS,
            }
            hubinfo[h] = info
            if info["status"] == "abgeschlossen":
                closed.append(pd)
            if info["status"] == "aktiv":
                active.append({"hub": stem(hp), "project": pd, "phase": info["phase"],
                               "aktualisiert": info["aktualisiert"], "age_days": age,
                               "pre_backlog_open": pb})
        decisions = []
        for f in md_all:
            if f.startswith(pd + "/Decisions/"):
                fm = frontmatter(texts[f])
                problems = []
                if fm_value(fm, "status") == "entschieden" and not fm_value(fm, "entschieden_am"):
                    problems.append("entschieden_am leer")
                if fm_value(fm, "type") != "entscheidung":
                    problems.append("type fehlt oder nicht entscheidung")
                if problems:
                    decisions.append({"path": f, "problems": problems})
        projects[pd] = {
            "rootfiles": rootfiles,
            "whitelist_violations": [f for f in rootfiles if f not in skip],
            "readme": "README.md" in rootfiles,
            "missing": missing,
            "missing_subdirs": [s for s in PROJECT_SUBDIRS if not os.path.isdir(os.path.join(vault, pd, s))],
            "naming": naming,
            "md_in_assets": md_assets,
            "hubs": hubinfo,
            "decisions": decisions,
        }
    active.sort(key=lambda p: (p["aktualisiert"] or ""), reverse=True)

    hub_paths = {pd + "/" + h for pd, p in projects.items() for h in p["hubs"]}
    broken = OrderedDict()
    for f in notes:
        if f in hub_paths:
            continue
        b = [{"link": raw, "line": line} for raw, tgt, line in links[f] if tgt is None]
        if b:
            broken[f] = b

    daily = sorted((stem(f) for f in direct_files(md_set, "05 Daily Notes") if DAILY.match(f)), reverse=True)
    reports = sorted((stem(f) for f in direct_files(md_set, "Lint-Reports") if "Vault Lint Report" in f),
                     reverse=True)
    kontext = {"files": [stem(f) for f in direct_files(md_set, "00 Kontext") if f.endswith(".md")],
               "dirs": subdirs(vault, "00 Kontext")}
    counts = {
        "notes": len(notes), "notes_with_memory": len(md_all), "memory": len(md_all) - len(notes),
        "archive": sum(1 for f in notes if top(f) == "06 Archiv"),
        "briefings": sum(1 for f in files if top(f) == "Briefings"),
        "inbox": len(inbox), "orphans": len(orphans), "no_frontmatter": len(no_fm), "no_tags": len(no_tags),
        "projects": len(projects), "projects_active": len(active), "containers": len(containers),
    }
    ents = entities(notes, texts)
    sources = [f for f in notes if not is_underscore_or_excluded(f) and not is_generated(f)]
    graph = {"entities": {p: {"type": e["type"], "names": e["names"]} for p, e in ents.items()},
             "L4": l4_conflicts(ents, resolver),
             "L1": l1_mentions(ents, sources, texts, links),
             "L2": l2_entity_orphans(ents, incoming),
             "L3": l3_backlinks(ents, links, texts),
             "L5": l5_dienst(ents, links)}
    return {
        "vault": vault, "today": today.isoformat(), "counts": counts,
        "orphans": orphans, "mentions": mentions,
        "no_frontmatter": no_fm, "no_tags": no_tags, "inbox": sorted(inbox),
        "closed_projects": closed,
        "synthesis_missing": [r["name"] for r in ressourcen if not r["start"]],
        "root_strays": root_strays, "root_dirs": root_dirs, "projects_root_files": projects_root_files,
        "containers": containers, "projects": projects, "broken_links": broken,
        "index": {"projects_active": active, "bereiche": bereiche, "ressourcen": ressourcen,
                  "kontext": kontext, "daily_last": daily[:5], "daily_count": len(daily),
                  "lint_reports_last": reports[:3]},
        "graph": graph,
    }


def grouped(paths, limit=10):
    groups = OrderedDict()
    for p in paths:
        groups.setdefault(parent(p) or "(Wurzel)", []).append(p.rsplit("/", 1)[-1])
    lines = []
    for folder, names in groups.items():
        shown = ", ".join(names[:limit]) + (" … +%d" % (len(names) - limit) if len(names) > limit else "")
        lines.append("    %s (%d): %s" % (folder, len(names), shown))
    return lines


def summary(r, teil="alles"):
    c = r["counts"]
    out = ["Lint-Pruefer · %s · Stand %s" % (r["vault"], r["today"]),
           "Notizen: %d ohne memory/ (%d mit), davon %d in 06 Archiv" % (c["notes"], c["notes_with_memory"], c["archive"])]
    if teil in ("alles", "orphans"):
        out.append("[1] Verwaiste Notizen: %d" % c["orphans"])
        out += grouped(r["orphans"])
        hinted = [(o, h) for o, h in r["mentions"].items() if h]
        if hinted:
            out.append("  Erwaehnt ohne Link (erste Fundstelle):")
            for o, h in hinted:
                out.append("    %s <- %s:%d" % (stem(o), h[0]["source"], h[0]["line"]))
    if teil in ("alles", "inbox"):
        mark = "⚠" if c["inbox"] > INBOX_WARN else "✓"
        out.append("[3a] %s Inbox: %d" % (mark, c["inbox"]))
    if teil == "alles":
        out.append("[3b] Abgeschlossene Projekte (status im Hub): %s" % (", ".join(r["closed_projects"]) or "keine"))
        out.append("[3c] Ohne Frontmatter: %d" % c["no_frontmatter"])
        out += grouped(r["no_frontmatter"], limit=4)
        out.append("     Ohne tags: %d" % c["no_tags"])
        out += grouped(r["no_tags"], limit=4)
        out.append("[3d] Ressourcen-Ordner ohne gleichnamige Start-Datei: %s" % (", ".join(r["synthesis_missing"]) or "keine"))
        no_start = [b["name"] for b in r["index"]["bereiche"] if not b["start"]]
        out.append("[3e] Bereiche ohne Start-Datei: %s" % (", ".join(no_start) or "keine"))
        out.append("     Wurzel, weitere Dateien: %s" % (", ".join(r["root_strays"]) or "keine"))
        if r["root_dirs"]:
            out.append("     Wurzel, weitere Ordner: %s" % ", ".join(r["root_dirs"]))
    if teil in ("alles", "projekte"):
        ps = r["projects"]
        out.append("[4] Projekte: %d, Container: %d" % (len(ps), len(r["containers"])))
        for k in r["containers"]:
            note = " (nur %d Sub-Projekt, Container-Ebene noetig?)" % len(k["subprojects"]) if len(k["subprojects"]) <= 1 else ""
            out.append("    Container %s: %s%s" % (k["name"], ", ".join(k["subprojects"]) or "leer", note))
        if r["projects_root_files"]:
            out.append("    Dateien direkt in 02 Projekte/: %s" % ", ".join(r["projects_root_files"]))

        def line(label, items):
            out.append("  %s %s: %s" % ("✗" if items else "✓", label, "; ".join(items) if items else "keine"))

        line("4a Whitelist", ["%s: %s%s" % (pd.rsplit("/", 1)[-1], ", ".join(p["whitelist_violations"]),
                                            " (README verboten)" if p["readme"] else "")
                              for pd, p in ps.items() if p["whitelist_violations"]])
        line("4b Pflicht-Dateien", ["%s: %s" % (pd.rsplit("/", 1)[-1], ", ".join(p["missing"]))
                                    for pd, p in ps.items() if p["missing"]])
        line("4b Subordner", ["%s: %s" % (pd.rsplit("/", 1)[-1], ", ".join(p["missing_subdirs"]))
                              for pd, p in ps.items() if p["missing_subdirs"]])
        line("4c Naming", ["%s: %s -> %s" % (pd.rsplit("/", 1)[-1], n["file"], n["suggest"])
                           for pd, p in ps.items() for n in p["naming"]])
        line("4d Markdown in Research/assets", [m["path"] for p in ps.values() for m in p["md_in_assets"] if m["research"]])
        other = [m["path"] for p in ps.values() for m in p["md_in_assets"] if not m["research"]]
        if other:
            out.append("  ⚠ Hinweis Markdown in anderen assets/: %s" % "; ".join(other))
        line("4e Kaputte Hub-Links", ["%s Z.%d [[%s]]" % (h, b["line"], b["link"])
                                      for p in ps.values() for h, i in p["hubs"].items() for b in i["broken"]])
        line("4f Decisions", ["%s: %s" % (d["path"], ", ".join(d["problems"])) for p in ps.values() for d in p["decisions"]])
        line("4g Pre-Backlog > %d Tage" % PRE_BACKLOG_MAX_DAYS,
             ["%s: %d offen, Hub %d Tage" % (h, i["pre_backlog_open"], i["age_days"])
              for p in ps.values() for h, i in p["hubs"].items() if i["pre_backlog_stale"]])
        for pd, p in ps.items():
            for h, i in p["hubs"].items():
                pb = "" if i["pre_backlog_open"] is None else ", Pre-Backlog %d offen" % i["pre_backlog_open"]
                out.append("    %s: %s | %s | aktualisiert %s (%s Tage)%s" % (
                    h[:-3], i["status"], i["phase"], i["aktualisiert"], i["age_days"], pb))
    if teil == "alles" and r["broken_links"]:
        n = sum(len(b) for b in r["broken_links"].values())
        out.append("[i] Kaputte Links ausserhalb der Hubs: %d in %d Notizen" % (n, len(r["broken_links"])))
        for f, b in r["broken_links"].items():
            out.append("    %s: %s" % (f, ", ".join("Z.%d [[%s]]" % (x["line"], x["link"]) for x in b[:5])
                                       + (" … +%d" % (len(b) - 5) if len(b) > 5 else "")))
    if teil in ("alles", "index"):
        ix = r["index"]
        out.append("[6] Index: %d aktive Projekte, %d Bereiche, %d Ressourcen-Ordner, Daily Notes bis %s, Reports: %s" % (
            len(ix["projects_active"]), len(ix["bereiche"]), len(ix["ressourcen"]),
            ix["daily_last"][0] if ix["daily_last"] else "—", ", ".join(ix["lint_reports_last"]) or "keine"))
    if teil in ("alles", "graph") and "graph" in r:
        g = r["graph"]
        n = {t: sum(1 for e in g["entities"].values() if e["type"] == t) for t in ENTITY_TYPES}
        out.append("[7] Graph: %d Entitäten (%s)" % (len(g["entities"]),
                                                     ", ".join("%s %d" % (t, n[t]) for t in ENTITY_TYPES)))
        l1 = g["L1"]
        out.append("  L1 Unverlinkte Erwähnungen: %d in %d Notizen" % (len(l1), len({f["note"] for f in l1})))
        per = OrderedDict()
        for f in l1:
            per.setdefault(f["entity"], []).append(f)
        rang = sorted(per.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        for e, fs in rang[:15]:
            out.append("    %s: %d (erste: %s:%d)" % (stem(e), len(fs), stem(fs[0]["note"]), fs[0]["line"]))
        if len(rang) > 15:
            out.append("    … +%d" % (len(rang) - 15))
        out.append("  L2 Entitäten ohne eingehenden Link: %d" % len(g["L2"]))
        if g["L2"]:
            out.append("    " + ", ".join(stem(e) for e in g["L2"]))
        out.append("  L3 Fehlende Rückverweise: %d" % len(g["L3"]))
        out += ["    %s -> %s (Z.%d)" % (stem(f["from"]), stem(f["to"]), f["line"]) for f in g["L3"][:10]]
        if len(g["L3"]) > 10:
            out.append("    … +%d" % (len(g["L3"]) - 10))
        out.append("  L4 Widersprüche: %d" % len(g["L4"]))
        out += ["    " + l4_text(f) for f in g["L4"][:5]]
        if len(g["L4"]) > 5:
            out.append("    … +%d" % (len(g["L4"]) - 5))
        out.append("  L5 Grenze Dienstliches: %d" % len(g["L5"]))
        out += ["    %s: %s (%s)" % (stem(f["person"]), stem(f["andere"]), f["richtung"]) for f in g["L5"]]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pruefskript des Lint-Skills (aendert nichts).")
    ap.add_argument("--vault", default=None, help="Vorgabe: Einstellung vault")
    ap.add_argument("--heute", help="Stichtag JJJJ-MM-TT (Vorgabe: heute)")
    ap.add_argument("--json", help="volle Ergebnisse als JSON in diese Datei")
    ap.add_argument("--teil", default="alles", choices=["alles", "orphans", "inbox", "projekte", "index", "graph"])
    a = ap.parse_args(argv)
    try:
        vault = vault_waehlen(a.vault)
        dienst_ordner()  # Einstellungsdatei einmal vorab pruefen: Fehler als Klartext, nicht mitten im Lauf
    except EinstellungsFehler as ex:
        print(ex, file=sys.stderr)
        return 2
    if not os.path.isdir(vault):
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    today = datetime.date.fromisoformat(a.heute) if a.heute else datetime.date.today()
    r = analyse(vault, today)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
    print(summary(r, a.teil))
    return 0


if __name__ == "__main__":
    sys.exit(main())
