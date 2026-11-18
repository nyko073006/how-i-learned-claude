"""Sammelmodus: viele Reels auf einmal holen, statt eines nach dem anderen.

  dm [--chat NAME]     Reel-Links aus einem Instagram-DM-Chat des Lesekontos (Chrome-Profil,
                       OpenCLI). Ohne --chat der oberste Chat. Gibt je Zeile eine URL aus.
  export ZIP [--seit JJJJ-MM-TT] [--bekannt NOTIZ ...]
                       Links aus dem Instagram-Datenexport "Gespeichert" (saved_posts.json),
                       aelteste zuerst. --bekannt laesst Shortcodes weg, die schon in frueheren
                       Vault-Notizen stehen. Gibt je Zeile eine URL aus.
  hole URL ...         Laedt jedes Reel in niedrigster Qualitaet (mit Ton), baut das Dossier
                       (Frames, Palette, Transkript), traegt Caption und Uploader nach und
                       loescht danach alle Videodateien. Gibt je Reel den Dossier-Ordner aus.
                       Bild- und Karussell-Posts (yt-dlp: "No video formats found") holt
                       gallery-dl mit den Cookies des Lesekontos; die Bilder werden zu Frames.
  steckbrief ORDNER ...  Je Dossier kontaktbogen.jpg (alle Frames) und steckbrief.md (Caption,
                       Transkript, Metadaten) fuer die Auswertung durch Sub-Agents.
  aufraeumen ORDNER ...  Loescht Dossier-Ordner (Frames, dossier.json) nach der Auswertung.

Aufruf aus dem Skill-Ordner:
  cd ~/.claude/skills/reel-ingest && venv/bin/python scripts/sammle.py dm
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.fetch import _yt_dlp_pfad          # noqa: E402
from src.pipeline import WURZEL, verarbeite_datei   # noqa: E402

EINSTELLUNGEN_ENV = "CLAUDE_SKILLS_EINSTELLUNGEN"
EINSTELLUNGEN_PFAD = "~/.config/claude-skills/einstellungen.json"
SITZUNG = "reels-sammeln"
INBOX = "https://www.instagram.com/direct/inbox/"
GALLERY_DL = Path(sys.executable).with_name("gallery-dl")
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
BILD_MASS = (1080, 1350)    # alle Folien auf ein Mass, sonst kachelt steckbrief nicht


def einstellungen_pfad() -> str:
    """Env CLAUDE_SKILLS_EINSTELLUNGEN, sonst die Vorgabe."""
    return os.path.expanduser(os.environ.get(EINSTELLUNGEN_ENV, "").strip() or EINSTELLUNGEN_PFAD)


def einstellungen() -> dict:
    """Einstellungen frisch gelesen; fehlt die Datei oder ist sie unlesbar, {}."""
    try:
        daten = json.loads(Path(einstellungen_pfad()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def chrome_profil() -> str:
    """Chrome-Profil des Instagram-Lesekontos aus `reel_chrome_profil`; leer, wenn nicht gesetzt."""
    wert = einstellungen().get("reel_chrome_profil")
    return wert.strip() if isinstance(wert, str) else ""


def _cli(*args: str, zeit: float = 60) -> str:
    r = subprocess.run(["opencli", *args], capture_output=True, text=True, timeout=zeit)
    if r.returncode != 0:
        raise RuntimeError(f"opencli {' '.join(args[:3])}: {r.stderr.strip()[:300]}")
    return r.stdout


def _js(code: str) -> str:
    # opencli haengt Update-Hinweise an; das Ergebnis steht in der ersten Zeile.
    return _cli("browser", SITZUNG, "eval", code).strip().splitlines()[0]


def _verbinde() -> None:
    if "Connectivity: connected" in _cli("doctor", zeit=30):
        return
    subprocess.run(["open", "-na", "Google Chrome", "--args", f"--profile-directory={chrome_profil()}"],
                   check=True, timeout=30)
    for _ in range(12):
        time.sleep(5)
        if "Connectivity: connected" in _cli("doctor", zeit=30):
            return
    raise RuntimeError("OpenCLI-Erweiterung verbindet sich nicht (opencli doctor)")


_SCHLEIFEN = """(()=>{
  const A='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  const sc=id=>{let n=BigInt(id),s='';while(n>0n){s=A[Number(n%64n)]+s;n/=64n}return s};
  const box=()=>[...document.querySelectorAll('div')].filter(d=>d.scrollHeight>d.clientHeight+50
    &&/(auto|scroll)/.test(getComputedStyle(d).overflowY))[0];
  const w=ms=>new Promise(r=>setTimeout(r,ms));
  window.__reels=new Set();
  const sammle=()=>document.querySelectorAll('img').forEach(i=>{
    const m=i.src.match(/ig_cache_key=([^&.]+)/);if(!m)return;
    let id;try{id=atob(decodeURIComponent(m[1]))}catch(e){return}
    if(/^\\d+$/.test(id))window.__reels.add('https://www.instagram.com/reel/'+sc(id)+'/')});
  window.__nachladen=async()=>{let still=0,h=0;
    while(still<15){const d=box();d.scrollBy(0,400);await w(500);d.scrollTop=-d.scrollHeight;
      await w(2500);sammle();
      if(d.scrollHeight===h&&!d.querySelector('[role=progressbar]'))still++;else still=0;
      h=d.scrollHeight;window.__stand=h+' px, '+window.__reels.size+' Reels'}
    window.__fertig=true};
  window.__abfahren=async()=>{let d=box();d.scrollTop=-d.scrollHeight;await w(2500);
    while(true){d=box();sammle();window.__stand=window.__reels.size+' Reels';
      if(d.scrollTop>=-1)break;d.scrollBy(0,300);await w(1800)}
    window.__fertig=true};
  return 1})()"""


def _nach_vorn() -> None:
    """Holt das Chrome-Fenster mit dem Instagram-Tab nach vorn, sonst rendert Chrome nicht."""
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome"', "-e",
                    "repeat with w in windows", "-e",
                    'if title of active tab of w contains "Instagram" then', "-e",
                    "set minimized of w to false", "-e", "set index of w to 1", "-e", "end if",
                    "-e", "end repeat", "-e", "activate", "-e", "end tell"],
                   capture_output=True, timeout=30)


def links_aus_dm(chat: str | None) -> list[str]:
    _verbinde()
    _cli("browser", SITZUNG, "open", INBOX)
    time.sleep(6)
    wahl = json.dumps(chat or "")
    # Chats sind role=button ohne href; der Text beginnt mit dem Anzeigenamen.
    _js(f"""(()=>{{const c=[...document.querySelectorAll('[role=button]')]
        .filter(e=>/\\u00b7/.test(e.innerText)&&e.innerText.length<200);
        const z={wahl}?c.find(e=>e.innerText.startsWith({wahl})):c[0];z.click();return 'ok'}})()""")
    time.sleep(6)
    thread = _js("location.href")
    if "/direct/t/" not in thread:
        raise RuntimeError(f"Chat nicht geoeffnet ({thread})")
    # Der Verlauf ist umgekehrt aufgebaut (scrollTop 0 = unten, aelter = negativ), laedt aeltere
    # Nachrichten erst oben nach und ist virtualisiert: nur der Ausschnitt um die Scrollposition steht
    # im DOM. Geteilte Reels haben kein href; ihre Vorschaubilder tragen aber ig_cache_key = base64
    # der Medien-ID, daraus folgt der Shortcode (Basis 64). Verdeckter Tab (visibilityState hidden):
    # Chrome rendert nicht, es wird nichts gefunden. Deshalb Fenster vor jeder Phase nach vorn.
    # Phase 1 laedt oben nach, bis der Ladekreisel weg ist; Phase 2 faehrt von oben nach unten.
    _js(_SCHLEIFEN)
    for phase in ("__nachladen()", "__abfahren()"):
        _nach_vorn()
        _js(f"(()=>{{window.__fertig=false;{phase};return 1}})()")
        for _ in range(150):                # hoechstens 20 Minuten je Phase
            time.sleep(8)
            if _js("String(window.__fertig)") == "true":
                break
            if _js("document.visibilityState") != "visible":
                _nach_vorn()
        else:
            raise RuntimeError(f"Zeitlimit in {phase}")
    stand = _js("window.__stand")
    print(f"Verlauf: {stand}", file=sys.stderr)
    links = [z for z in _cli("browser", SITZUNG, "eval", "[...window.__reels].join('\\n')").splitlines()
             if z.startswith("https://")]
    _cli("browser", SITZUNG, "close")
    return links


def hole(url: str) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp)
        subprocess.run([_yt_dlp_pfad(), "-q", "--no-warnings", "-f", "worst[ext=mp4]/worst",
                        "-S", "+res,+size", "--write-info-json", "-o", str(ziel / "reel.%(ext)s"),
                        url], check=True, timeout=300)
        info = json.loads((ziel / "reel.info.json").read_text(encoding="utf-8"))
        video = next(ziel.glob("reel.mp4"))
        if not info.get("duration"):    # Instagram liefert im info.json oft keine Dauer
            info["duration"] = round(float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                 str(video)], capture_output=True, text=True, check=True).stdout.strip()), 1)
        dossier = verarbeite_datei(video)
    ordner = Path(dossier["ordner"])
    dossier.update(url=url, plattform="instagram", caption=info.get("description") or "",
                   uploader=info.get("uploader") or "", dauer_sekunden=info.get("duration"),
                   quelle_datum=info.get("upload_date"))
    (ordner / "dossier.json").write_text(json.dumps(dossier, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    for video in ordner.glob("*.mp4"):
        video.unlink()
    return ordner


EXPORT_PFAD = "your_instagram_activity/saved/saved_posts.json"
SHORTCODE = re.compile(r"instagram\.com/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)")


def links_aus_export(zip_pfad: Path, seit: str | None = None,
                     bekannt: list[Path] | None = None) -> list[str]:
    """Links aus dem Instagram-Datenexport "Gespeichert", aelteste zuerst.

    seit: nur Beitraege, die an oder nach diesem Tag (JJJJ-MM-TT, UTC) gespeichert wurden.
    bekannt: Dateien (etwa fruehere Vault-Notizen), deren Shortcodes schon ausgewertet sind.
    """
    with zipfile.ZipFile(zip_pfad) as z:
        eintraege = json.loads(z.read(EXPORT_PFAD))
    grenze = (datetime.fromisoformat(seit).replace(tzinfo=timezone.utc).timestamp()
              if seit else 0)
    alt = {m for d in bekannt or [] for m in SHORTCODE.findall(d.read_text(encoding="utf-8"))}
    links, gesehen = [], set()
    for e in sorted(eintraege, key=lambda e: e.get("timestamp", 0)):
        if e.get("timestamp", 0) < grenze:
            continue
        url = next((lv.get("href") or lv.get("value") for lv in e.get("label_values", [])
                    if lv.get("label") == "URL"), None)
        m = SHORTCODE.search(url or "")
        if not url or not m or m.group(1) in alt or m.group(1) in gesehen:
            continue
        gesehen.add(m.group(1))
        links.append(url.split("?")[0])
    return links


def _post_kennung(url: str) -> str | None:
    """Shortcode des Posts, zu dem ein Folien-Link gehoert (yt-dlp loest Karussells auf)."""
    r = subprocess.run([_yt_dlp_pfad(), "-J", "--flat-playlist", "--ignore-errors", url],
                       capture_output=True, text=True, timeout=120)
    try:
        info = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    return info.get("id") if info.get("_type") == "playlist" else None


def hole_bilder(url: str, wurzel: Path = WURZEL) -> Path:
    """Bild- und Karussell-Posts: gallery-dl laedt die Folien, sie werden die Frames des Dossiers."""
    post_url = url
    # ASSUMPTION: nur /reel/-Links aufloesen, weil dm bei Karussells die Kennung einer Folie als
    # /reel/ liefert (gallery-dl holt dann nur diese Folie ohne Caption); /p/ ist schon der Post.
    if "/reel/" in url:
        kennung = _post_kennung(url)
        if kennung:
            post_url = f"https://www.instagram.com/p/{kennung}/"
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp)
        profil = chrome_profil()
        cookies = ["--cookies-from-browser", f"chrome:{profil}"] if profil else []
        subprocess.run([str(GALLERY_DL), "-q", *cookies,
                        "--write-metadata", "-D", str(ziel), "-f", "{num:>03}.{extension}",
                        post_url], check=True, timeout=300)
        bilder = sorted(b for b in ziel.iterdir() if b.suffix.lower() in BILD_ENDUNGEN)
        if not bilder:
            raise RuntimeError("gallery-dl lieferte keine Bilder")
        videos = sum(1 for b in ziel.iterdir() if b.suffix.lower() == ".mp4")
        meta = json.loads((ziel / f"{bilder[0].name}.json").read_text(encoding="utf-8"))
        ordner = wurzel / f"bild-{meta.get('post_shortcode') or url.rstrip('/').rsplit('/', 1)[-1]}"
        frames_ordner = ordner / "frames"
        frames_ordner.mkdir(parents=True, exist_ok=True)
        b, h = BILD_MASS
        frames = []
        for i, bild in enumerate(bilder, 1):
            frame = frames_ordner / f"frame_{i:03d}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bild), "-vf",
                            f"scale={b}:{h}:force_original_aspect_ratio=decrease,"
                            f"pad={b}:{h}:(ow-iw)/2:(oh-ih)/2:white", "-frames:v", "1", str(frame)],
                           check=True, timeout=60)
            frames.append(str(frame))
    dossier = {"url": url, "post_url": post_url, "plattform": "instagram", "art": "bilder",
               "caption": meta.get("description") or "", "uploader": meta.get("username") or "",
               "dauer_sekunden": None, "quelle_datum": meta.get("post_date") or meta.get("date"),
               "transkript_quelle": "keins (Bildpost)", "transkript": "",
               "frames": frames, "videos_ausgelassen": videos, "ordner": str(ordner)}
    (ordner / "dossier.json").write_text(json.dumps(dossier, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    return ordner


def steckbrief(ordner: Path) -> Path:
    """Kontaktbogen aller Frames plus Markdown mit Caption und Transkript, fuer die Auswertung."""
    d = json.loads((ordner / "dossier.json").read_text(encoding="utf-8"))
    frames = sorted((ordner / "frames").glob("frame_*.jpg"))
    if frames:
        spalten = min(len(frames), 8)
        zeilen = -(-len(frames) // spalten)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ordner / "frames" / "frame_%03d.jpg"),
                        "-vf", f"scale=240:-1,tile={spalten}x{zeilen}", "-frames:v", "1",
                        str(ordner / "kontaktbogen.jpg")], check=True, timeout=120)
    md = ordner / "steckbrief.md"
    md.write_text(
        f"# {d.get('url')}\n\n- Uploader: {d.get('uploader')}\n- Datum: {d.get('quelle_datum')}\n"
        f"- Dauer: {d.get('dauer_sekunden')} s\n- Frames: {len(frames)} (Kontaktbogen: "
        f"{ordner / 'kontaktbogen.jpg'})\n- Fehler: frames={d.get('frames_fehler')}, "
        f"transkript={d.get('transkript_fehler')}\n\n## Caption\n\n{d.get('caption')}\n\n"
        f"## Transkript ({d.get('transkript_quelle')})\n\n{d.get('transkript')}\n", encoding="utf-8")
    return md


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="befehl", required=True)
    dm = sub.add_parser("dm")
    dm.add_argument("--chat")
    ex = sub.add_parser("export")
    ex.add_argument("zip", type=Path)
    ex.add_argument("--seit", help="JJJJ-MM-TT, nur ab diesem Speichertag")
    ex.add_argument("--bekannt", nargs="*", type=Path, default=[],
                    help="Dateien mit schon ausgewerteten Links (fruehere Vault-Notizen)")
    sub.add_parser("hole").add_argument("urls", nargs="+")
    sub.add_parser("aufraeumen").add_argument("ordner", nargs="+")
    sub.add_parser("steckbrief").add_argument("ordner", nargs="+")
    a = p.parse_args()
    if a.befehl == "dm":
        if not chrome_profil():
            print(f"FEHLER reel_chrome_profil fehlt in {einstellungen_pfad()}", file=sys.stderr)
            return 2
        print("\n".join(links_aus_dm(a.chat)))
    elif a.befehl == "export":
        links = links_aus_export(a.zip, a.seit, a.bekannt)
        print(f"Export: {len(links)} neue Links", file=sys.stderr)
        print("\n".join(links))
    elif a.befehl == "hole":
        for url in a.urls:          # ein geloeschtes oder privates Reel bricht den Lauf nicht ab
            try:
                print(hole(url), flush=True)
            except Exception as e:  # noqa: BLE001
                try:                # Bild- oder Karussell-Post: yt-dlp findet kein Video
                    print(hole_bilder(url), flush=True)
                except Exception as e2:  # noqa: BLE001
                    print(f"FEHLER {url}: {str(e)[:200]} | Bilder: {str(e2)[:200]}", flush=True)
    elif a.befehl == "steckbrief":
        for o in map(Path, a.ordner):
            print(steckbrief(o))
    else:
        for o in map(Path, a.ordner):
            if (o / "dossier.json").exists():   # nur echte Dossier-Ordner loeschen
                shutil.rmtree(o)
                print(f"geloescht: {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
