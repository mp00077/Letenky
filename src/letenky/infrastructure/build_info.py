"""Embed metadata at build time; a frozen application never invokes Git."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone


def collect_build_info(root, *, built=False):
    def git(*args):
        try:
            result = subprocess.run(
                [os.environ.get("LETENKY_GIT_EXECUTABLE", "git"), "-C", str(root), *args],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    commit = git("rev-parse", "--verify", "HEAD")
    tags = git("tag", "--points-at", "HEAD") if commit else None
    dirty = git("status", "--porcelain", "--untracked-files=normal") if commit else None
    return {
        "built_at": datetime.now(timezone.utc).isoformat() if built else None,
        "python": platform.python_version(),
        "git_tag": tags.replace("\n", ", ") if tags else ("Bez tagu" if commit else "Nedostupný"),
        "git_commit": commit or "Nedostupný", "dirty": bool(dirty),
    }


def get_build_info():
    if not getattr(sys, "frozen", False):
        return collect_build_info(Path(__file__).resolve().parents[3])
    try:
        data = json.loads(Path(__file__).with_name("build_info.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict) or any(not isinstance(data.get(key), str)
                                            for key in ("built_at", "python", "git_tag", "git_commit")):
            raise ValueError("Invalid build metadata")
        datetime.fromisoformat(data["built_at"])
        return data
    except (OSError, ValueError):
        return {"built_at": None, "python": platform.python_version(),
                "git_tag": "Nedostupný", "git_commit": "Nedostupný", "dirty": False}
