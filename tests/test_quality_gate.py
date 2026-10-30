"""Exercise quality gates at real Git commit boundaries in temporary repositories."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UV_STUB = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

arguments = sys.argv[1:]
project = "cli" if "--project" in arguments or Path.cwd().name == "cli" else "root"
if "ruff" in arguments:
    stage = "format" if "format" in arguments else "lint"
elif "mypy" in arguments:
    stage = "type"
elif "pytest" in arguments:
    stage = "test"
else:
    sys.exit("Unexpected uv invocation")
with Path(os.environ["QUALITY_GATE_LOG"]).open("a") as log:
    log.write(json.dumps({"project": project, "stage": stage}) + "\\n")
injected_failure = (
    os.environ.get("QUALITY_GATE_FAIL_STAGE") == stage
    and os.environ.get("QUALITY_GATE_FAIL_PROJECT") == project
)
invalid_source = (
    project == "root"
    and stage == "lint"
    and "undefined_quality_gate_name" in Path("app/main.py").read_text()
)
if injected_failure or invalid_source:
    sys.exit(f"Quality gate rejected {project} {stage}")
"""


def run(
    repository: Path, environment: dict[str, str], *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run a bounded command only inside the disposable repository."""
    return subprocess.run(
        arguments,
        cwd=repository,
        env=environment,
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def quality_repository(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Install the real hook around stubbed tools, without touching the user index."""
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "scripts").mkdir()
    shutil.copy2(PROJECT_ROOT / "scripts/verify.sh", repository / "scripts/verify.sh")
    shutil.copy2(
        PROJECT_ROOT / ".pre-commit-config.yaml",
        repository / ".pre-commit-config.yaml",
    )
    for relative, content in {
        "app/main.py": "VALUE = 1\n",
        "tests/test_sample.py": "def test_sample():\n    assert True\n",
        "cli/src/ttodo/__init__.py": "",
        "cli/tests/test_sample.py": "def test_sample():\n    assert True\n",
    }.items():
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    tools_directory = tmp_path / "bin"
    tools_directory.mkdir()
    uv = tools_directory / "uv"
    uv.write_text(UV_STUB)
    uv.chmod(0o755)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "PRE_COMMIT_HOME": str(tmp_path / "pre-commit-cache"),
            "QUALITY_GATE_LOG": str(tmp_path / "quality-gate.jsonl"),
            "QUALITY_GATE_FAIL_STAGE": "",
            "QUALITY_GATE_FAIL_PROJECT": "",
            "PATH": os.pathsep.join(
                [str(tools_directory), str(Path(sys.executable).parent), os.defpath]
            ),
        }
    )
    run(repository, environment, "git", "init", "--initial-branch=main")
    run(repository, environment, "git", "config", "user.name", "Quality Gate Test")
    run(
        repository,
        environment,
        "git",
        "config",
        "user.email",
        "quality-gate@example.invalid",
    )
    run(repository, environment, "git", "add", ".")
    run(repository, environment, "git", "commit", "-m", "Initial fixture")
    run(repository, environment, sys.executable, "-m", "pre_commit", "install")
    (repository / "app/main.py").write_text("VALUE = 2\n")
    run(repository, environment, "git", "add", "app/main.py")
    return repository, environment


@pytest.mark.parametrize("project", ["root", "cli"])
@pytest.mark.parametrize("stage", ["lint", "format", "type", "test"])
def test_qg_001_failed_check_blocks_commit(
    quality_repository: tuple[Path, dict[str, str]], project: str, stage: str
) -> None:
    """QG-001: Every backend and CLI check failure prevents the actual commit."""
    repository, environment = quality_repository
    previous_head = run(repository, environment, "git", "rev-parse", "HEAD").stdout
    environment["QUALITY_GATE_FAIL_PROJECT"] = project
    environment["QUALITY_GATE_FAIL_STAGE"] = stage

    result = run(repository, environment, "git", "commit", "-m", "Reject", check=False)

    assert result.returncode != 0
    assert f"Quality gate rejected {project} {stage}" in result.stdout + result.stderr
    assert (
        run(repository, environment, "git", "rev-parse", "HEAD").stdout == previous_head
    )
    log = Path(environment["QUALITY_GATE_LOG"]).read_text().splitlines()
    assert json.loads(log[-1]) == {"project": project, "stage": stage}


def test_qg_002_missing_tests_block_commit(
    quality_repository: tuple[Path, dict[str, str]],
) -> None:
    """QG-002: An app without its required test files cannot be committed."""
    repository, environment = quality_repository
    previous_head = run(repository, environment, "git", "rev-parse", "HEAD").stdout
    (repository / "tests/test_sample.py").unlink()
    run(repository, environment, "git", "add", "-u", "tests")

    result = run(repository, environment, "git", "commit", "-m", "Reject", check=False)

    assert result.returncode != 0
    assert "tests/test_*.py" in result.stdout + result.stderr
    assert (
        run(repository, environment, "git", "rev-parse", "HEAD").stdout == previous_head
    )


def test_qg_003_passing_checks_allow_commit(
    quality_repository: tuple[Path, dict[str, str]],
) -> None:
    """QG-003: A valid change is committed after all checks succeed."""
    repository, environment = quality_repository
    previous_head = run(repository, environment, "git", "rev-parse", "HEAD").stdout

    result = run(repository, environment, "git", "commit", "-m", "Accept", check=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        run(repository, environment, "git", "rev-parse", "HEAD").stdout != previous_head
    )
    assert (
        run(repository, environment, "git", "show", "HEAD:app/main.py").stdout
        == "VALUE = 2\n"
    )
    assert run(repository, environment, "git", "status", "--porcelain").stdout == ""


def test_qg_004_unstaged_fix_does_not_hide_staged_failure(
    quality_repository: tuple[Path, dict[str, str]],
) -> None:
    """QG-004: Reject staged bad code and preserve the index and working tree."""
    repository, environment = quality_repository
    previous_head = run(repository, environment, "git", "rev-parse", "HEAD").stdout
    source = repository / "app/main.py"
    staged_content = "VALUE = undefined_quality_gate_name\n"
    working_content = "VALUE = 3\n"
    source.write_text(staged_content)
    run(repository, environment, "git", "add", "app/main.py")
    source.write_text(working_content)
    previous_index = run(repository, environment, "git", "write-tree").stdout

    result = run(repository, environment, "git", "commit", "-m", "Reject", check=False)

    assert result.returncode != 0
    assert "Quality gate rejected root lint" in result.stdout + result.stderr
    assert (
        run(repository, environment, "git", "rev-parse", "HEAD").stdout == previous_head
    )
    assert run(repository, environment, "git", "write-tree").stdout == previous_index
    assert (
        run(repository, environment, "git", "show", ":app/main.py").stdout
        == staged_content
    )
    assert source.read_text() == working_content
