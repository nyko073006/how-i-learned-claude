"""Prueft die Nachtwache: gesperrte Befehle muessen mit Exit 2 scheitern, harmlose durchgehen.
Aufruf: python3 -I test_nachtwache.py"""
import json, subprocess, sys
from pathlib import Path

SKRIPT = Path(__file__).with_name("nachtwache.py")


def lauf(werkzeug: str, eingabe: dict) -> int:
    r = subprocess.run([sys.executable, "-I", str(SKRIPT)], capture_output=True, text=True,
                       input=json.dumps({"tool_name": werkzeug, "tool_input": eingabe}))
    return r.returncode


GESPERRT = [
    "git push origin afk/x", "git -C ~/Developer/foo push", "cd a && git push --force",
    "git merge main", "gh pr create --fill", "gh pr merge 12", "gh issue comment 3 -b hi",
    "gh api repos/a/b/issues -X POST -f title=x", "supabase db push", "vercel --prod",
    "vercel deploy", "firebase deploy", "git reset --hard HEAD~1", "git clean -fd",
    "git branch -D afk/x", "fastlane release",
]
ERLAUBT = [
    "git status", "git commit -m 'push merge erwaehnt'", "git log --oneline", "gh pr list",
    "gh issue view 3", "gh api repos/a/b/issues", "npm test", "git worktree add ../x -b afk/x",
    "pytest -q", "echo vercel",
]


def main() -> int:
    fehler = [f"nicht gesperrt: {c}" for c in GESPERRT if lauf("Bash", {"command": c}) != 2]
    fehler += [f"faelschlich gesperrt: {c}" for c in ERLAUBT if lauf("Bash", {"command": c}) != 0]
    if lauf("mcp__claude_ai_Gmail__send_message", {}) != 2:
        fehler.append("MCP-Senden nicht gesperrt")
    if lauf("mcp__claude_ai_Gmail__search_threads", {}) != 0:
        fehler.append("MCP-Lesen faelschlich gesperrt")
    gesamt = len(GESPERRT) + len(ERLAUBT) + 2
    print(f"{gesamt - len(fehler)} gruen, {len(fehler)} rot")
    print("\n".join(fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
