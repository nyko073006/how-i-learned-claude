#!/usr/bin/env python3
"""Prueft, was beim letzten Neuladen oder Neustart von Obsidian an Claude-Sitzungen verloren ging.

Liest nur, aendert nichts. Je Sitzung: letzte gespeicherte Nachricht im Transkript
(~/.claude/projects/*/<id>.jsonl) gegen Belege fuer spaetere Arbeit:
  1. Kontextstand der Cockpit-Statusdatei weicht vom letzten Stand im Transkript ab,
  2. Commits mit dem Claude-Session-Trailer der Sitzung nach der letzten Nachricht,
  3. Vault-Dateien, die nach der letzten Nachricht geaendert wurden und die Session-URL nennen.
Der Zeitstempel der Statusdatei allein ist kein Beleg: die Statuszeile schreibt ihn auch im Leerlauf
(refreshInterval). Nur Python-Standardbibliothek.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

EINSTELLUNGEN_ENV = "CLAUDE_SKILLS_EINSTELLUNGEN"
EINSTELLUNGEN_PFAD = "~/.config/claude-skills/einstellungen.json"
OBSIDIAN_BIN = "/Applications/Obsidian.app/Contents/MacOS/Obsidian"
# ASSUMPTION: Belege bis 10 Minuten nach der letzten Nachricht gehoeren noch zu ihr (Nachschreiben, Commit-Dauer).
GAP_MIN = 10
SESSION_RE = re.compile(r"session_([A-Za-z0-9]{20,})")
# Repos in iCloud-Ordnern: ohne trustctime=false haengt git status (ctime aendert sich staendig).
GIT = ["git", "-c", "core.trustctime=false", "-c", "core.checkStat=minimal"]


class EinstellungsFehler(Exception):
    """Einstellungsdatei unlesbar oder Pflichtwert fehlt; der Text ist die Meldung fuer stderr."""


def einstellungen_pfad():
    """Env CLAUDE_SKILLS_EINSTELLUNGEN, sonst die Vorgabe."""
    return os.path.expanduser(os.environ.get(EINSTELLUNGEN_ENV, "").strip() or EINSTELLUNGEN_PFAD)


def einstellungen():
    """Einstellungen als dict, bei jedem Aufruf frisch gelesen; fehlt die Datei, {}.
    Kaputtes JSON oder kein Objekt: EinstellungsFehler mit Pfad."""
    ziel = einstellungen_pfad()
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


def vault_waehlen(arg):
    """--vault, sonst Einstellung vault, mit ~ aufgeloest. Fehlt beides: EinstellungsFehler."""
    v = arg
    if not v:
        w = einstellungen().get("vault")
        v = w if isinstance(w, str) and w.strip() else None
    if not v:
        raise EinstellungsFehler("Vault-Pfad fehlt: --vault angeben oder `vault` in %s setzen"
                                 % einstellungen_pfad())
    return os.path.expanduser(v)


def repo_wurzeln_waehlen(arg):
    """--repos, sonst Einstellung repo_wurzeln, sonst ~/Developer (nur wenn der Schluessel fehlt); mit ~ aufgeloest.
    Vorhanden, aber keine nichtleere Liste aus Strings: EinstellungsFehler, kein stiller Rueckfall."""
    if arg is not None:
        # ASSUMPTION: Mit --repos wird die Einstellung nicht geprueft, weil sie dann nicht gebraucht wird.
        return [os.path.expanduser(r) for r in arg]
    daten = einstellungen()
    # ASSUMPTION: null zaehlt wie ein fehlender Schluessel, weil JSON null "kein Wert" bedeutet
    w = daten.get("repo_wurzeln")
    if w is None:
        return [os.path.expanduser("~/Developer")]
    # ASSUMPTION: Ein leerer oder nur aus Leerraum bestehender Pfad ist keine Wurzel und gilt als Fehler.
    if not (isinstance(w, list) and w and all(isinstance(r, str) and r.strip() for r in w)):
        raise EinstellungsFehler("Einstellung `repo_wurzeln` in %s muss eine nichtleere Liste aus Pfaden (Strings, nicht leer) sein, "
                                 "gefunden: %s" % (einstellungen_pfad(), _typname(w)))
    return [os.path.expanduser(r) for r in w]


def _typname(wert):
    if isinstance(wert, list):
        return "leere Liste" if not wert else "Liste mit Nicht-Strings oder leeren Pfaden"
    return {bool: "Wahrheitswert", int: "Zahl", float: "Zahl", dict: "Objekt", str: "String"}.get(
        type(wert), "null" if wert is None else type(wert).__name__)


def local(ts):
    return dt.datetime.fromtimestamp(ts).astimezone()


def parse_iso(s):
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone()
    except (ValueError, AttributeError):
        return None


def fmt(t):
    return t.strftime("%d.%m. %H:%M") if t else "–"


def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def obsidian_process():
    """(pid, startzeit, kind_markierung) des Obsidian-Hauptprozesses oder None."""
    rc, out = run(["ps", "-axo", "pid=,lstart=,command="])
    if rc != 0:
        return None
    for line in out.splitlines():
        m = re.match(r"\s*(\d+)\s+(\w{3}\s+\w{3}\s+\d+\s+[\d:]+\s+\d{4})\s+(.*)$", line)
        if m and m.group(3).strip() == OBSIDIAN_BIN:
            start = dt.datetime.strptime(" ".join(m.group(2).split()), "%a %b %d %H:%M:%S %Y").astimezone()
            _, env = run(["ps", "eww", "-o", "command=", "-p", m.group(1)])
            return int(m.group(1)), start, "CLAUDE_CODE_CHILD_SESSION=" in env
    return None


def context_of(usage):
    return (usage.get("input_tokens") or 0) + (usage.get("cache_creation_input_tokens") or 0) + \
        (usage.get("cache_read_input_tokens") or 0)


def read_transcript(path, cut):
    """Kennzahlen eines Transkripts, nur Nachrichten vor cut zaehlen als 'davor'."""
    info = {"path": path, "cwd": None, "last_msg": None, "last_ctx": None, "last_prompt": None,
            "open_call": None, "after": 0, "bridges": set(), "mtime": local(os.path.getmtime(path))}
    uses, done = {}, set()
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            info["cwd"] = info["cwd"] or e.get("cwd")
            if e.get("type") == "bridge-session" and str(e.get("bridgeSessionId", "")).startswith("cse_"):
                info["bridges"].add(e["bridgeSessionId"][4:])
            if e.get("type") not in ("user", "assistant"):
                continue
            t = parse_iso(e.get("timestamp"))
            if not t:
                continue
            if t >= cut:
                info["after"] += 1
                continue
            msg = e.get("message") or {}
            if e["type"] == "assistant" and isinstance(msg.get("usage"), dict):
                info["last_ctx"] = context_of(msg["usage"])
            content = msg.get("content")
            text = content if isinstance(content, str) else ""
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        uses[b.get("id")] = (t, b.get("name"), json.dumps(b.get("input"), ensure_ascii=False)[:160])
                    elif b.get("type") == "tool_result":
                        done.add(b.get("tool_use_id"))
                    elif b.get("type") == "text":
                        text += b.get("text", "")
            if not info["last_msg"] or t > info["last_msg"]:
                info["last_msg"] = t
            if e["type"] == "user" and text.strip() and not text.lstrip().startswith("<") and not e.get("isMeta"):
                info["last_prompt"] = (t, " ".join(text.split())[:160])
    pending = [v for k, v in uses.items() if k not in done]
    if pending:
        info["open_call"] = max(pending)
    return info


def find_transcripts(projects):
    return {os.path.basename(p)[:-6]: p for p in glob.glob(os.path.join(glob.escape(projects), "*", "*.jsonl"))}


def cockpit_status(cockpit):
    out = {}
    for p in glob.glob(os.path.join(glob.escape(cockpit), "sessions", "*.json")):
        try:
            with open(p) as fh:
                d = json.load(fh)
        except (ValueError, OSError):
            continue
        sid = d.get("session_id") or os.path.basename(p)[:-5]
        written = d.get("written_at")
        out[sid] = {"written": local(written) if written else local(os.path.getmtime(p)),
                    "context": d.get("context_tokens"), "model": d.get("model")}
    return out


def git_repos(roots, extra):
    """Haupt-Repos unter den Wurzeln (eine Ebene tief) plus die Repos der Sitzungsordner."""
    repos = set()
    candidates = list(extra)
    for root in roots:
        candidates += [p for p in glob.glob(os.path.join(glob.escape(root), "*")) if os.path.isdir(p)]
    for c in candidates:
        if not c or not os.path.isdir(c):
            continue
        rc, out = run(GIT + ["-C", c, "rev-parse", "--path-format=absolute", "--git-common-dir"])
        common = out.strip()
        if rc == 0 and common.endswith("/.git"):
            repos.add(os.path.dirname(common))
    return sorted(repos)


def commits_between(repo, since, until):
    """[(zeit, hash, betreff, session_suffix|None)] auf allen Zweigen."""
    rc, out = run(GIT + ["-C", repo, "log", "--all", f"--since={since.isoformat()}", f"--until={until.isoformat()}",
                   "--format=%at%x1f%h%x1f%s%x1f%(trailers:key=Claude-Session,valueonly,separator=%x20)"])
    res = []
    for line in out.splitlines() if rc == 0 else []:
        parts = line.split("\x1f")
        if len(parts) == 4:
            m = SESSION_RE.search(parts[3])
            res.append((local(int(parts[0])), parts[1], parts[2], m.group(1) if m else None))
    return res


def dirty_worktrees(repo, since):
    """Worktrees mit ungesicherten Aenderungen, deren Dateien seit 'since' angefasst wurden."""
    res = []
    rc, out = run(GIT + ["-C", repo, "worktree", "list", "--porcelain"])
    for line in out.splitlines() if rc == 0 else []:
        if not line.startswith("worktree "):
            continue
        wt = line[9:]
        rc2, st = run(GIT + ["-C", wt, "status", "--porcelain"])
        if rc2 != 0 or not st.strip():
            continue
        recent = 0
        for row in st.splitlines():
            p = os.path.join(wt, row[3:].split(" -> ")[-1].strip('"'))
            try:
                if local(os.path.getmtime(p)) >= since:
                    recent += 1
            except OSError:
                pass
        if recent:
            res.append((wt, len(st.splitlines()), recent))
    return res


def vault_files(vault, since, until):
    """[(mtime, relpfad, {session_suffixe})] der .md-Dateien im Zeitraum."""
    hits = []
    if not vault or not os.path.isdir(vault):
        return hits
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            m = local(os.path.getmtime(p))
            if since <= m < until:
                try:
                    with open(p, errors="replace") as fh:
                        ids = set(SESSION_RE.findall(fh.read()))
                except OSError:
                    ids = set()
                hits.append((m, os.path.relpath(p, vault), ids))
    return sorted(hits)


def analyse(cut, lookback_h, projects, cockpit, vault, repo_roots):
    window_start = cut - dt.timedelta(hours=lookback_h)
    transcripts = find_transcripts(projects)
    status = cockpit_status(cockpit)
    ids = {sid for sid, s in status.items() if s["written"] >= window_start}
    ids |= {sid for sid, p in transcripts.items() if local(os.path.getmtime(p)) >= window_start}
    rows = []
    for sid in ids:
        st = status.get(sid)
        tr = read_transcript(transcripts[sid], cut) if sid in transcripts else None
        if not tr and (not st or not st["context"] or st["written"] >= cut):
            continue  # leerer Tab oder erst nach dem Neustart entstanden
        if tr and not tr["last_msg"]:
            continue  # erst nach dem Neustart begonnen
        rows.append({"id": sid, "st": st, "tr": tr, "proof": [], "verdict": None})
    gap_starts = [r["tr"]["last_msg"] for r in rows if r["tr"]]
    since = max(window_start, min(gap_starts)) if gap_starts else window_start
    until = cut + dt.timedelta(minutes=1)
    roots = repo_roots + [r["tr"]["cwd"] for r in rows if r["tr"] and r["tr"]["cwd"]]
    commits = {repo: commits_between(repo, since, until) for repo in git_repos(repo_roots, roots[len(repo_roots):])}
    files = vault_files(vault, since, until)
    # Eine Remote-Session (cse_…) ueberlebt /clear; Belege gehoeren der juengsten Sitzung im Tab.
    owner = {}
    for r in rows:
        for b in (r["tr"]["bridges"] if r["tr"] else ()):
            if b not in owner or r["tr"]["last_msg"] > owner[b]["tr"]["last_msg"]:
                owner[b] = r
    for r in rows:
        tr, st = r["tr"], r["st"]
        if tr:
            tr["own"] = {b for b in tr["bridges"] if owner.get(b) is r}
        if not tr:
            r["verdict"] = "KEIN TRANSKRIPT"
            continue
        limit = tr["last_msg"] + dt.timedelta(minutes=GAP_MIN)
        if st and st["written"] < cut and st["context"] and tr["last_ctx"] is not None and st["context"] != tr["last_ctx"]:
            r["proof"].append((st["written"], f"Kontext laut Statuszeile {st['context']}, im Transkript zuletzt {tr['last_ctx']}"))
        for repo, cs in commits.items():
            for t, h, subj, sess in cs:
                if sess and sess in tr["own"] and t > limit:
                    r["proof"].append((t, f"Commit {h} in {repo}: {subj}"))
        for m, rel, sids in files:
            if sids & tr["own"] and m > limit:
                r["proof"].append((m, f"Vault: {rel}"))
        r["proof"].sort()
        if r["proof"]:
            r["verdict"] = "VERLUST"
        elif tr["open_call"] and tr["open_call"][0] >= tr["last_msg"] - dt.timedelta(seconds=1):
            r["verdict"] = "OFFENER AUFRUF"
        else:
            r["verdict"] = "OK"
    order = {"KEIN TRANSKRIPT": 0, "VERLUST": 1, "OFFENER AUFRUF": 2, "OK": 3}
    rows.sort(key=lambda r: (order[r["verdict"]], -((r["tr"] and r["tr"]["last_msg"]) or cut).timestamp()))
    # Ohne Zuordnung nur ab der fruehesten letzten Nachricht einer betroffenen Sitzung.
    lost_from = [r["tr"]["last_msg"] for r in rows if r["verdict"] != "OK" and r["tr"]]
    loose_since = min(lost_from) if lost_from else None
    loose, dirty = [], []
    if loose_since:
        known = {b for r in rows if r["tr"] for b in r["tr"]["bridges"]}
        for repo, cs in commits.items():
            for t, h, subj, sess in cs:
                if t >= loose_since and (not sess or sess not in known):
                    loose.append((t, f"Commit {h} in {repo}: {subj}" + ("" if sess else " (ohne Session-Trailer)")))
        dirty = [(repo, d) for repo in commits for d in dirty_worktrees(repo, loose_since)]
    return {"rows": rows, "since": loose_since, "window_start": window_start, "loose": sorted(loose), "dirty": dirty}


def report(cut, cut_source, proc, res, lookback_h, out=sys.stdout):
    w = lambda s="": print(s, file=out)
    w(f"# Reload-Verlust: Neustart {fmt(cut)} ({cut_source})\n")
    if proc:
        pid, start, child = proc
        w(f"Obsidian läuft seit {fmt(start)} (PID {pid}). Geerbte CLAUDE_CODE_CHILD_SESSION: "
          f"{'JA, die Cockpit-Tabs speichern gerade keine Transkripte' if child else 'nein'}.")
    else:
        w("Obsidian-Hauptprozess nicht gefunden.")
    w(f"Geprüft: Sitzungen mit Lebenszeichen ab {fmt(res['window_start'])} ({lookback_h:g} h vor dem Neustart).\n")
    rows = res["rows"]
    if not rows:
        w("Keine Sitzung im Zeitraum.")
        return
    lost = [r for r in rows if r["verdict"] != "OK"]
    w(f"**Ergebnis:** {len(lost)} von {len(rows)} Sitzungen betroffen.\n")
    w("## Sitzungen\n")
    for r in rows:
        tr, st = r["tr"], r["st"]
        w(f"### {r['id'][:8]} [{r['verdict']}] {(tr and tr['cwd']) or '?'}")
        if tr:
            w(f"- letzte gespeicherte Nachricht: {fmt(tr['last_msg'])}")
        if st:
            open_until = fmt(st["written"]) if st["written"] < cut else "nach dem Neustart wieder offen"
            w(f"- Tab offen bis: {open_until}; Kontext {st['context']} Tokens, {st['model']}")
        if tr and tr["last_prompt"]:
            w(f"- letzter gespeicherter Prompt {fmt(tr['last_prompt'][0])}: {tr['last_prompt'][1]}")
        for t, text in r["proof"]:
            w(f"- Beleg {fmt(t)}: {text}")
        if r["verdict"] == "OFFENER AUFRUF":
            t, name, inp = tr["open_call"]
            w(f"- offener Aufruf {fmt(t)}: {name} {inp}")
        if r["verdict"] == "KEIN TRANSKRIPT":
            w("- ganze Sitzung ohne Transkript, Inhalt nur aus Dateien rekonstruierbar")
        if tr:
            w(f"- nach dem Neustart: {tr['after']} Nachrichten" + (" (fortgesetzt)" if tr["after"] else ""))
        w()
    if res["loose"] or res["dirty"]:
        w(f"## Ohne Zuordnung ab {fmt(res['since'])}\n")
        for t, text in res["loose"]:
            w(f"- {fmt(t)} {text}")
        for repo, (wt, n, recent) in res["dirty"]:
            w(f"- UNGESICHERT: {wt} ({n} Dateien geändert, {recent} davon seit {fmt(res['since'])})")
        w()


def parse_zeit(s, now=None):
    now = now or dt.datetime.now().astimezone()
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        h, m = map(int, s.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M").astimezone()


def main(argv=None):
    home = os.path.expanduser("~")
    ap = argparse.ArgumentParser(description="Was ging beim letzten Obsidian-Neuladen an Claude-Sitzungen verloren?")
    ap.add_argument("--zeit", help="Neustart 'HH:MM' (heute) oder 'JJJJ-MM-TT HH:MM'; Vorgabe: Start des Obsidian-Prozesses")
    ap.add_argument("--stunden", type=float, default=12, help="Rückblick vor dem Neustart in Stunden (Vorgabe 12)")
    ap.add_argument("--projects", default=os.path.join(home, ".claude", "projects"))
    ap.add_argument("--cockpit", default=os.path.join(home, ".claude", "cockpit"))
    ap.add_argument("--vault", default=None, help="Vault-Pfad; Vorgabe: `vault` aus den Einstellungen")
    ap.add_argument("--repos", action="append", help="Ordner mit Git-Repos (eine Ebene tief), mehrfach möglich; "
                    "Vorgabe: `repo_wurzeln` aus den Einstellungen, sonst ~/Developer")
    a = ap.parse_args(argv)
    proc = obsidian_process()
    if a.zeit:
        try:
            cut = parse_zeit(a.zeit)
        except ValueError:
            print(f"Fehler: --zeit '{a.zeit}' nicht lesbar, erwartet 'HH:MM' oder 'JJJJ-MM-TT HH:MM'.", file=sys.stderr)
            return 1
        source = "--zeit"
    elif proc:
        cut, source = proc[1], "Start des Obsidian-Prozesses"
    else:
        print("Fehler: Obsidian läuft nicht, Zeitpunkt mit --zeit angeben.", file=sys.stderr)
        return 1
    try:
        vault = vault_waehlen(a.vault)
        roots = repo_wurzeln_waehlen(a.repos)
    except EinstellungsFehler as ex:
        print("Fehler: %s" % ex, file=sys.stderr)
        return 2
    if not os.path.isdir(vault):
        # Wie lint und verknuepfen: ein falscher Pfad wuerde sonst still "keine Vault-Belege" ergeben.
        print("Vault nicht gefunden: %s" % vault, file=sys.stderr)
        return 2
    res = analyse(cut, a.stunden, a.projects, a.cockpit, vault, roots)
    report(cut, source, proc, res, a.stunden)
    return 0


if __name__ == "__main__":
    sys.exit(main())
