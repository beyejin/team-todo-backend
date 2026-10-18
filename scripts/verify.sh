#!/usr/bin/env bash
set -euo pipefail

uv run ruff check .
uv run ruff format --check .

if [[ -d app ]]; then
  uv run mypy app
else
  printf '%s\n' 'SKIP mypy: app/ 아직 없습니다.'
fi

if [[ -d tests ]] && find tests -type f -name 'test_*.py' -print -quit | grep -q .; then
  uv run pytest
elif [[ -d app ]]; then
  printf '%s\n' 'ERROR: app/ 코드에 대응하는 tests/test_*.py가 없습니다.' >&2
  exit 1
else
  printf '%s\n' 'SKIP pytest: app/ 구현과 테스트가 아직 없습니다.'
fi

if [[ -d cli ]]; then
  uv run --project cli ruff check cli/src/ttodo cli/tests
  uv run --project cli ruff format --check cli/src/ttodo cli/tests
  uv run --project cli mypy --config-file cli/pyproject.toml cli/src/ttodo
  (cd cli && uv run pytest)
fi
