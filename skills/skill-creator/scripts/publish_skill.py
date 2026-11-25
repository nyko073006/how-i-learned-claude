#!/usr/bin/env python3
"""publish_skill.py — Veroeffentlicht einen Claude-Skill in einem Zug.

Stufen des Skill-Lifecycles:
  1. lokal      — Skill unter ~/.claude/skills/<name>/ validieren, Version bumpen
  2. GitHub     — Skill-Ordner ins Repo spiegeln, committen, ggf. pushen
  3. Vault      — Doku unter "03 Bereiche/Skills/<name>.md" aktualisieren
  4. oeffentlich— nur fuer Skills in "oeffentlich": Sperrlisten-Pruefung, dann
                  Spiegel nach <oeffentlich_repo>/skills/<name>/ und Commit (nie Push)

Pfade und Namen stehen in der Einstellungsdatei (Env CLAUDE_SKILLS_EINSTELLUNGEN,
sonst ~/.config/claude-skills/einstellungen.json), nicht im Code:
  skill_repo, skill_remote, vault, oeffentlich_repo, oeffentlich (Liste), sperrliste.

SICHERHEITSREGEL: Eine bestehende Vault-Doku wird NIEMALS ueberschrieben.
Erlaubt sind genau zwei Eingriffe: Frontmatter (version, aktualisiert) und eine
neue Zeile in der Tabelle "Versionshistorie".

Nur Python-Standardbibliothek. Getestet mit Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from fnmatch import fnmatch
from pathlib import Path

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

DOC_SUBDIR = Path("03 Bereiche") / "Skills"
EINSTELLUNGEN_ENV = "CLAUDE_SKILLS_EINSTELLUNGEN"
# Immer gesperrt, auch wenn die Sperrliste sie nicht nennt. Sie sind selbst nicht
# privat; zusammengesetzt, damit diese Datei die eigene Pruefung besteht.
EXTRA_BEGRIFFE = ("/us" "ers/", "claude.ai/code/" "session_")

# Diese Ordner werden NIE gespiegelt. Kritisch: einzelne Skills enthalten
# ueber 27.000 Dateien in .venv/ bzw. ms-playwright/.
EXCLUDED_DIRS = {
    ".git",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    "ms-playwright",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_FILES = {".DS_Store"}
# Zusaetzlich aus Secrets-Gruenden: niemals .env-Dateien ins Repo spiegeln.
EXCLUDED_PATTERNS = ("*.pyc", "*.pyo", ".env", ".env.*", "*.log")

GITIGNORE_CONTENT = """# Von publish_skill.py angelegt
.git/
venv/
.venv/
node_modules/
__pycache__/
ms-playwright/
.DS_Store
*.pyc
*.pyo
*.log
.env
.env.*
"""

DOC_SECTIONS = [
    "Ueberblick",
    "Trigger",
    "Funktionsumfang",
    "Nutzungsbeispiele",
    "Voraussetzungen",
    "Dateistruktur",
    "Verwandt",
    "Versionshistorie",
]


class PublishError(Exception):
    """Erwarteter Fehler — wird als klare Meldung ausgegeben, nicht als Traceback."""



class EinstellungsFehler(PublishError):
    """Einstellung fehlt oder ist unbrauchbar — die CLI endet dann mit Exit 2."""


class AufrufFehler(PublishError):
    """Unbrauchbarer Aufruf (z. B. Skillname) — die CLI endet dann mit Exit 2."""


# Skillname wird Ordnername in zwei Repos und Teil der Commit-Nachricht: kein Pfad, kein Punkt vorn.
SKILLNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------

def einstellungen_pfad(pfad: Path | None = None) -> Path:
    if pfad is not None:
        return Path(pfad).expanduser()
    env = os.environ.get(EINSTELLUNGEN_ENV, "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "claude-skills" / "einstellungen.json"


def lade_einstellungen(pfad: Path | None = None) -> dict:
    """Einstellungen als dict; fehlt die Datei, {}. Kaputtes JSON ist ein Fehler mit Pfad."""
    ziel = einstellungen_pfad(pfad)
    if not ziel.is_file():
        return {}
    try:
        daten = json.loads(ziel.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise EinstellungsFehler(f"Einstellungsdatei '{ziel}' ist kein gueltiges JSON: {exc}")
    if not isinstance(daten, dict):
        raise EinstellungsFehler(f"Einstellungsdatei '{ziel}' muss ein JSON-Objekt sein.")
    return daten


def oeffentlich_liste(einstellungen: dict) -> list[str]:
    """Die Einstellung 'oeffentlich' als Liste von Skillnamen. Fehlt sie (oder null): leer.
    Alles andere als eine Liste von Strings ist ein Fehler, damit ein String wie "lint" nie als
    Teilstring- oder Zeichenliste ausgelegt wird."""
    wert = einstellungen.get("oeffentlich")
    if wert is None:
        return []
    if not isinstance(wert, list) or not all(isinstance(x, str) for x in wert):
        raise EinstellungsFehler(
            f"oeffentlich in {einstellungen_pfad()} muss eine Liste von Skillnamen sein, "
            f'z. B. ["lint", "ingest"].'
        )
    return list(wert)


# ---------------------------------------------------------------------------
# Ausgabe-Helfer
# ---------------------------------------------------------------------------

def info(msg: str) -> None:
    print(msg)


def step(msg: str) -> None:
    print(f"\n== {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def plan(msg: str, dry_run: bool) -> None:
    prefix = "  [dry-run] " if dry_run else "  "
    print(f"{prefix}{msg}")


# ---------------------------------------------------------------------------
# YAML-Frontmatter (minimaler Parser, bewusst ohne externe Pakete)
# ---------------------------------------------------------------------------

FM_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):[ \t]*(.*)$")


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str):
    """Gibt (data, key_line_index, fm_end_line) zurueck oder None.

    key_line_index bildet Top-Level-Keys auf ihre Zeilennummer ab, damit
    einzelne Felder zielgenau ersetzt werden koennen.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    fm_end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() in ("---", "..."):
            fm_end = idx
            break
    if fm_end is None:
        return None

    data = {}
    key_line = {}
    i = 1
    while i < fm_end:
        match = FM_KEY_RE.match(lines[i])
        if not match:
            i += 1
            continue
        key, raw = match.group(1), match.group(2).strip()
        key_line[key] = i

        if raw[:1] in (">", "|"):
            # Block-Skalar: alle eingerueckten Folgezeilen gehoeren dazu.
            block = []
            i += 1
            while i < fm_end and (lines[i].strip() == "" or lines[i][:1] in (" ", "\t")):
                block.append(lines[i].strip())
                i += 1
            data[key] = " ".join(part for part in block if part)
            continue

        if raw == "":
            # Liste oder verschachtelte Mapping-Keys (z.B. metadata.version).
            values = []
            i += 1
            while i < fm_end and (lines[i].strip() == "" or lines[i][:1] in (" ", "\t")):
                stripped = lines[i].strip()
                if stripped.startswith("- "):
                    values.append(_strip_quotes(stripped[2:]))
                else:
                    child = FM_KEY_RE.match(stripped)
                    if child:
                        dotted = f"{key}.{child.group(1)}"
                        data[dotted] = _strip_quotes(child.group(2))
                        key_line[dotted] = i
                i += 1
            data[key] = values
            continue

        data[key] = _strip_quotes(raw)
        i += 1

    return data, key_line, fm_end


def set_frontmatter_field(text: str, key: str, value: str, after: str = None) -> str:
    """Setzt genau ein Frontmatter-Feld. Rest der Datei bleibt unangetastet.

    'key' darf verschachtelt sein ("metadata.version"); dann wird die vorhandene
    Zeile inklusive Einrueckung und Anfuehrungszeichen-Stil ersetzt.
    """
    parsed = parse_frontmatter(text)
    if parsed is None:
        raise PublishError("Datei hat kein gueltiges YAML-Frontmatter (--- ... ---).")
    _, key_line, fm_end = parsed
    lines = text.splitlines(keepends=True)
    newline = "\n"

    def with_nl(s: str) -> str:
        return s if s.endswith("\n") else s + newline

    if key in key_line and "." in key:
        idx = key_line[key]
        original = lines[idx]
        indent = original[: len(original) - len(original.lstrip())]
        child = key.split(".", 1)[1]
        quoted = f'"{value}"' if re.search(rf'{re.escape(child)}:\s*["\']', original) else value
        lines[idx] = with_nl(f"{indent}{child}: {quoted}")
    elif key in key_line:
        lines[key_line[key]] = with_nl(f"{key}: {value}")
    else:
        insert_at = fm_end
        if after and after in key_line:
            insert_at = key_line[after] + 1
        lines.insert(insert_at, with_nl(f"{key}: {value}"))
    return "".join(lines)


# ---------------------------------------------------------------------------
# Versionierung
# ---------------------------------------------------------------------------

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def bump_version(current: str, part: str) -> str:
    match = SEMVER_RE.match(current.strip())
    if not match:
        raise PublishError(f"'{current}' ist keine gueltige SemVer-Version (X.Y.Z).")
    major, minor, patch = (int(g) for g in match.groups())
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


# ---------------------------------------------------------------------------
# Spiegeln
# ---------------------------------------------------------------------------

def is_excluded_file(name: str) -> bool:
    if name in EXCLUDED_FILES:
        return True
    from fnmatch import fnmatch

    return any(fnmatch(name, pattern) for pattern in EXCLUDED_PATTERNS)


def collect_source_files(src: Path):
    """Relative Pfade aller zu spiegelnden Dateien. Ausschluesse greifen beim Abstieg."""
    found = []
    skipped_dirs = []
    for root, dirs, files in os.walk(src, followlinks=False):
        keep = []
        for d in sorted(dirs):
            if d in EXCLUDED_DIRS:
                skipped_dirs.append(str(Path(root, d).relative_to(src)))
            else:
                keep.append(d)
        dirs[:] = keep
        for f in sorted(files):
            if is_excluded_file(f):
                continue
            found.append(Path(root, f).relative_to(src))
    return found, skipped_dirs


def collect_target_files(dst: Path):
    if not dst.exists():
        return []
    found = []
    for root, dirs, files in os.walk(dst, followlinks=False):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if is_excluded_file(f):
                continue
            found.append(Path(root, f).relative_to(dst))
    return found


def pruefe_symlinks(wurzel: Path, ziel: Path, liste=None) -> None:
    """PublishError, wenn 'ziel', ein Ordner zwischen 'wurzel' und 'ziel' oder irgendein Eintrag
    unter 'ziel' ein Symlink ist. Der Spiegel schreibt, loescht und vergleicht sonst durch den Link
    hindurch in fremden Ordnern. Pfade in der Meldung relativ zu 'wurzel', mit 'liste' maskiert."""
    wurzel, ziel = Path(wurzel), Path(ziel)

    def zeige(pfad: Path) -> str:
        rel = pfad.relative_to(wurzel).as_posix()
        return maskiere(rel, liste) if liste else rel

    try:
        teile = ziel.relative_to(wurzel).parts
    except ValueError:
        raise PublishError(f"Spiegelziel '{ziel}' liegt nicht unter '{wurzel}'.")
    if not teile:
        raise PublishError(f"Spiegelziel '{ziel}' ist das Repo selbst.")
    gefunden = []
    pfad = wurzel
    for teil in teile:
        pfad = pfad / teil
        if pfad.is_symlink():
            gefunden.append(pfad)
            break
    if not gefunden and ziel.is_dir():
        for root, dirs, files in os.walk(ziel, followlinks=False):
            dirs.sort()
            for name in sorted(dirs + files):
                if Path(root, name).is_symlink():
                    gefunden.append(Path(root, name))
            # In Ausschlussordner (venv, node_modules, ...) schreibt und loescht der Spiegel nie;
            # ihr Eintrag selbst wird oben geprueft, ihr Inhalt nicht.
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
    if gefunden:
        raise PublishError(
            "Symlink im Spiegelziel, nichts geschrieben (der Spiegel folgt keinen Links):\n    "
            + "\n    ".join(f"{zeige(p)}:0 (symlink)" for p in gefunden)
        )


def mirror_skill(src: Path, dst: Path, dry_run: bool, files=None, wurzel=None, liste=None):
    """Spiegelt src nach dst. 'files' begrenzt den Umfang (relative Pfade); alles
    andere im Ziel gilt als veraltet und wird geloescht. Vorher bricht pruefe_symlinks ab,
    wenn dst oder ein Elternordner bis 'wurzel' (Vorgabe: dst.parent) oder ein Eintrag darin ein
    Symlink ist."""
    pruefe_symlinks(Path(wurzel) if wurzel is not None else Path(dst).parent, dst, liste)
    src_files, skipped_dirs = collect_source_files(src)
    if files is not None:
        src_files = list(files)
    dst_files = set(collect_target_files(dst))

    added, updated, unchanged = [], [], []
    for rel in src_files:
        target = dst / rel
        if not target.exists():
            added.append(rel)
        elif filecmp.cmp(src / rel, target, shallow=False):
            unchanged.append(rel)
        else:
            updated.append(rel)

    removed = sorted(dst_files - set(src_files))

    if not dry_run:
        for rel in added + updated:
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            # Zweite Sperre (Link zwischen Pruefung und Kopie entstanden): nie durch einen Link schreiben.
            if target.is_symlink() or target.parent.is_symlink():
                raise PublishError(f"Symlink im Spiegelziel: {rel.as_posix()} — Abbruch vor dem Kopieren.")
            shutil.copy2(src / rel, target)
        for rel in removed:
            (dst / rel).unlink(missing_ok=True)
        # leere Ordner aufraeumen
        if dst.exists():
            for root, dirs, files in os.walk(dst, topdown=False):
                path = Path(root)
                if path == dst:
                    continue
                if not any(path.iterdir()):
                    path.rmdir()

    return {
        "total": len(src_files),
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "removed": removed,
        "skipped_dirs": skipped_dirs,
    }


# ---------------------------------------------------------------------------
# Sperrliste (gleiche Semantik wie der Waechter von Glasscockpit, public-check.ts)
# ---------------------------------------------------------------------------

MASKE = "***"
WORT_RE = re.compile(r"[a-z0-9_]")
ENTFERNT = {"Mn", "Mc", "Me", "Cf"}
# Wie TextDecoder("latin1") im Browser/Node: das ist windows-1252, undefinierte Bytes
# bleiben als C1-Steuerzeichen stehen.
def _cp1252_zeichen(b: int) -> str:
    try:
        return bytes([b]).decode("cp1252")
    except UnicodeDecodeError:
        return chr(b)


CP1252 = "".join(_cp1252_zeichen(b) for b in range(256))


def normalisiere(text: str) -> str:
    """Vergleichsform: NFKD, ohne Kombinations- und Formatzeichen (Mn, Mc, Me, Cf), klein."""
    zerlegt = unicodedata.normalize("NFKD", text)
    return "".join(z for z in zerlegt if unicodedata.category(z) not in ENTFERNT).lower()


def parse_sperrliste(text: str) -> tuple[list[str], list[str]]:
    """(Begriffe, Ausnahmen), normalisiert. '#' Kommentar, '!' vorn = Ausnahme, Leerzeilen zaehlen nicht."""
    begriffe, ausnahmen = [], []
    for roh in re.split(r"\r?\n", text):
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if zeile.startswith("!"):
            wert = normalisiere(zeile[1:].strip())
            if wert:
                ausnahmen.append(wert)
        else:
            wert = normalisiere(zeile)
            if wert:
                begriffe.append(wert)
    return begriffe, ausnahmen


def sperrliste_vorgabe() -> Path:
    """Vorgabe, wenn die Einstellung 'sperrliste' fehlt (dieselbe Liste wie beim Glasscockpit-Waechter)."""
    return Path.home() / ".config" / "cockpit" / "public-denylist.txt"


def lade_sperrliste(einstellungen: dict) -> tuple[list[str], list[str]]:
    """Sperrliste aus der Einstellung 'sperrliste', sonst aus sperrliste_vorgabe(). Fehlt die Datei
    oder ist sie leer: Fehler, denn ohne Begriffe waere die Pruefung wirkungslos."""
    wert = einstellungen.get("sperrliste")
    pfad = Path(wert).expanduser() if wert else sperrliste_vorgabe()
    if not pfad.is_file():
        herkunft = "Einstellung sperrliste" if wert else f"Vorgabe (sperrliste fehlt in {einstellungen_pfad()})"
        raise EinstellungsFehler(
            f"Sperrliste '{pfad}' existiert nicht ({herkunft}) — ohne Sperrliste keine oeffentliche Pruefung."
        )
    try:
        text = pfad.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise EinstellungsFehler(f"Sperrliste '{pfad}' ist nicht UTF-8 — bitte als UTF-8 speichern.")
    liste = parse_sperrliste(text)
    if not liste[0]:
        raise EinstellungsFehler(
            f"Sperrliste '{pfad}' enthaelt keine Begriffe — ohne Begriffe waere die Pruefung wirkungslos."
        )
    return liste


def _mit_abbildung(text: str):
    """Normalisierter Text plus fuer jedes Zeichen [Start, Ende) im Original."""
    teile, von, bis = [], [], []
    for pos, zeichen in enumerate(text):
        n = normalisiere(zeichen)
        teile.append(n)
        von.extend([pos] * len(n))
        bis.extend([pos + 1] * len(n))
    return "".join(teile), von, bis


def _treffer_bereiche(text: str, begriffe, ausnahmen):
    norm, von, bis = _mit_abbildung(text)
    if not norm:
        return []
    zeichen = list(norm)
    for ausnahme in ausnahmen:
        i = norm.find(ausnahme)
        while i != -1:
            vor = norm[i - 1] if i > 0 else ""
            nach = norm[i + len(ausnahme)] if i + len(ausnahme) < len(norm) else ""
            if not (vor and WORT_RE.match(vor)) and not (nach and WORT_RE.match(nach)):
                for k in range(i, i + len(ausnahme)):
                    zeichen[k] = " "
            i = norm.find(ausnahme, i + 1)
    frei = "".join(zeichen)
    bereiche = []
    for begriff in begriffe:
        i = frei.find(begriff)
        while i != -1:
            bereiche.append((von[i], bis[i + len(begriff) - 1]))
            i = frei.find(begriff, i + 1)
    return bereiche


def _maskiere(pfad: str, begriffe, ausnahmen) -> str:
    aus, pos = [], 0
    for start, ende in sorted(_treffer_bereiche(pfad, begriffe, ausnahmen)):
        if ende <= pos:
            continue
        aus.append(pfad[pos:max(pos, start)] + MASKE)
        pos = ende
    return "".join(aus) + pfad[pos:]


def _utf16le(daten: bytes) -> str:
    return daten[: len(daten) - len(daten) % 2].decode("utf-16-le", errors="replace")


def _pruefe_text(maskiert: str, text: str, begriffe, ausnahmen) -> list[str]:
    return [f"{maskiert}:{nr}" for nr, zeile in enumerate(re.split(r"\r?\n", text), start=1)
            if _treffer_bereiche(zeile, begriffe, ausnahmen)]


def _teile(liste):
    """(Begriffe samt EXTRA_BEGRIFFE, Ausnahmen)."""
    return list(liste[0]) + [b for b in EXTRA_BEGRIFFE if b not in liste[0]], list(liste[1])


def maskiere(text: str, liste) -> str:
    """Text mit jedem Sperrbegriff als '***' (Ausnahmen bleiben stehen)."""
    return _maskiere(text, *_teile(liste))


def pruefe_dateien(wurzel: Path, dateien, liste) -> list[str]:
    """Treffer als "<maskierter Pfad>:<Zeile>"; Zeile 0 = Treffer im Pfad, "(binär)" = in Binaerdaten.
    Der Treffertext steht nie im Ergebnis.

    Ein Symlink ist immer ein Treffer "(symlink)", ohne ihm zu folgen: Der Spiegel kopiert Inhalte
    (shutil.copy2 folgt Links) und erzeugt nie selbst einen Link; ein Link im Pruefumfang ist also
    fremd, und git wuerde seinen Linktext committen. Unlesbare Dateien melden "(unlesbar)"."""
    begriffe, ausnahmen = _teile(liste)
    wurzel = Path(wurzel)
    treffer = []
    for datei in dateien:
        datei = Path(datei)
        rel = datei.relative_to(wurzel) if datei.is_absolute() else datei
        pfad = rel.as_posix()
        maskiert = _maskiere(pfad, begriffe, ausnahmen)
        if maskiert != pfad:
            treffer.append(f"{maskiert}:0")
        voll = wurzel / rel
        if voll.is_symlink():
            treffer.append(f"{maskiert}:0 (symlink)")
            continue
        try:
            daten = voll.read_bytes()
        except OSError:
            treffer.append(f"{maskiert}:0 (unlesbar)")
            continue
        treffer += _pruefe_daten(maskiert, daten, begriffe, ausnahmen)
    return treffer


def _pruefe_daten(maskiert: str, daten: bytes, begriffe, ausnahmen) -> list[str]:
    """Inhaltspruefung einer Datei (Text zeilenweise, UTF-16 mit BOM, sonst Binaer)."""
    if daten[:2] == b"\xff\xfe":
        return _pruefe_text(maskiert, _utf16le(daten[2:]), begriffe, ausnahmen)
    if daten[:2] == b"\xfe\xff":
        return _pruefe_text(maskiert, daten[2: len(daten) - len(daten) % 2].decode(
            "utf-16-be", errors="replace"), begriffe, ausnahmen)
    if b"\x00" not in daten[:8000]:
        text = daten.decode("utf-8", errors="replace")
        if text.startswith("\ufeff"):
            text = text[1:]
        return _pruefe_text(maskiert, text, begriffe, ausnahmen)
    kandidaten = ("".join(CP1252[b] for b in daten), _utf16le(daten), _utf16le(daten[1:]))
    if any(_treffer_bereiche(k, begriffe, ausnahmen) for k in kandidaten):
        return [f"{maskiert}:0 (binär)"]
    return []


# ---------------------------------------------------------------------------
# Oeffentliches Ziel
# ---------------------------------------------------------------------------

def oeffentliche_dateien(src: Path) -> list[Path]:
    """Spiegelumfang abzueglich der Muster aus src/.publicignore (und dieser Datei selbst)."""
    muster = []
    ignore = src / ".publicignore"
    if ignore.is_file():
        for roh in ignore.read_text(encoding="utf-8").splitlines():
            zeile = roh.strip()
            if zeile and not zeile.startswith("#"):
                muster.append(zeile)

    def ausgeschlossen(rel: str) -> bool:
        for m in muster:
            if m.endswith("/"):
                if rel.startswith(m) or fnmatch(rel, m + "*"):
                    return True
            elif fnmatch(rel, m):
                return True
        return False

    return [rel for rel in collect_source_files(src)[0]
            if rel.as_posix() != ".publicignore" and not ausgeschlossen(rel.as_posix())]


def pruefe_veroeffentlichung(src: Path, skill: str, message: str, liste) -> list[str]:
    """Alles, was in den oeffentlichen Commit gelangt: Dateien des oeffentlichen Umfangs,
    Skillname (wird Ordner- und Commit-Text) und Nachricht. Eintraege sind maskiert."""
    treffer = pruefe_dateien(src, oeffentliche_dateien(src), liste)
    if maskiere(skill, liste) != skill:
        treffer.append(f"Skillname: {maskiere(skill, liste)}")
    if maskiere(message, liste) != message:
        treffer.append(f"Nachricht (-m): {maskiere(message, liste)}")
    return treffer


def treffer_fehler(skill: str, treffer, liste, was: str) -> PublishError:
    return PublishError(
        f"Sperrliste: {len(treffer)} Treffer in '{maskiere(skill, liste)}', {was}:\n    "
        + "\n    ".join(treffer)
    )


def _index_zuruecksetzen(repo: Path, pfad: str) -> None:
    """Nimmt nur den Index fuer 'pfad' zurueck; Dateien im Arbeitsbaum bleiben liegen."""
    if run_git(repo, ["rev-parse", "--verify", "-q", "HEAD"], check=False).returncode == 0:
        run_git(repo, ["reset", "-q", "--", pfad], check=False)
    else:
        run_git(repo, ["rm", "--cached", "-r", "-q", "--ignore-unmatch", "--", pfad], check=False)


def spiegle_oeffentlich(src: Path, repo: Path, skill: str, liste, message: str, dry_run: bool) -> dict:
    """Erst pruefen, dann nach repo/skills/<skill>/ spiegeln und committen. Nie ein Push."""
    result = {"treffer": [], "committed": False, "commit": None}
    dateien = oeffentliche_dateien(src)
    treffer = pruefe_veroeffentlichung(src, skill, message, liste)
    result["treffer"] = treffer
    if treffer:
        raise treffer_fehler(skill, treffer, liste, "nichts veroeffentlicht")
    if not (repo / ".git").exists():
        raise PublishError(f"Oeffentliches Repo '{repo}' ist kein git-Repo.")
    ziel = repo / "skills" / skill
    mirror = mirror_skill(src, ziel, dry_run, files=dateien, wurzel=repo, liste=liste)
    plan(f"{mirror['total']} Datei(en) nach {ziel} "
         f"(+{len(mirror['added'])} neu, ~{len(mirror['updated'])} geaendert, "
         f"-{len(mirror['removed'])} entfernt)", dry_run)
    if dry_run:
        plan(f"git add -A -- skills/{skill}", dry_run)
        plan(f'git commit -m "skills/{skill}: {message}" (kein Push)', dry_run)
        return result
    pfad = f"skills/{skill}"
    # Staged wird ausdruecklich nur skills/<skill>; fremde Aenderungen im Repo bleiben unberuehrt.
    run_git(repo, ["add", "-A", "--", pfad])
    # Der Commit-Umfang ist der Index, nicht der Spiegel: Fremde Dateien im Ziel (Logs, Caches)
    # kaemen sonst ungeprueft mit.
    # Geprueft wird nur, was hinzukommt oder sich aendert; Loeschungen blockieren nie (sonst bliebe
    # ein Pfad, dessen Begriff spaeter auf die Liste kam, fuer immer veroeffentlicht).
    if run_git(repo, ["diff", "--cached", "--quiet", "--", pfad], check=False).returncode == 0:
        return result
    neu = run_git(repo, ["diff", "--cached", "--name-only", "--no-renames", "--diff-filter=d", "-z",
                         "--", pfad]).stdout.split("\0")
    index_treffer = pruefe_dateien(repo, [Path(p) for p in neu if p], liste)
    if index_treffer:
        _index_zuruecksetzen(repo, pfad)
        result["treffer"] = index_treffer
        raise treffer_fehler(skill, index_treffer, liste, "Index zurueckgesetzt, nichts committet")
    run_git(repo, ["commit", "-m", f"skills/{skill}: {message}", "--", f"skills/{skill}"])
    result["committed"] = True
    result["commit"] = run_git(repo, ["rev-parse", "--short", "HEAD"]).stdout.strip()
    return result


def pruefe_skills_ordner(repo: Path, normallauf: bool) -> None:
    """EinstellungsFehler, wenn <repo>/skills/ fehlt oder kein Ordner ist. Die eine Stelle fuer diese
    Bedingung: Spiegel (Vorabpruefung, normallauf=True) und --pruefe-oeffentlich (False) nutzen sie
    beide; eine Pruefung ohne skills/ prueft nichts und darf nicht 'sauber' melden."""
    basis = repo / "skills"
    if basis.is_dir():
        return
    nachsatz = " Nichts geschrieben." if normallauf else ""
    if basis.exists() or basis.is_symlink():
        raise EinstellungsFehler(
            f"'{basis}' ist kein Ordner (Datei oder kaputter Link); oeffentlich_repo in "
            f"{einstellungen_pfad()}. Eintrag entfernen oder verschieben und skills/ als Ordner anlegen.{nachsatz}"
        )
    if normallauf:
        # ASSUMPTION: Ein Repo ohne einen einzigen Commit ist die Erstveroeffentlichung (der Spiegel legt
        # skills/ dann an); die Bestandstests und der erste Lauf brauchen das. Nur Rueckgabewert 1 von
        # 'rev-parse --verify -q HEAD' heisst "HEAD zeigt auf nichts" (gemessen: leeres Repo 1, kein oder
        # kaputtes Git 128); jeder andere Wert ist ein Git-Fehler und bricht ab. --pruefe-oeffentlich
        # kennt keine Ausnahme: dort braucht sie kein Test, und eine Pruefung ohne Ziel meldet nie sauber.
        rc = run_git(repo, ["rev-parse", "--verify", "-q", "HEAD"], check=False).returncode
        if rc == 1:
            return
        if rc != 0:
            raise EinstellungsFehler(
                f"git im oeffentlichen Repo '{repo}' antwortet mit Fehler (Rueckgabewert {rc}); "
                f"oeffentlich_repo in {einstellungen_pfad()} pruefen.{nachsatz}"
            )
    raise EinstellungsFehler(
        f"Im oeffentlichen Repo '{repo}' fehlt der Ordner 'skills/' (oeffentlich_repo in "
        f"{einstellungen_pfad()}). Pfad korrigieren oder skills/ im Repo anlegen.{nachsatz}"
    )


def pruefe_oeffentlich(repo: Path, erlaubt, liste) -> list[str]:
    """Treffer ueber alle Dateien unter repo/skills/ plus "verwaist: skills/<x>" fuer
    Ordner, die nicht in 'erlaubt' stehen. Lose Dateien in skills/ werden nur geprueft."""
    basis = repo / "skills"
    if not basis.is_dir():
        return []
    # Ohne die Spiegel-Ausschluesse: auch Logs, Caches und .env im Ziel werden geprueft.
    dateien = []
    for root, dirs, files in os.walk(basis, followlinks=False):
        dirs.sort()
        # Links auf Ordner stehen in 'dirs' (os.walk steigt nicht ab); als Eintrag pruefen.
        namen = files + [d for d in dirs if Path(root, d).is_symlink()]
        for f in sorted(namen):
            dateien.append(Path(root, f).relative_to(repo))
    treffer = pruefe_dateien(repo, dateien, liste)
    for eintrag in sorted(basis.iterdir()):
        if eintrag.is_dir() and eintrag.name not in erlaubt:
            treffer.append(f"verwaist: skills/{maskiere(eintrag.name, liste)}")
    return treffer


def _git_bytes(repo: Path, args) -> bytes:
    """Wie run_git, aber stdout als Bytes (Blob-Inhalte, Pfade mit -z)."""
    proc = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise PublishError(f"git {' '.join(args)} fehlgeschlagen: {detail[-1] if detail else 'unbekannt'}")
    return proc.stdout


def pruefe_historie(repo: Path, erlaubt, liste):
    """Gepusht werden Commits, nicht der Arbeitsbaum. Prueft jeden Commit in <upstream>..HEAD:
    Ordner unter skills/, die nicht in 'erlaubt' stehen ("verwaist in Historie"), jede dort
    hinzugefuegte oder geaenderte Datei unter skills/ (Pfad und Inhalt) und die Commit-Nachricht.
    Rueckgabe (Treffer, Hinweis); ohne Upstream keine Treffer und ein Hinweis."""
    begriffe, ausnahmen = _teile(liste)
    up = run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if up.returncode != 0 or not up.stdout.strip():
        return [], "Historie: kein Upstream (@{u}) — nur der Arbeitsbaum ist geprueft."
    upstream = up.stdout.strip()
    commits = run_git(repo, ["rev-list", "--reverse", f"{upstream}..HEAD"]).stdout.split()
    treffer, verwaist = [], set()
    for commit in commits:
        kurz = commit[:7]
        ordner = _git_bytes(repo, ["ls-tree", "-d", "--name-only", "-z", commit, "skills/"])
        for name in ordner.decode("utf-8", errors="replace").split("\0"):
            name = name[len("skills/"):] if name.startswith("skills/") else name
            if name and name not in erlaubt and name not in verwaist:
                verwaist.add(name)
                treffer.append(f"verwaist in Historie: skills/{maskiere(name, liste)} ({kurz})")
        roh = _git_bytes(repo, ["diff-tree", "-r", "-m", "--root", "--no-commit-id", "--no-renames",
                                "--diff-filter=d", "-z", commit, "--", "skills/"])
        teile = roh.split(b"\0")
        gesehen = set()
        for i in range(0, len(teile) - 1, 2):
            meta, pfad_b = teile[i].decode("ascii", errors="replace"), teile[i + 1]
            felder = meta.lstrip(":").split()
            if len(felder) < 5 or (pfad_b, felder[3]) in gesehen:
                continue
            gesehen.add((pfad_b, felder[3]))
            pfad = pfad_b.decode("utf-8", errors="replace")
            maskiert = _maskiere(pfad, begriffe, ausnahmen)
            if maskiert != pfad:
                treffer.append(f"{maskiert}:0 ({kurz})")
            modus, blob = felder[1], felder[3]
            if modus == "120000":
                treffer.append(f"{maskiert}:0 (symlink) ({kurz})")
                continue
            if modus == "160000":
                continue
            daten = _git_bytes(repo, ["cat-file", "blob", blob])
            treffer += [f"{t} ({kurz})" for t in _pruefe_daten(maskiert, daten, begriffe, ausnahmen)]
        nachricht = run_git(repo, ["log", "-1", "--format=%B", commit]).stdout
        for nr, zeile in enumerate(re.split(r"\r?\n", nachricht), start=1):
            if _treffer_bereiche(zeile, begriffe, ausnahmen):
                treffer.append(f"Commit-Nachricht ({kurz}):{nr}")
    return treffer, f"Historie: {len(commits)} Commit(s) in {maskiere(upstream, liste)}..HEAD geprueft."


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def run_git(repo: Path, args, check: bool = True):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo)] + list(args),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise PublishError("git ist nicht installiert oder nicht im PATH.")
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        tail = detail[-1] if detail else "unbekannter Fehler"
        raise PublishError(f"git {' '.join(args)} fehlgeschlagen: {tail}")
    return result


def git_step(repo: Path, skill: str, message: str, dry_run: bool, create_remote: bool,
             remote_slug: str | None = None):
    result = {"committed": False, "commit": None, "pushed": False, "hint": None}

    repo_exists = (repo / ".git").is_dir()
    if not repo_exists:
        plan(f"Repo anlegen: git init in {repo}", dry_run)
        plan(".gitignore mit den Ausschlussmustern schreiben", dry_run)
        if not dry_run:
            repo.mkdir(parents=True, exist_ok=True)
            run_git(repo, ["init", "-b", "main"])
            (repo / ".gitignore").write_text(GITIGNORE_CONTENT, encoding="utf-8")
    else:
        gitignore = repo / ".gitignore"
        if not gitignore.exists():
            plan(".gitignore fehlt — wird angelegt", dry_run)
            if not dry_run:
                gitignore.write_text(GITIGNORE_CONTENT, encoding="utf-8")

    if dry_run:
        plan(f"git add -- {skill} .gitignore", dry_run)
        plan(f'git commit -m "{skill}: {message}"', dry_run)
        if repo_exists:
            remotes = run_git(repo, ["remote"], check=False).stdout.split()
        else:
            remotes = []
        if "origin" in remotes:
            plan("git push -u origin <branch>", dry_run)
            result["hint"] = "Remote 'origin' vorhanden — es wuerde gepusht."
        else:
            result["hint"] = (
                "Kein Remote 'origin' — Push wird uebersprungen. "
                f"Nachtragen mit: git -C '{repo}' remote add origin "
                f"git@github.com:{remote_slug or '<besitzer>/<repo>'}.git"
            )
        return result

    if create_remote:
        remotes = run_git(repo, ["remote"], check=False).stdout.split()
        if "origin" in remotes:
            warn("Remote 'origin' existiert bereits — --create-remote wird ignoriert.")
        elif not remote_slug:
            raise EinstellungsFehler(
                f"skill_remote fehlt in {einstellungen_pfad()} — ohne Slug kein --create-remote."
            )
        else:
            info(f"  gh repo create {remote_slug} (explizit angefordert)")
            proc = subprocess.run(
                ["gh", "repo", "create", remote_slug,
                 "--private", "--source", str(repo), "--remote", "origin"],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                raise PublishError(
                    "gh repo create fehlgeschlagen: "
                    + (proc.stderr or proc.stdout).strip().splitlines()[-1]
                )

    run_git(repo, ["add", "-A", "--", skill, ".gitignore"], check=False)
    staged = run_git(repo, ["diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        result["hint"] = "Keine Aenderungen zu committen."
        return result

    run_git(repo, ["commit", "-m", f"{skill}: {message}"])
    result["committed"] = True
    result["commit"] = run_git(repo, ["rev-parse", "--short", "HEAD"]).stdout.strip()

    remotes = run_git(repo, ["remote"], check=False).stdout.split()
    if "origin" not in remotes:
        result["hint"] = (
            "Kein Remote konfiguriert — nicht gepusht. Nachtragen mit:\n"
            f"    git -C '{repo}' remote add origin git@github.com:{remote_slug or '<besitzer>/<repo>'}.git\n"
            f"    git -C '{repo}' push -u origin main"
        )
        return result

    branch = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    push = run_git(repo, ["push", "-u", "origin", branch], check=False)
    if push.returncode == 0:
        result["pushed"] = True
    else:
        tail = (push.stderr or push.stdout).strip().splitlines()
        result["hint"] = "Push fehlgeschlagen: " + (tail[-1] if tail else "unbekannt")
    return result


# ---------------------------------------------------------------------------
# Vault-Doku
# ---------------------------------------------------------------------------

def escape_table_cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def append_history_row(text: str, row: str):
    """Haengt eine Zeile an die Versionshistorie an. Bestehender Inhalt bleibt."""
    lines = text.splitlines(keepends=True)
    heading = None
    for idx, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+Versionshistorie\s*$", line.strip()):
            heading = idx
            break

    if heading is None:
        block = "\n## Versionshistorie\n\n| Datum | Version | Aenderung |\n|-------|---------|-----------|\n" + row + "\n"
        if text and not text.endswith("\n"):
            block = "\n" + block
        return text + block, "Sektion 'Versionshistorie' angelegt und Zeile angehaengt"

    last_row = None
    for idx in range(heading + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith("|"):
            last_row = idx
        elif stripped.startswith("#"):
            break
    if last_row is None:
        insert_at = heading + 1
        lines.insert(insert_at, "\n| Datum | Version | Aenderung |\n|-------|---------|-----------|\n")
        lines.insert(insert_at + 1, row + "\n")
        return "".join(lines), "Tabellenkopf ergaenzt und Zeile angehaengt"

    lines.insert(last_row + 1, row + "\n")
    return "".join(lines), "Zeile an Versionshistorie angehaengt"


def doc_template(skill: str, version: str, today: str, description: str, tree: str) -> str:
    desc = " ".join(description.split()) if description else ""
    ueberblick = (
        f"TODO — 2 bis 3 Saetze: Was macht der Skill, welches Problem loest er, fuer wen?\n\n"
        f"> Aus SKILL.md uebernommen: {desc}" if desc
        else "TODO — 2 bis 3 Saetze: Was macht der Skill, welches Problem loest er, fuer wen?"
    )
    return f"""---
tags:
  - ki-skill
skill: {skill}
version: {version}
aktualisiert: {today}
status: aktiv
source: claude
chat_url: unbekannt
---

# {skill}

## Ueberblick

{ueberblick}

## Trigger

- TODO — wann soll der Skill anspringen? (Trigger-Woerter Deutsch und Englisch)
- TODO — wann ausdruecklich NICHT?

## Funktionsumfang

- TODO — alle Funktionen als Bullet-Points auflisten

## Nutzungsbeispiele

**Beispiel 1: TODO**
- Ausloeser: TODO
- Ergebnis: TODO

**Beispiel 2: TODO**
- Ausloeser: TODO
- Ergebnis: TODO

## Voraussetzungen

TODO — MCPs, CLIs, API-Keys, Vault-Pfade? "Keine — laeuft mit Bordmitteln." wenn nichts noetig ist.

## Dateistruktur

```
~/.claude/skills/{skill}/
{tree}```

## Verwandt

- TODO — verwandte Skills als [[Wikilinks]]

## Versionshistorie

| Datum | Version | Aenderung |
|-------|---------|-----------|
"""


def build_tree(src: Path, files) -> str:
    """Kompakter Baum: Top-Level-Dateien und Ordner mit Dateizahl."""
    top_files = sorted({str(rel) for rel in files if len(rel.parts) == 1})
    dirs = {}
    for rel in files:
        if len(rel.parts) > 1:
            dirs[rel.parts[0]] = dirs.get(rel.parts[0], 0) + 1
    lines = []
    entries = [(name, None) for name in top_files] + [(name, count) for name, count in sorted(dirs.items())]
    for idx, (name, count) in enumerate(entries):
        connector = "└── " if idx == len(entries) - 1 else "├── "
        if count is None:
            lines.append(f"{connector}{name}")
        else:
            lines.append(f"{connector}{name}/   # {count} Datei(en)")
    return "\n".join(lines) + ("\n" if lines else "")


def update_doc(doc_path: Path, skill: str, version: str, today: str, message: str,
               description: str, tree: str, dry_run: bool):
    row = f"| {today} | {version} | {escape_table_cell(message)} |"
    actions = []

    if not doc_path.exists():
        actions.append(f"neu anlegen (Template mit TODO-Platzhaltern)")
        actions.append(f"Versionshistorie-Zeile: {row}")
        if not dry_run:
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            content = doc_template(skill, version, today, description, tree)
            content += row + "\n"
            doc_path.write_text(content, encoding="utf-8")
        return {"created": True, "actions": actions}

    original = doc_path.read_text(encoding="utf-8")
    parsed = parse_frontmatter(original)
    if parsed is None:
        raise PublishError(
            f"Doku '{doc_path}' hat kein gueltiges YAML-Frontmatter. "
            "Abbruch, damit nichts kaputt geschrieben wird."
        )
    data = parsed[0]

    updated = original
    old_version = data.get("version", "(fehlt)")
    if old_version != version:
        actions.append(f"Frontmatter version: {old_version} -> {version}")
    else:
        actions.append(f"Frontmatter version: {version} (unveraendert)")
    updated = set_frontmatter_field(updated, "version", version, after="skill")

    old_date = data.get("aktualisiert", "(fehlt)")
    actions.append(f"Frontmatter aktualisiert: {old_date} -> {today}")
    updated = set_frontmatter_field(updated, "aktualisiert", today, after="version")

    updated, hist_action = append_history_row(updated, row)
    actions.append(f"{hist_action}: {row}")

    if not dry_run:
        doc_path.write_text(updated, encoding="utf-8")

    return {"created": False, "actions": actions}


# ---------------------------------------------------------------------------
# Hauptablauf
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish_skill.py",
        description="Veroeffentlicht einen Claude-Skill: Version bumpen, ins GitHub-Repo "
                    "spiegeln, committen, die Vault-Doku aktualisieren und, wenn der Skill "
                    "in 'oeffentlich' steht, geprueft ins oeffentliche Repo spiegeln.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  publish_skill.py lint -m \"Projekt-Compliance ergaenzt\"\n"
            "  publish_skill.py mein-skill -m \"Erstveroeffentlichung\" --no-version-bump\n"
            "  publish_skill.py mein-skill -m \"Neue Sub-Skills\" --bump minor --dry-run\n"
            "  publish_skill.py --pruefe-oeffentlich\n"
        ),
    )
    parser.add_argument("skill", nargs="?", help="Name des Skills (Ordnername unter ~/.claude/skills/)")
    parser.add_argument("-m", "--message", help="Was wurde geaendert? (Pflicht ausser bei --pruefe-oeffentlich)")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch",
                        help="SemVer-Sprung (Default: patch)")
    parser.add_argument("--no-version-bump", action="store_true",
                        help="Version unveraendert lassen (Erstveroeffentlichung)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur zeigen was passieren wuerde, nichts schreiben")
    parser.add_argument("--create-remote", action="store_true",
                        help="GitHub-Repo per 'gh repo create' anlegen (Default: AUS)")
    parser.add_argument("--pruefe-oeffentlich", action="store_true",
                        help="Nur das oeffentliche Repo gegen Sperrliste und Liste 'oeffentlich' pruefen")
    parser.add_argument("--skills-dir", default=None, help="Default: ~/.claude/skills")
    parser.add_argument("--repo-dir", default=None, help="Default: Einstellung skill_repo")
    parser.add_argument("--vault-dir", default=None, help="Default: Einstellung vault")
    return parser


def pruefe_oeffentlich_cli() -> int:
    einst = lade_einstellungen()
    wert = einst.get("oeffentlich_repo")
    if not wert:
        raise EinstellungsFehler(f"oeffentlich_repo fehlt in {einstellungen_pfad()}.")
    repo = Path(wert).expanduser()
    if not repo.is_dir():
        raise EinstellungsFehler(f"Oeffentliches Repo '{repo}' existiert nicht.")
    erlaubt = oeffentlich_liste(einst)
    liste = lade_sperrliste(einst)
    pruefe_skills_ordner(repo, normallauf=False)
    treffer = pruefe_oeffentlich(repo, erlaubt, liste)
    historie, hinweis = pruefe_historie(repo, erlaubt, liste)
    treffer += historie
    for eintrag in treffer:
        info(eintrag)
    info(hinweis)
    info(f"pruefe-oeffentlich: {len(treffer)} Treffer in {repo / 'skills'} (Arbeitsbaum und Historie)")
    return 2 if treffer else 0


def main(argv=None) -> int:
    try:
        return _main(argv)
    except (EinstellungsFehler, AufrufFehler) as exc:
        print(f"\nFehler: {exc}", file=sys.stderr)
        return 2


def _main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.pruefe_oeffentlich:
        return pruefe_oeffentlich_cli()
    if not args.skill or args.message is None:
        parser.error("skill und -m sind Pflicht (ausser bei --pruefe-oeffentlich).")

    message = " ".join(args.message.split())
    if not message:
        raise PublishError("Die Commit-Nachricht (-m) darf nicht leer sein.")

    einst = lade_einstellungen()
    repo_wert = args.repo_dir or einst.get("skill_repo")
    if not repo_wert:
        raise EinstellungsFehler(f"skill_repo fehlt in {einstellungen_pfad()}")
    repo_dir = Path(repo_wert).expanduser()
    vault_wert = args.vault_dir or einst.get("vault")
    vault_dir = Path(vault_wert).expanduser() if vault_wert else None
    remote_slug = einst.get("skill_remote") or None
    skills_dir = Path(args.skills_dir).expanduser() if args.skills_dir else Path.home() / ".claude" / "skills"
    skill = args.skill.strip().strip("/")
    if not SKILLNAME_RE.match(skill):
        raise AufrufFehler(
            f"Skillname '{skill}' ist ungueltig: nur Buchstaben, Ziffern, '.', '_', '-', "
            "vorn Buchstabe oder Ziffer, kein Pfad."
        )
    src = skills_dir / skill
    dry = args.dry_run

    oeffentlich = skill in oeffentlich_liste(einst)
    liste = oeff_repo = None
    if oeffentlich:
        liste = lade_sperrliste(einst)
        oeff_wert = einst.get("oeffentlich_repo")
        if not oeff_wert:
            raise EinstellungsFehler(f"oeffentlich_repo fehlt in {einstellungen_pfad()}")
        oeff_repo = Path(oeff_wert).expanduser()
    gesamt = 6 if oeffentlich else 5

    # Vorbedingungen VOR dem ersten Schreibzugriff (Version, Spiegel, Commit): Ein Abbruch spaeter
    # liesse eine erhoehte Version und einen Commit ohne Doku bzw. ohne oeffentlichen Spiegel zurueck.
    if vault_dir is not None and not (vault_dir / DOC_SUBDIR).is_dir():
        raise EinstellungsFehler(
            f"Doku-Ordner '{vault_dir / DOC_SUBDIR}' existiert nicht (vault in {einstellungen_pfad()}). "
            "Ordner anlegen oder vault korrigieren; nichts geschrieben."
        )
    if repo_dir.exists() and not (repo_dir / ".git").exists():
        raise EinstellungsFehler(
            f"skill_repo '{repo_dir}' existiert, ist aber kein git-Repo. "
            "Pfad korrigieren oder einen leeren Ordner angeben; nichts geschrieben."
        )
    if oeffentlich and not (oeff_repo / ".git").exists():
        raise EinstellungsFehler(
            f"Oeffentliches Repo '{oeff_repo}' ist kein git-Repo (oeffentlich_repo in {einstellungen_pfad()}); "
            "nichts geschrieben."
        )
    # ASSUMPTION: Nur ein oeffentlich gespiegelter Skill braucht skills/; alle anderen laufen wie bisher,
    # weil sie das oeffentliche Repo nie anfassen.
    if oeffentlich:
        pruefe_skills_ordner(oeff_repo, normallauf=True)
    # Symlinks in den Spiegelzielen sperren den Spiegel; deshalb hier und nicht erst in Schritt 3/6.
    pruefe_symlinks(repo_dir, repo_dir / skill)
    if oeffentlich:
        pruefe_symlinks(oeff_repo, oeff_repo / "skills" / skill, liste)
    if args.create_remote and not dry and not remote_slug:
        hat_origin = (repo_dir / ".git").exists() and \
            "origin" in run_git(repo_dir, ["remote"], check=False).stdout.split()
        if not hat_origin:
            raise EinstellungsFehler(
                f"skill_remote fehlt in {einstellungen_pfad()} — ohne Slug kein --create-remote; "
                "nichts geschrieben."
            )

    if vault_dir is None:
        warn(f"vault fehlt in {einstellungen_pfad()} — kein Vault-Doku-Schritt.")
    if dry and args.create_remote:
        warn("--create-remote wird im --dry-run nicht ausgefuehrt.")

    today = datetime.date.today().isoformat()

    # --- a) Skill validieren -------------------------------------------------
    step(f"1/{gesamt} Skill validieren: {skill}")
    if not src.is_dir():
        candidates = sorted(
            p.name for p in skills_dir.iterdir()
            if p.is_dir() and skill.lower() in p.name.lower()
        ) if skills_dir.is_dir() else []
        hint = f" Meintest du: {', '.join(candidates[:5])}?" if candidates else ""
        raise PublishError(f"Skill-Ordner '{src}' existiert nicht.{hint}")

    skill_md = src / "SKILL.md"
    if not skill_md.is_file():
        raise PublishError(f"'{skill_md}' fehlt — jeder Skill braucht eine SKILL.md.")

    skill_text = skill_md.read_text(encoding="utf-8")
    parsed = parse_frontmatter(skill_text)
    if parsed is None:
        raise PublishError(
            f"'{skill_md}' hat kein gueltiges YAML-Frontmatter (--- am Anfang und Ende)."
        )
    fm = parsed[0]
    if not fm.get("name"):
        warn("Frontmatter-Feld 'name' fehlt — empfohlen, aber kein Abbruch.")
    elif fm.get("name") != skill:
        warn(f"Frontmatter 'name: {fm.get('name')}' weicht vom Ordnernamen '{skill}' ab.")
    info(f"  OK: {skill_md}")
    if oeffentlich:
        # Vorab pruefen, damit ein Treffer abbricht, bevor irgendetwas geschrieben ist.
        vorab = pruefe_veroeffentlichung(src, skill, message, liste)
        if vorab:
            raise treffer_fehler(skill, vorab, liste, "nichts geschrieben")
        info("  Sperrliste: 0 Treffer im oeffentlichen Umfang")

    # --- b) Version ----------------------------------------------------------
    step(f"2/{gesamt} Version ermitteln")
    # Manche Skills legen die Version unter metadata.version ab statt top-level.
    version_key = "version"
    raw_version = fm.get("version")
    if isinstance(raw_version, list) or not raw_version:
        for alt in ("metadata.version", "meta.version"):
            if fm.get(alt):
                version_key, raw_version = alt, fm[alt]
                info(f"  Version steht unter '{alt}'")
                break
    version_missing = False
    if isinstance(raw_version, list) or not raw_version:
        version_missing = True
        old_version = "(fehlt)"
    elif not SEMVER_RE.match(str(raw_version).strip()):
        warn(f"Version '{raw_version}' ist kein SemVer — es wird bei 1.0.0 gestartet.")
        version_missing = True
        old_version = str(raw_version)
    else:
        old_version = str(raw_version).strip()

    if version_missing:
        new_version = "1.0.0"
        info(f"  Kein gueltiges version-Feld -> Start bei {new_version}")
    elif args.no_version_bump:
        new_version = old_version
        info(f"  --no-version-bump: Version bleibt {new_version}")
    else:
        new_version = bump_version(old_version, args.bump)
        info(f"  {old_version} -> {new_version} ({args.bump})")

    if new_version != old_version or version_missing:
        plan(f"SKILL.md Frontmatter {version_key}: {new_version} schreiben", dry)
        if not dry:
            skill_md.write_text(
                set_frontmatter_field(skill_text, version_key, new_version, after="name"),
                encoding="utf-8",
            )
        # Die englische Fassung traegt dieselbe Version, sonst laufen beide beim naechsten Bump auseinander.
        skill_en = src / "SKILL.en.md"
        if skill_en.is_file():
            en_text = skill_en.read_text(encoding="utf-8")
            if parse_frontmatter(en_text) is None:
                warn(f"'{skill_en}' hat kein gueltiges Frontmatter — Version dort nicht gesetzt.")
            else:
                plan(f"SKILL.en.md Frontmatter {version_key}: {new_version} schreiben", dry)
                if not dry:
                    skill_en.write_text(
                        set_frontmatter_field(en_text, version_key, new_version, after="name"),
                        encoding="utf-8",
                    )

    # --- c) Spiegeln ---------------------------------------------------------
    step(f"3/{gesamt} Spiegeln nach {repo_dir / skill}")
    mirror = mirror_skill(src, repo_dir / skill, dry, wurzel=repo_dir)
    info(f"  {mirror['total']} Datei(en) im Umfang "
         f"(+{len(mirror['added'])} neu, ~{len(mirror['updated'])} geaendert, "
         f"={len(mirror['unchanged'])} unveraendert, -{len(mirror['removed'])} entfernt)")
    if mirror["skipped_dirs"]:
        shown = ", ".join(mirror["skipped_dirs"][:6])
        more = f" (+{len(mirror['skipped_dirs']) - 6} weitere)" if len(mirror["skipped_dirs"]) > 6 else ""
        info(f"  ausgeschlossen: {shown}{more}")
    for label, items in (("neu", mirror["added"]), ("geaendert", mirror["updated"]),
                         ("entfernt", mirror["removed"])):
        for rel in items[:10]:
            plan(f"{label}: {rel}", dry)
        if len(items) > 10:
            plan(f"{label}: ... und {len(items) - 10} weitere", dry)

    # --- d) Git --------------------------------------------------------------
    step(f"4/{gesamt} Git")
    git_result = git_step(repo_dir, skill, message, dry, args.create_remote, remote_slug)

    # --- e) Vault-Doku -------------------------------------------------------
    doc_path = doc_result = None
    if vault_dir is None:
        step(f"5/{gesamt} Vault-Doku: uebersprungen (vault nicht gesetzt)")
    else:
        doc_path = vault_dir / DOC_SUBDIR / f"{skill}.md"
        step(f"5/{gesamt} Vault-Doku: {doc_path}")
        if not (vault_dir / DOC_SUBDIR).is_dir():
            raise PublishError(f"Doku-Ordner '{vault_dir / DOC_SUBDIR}' existiert nicht.")
        tree = build_tree(src, [rel for rel in collect_source_files(src)[0]])
        doc_result = update_doc(doc_path, skill, new_version, today, message,
                                fm.get("description", ""), tree, dry)
        if doc_result["created"]:
            info("  Doku existiert nicht -> wird neu angelegt")
        else:
            info("  Doku existiert -> Inhalt bleibt unangetastet, nur Frontmatter + Historie")
        for action in doc_result["actions"]:
            plan(action, dry)

    # --- f) Oeffentlich ------------------------------------------------------
    oeff_result = None
    if oeffentlich:
        step(f"6/6 Öffentlich: {oeff_repo / 'skills' / skill}")
        oeff_result = spiegle_oeffentlich(src, oeff_repo, skill, liste, message, dry)
        info(f"  Sperrliste: {len(oeff_result['treffer'])} Treffer")

    # --- g) Zusammenfassung --------------------------------------------------
    step("Zusammenfassung")
    info(f"  Skill        : {skill}")
    info(f"  Version      : {old_version} -> {new_version}")
    info(f"  Gespiegelt   : {mirror['total']} Datei(en) nach {repo_dir / skill}")
    info(f"                 +{len(mirror['added'])} neu, ~{len(mirror['updated'])} geaendert, "
         f"-{len(mirror['removed'])} entfernt")
    if git_result["committed"]:
        info(f"  Commit       : {git_result['commit']}")
    else:
        info("  Commit       : keiner")
    info(f"  Push         : {'ja' if git_result['pushed'] else 'nein'}")
    if git_result["hint"]:
        info(f"  Hinweis      : {git_result['hint']}")
    if doc_result is None:
        info("  Doku         : keine (vault nicht gesetzt)")
    else:
        info(f"  Doku         : {doc_path}"
             + (" (neu angelegt — TODOs ausfuellen!)" if doc_result["created"] else " (ergaenzt)"))
    if oeff_result is not None:
        info(f"  Oeffentlich  : {oeff_result['commit'] or 'kein Commit'} (kein Push)")
    if dry:
        info("\n  DRY-RUN — es wurde nichts geschrieben.")
    elif doc_result is not None and doc_result["created"]:
        info("\n  Naechster Schritt: TODO-Platzhalter in der Doku durch echten Inhalt ersetzen.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PublishError as exc:
        print(f"\nFehler: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        sys.exit(130)
    except OSError as exc:
        print(f"\nFehler (Dateisystem): {exc}", file=sys.stderr)
        sys.exit(1)
