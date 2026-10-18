"""Download the running API schema and regenerate the packaged API client."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_URL = os.environ.get("TTODO_OPENAPI_URL", "http://127.0.0.1:8000/openapi.json")


def main() -> None:
    """Fetch OpenAPI and run the installed client generator."""
    generator = shutil.which("openapi-python-client")
    if generator is None:
        raise SystemExit(
            "Install the ttodo development tools with `uv sync --project cli`."
        )
    with urlopen(SCHEMA_URL, timeout=10) as response:
        ROOT.joinpath("openapi.json").write_bytes(response.read())
    subprocess.run(
        [
            generator,
            "generate",
            "--path",
            str(ROOT / "openapi.json"),
            "--output-path",
            str(ROOT / "src" / "ttodo" / "generated"),
            "--config",
            str(ROOT / "openapi-client.yaml"),
            "--meta",
            "none",
            "--overwrite",
        ],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
