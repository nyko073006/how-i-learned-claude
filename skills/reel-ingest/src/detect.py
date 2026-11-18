"""Erkennt Reel-Links in eingehenden Nachrichten."""
import re

# Reihenfolge egal — die Muster überschneiden sich nicht.
MUSTER = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/reels?/[\w-]+", re.I),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/shorts/[\w-]+", re.I),
    "tiktok": re.compile(r"https?://(?:www\.)?(?:vm\.)?tiktok\.com/[^\s]+", re.I),
}

# "fyi:" am Anfang heisst: nur zeigen, nicht verarbeiten.
SKIP_PRAEFIX = re.compile(r"^\s*fyi\s*:", re.I)


def detect_reel(text: str) -> tuple[str, str] | None:
    """Gibt (plattform, url) zurueck, oder None wenn nichts zu tun ist."""
    if not text or SKIP_PRAEFIX.search(text):
        return None
    for plattform, muster in MUSTER.items():
        treffer = muster.search(text)
        if treffer:
            return (plattform, treffer.group(0))
    return None
