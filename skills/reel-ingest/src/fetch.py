"""Beschafft das Video und seine Metadaten."""
import json
import subprocess
import sys
from pathlib import Path


VIDEO_ENDUNGEN = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}

# Zeitlimits fuer die beiden yt-dlp-subprocess.run()-Aufrufe in hole_reel()
# (Task 11c). Ohne timeout= blieb ein haengendes yt-dlp (z.B. Netzwerk-Stall)
# unbegrenzt am Leben -- der aeussere Waechter (hooks/reel_guard.sh) killt
# nur den Python-Prozess, yt-dlp haengt als verwaistes Enkelkind weiter.
#
# VIDEO_ZEITLIMIT_SEKUNDEN = 180: gemessen 8,13s fuer 84,5 MB bei ~14,8 MB/s
# (echter Lauf, Task 11 Durchstich). 180s decken bei gleicher Bandbreite
# ~2,6 GB ab -- weit mehr, als ein Reel/Short/TikTok je hat -- und bei einer
# 5x langsameren Verbindung immer noch ein 4x groesseres Video. Grosszuegig
# fuer ein echtes Langsam-Netz, eng genug, um einen echten Stall in
# 3 Minuten zu erkennen statt endlos zu haengen.
VIDEO_ZEITLIMIT_SEKUNDEN = 180
# UNTERTITEL_ZEITLIMIT_SEKUNDEN = 60: gemessen 2,97s. Untertitel sind winzige
# Text-Payloads -- die Kosten stecken in Metadaten-/Rate-Limit-Backoff, nicht
# in Bytes. 60s decken mehrere yt-dlp-eigene Retry-Zyklen ab; scheitert der
# Aufruf trotzdem, ist das ohnehin kein harter Fehler (Whisper-Fallback).
UNTERTITEL_ZEITLIMIT_SEKUNDEN = 60


class BeschaffungsFehler(RuntimeError):
    """yt-dlp kam nicht an das Video heran."""


def _yt_dlp_pfad() -> str:
    """Pfad zum yt-dlp-Binary des Projekt-venv -- bewusst NICHT ueber PATH.

    Befund: die blosse Zeichenkette "yt-dlp" wird von subprocess ueber PATH
    aufgeloest. Auf der Entwicklungsmaschine fand PATH ein voellig anderes
    yt-dlp (z.B. unter /usr/local/bin/yt-dlp, Version 2026.03.17)
    als das im venv installierte (2026.07.04) -- und damit auch als das in
    requirements.txt gepinnte (yt-dlp>=2026.7.4). Der Pin war so
    wirkungslos: der Code lief nie gegen das Binary, das er deklariert.

    Anker ist sys.executable statt eines fest verdrahteten Pfads:
    hole_reel() laeuft immer unter dem venv-Python (der Hook ruft
    "$WURZEL/venv/bin/python", die Tests laufen unter "./venv/bin/pytest"),
    sys.executable trifft das aktive venv also auch dann noch, wenn es
    verschoben oder neu aufgesetzt wird.

    Fehlt das Binary dort, wird NICHT still auf PATH zurueckgefallen -- das
    waere genau der Defekt, den diese Funktion beheben soll. Stattdessen
    ein klarer Fehler mit dem gesuchten Pfad.
    """
    kandidat = Path(sys.executable).parent / "yt-dlp"
    if not kandidat.is_file():
        raise BeschaffungsFehler(
            f"yt-dlp nicht gefunden unter {kandidat} — venv unvollstaendig "
            "oder falsch aufgesetzt? 'venv/bin/pip install -r "
            "requirements.txt' erneut ausfuehren."
        )
    return str(kandidat)


def finde_video(ordner: Path) -> Path | None:
    """Die Videodatei im Dossier-Ordner.

    Nicht ueber glob('video.*') suchen: das trifft auch video.info.json und
    video.de.srt, die yt-dlp danebenlegt. Unterordner werden ignoriert.
    Wirft BeschaffungsFehler, wenn mehrere Video-Kandidaten existieren.
    """
    kandidaten = []
    for pfad in sorted(ordner.iterdir()):
        if pfad.is_file() and pfad.suffix.lower() in VIDEO_ENDUNGEN:
            kandidaten.append(pfad)

    if len(kandidaten) > 1:
        dateinamen = ", ".join(p.name for p in kandidaten)
        raise BeschaffungsFehler(
            f"Mehrere Video-Dateien im Ordner gefunden — nicht eindeutig: {dateinamen}"
        )

    return kandidaten[0] if kandidaten else None


def baue_ytdlp_befehl(url: str, zielordner: Path,
                      cookies_browser: str | None = None) -> list[str]:
    """Baut den yt-dlp-Aufruf fuer Video und Metadaten. Kein Seiteneffekt
    auf zielordner/url — kann aber BeschaffungsFehler werfen, wenn das
    yt-dlp-Binary im venv fehlt (siehe _yt_dlp_pfad()).

    Baut NUR den Video-Teil, ohne Untertitel-Flags. Untertitel laufen
    ausschliesslich ueber den separaten baue_ytdlp_untertitel_befehl()
    (siehe hole_reel()): ein Fehlschlag am Untertitel-Endpunkt (z.B.
    YouTube-Rate-Limit, siehe Befund im Live-Dry-Run) darf den
    Video-Download nicht mehr verhindern. Fund 2 (Fix-Runde 1): frueher
    gab es hier zusaetzlich einen mit_untertiteln-Schalter mit Default
    True — die einzige Produktiv-Aufrufstelle rief aber immer mit
    mit_untertiteln=False auf, der Default war also toter, zugleich der
    urspruenglich fehlerhafte Code-Pfad. Entfernt statt nur ungenutzt
    liegengelassen.
    """
    cmd = [
        _yt_dlp_pfad(),
        "--no-playlist",          # Reel-Links zeigen manchmal auf ein ganzes Profil
        "--write-info-json",      # Caption, Uploader, verlinkte Repos
        "-f", "mp4/best",
        "-o", str(zielordner / "video.%(ext)s"),
    ]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    cmd.append(url)               # URL immer zuletzt
    return cmd


def baue_ytdlp_untertitel_befehl(url: str, zielordner: Path,
                                 cookies_browser: str | None = None) -> list[str]:
    """Baut den separaten Untertitel-Nachhol-Befehl. Kein Seiteneffekt auf
    zielordner/url — kann aber BeschaffungsFehler werfen, wenn das
    yt-dlp-Binary im venv fehlt (siehe _yt_dlp_pfad()).

    --skip-download: das Video liegt aus dem vorangegangenen Aufruf schon
    da, dieser zweite Aufruf soll ausschliesslich die Untertitel-Endpunkte
    treffen. So bleibt bei einem Fehlschlag kein zweiter Video-Kandidat im
    Ordner liegen, den finde_video() spaeter als mehrdeutig ablehnen wuerde.
    """
    cmd = [
        _yt_dlp_pfad(),
        "--no-playlist",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "de,en",
        "--convert-subs", "srt",
        "-o", str(zielordner / "video.%(ext)s"),
    ]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    cmd.append(url)
    return cmd


def _bestimme_hinweis(stderr: str) -> str | None:
    """Ordnet bekannte yt-dlp-Fehlertexte einem umsetzbaren Hinweis zu.

    Nur fuer Faelle, die die Nutzerin selbst beheben kann: Zugriffssperren
    (privat, login-pflichtig, altersbeschraenkt) und Rate-Limits. Fuer
    unbekannte Fehler gibt es bewusst KEINEN erfundenen Hinweis — ein
    Hinweis, der nur bei Formulierungen greift, die real nie auftreten,
    taeuscht eine Abdeckung vor, die nicht existiert. Genau das war der
    urspruengliche Befund: das alte "login"/"rate-limit"-Muster traf die
    reale Instagram-Meldung ("This content isn't available to everyone:
    It can't be seen by certain audiences.") nicht.

    Fund 1 (Fix-Runde 1): zwei der ersten Ersatz-Muster waren selbst wieder
    zu unspezifisch und trafen gewoehnliche macOS-/yt-dlp-Ausgabe, die mit
    einer Zugriffssperre nichts zu tun hat:
    - "cookies" traf yt-dlps eigenen Standard-Nachsatz ("Use
      --cookies-from-browser or --cookies for the authentication"), den es
      an viele verschiedene Fehler anhaengt (auch echte Rate-Limits), UND
      Fehler beim Cookie-*Auslesen* selbst (z.B. "could not find safari
      cookies database"). Dort haette der Rat "cookies_browser='safari'
      erneut versuchen" im Kreis gefuehrt. Ersatzlos entfernt: eine
      Formulierung, die nur den echten Sperrfall trifft und weder den
      Nachsatz noch Lesefehler, liess sich nicht finden — die verbleibenden
      Muster (login, sign in, die Instagram-Wendungen, age-restricted)
      decken die bekannten echten Faelle bereits ohne dieses Risiko ab.
    - "private" traf "/private/var/folders/…", den auf macOS real
      aufgeloesten TMPDIR-Pfad, der in yt-dlp-/ffmpeg-Ausgaben routinemaessig
      vorkommt. Ersetzt durch "is private"/"this video is private" — diese
      Wendung steht nicht vor einem Pfad-Praefix.
    Die Rate-Limit-Pruefung laeuft jetzt VOR der Sperr-Pruefung: yt-dlps
    eigene Meldung "rate-limit reached or login required" enthaelt beide
    Wortgruppen gleichzeitig, und ein echtes Rate-Limit soll dann "spaeter
    erneut versuchen" bekommen, nicht den (hier unpassenden) Cookie-Rat.
    "429" als blosse Teilzeichenkette traf ausserdem jede Zahl, die 429
    enthaelt (z.B. Fragment-Nummern) — ersetzt durch "http error 429".

    Fund (Task 11c): die reale Instagram-Meldung aus dem Live-Durchstich
    lautete "… without being logged-in …" — "login" ist KEINE Teilzeichenkette
    von "logged-in" (kein "i" direkt nach "log"), traf also nicht, obwohl das
    genau der Fall ist, in dem der Cookie-Rat richtig waere. Ergaenzt wurde
    die volle Wendung "without being logged-in" statt des blossen Worts
    "logged-in": dieselbe Vorsicht wie bei "is private" -- ein bejahender
    Satz ("bereits eingeloggt", "successfully logged-in") ist kein Sperrfall
    und soll keinen Treffer ausloesen, nur die Verneinung ist eines.
    Zweite beobachtete Instagram-Wendung: "Instagram sent an empty media
    response" -- als "empty media response" aufgenommen (drei Woerter,
    keine plausible Kollision mit unabhaengigem "empty"/"response"-Vokabular
    in anderen Fehlermeldungen, siehe Gegenprobe in test_fetch.py).
    """
    text = stderr.lower()

    rate_limit_muster = ("http error 429", "too many requests", "rate-limit", "rate limit")
    if any(muster in text for muster in rate_limit_muster):
        return " — Rate-Limit erreicht. Spaeter erneut versuchen, nicht sofort wiederholen."

    sperr_muster = (
        "login", "log in", "sign in", "without being logged-in",
        "is private", "this video is private",
        "isn't available to everyone", "certain audiences",
        "age-restricted", "age restricted",
        "empty media response",
    )
    if any(muster in text for muster in sperr_muster):
        return (" — Inhalt scheint gesperrt (privat/altersbeschraenkt/"
                "login-pflichtig). Mit cookies_browser='safari' erneut versuchen.")

    return None


def _fehlermeldung(ergebnis: subprocess.CompletedProcess, praefix: str = "yt-dlp") -> str:
    """Einheitliches Format: Praefix, erkannter Hinweis (falls vorhanden), stderr-Tail."""
    hinweis = _bestimme_hinweis(ergebnis.stderr) or ""
    return f"{praefix} fehlgeschlagen ({ergebnis.returncode}){hinweis}\n{ergebnis.stderr[-800:]}"


def hole_reel(url: str, zielordner: Path,
              cookies_browser: str | None = None) -> dict:
    """Laedt Video und Metadaten; Untertitel sind ein optionaler Zusatzversuch danach.

    Untertitel sind eine Optimierung: sie schlagen Whisper an Qualitaet und
    Tempo, aber Whisper ist der dokumentierte Fallback und funktioniert
    offline (siehe transcript.hole_transkript, das ohne .srt-Datei
    automatisch auf Whisper zurueckfaellt). Der Video-Download laeuft
    deshalb in einem eigenen yt-dlp-Aufruf ohne Untertitel-Flags: ein
    Fehlschlag am Untertitel-Endpunkt darf nicht mehr den kompletten
    Download verhindern, wie es der Live-Dry-Run zeigte.
    """
    zielordner.mkdir(parents=True, exist_ok=True)

    try:
        video_ergebnis = subprocess.run(
            baue_ytdlp_befehl(url, zielordner, cookies_browser),
            capture_output=True, text=True, timeout=VIDEO_ZEITLIMIT_SEKUNDEN,
        )
    except subprocess.TimeoutExpired as fehler:
        # Der Video-Download ist die harte Voraussetzung fuer alles Weitere
        # -- ein Timeout hier ist wie jeder andere Video-Fehlschlag ein
        # harter Abbruch (siehe test_hole_reel_video_fehlschlag_wirft_weiterhin).
        raise BeschaffungsFehler(
            f"yt-dlp (Video) hat nach {VIDEO_ZEITLIMIT_SEKUNDEN}s nicht "
            "reagiert -- abgebrochen."
        ) from fehler
    if video_ergebnis.returncode != 0:
        raise BeschaffungsFehler(_fehlermeldung(video_ergebnis))

    try:
        untertitel_ergebnis = subprocess.run(
            baue_ytdlp_untertitel_befehl(url, zielordner, cookies_browser),
            capture_output=True, text=True, timeout=UNTERTITEL_ZEITLIMIT_SEKUNDEN,
        )
    except subprocess.TimeoutExpired:
        untertitel_ergebnis = None

    untertitel_fehler = None
    if untertitel_ergebnis is None:
        # Wird NICHT geworfen, aus demselben Grund wie ein regulaerer
        # Untertitel-Fehlschlag unten: hole_transkript() faellt ohne
        # .srt-Datei automatisch auf Whisper zurueck.
        untertitel_fehler = (
            f"Untertitel-Abruf abgebrochen — hat nach "
            f"{UNTERTITEL_ZEITLIMIT_SEKUNDEN}s nicht reagiert."
        )
    elif untertitel_ergebnis.returncode != 0:
        # Wird NICHT geworfen: hole_transkript() faellt ohne .srt-Datei
        # automatisch auf Whisper zurueck. Der Fehler wird trotzdem
        # festgehalten, statt kommentarlos zu verschwinden.
        untertitel_fehler = _fehlermeldung(untertitel_ergebnis, praefix="Untertitel-Abruf")

    info_dateien = list(zielordner.glob("*.info.json"))
    if not info_dateien:
        raise BeschaffungsFehler("Kein info.json — Download unvollstaendig")
    info = json.loads(info_dateien[0].read_text())
    if untertitel_fehler:
        info["untertitel_fehler"] = untertitel_fehler
    return info
