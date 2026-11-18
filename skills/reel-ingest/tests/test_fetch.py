import json
import subprocess
import sys
from pathlib import Path
import pytest
from src.fetch import baue_ytdlp_befehl, BeschaffungsFehler


def test_befehl_enthaelt_metadaten_kein_untertitel():
    # Fund 2 (Fix-Runde 1): baue_ytdlp_befehl() baut NUR NOCH den Video-Teil.
    # Untertitel-Flags gehoeren seit Defekt 1 (kombinierter Aufruf riss den
    # Video-Download mit, wenn nur der Untertitel-Endpunkt scheiterte) in den
    # separaten baue_ytdlp_untertitel_befehl() -- siehe dessen Test unten,
    # der die frueher hier stehenden --write-auto-subs/--convert-subs-
    # Zusicherungen uebernimmt. Diese Funktion ist die einzige, die
    # hole_reel() fuer den Video-Teil tatsaechlich aufruft.
    cmd = baue_ytdlp_befehl("https://x/y", Path("/tmp/z"))
    assert "--write-info-json" in cmd
    assert "-f" in cmd and "mp4/best" in cmd
    assert "--write-subs" not in cmd
    assert "--write-auto-subs" not in cmd
    assert "--convert-subs" not in cmd


def test_url_steht_am_ende():
    cmd = baue_ytdlp_befehl("https://x/y", Path("/tmp/z"))
    assert cmd[-1] == "https://x/y"


def test_ohne_cookies_kein_cookie_flag():
    cmd = baue_ytdlp_befehl("https://x/y", Path("/tmp/z"))
    assert not any("cookies" in teil for teil in cmd)


def test_cookies_werden_vor_der_url_eingehaengt():
    cmd = baue_ytdlp_befehl("https://x/y", Path("/tmp/z"), cookies_browser="safari")
    assert "--cookies-from-browser" in cmd
    assert cmd[cmd.index("--cookies-from-browser") + 1] == "safari"
    assert cmd[-1] == "https://x/y"


def test_kein_playlist_download():
    # Ein Reel-Link kann auf ein Profil zeigen — sonst laedt yt-dlp alles.
    assert "--no-playlist" in baue_ytdlp_befehl("https://x/y", Path("/tmp/z"))


# --- Task 11b: yt-dlp aus dem venv aufrufen, nicht ueber PATH ---
#
# Befund: PATH loeste auf dieser Maschine ein voelliges anderes yt-dlp auf
# (z.B. unter /usr/local/bin/yt-dlp, Version 2026.03.17) als das
# im Projekt-venv (2026.07.04) -- und damit auch als das in requirements.txt
# gepinnte (yt-dlp>=2026.7.4). Der Pin war dadurch wirkungslos. Anker fuer
# den richtigen Pfad ist sys.executable statt eines fest verdrahteten Pfads,
# weil hole_reel() immer unter dem venv-Python laeuft (Hook ruft
# "$WURZEL/venv/bin/python", Tests laufen unter "./venv/bin/pytest").


def test_baue_ytdlp_befehl_nutzt_venv_binary_nicht_path():
    """cmd[0] muss auf das yt-dlp neben dem aktiven Python zeigen -- nicht
    auf die blosse Zeichenkette "yt-dlp", die ueber PATH aufgeloest wuerde
    und dabei ein anderes Binary treffen kann als das gepinnte."""
    erwarteter_pfad = str(Path(sys.executable).parent / "yt-dlp")
    cmd = baue_ytdlp_befehl("https://x/y", Path("/tmp/z"))
    assert cmd[0] == erwarteter_pfad
    assert cmd[0] != "yt-dlp"


def test_baue_ytdlp_untertitel_befehl_nutzt_venv_binary_nicht_path():
    from src.fetch import baue_ytdlp_untertitel_befehl
    erwarteter_pfad = str(Path(sys.executable).parent / "yt-dlp")
    cmd = baue_ytdlp_untertitel_befehl("https://x/y", Path("/tmp/z"))
    assert cmd[0] == erwarteter_pfad
    assert cmd[0] != "yt-dlp"


def test_baue_ytdlp_befehl_wirft_wenn_venv_binary_fehlt(monkeypatch, tmp_path):
    """Fehlt das yt-dlp-Binary neben dem aktiven Python, darf NICHT still
    auf PATH zurueckgefallen werden -- das waere exakt der Defekt, der hier
    behoben wird. Stattdessen: klarer Fehler mit dem gesuchten Pfad."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text("")  # Nur die Existenz zaehlt, wird nie ausgefuehrt
    monkeypatch.setattr(sys, "executable", str(fake_python))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        baue_ytdlp_befehl("https://x/y", Path("/tmp/z"))

    meldung = str(exc_info.value)
    assert str(fake_bin / "yt-dlp") in meldung


def test_finde_video_ignoriert_untertitel_und_metadaten(tmp_path):
    # yt-dlp legt video.info.json und video.de.srt daneben. Ein naives
    # glob("video.*") wuerde die als Video an ffmpeg reichen.
    from src.fetch import finde_video
    (tmp_path / "video.info.json").write_text("{}")
    (tmp_path / "video.de.srt").write_text("1\n")
    (tmp_path / "video.mp4").write_bytes(b"\x00")
    assert finde_video(tmp_path).name == "video.mp4"


def test_finde_video_ohne_video_gibt_none(tmp_path):
    from src.fetch import finde_video
    (tmp_path / "video.info.json").write_text("{}")
    assert finde_video(tmp_path) is None


def test_finde_video_mehrere_kandidaten_werfen_fehler(tmp_path):
    # Wenn mehrere Video-Dateien existieren, soll die Funktion nicht
    # still waehlen, sondern klar signalisieren, dass die Wahl mehrdeutig ist.
    from src.fetch import finde_video
    (tmp_path / "video.mp4").write_bytes(b"\x00")
    (tmp_path / "video.webm").write_bytes(b"\x00")
    with pytest.raises(BeschaffungsFehler) as exc_info:
        finde_video(tmp_path)
    # Fehlermeldung soll beide Dateinamen nennen
    assert "video.mp4" in str(exc_info.value)
    assert "video.webm" in str(exc_info.value)


def test_finde_video_ignoriert_unterordner(tmp_path):
    # Unterordner mit Videoendung (z.B. frames.mp4/) sollen ignoriert werden.
    # Nur echte Dateien mit Videoendung sind Treffer.
    from src.fetch import finde_video
    (tmp_path / "frames.mp4").mkdir()  # Verzeichnis, kein File
    (tmp_path / "video.mp4").write_bytes(b"\x00")  # echte Datei
    assert finde_video(tmp_path).name == "video.mp4"


# --- Defekt 1: ein Untertitel-Fehlschlag darf den Video-Download nicht killen ---
#
# Beobachtet im Live-Dry-Run: YouTube blockte mit HTTP 429 NUR die
# Untertitel-Anfrage. Der alte, kombinierte yt-dlp-Aufruf (Video + Untertitel
# in einem Kommando) schlug daraufhin komplett fehl -- kein Video, obwohl es
# ganz normal verfuegbar war. hole_reel() macht deshalb zwei getrennte
# yt-dlp-Aufrufe: einen fuer Video+Metadaten (muss klappen), einen fuer
# Untertitel danach (darf scheitern, siehe transcript.hole_transkript(), das
# ohne .srt automatisch auf Whisper zurueckfaellt).


def test_baue_ytdlp_untertitel_befehl_ist_reiner_untertitel_abruf():
    from src.fetch import baue_ytdlp_untertitel_befehl
    cmd = baue_ytdlp_untertitel_befehl("https://x/y", Path("/tmp/z"))
    # --skip-download: das Video liegt schon aus dem ersten Aufruf da, hier
    # soll wirklich nur der Untertitel-Endpunkt getroffen werden -- sonst
    # koennte ein zweiter Video-Kandidat entstehen, den finde_video() dann
    # als mehrdeutig ablehnt.
    assert "--skip-download" in cmd
    assert "--write-subs" in cmd
    assert "--write-auto-subs" in cmd
    assert "--convert-subs" in cmd and "srt" in cmd
    assert cmd[-1] == "https://x/y"


def test_baue_ytdlp_untertitel_befehl_haengt_cookies_vor_url():
    from src.fetch import baue_ytdlp_untertitel_befehl
    cmd = baue_ytdlp_untertitel_befehl("https://x/y", Path("/tmp/z"), cookies_browser="safari")
    assert cmd[cmd.index("--cookies-from-browser") + 1] == "safari"
    assert cmd[-1] == "https://x/y"


def _info_json_schreiben(ordner: Path, **felder) -> None:
    daten = {"title": "Testtitel", "uploader": "tester", "description": "", "duration": 12}
    daten.update(felder)
    (ordner / "video.info.json").write_text(json.dumps(daten))


def test_hole_reel_toleriert_untertitel_fehlschlag(tmp_path, monkeypatch):
    """Untertitel-429 darf weder Ausnahme werfen noch Video/Metadaten verhindern."""
    from src.fetch import hole_reel

    aufrufe = []

    def fake_run(cmd, **kwargs):
        aufrufe.append(cmd)
        if "--write-subs" in cmd:
            # Der separate Untertitel-Nachhol-Versuch: schlaegt fehl.
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="",
                stderr="ERROR: unable to download video subtitles: "
                       "HTTP Error 429: Too Many Requests\n",
            )
        # Der Video-Aufruf: erfolgreich, legt info.json ab (wie echtes yt-dlp).
        (tmp_path / "video.mp4").write_bytes(b"\x00")
        _info_json_schreiben(tmp_path)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = hole_reel("https://x/y", tmp_path)  # darf NICHT werfen

    assert info["title"] == "Testtitel"
    assert (tmp_path / "video.mp4").exists()
    # Der Untertitel-Fehlschlag wird festgehalten, nicht verschluckt.
    assert info.get("untertitel_fehler")
    assert "429" in info["untertitel_fehler"]
    # Auch zu erledigen (Fix-Runde 1): die Unversehrtheit von finde_video()
    # haengt daran, dass der tatsaechlich ABGESETZTE zweite Befehl
    # --skip-download traegt -- nicht nur der Bauer in Isolation (das deckt
    # bereits test_baue_ytdlp_untertitel_befehl_ist_reiner_untertitel_abruf
    # ab, aber nicht die Verdrahtung in hole_reel()).
    assert len(aufrufe) == 2
    assert "--skip-download" in aufrufe[1]


def test_hole_reel_beide_aufrufe_erfolgreich_kein_untertitel_fehler_schluessel(tmp_path, monkeypatch):
    """Fehlender Erfolgsfall (Fix-Runde 1): klappen beide Aufrufe, gibt es
    keinen untertitel_fehler-Schluessel im Rueckgabe-dict -- kein
    None-Rauschen bei Erfolg."""
    from src.fetch import hole_reel

    def fake_run(cmd, **kwargs):
        if "--write-subs" in cmd:
            (tmp_path / "video.de.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nHallo\n"
            )
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
        (tmp_path / "video.mp4").write_bytes(b"\x00")
        _info_json_schreiben(tmp_path)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = hole_reel("https://x/y", tmp_path)

    assert "untertitel_fehler" not in info


def test_hole_reel_video_fehlschlag_wirft_weiterhin(tmp_path, monkeypatch):
    """Scheitert der Video-Download selbst, bleibt das ein harter Fehler."""
    from src.fetch import hole_reel

    aufrufe = []

    def fake_run(cmd, **kwargs):
        aufrufe.append(cmd)
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="",
            stderr="ERROR: [youtube] abc: Video unavailable\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(BeschaffungsFehler):
        hole_reel("https://x/y", tmp_path)

    # Schlaegt schon der Video-Aufruf fehl, gibt es keinen Grund mehr, noch
    # den Untertitel-Nachhol-Versuch zu starten.
    assert len(aufrufe) == 1


def test_hole_reel_instagram_sperre_gibt_umsetzbaren_hinweis(tmp_path, monkeypatch):
    """Die reale Instagram-Meldung aus dem Dry-Run muss einen Hinweis ausloesen."""
    from src.fetch import hole_reel

    stderr = ("ERROR: [Instagram] ABC123: This content isn't available to "
              "everyone: It can't be seen by certain audiences.\n")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://instagram.com/reel/x", tmp_path)

    meldung = str(exc_info.value)
    assert "isn't available to everyone" in meldung  # stderr-Tail bleibt erhalten
    assert "cookies_browser" in meldung  # ein umsetzbarer Hinweis wurde ergaenzt


def test_hole_reel_rate_limit_gibt_umsetzbaren_hinweis(tmp_path, monkeypatch):
    """Ein HTTP 429 beim Video-Aufruf selbst muss ebenfalls einen Hinweis ausloesen."""
    from src.fetch import hole_reel

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="",
            stderr="ERROR: unable to download video data: HTTP Error 429: Too Many Requests\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://youtube.com/shorts/x", tmp_path)

    meldung = str(exc_info.value)
    assert "429" in meldung
    assert "Rate-Limit" in meldung


def test_hole_reel_unbekannter_fehler_ohne_erfundenen_hinweis(tmp_path, monkeypatch):
    """Fuer echte Unbekannte gibt es ehrlich keinen Hinweis, aber den stderr-Tail."""
    from src.fetch import hole_reel

    stderr = "ERROR: [generic] Unsupported URL: ein voellig neuartiger Fehlerfall\n"

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://example.com/whatever", tmp_path)

    meldung = str(exc_info.value)
    assert "Unsupported URL" in meldung          # stderr-Tail bleibt erhalten
    assert "cookies_browser" not in meldung      # kein erfundener Hinweis
    assert "Rate-Limit" not in meldung


# --- Fund 1 (Fix-Runde 1): Falsch-Positive der Hinweis-Erkennung ---
#
# _bestimme_hinweis() arbeitete mit unverankerten Teilzeichenketten. Drei
# davon trafen gewoehnliche macOS-/yt-dlp-Ausgabe, die mit einer
# Zugriffssperre nichts zu tun hat, und die Sperr-Pruefung lief vor der
# Rate-Limit-Pruefung, sodass ueberlappender Text immer den (hier falschen)
# Cookie-Rat bekam. Jeder Test unten deckt genau die Falsch-Positiv-Richtung
# einer geaenderten Regel ab.


def _fake_run_video_fehlschlag(stderr: str):
    """subprocess.run-Double: der (erste) Video-Aufruf schlaegt mit dem
    gegebenen stderr fehl. Fuer die Hinweis-Klassifizierung reicht das --
    welcher der beiden yt-dlp-Aufrufe den Fehlertext liefert, ist fuer
    _bestimme_hinweis() irrelevant."""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=stderr)
    return fake_run


def test_hole_reel_ytdlp_cookie_nachsatz_bei_429_bekommt_rate_limit_hinweis(tmp_path, monkeypatch):
    """yt-dlp haengt seinen "--cookies-from-browser"-Nachsatz an viele
    verschiedene Fehler an, auch an echte Rate-Limits. "cookies" als
    Treffer-Token haette hier faelschlich den Sperr-Hinweis statt "spaeter
    erneut versuchen" ausgeloest."""
    from src.fetch import hole_reel

    stderr = ("ERROR: unable to download webpage: HTTP Error 429: Too Many "
              "Requests. Use --cookies-from-browser or --cookies for the "
              "authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ "
              "for how to manually pass cookies.\n")
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://youtube.com/shorts/x", tmp_path)

    meldung = str(exc_info.value)
    assert "Rate-Limit erreicht" in meldung
    assert "Inhalt scheint gesperrt" not in meldung


def test_hole_reel_cookie_lesefehler_bekommt_keinen_erfundenen_hinweis(tmp_path, monkeypatch):
    """Ein Fehler beim Cookie-*Auslesen* selbst (z.B. fehlender Vollzugriff
    auf die Safari-Cookie-Datenbank) ist keine Zugriffssperre -- der Rat
    "cookies_browser='safari' erneut versuchen" waere hier ein Kreis zurueck
    zur Fehlerursache."""
    from src.fetch import hole_reel

    stderr = ("ERROR: Could not find Safari cookies database. Please check "
              "the Full Disk Access permission in System Settings.\n")
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://x/y", tmp_path)

    meldung = str(exc_info.value)
    assert "Full Disk Access" in meldung          # stderr-Tail bleibt erhalten
    assert "Inhalt scheint gesperrt" not in meldung
    assert "Rate-Limit" not in meldung


def test_hole_reel_macos_tmp_pfad_bekommt_keinen_sperr_hinweis(tmp_path, monkeypatch):
    """"/private/var/..." ist auf macOS der real aufgeloeste TMPDIR und
    taucht routinemaessig in yt-dlp-/ffmpeg-Fehlern auf -- bloss weil ein
    Temp-Pfad im Text steht, ist der Inhalt nicht gesperrt."""
    from src.fetch import hole_reel

    stderr = ("ERROR: unable to convert subtitles: "
              "'/private/var/folders/_3/abcd1234/T/tmpXYZ.srt' konnte nicht "
              "geschrieben werden: Permission denied\n")
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://x/y", tmp_path)

    meldung = str(exc_info.value)
    assert "Permission denied" in meldung
    assert "Inhalt scheint gesperrt" not in meldung


def test_hole_reel_zahl_mit_429_als_teilstring_bekommt_keinen_rate_limit_hinweis(tmp_path, monkeypatch):
    """Eine Fragment-Nummer wie "1429" enthaelt "429" als Teilzeichenkette,
    ist aber kein HTTP-429-Rate-Limit."""
    from src.fetch import hole_reel

    stderr = "ERROR: unable to download fragment 1429 of 2000: giving up after 3 retries\n"
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://x/y", tmp_path)

    meldung = str(exc_info.value)
    assert "giving up after 3 retries" in meldung
    assert "Rate-Limit" not in meldung


def test_hole_reel_instagram_ohne_login_bekommt_sperr_hinweis(tmp_path, monkeypatch):
    """Task 11c: die reale Instagram-Meldung aus dem Live-Durchstich nutzt
    "logged-in" (mit Bindestrich) -- "login" als Teilzeichenkette trifft das
    NICHT (kein "i" direkt nach "log"), obwohl genau das der Fall ist, in dem
    der Cookie-Rat richtig waere."""
    from src.fetch import hole_reel

    stderr = ("ERROR: [Instagram] abc123: Requested content is not "
              "available, without being logged-in you might not have "
              "access to this post.\n")
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://instagram.com/reel/x", tmp_path)

    meldung = str(exc_info.value)
    assert "Inhalt scheint gesperrt" in meldung
    assert "cookies_browser" in meldung


def test_hole_reel_bejahende_login_erwaehnung_bekommt_keinen_sperr_hinweis(tmp_path, monkeypatch):
    """Gegenprobe zur "logged-in"-Ergaenzung: ein bejahender Satz ("bereits
    eingeloggt") ist kein Sperrfall. Deshalb wurde die volle Wendung
    "without being logged-in" aufgenommen statt des blossen Worts
    "logged-in" -- dieselbe Vorsicht wie bei "is private" vs. TMPDIR-Pfaden."""
    from src.fetch import hole_reel

    stderr = ("DEBUG: [Cookies] session already logged-in as testuser -- "
              "reusing existing cookies, no re-authentication needed\n")
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://x/y", tmp_path)

    meldung = str(exc_info.value)
    assert "already logged-in" in meldung   # stderr-Tail bleibt erhalten
    assert "Inhalt scheint gesperrt" not in meldung


def test_hole_reel_instagram_empty_media_response_bekommt_sperr_hinweis(tmp_path, monkeypatch):
    """Zweite beobachtete Instagram-Wendung (Task 11c): "Instagram sent an
    empty media response" -- typisches Symptom fehlender Anmeldung, ebenfalls
    ohne den Cookie-Hinweis durchgefallen."""
    from src.fetch import hole_reel

    stderr = "ERROR: [Instagram] abc123: Instagram sent an empty media response\n"
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://instagram.com/reel/x", tmp_path)

    meldung = str(exc_info.value)
    assert "Inhalt scheint gesperrt" in meldung
    assert "cookies_browser" in meldung


def test_hole_reel_verstreutes_empty_response_vokabular_bekommt_keinen_sperr_hinweis(tmp_path, monkeypatch):
    """Gegenprobe: "empty" und "response" kommen unabhaengig voneinander vor,
    aber nicht als zusammenhaengende Wendung "empty media response" -- darf
    keinen Treffer ausloesen (dieselbe Logik wie bei der 429-Fragment-Nummer)."""
    from src.fetch import hole_reel

    stderr = "ERROR: empty response body for fragment 7, retrying download\n"
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://x/y", tmp_path)

    meldung = str(exc_info.value)
    assert "retrying download" in meldung
    assert "Inhalt scheint gesperrt" not in meldung


def test_hole_reel_ambige_ytdlp_meldung_bevorzugt_rate_limit_hinweis(tmp_path, monkeypatch):
    """yt-dlps eigene, unentschiedene Meldung ("rate-limit reached or login
    required") enthaelt Token aus BEIDEN Kategorien. Die Rate-Limit-Pruefung
    laeuft jetzt zuerst, damit ein echtes Rate-Limit nicht vom zufaellig
    mitgetroffenen Sperr-Muster ueberschrieben wird -- der im Auftrag als
    "schlimmer als kein Hinweis" benannte Fall."""
    from src.fetch import hole_reel

    stderr = ("ERROR: [Instagram] abc: Requested content is not available, "
              "rate-limit reached or login required.\n")
    monkeypatch.setattr(subprocess, "run", _fake_run_video_fehlschlag(stderr))

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://instagram.com/reel/x", tmp_path)

    meldung = str(exc_info.value)
    assert "Rate-Limit erreicht" in meldung
    assert "Inhalt scheint gesperrt" not in meldung


# --- Task 11c: Zeitlimits fuer die yt-dlp-subprocess.run()-Aufrufe ---
#
# Befund: keiner der subprocess.run()-Aufrufe in fetch.py/frames.py/
# transcript.py setzte bislang timeout= -- ein haengendes yt-dlp (z.B.
# Netzwerk-Stall) blieb unbegrenzt am Leben, auch nachdem der aeussere
# Waechter (hooks/reel_guard.sh) den Python-Prozess gekillt hatte, weil
# yt-dlp dessen Enkelkind ist und nicht mitstirbt.


def test_hole_reel_video_timeout_wirft_beschaffungsfehler_mit_zeitangabe(tmp_path, monkeypatch):
    """Ein haengender Video-Aufruf ist wie jeder andere Video-Fehlschlag ein
    harter Abbruch -- subprocess.TimeoutExpired darf NICHT als nackter
    Traceback durchschlagen, sondern muss als BeschaffungsFehler mit
    deutscher Meldung samt Zeitangabe auftauchen."""
    from src.fetch import hole_reel, VIDEO_ZEITLIMIT_SEKUNDEN

    def fake_run(cmd, **kwargs):
        if "--write-subs" not in cmd:
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(BeschaffungsFehler) as exc_info:
        hole_reel("https://x/y", tmp_path)

    meldung = str(exc_info.value)
    assert str(VIDEO_ZEITLIMIT_SEKUNDEN) in meldung
    assert "nicht reagiert" in meldung


def test_hole_reel_untertitel_timeout_wird_toleriert(tmp_path, monkeypatch):
    """Ein haengender Untertitel-Nachhol-Versuch darf weder Ausnahme werfen
    noch Video/Metadaten verhindern -- derselbe Vertrag wie bei einem
    regulaeren Untertitel-Fehlschlag (siehe
    test_hole_reel_toleriert_untertitel_fehlschlag). Der Zeitlimit-Fall wird
    im dossier-Feld festgehalten statt kommentarlos zu verschwinden."""
    from src.fetch import hole_reel, UNTERTITEL_ZEITLIMIT_SEKUNDEN

    def fake_run(cmd, **kwargs):
        if "--write-subs" in cmd:
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
        (tmp_path / "video.mp4").write_bytes(b"\x00")
        _info_json_schreiben(tmp_path)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = hole_reel("https://x/y", tmp_path)  # darf NICHT werfen

    assert info["title"] == "Testtitel"
    assert (tmp_path / "video.mp4").exists()
    assert info.get("untertitel_fehler")
    assert str(UNTERTITEL_ZEITLIMIT_SEKUNDEN) in info["untertitel_fehler"]


def test_video_und_untertitel_aufrufe_bekommen_ihr_jeweiliges_zeitlimit(tmp_path, monkeypatch):
    """Verdrahtungs-Check: subprocess.run() muss tatsaechlich mit den
    modul-eigenen Konstanten aufgerufen werden, nicht nur irgendein
    timeout=-Wert."""
    from src.fetch import (hole_reel, VIDEO_ZEITLIMIT_SEKUNDEN,
                           UNTERTITEL_ZEITLIMIT_SEKUNDEN)

    gesehene_timeouts = []

    def fake_run(cmd, **kwargs):
        gesehene_timeouts.append(kwargs.get("timeout"))
        if "--write-subs" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")
        (tmp_path / "video.mp4").write_bytes(b"\x00")
        _info_json_schreiben(tmp_path)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    hole_reel("https://x/y", tmp_path)

    assert gesehene_timeouts == [VIDEO_ZEITLIMIT_SEKUNDEN, UNTERTITEL_ZEITLIMIT_SEKUNDEN]
