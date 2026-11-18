"""Legt die Skill-Wurzel auf den Suchpfad, damit `import cli` funktioniert.

HOME und Einstellungsdatei zeigen vor jedem Import in einen Wegwerf-Ordner: kein Test liest die
echte Konfiguration oder berührt echte Dateien.
"""
import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

_HOME = tempfile.mkdtemp(prefix="reel-ingest-home-")
atexit.register(shutil.rmtree, _HOME, True)
os.environ["HOME"] = _HOME
os.environ["CLAUDE_SKILLS_EINSTELLUNGEN"] = os.path.join(_HOME, "fehlt.json")

sys.path.insert(0, str(Path(__file__).parent.parent))
