import pytest
from src.detect import detect_reel


def test_erkennt_instagram_reel():
    text = "schau mal https://www.instagram.com/reel/C8xYz1AbCdE/ an"
    assert detect_reel(text) == ("instagram", "https://www.instagram.com/reel/C8xYz1AbCdE")


def test_erkennt_youtube_shorts():
    text = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    assert detect_reel(text) == ("youtube", "https://www.youtube.com/shorts/dQw4w9WgXcQ")


def test_erkennt_tiktok():
    assert detect_reel("https://www.tiktok.com/@user/video/7123456789")[0] == "tiktok"


def test_fyi_praefix_unterdrueckt_verarbeitung():
    # Der Nutzer will das Reel nur zeigen, nicht verarbeiten lassen.
    assert detect_reel("fyi: https://www.youtube.com/shorts/dQw4w9WgXcQ") is None
    assert detect_reel("FYI:  https://www.instagram.com/reel/C8xYz1AbCdE/") is None


def test_normales_youtube_video_ist_kein_reel():
    # Nur Shorts, keine langen Videos — die sind nicht gemeint.
    assert detect_reel("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None


def test_reiner_text_ergibt_nichts():
    assert detect_reel("kannst du mal die Tests laufen lassen") is None
