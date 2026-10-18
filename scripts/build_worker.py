"""Prepare the Cloudflare Worker source without moving the local app."""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER_ROOT = PROJECT_ROOT / ".worker-build"


def main() -> None:
    """Copy the API package and write its ASGI Worker entry point."""
    app_target = WORKER_ROOT / "app"
    if app_target.exists():
        shutil.rmtree(app_target)
    shutil.copytree(
        PROJECT_ROOT / "app",
        app_target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (WORKER_ROOT / "worker.py").write_text(
        '"""Cloudflare Worker entry point for the Team Todo API."""\n\n'
        "from app.main import app\n"
        "from workers import asgi\n\n"
        "Default = asgi.entrypoint(app)\n"
    )


if __name__ == "__main__":
    main()
