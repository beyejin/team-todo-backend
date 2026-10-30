# AGENTS.md

## Python 개발 환경

- Python 버전은 3.13을 사용하고, 패키지 및 가상 환경 관리는 `uv`로 합니다.
- 프로젝트 의존성은 `pyproject.toml`에 선언하고 `uv.lock`을 함께 커밋합니다.
- 의존성을 추가하거나 변경할 때 `uv add` 또는 `uv remove`를 사용합니다.
- 환경 동기화는 `uv sync`, 명령 실행은 `uv run <명령>`을 사용합니다.
- 로컬 가상 환경은 프로젝트 루트의 `.venv/`에 둡니다. `.venv/`는 버전 관리에 포함하지 않습니다.
- 새 환경에서는 `uv sync`로 의존성을 설치한 뒤 `uv run uvicorn app.main:app --reload`로 개발 서버를 실행합니다.
- Ruff가 lint 규칙과 포맷을 모두 관리합니다. Python 코드를 작성한 뒤 다음 명령을 실행합니다.
  - 자동 수정: `uv run ruff check --fix .`
  - 포맷 적용: `uv run ruff format .`
  - 검사만 실행: `uv run ruff check . && uv run ruff format --check .`
- 타입 검사는 Pydantic 플러그인이 포함된 strict mypy를 사용합니다. 앱 코드가 있을 때 `uv run mypy app`을 실행합니다.
- 새 코드는 타입 어노테이션과 공개 모듈·클래스·함수의 docstring을 작성하고, 경고를 무시하는 설정이나 주석을 추가하지 않습니다. 불가피한 예외는 최소 범위에 이유를 함께 기록합니다.

## 에이전트 개발 루프

1. 작업 전에 `docs/PRD.md`, `docs/TSD.md`, `docs/database.md` 중 관련 기준과 `docs/TEST_CASE.md`의 해당 케이스를 읽습니다. 기준 문서끼리 충돌하면 임의로 해석하지 말고 충돌을 먼저 드러냅니다.
2. 한 번에 하나의 작은 동작을 선택하고, 완료 조건을 관련 `TC-###` ID와 함께 테스트로 표현한 뒤 구현합니다. 테스트는 실제 동작이나 오류 조건을 확인해야 하며, 구현 세부사항만 확인하는 테스트는 추가하지 않습니다.
3. `bash scripts/verify.sh`를 실행합니다. 이 명령은 `uv run --locked`로 의존성 잠금 파일의 불일치도 검사합니다. 실패 로그를 원인에 따라 수정하고 다시 실행합니다. 통과하지 않은 검사를 통과했다고 보고하지 않습니다.
4. 마지막에 변경 diff를 읽고 요구사항 추적, 실패 경로, 부작용, 불필요한 파일 변경을 확인합니다. 최종 수정 뒤 검증을 다시 실행하고 결과를 보고합니다.
5. 검증을 반복해도 진행되지 않거나 요구사항이 모호하면 임의로 우회하지 말고, 막힌 검사와 필요한 결정을 명시합니다.

기능 코드가 추가되면 `tests/`에 테스트를 포함해야 합니다. `app/`가 생긴 뒤 테스트 파일이 없으면 검증 스크립트는 실패하도록 유지합니다.

새 체크아웃에서는 `uv sync --locked`와 `uv sync --locked --project cli` 후
`uv run --locked pre-commit install`로 커밋 전 검사를 설치합니다.
훅에서 자동 수정하거나 검사를 우회해 실패를 감추지 않습니다.
하네스의 실행 범위와 검증 기준은 `docs/HARNESS.md`를 따릅니다.
프론트엔드는 별도 `../team-todo-frontend/docs/plan.md`와 `docs/TEST_CASE.md`의 `FE-###`를 연결하고,
사용자가 직접 실행하는 수동 시나리오를 유지합니다. Playwright E2E는 추가하지 않습니다.
