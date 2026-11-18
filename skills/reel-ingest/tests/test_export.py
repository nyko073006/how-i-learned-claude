"""Tests fuer `sammle.py export`: Links aus dem Instagram-Datenexport "Gespeichert"."""
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from sammle import links_aus_export  # noqa: E402

PFAD = "your_instagram_activity/saved/saved_posts.json"


def _ts(tag: str) -> int:
    return int(datetime.fromisoformat(tag).replace(tzinfo=timezone.utc).timestamp())


def _eintrag(url: str, tag: str) -> dict:
    return {"timestamp": _ts(tag), "media": [],
            "label_values": [{"label": "URL", "value": url, "href": url},
                             {"label": "Untertitel", "value": "egal"}]}


def _zip(tmp_path: Path, eintraege: list) -> Path:
    z = tmp_path / "export.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr(PFAD, json.dumps(eintraege))
    return z


def test_alle_links_aelteste_zuerst(tmp_path):
    z = _zip(tmp_path, [_eintrag("https://www.instagram.com/reel/NEU1/", "2026-11-10"),
                        _eintrag("https://www.instagram.com/p/ALT1/", "2026-10-01")])
    assert links_aus_export(z) == ["https://www.instagram.com/p/ALT1/",
                                   "https://www.instagram.com/reel/NEU1/"]


def test_seit_filtert_aeltere_weg(tmp_path):
    z = _zip(tmp_path, [_eintrag("https://www.instagram.com/reel/NEU1/", "2026-11-10"),
                        _eintrag("https://www.instagram.com/reel/ALT1/", "2026-11-05")])
    assert links_aus_export(z, seit="2026-11-06") == ["https://www.instagram.com/reel/NEU1/"]


def test_bekannte_shortcodes_aus_notizen_fallen_weg(tmp_path):
    notiz = tmp_path / "alt.md"
    notiz.write_text("| 1 | [ALT1](https://www.instagram.com/reel/ALT1/) | x |\n", encoding="utf-8")
    z = _zip(tmp_path, [_eintrag("https://www.instagram.com/reel/NEU1/", "2026-11-10"),
                        _eintrag("https://www.instagram.com/p/ALT1/", "2026-11-09")])
    assert links_aus_export(z, bekannt=[notiz]) == ["https://www.instagram.com/reel/NEU1/"]


def test_doppelte_links_nur_einmal(tmp_path):
    u = "https://www.instagram.com/reel/NEU1/"
    z = _zip(tmp_path, [_eintrag(u, "2026-11-10"), _eintrag(u + "?igsh=abc", "2026-11-11")])
    assert links_aus_export(z) == [u]
