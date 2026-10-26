#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
# Each uv project selects its own .venv, including when invoked through a hook.
unset VIRTUAL_ENV

uv run --locked ruff check .
uv run --locked ruff format --check .

if [[ -d app ]]; then
  uv run --locked mypy app
else
  printf '%s\n' 'SKIP mypy: app/ 아직 없습니다.'
fi

if [[ -d tests ]] && find tests -type f -name 'test_*.py' -print -quit | grep -q .; then
  uv run --locked pytest
elif [[ -d app ]]; then
  printf '%s\n' 'ERROR: app/ 코드에 대응하는 tests/test_*.py가 없습니다.' >&2
  exit 1
else
  printf '%s\n' 'SKIP pytest: app/ 구현과 테스트가 아직 없습니다.'
fi

if [[ -d cli ]]; then
  uv run --locked --project cli ruff check cli/src/ttodo cli/tests
  uv run --locked --project cli ruff format --check cli/src/ttodo cli/tests
  uv run --locked --project cli mypy --config-file cli/pyproject.toml cli/src/ttodo
  (cd cli && uv run --locked pytest)
fi
