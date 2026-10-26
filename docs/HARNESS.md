# 검증 하네스와 개발 루프

## 적용 범위

현재 저장소는 Python 3.13·uv를 사용하는 FastAPI 백엔드와 CLI입니다.
기존 `scripts/verify.sh`를 개발 중 검사, 커밋 전 검사, 기존 CI에서 공통으로 사용합니다.
프론트엔드는 별도 [team-todo-frontend](https://github.com/beyejin/team-todo-frontend) 저장소에서 Next.js로 구현합니다.
프론트 명세와 사용자 수동 테스트는 해당 저장소의 `docs/plan.md`, `docs/TEST_CASE.md`를 따릅니다.
Playwright를 이용한 E2E 테스트는 추가하지 않습니다.

## 검사 기준

| 순서 | 검사 | 실패 조건 |
| --- | --- | --- |
| 1 | Ruff lint | 오류 가능성, 잘못된 import, 타입 주석 누락, 비동기 사용 오류, 디버거 잔여 코드 등 |
| 2 | Ruff format 검사 | 저장된 코드가 지정된 포맷과 다름 |
| 3 | strict mypy | 앱의 타입 오류 또는 타입 검사에 필요한 설정 오류 |
| 4 | pytest | 테스트 실패·수집 오류·테스트 없음. `app/`가 있는데 테스트 파일이 없어도 실패 |
| 5 | CLI의 Ruff·format·mypy·pytest | CLI 전용 설정으로 동일한 검사 수행 |

- 모든 단계의 `uv run`에 `--locked`를 사용합니다. 의존성 선언과 lockfile이 다르면 실패하며 검사 도중 lockfile을 갱신하지 않습니다.
- 검증 프로세스는 부모의 활성 가상환경 표시를 제거하고 루트·CLI가 각각 자기 `.venv`를 사용하게 합니다. 터미널의 활성 환경은 바꾸지 않습니다.
- Ruff는 기존 `E`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`에 매개변수·반환 타입 주석 규칙, `ASYNC`, `C4`, `PIE`, `T10`을 더합니다. 루트와 CLI에 같은 규칙을 적용합니다.
- 무조건 `ALL`을 켜지 않습니다. 도구 업데이트 때 새 규칙이 자동 추가되는 일을 피하고, 현재 Python 코드에 맞는 규칙을 명시합니다. 새 무시 규칙으로 오류를 덮지 않습니다.
- Pydantic 플러그인을 사용하는 기존 앱 strict mypy와 CLI의 별도 strict 설정을 유지합니다.
- `set -euo pipefail`로 실패를 다음 단계에 숨기지 않습니다. 훅은 검사만 하며 자동 포맷·자동 스테이징을 하지 않습니다.
- PostgreSQL 테스트는 별도 `TEST_DATABASE_URL`, `TEST_KANBAN_DATABASE_URL`이 필요합니다. 미설정으로 건너뛴 테스트는 통과와 구분해 보고합니다. 기존 CI는 테스트용 PostgreSQL을 준비하도록 구성되어 있습니다.

## 설치와 실행

저장소 루트에서 실행합니다.

```console
uv sync --locked
uv sync --locked --project cli
uv run --locked pre-commit install
```

`pre-commit`은 uv 개발 의존성으로 고정합니다. 새 체크아웃마다 설치가 필요하며,
이 설정은 이 저장소의 Git 훅에만 적용합니다.

```console
# 개발 중 전체 검증
bash scripts/verify.sh

# pre-commit을 통해 전체 작업 트리 검증
uv run --locked pre-commit run --all-files

# 설정 문법 확인
uv run --locked pre-commit validate-config
```

일반 커밋에서는 `.pre-commit-config.yaml`의 `verify` 훅이 동일한 검증 스크립트를
실행합니다. `always_run: true`이므로 파일 종류 때문에 검사가 건너뛰어지지 않고,
`pass_filenames: false`이므로 일부 파일만 전달하지 않고 프로젝트 검사를 수행합니다.

### 커밋 검사 범위

- `pre-commit`은 커밋할 때 스테이징하지 않은 추적 파일 변경을 임시로 분리합니다. 스테이징된 코드에 오류가 있고 작업 트리에서만 고쳐진 경우도 차단해야 합니다.
- untracked 파일까지 제거한 완전한 격리 환경은 아닙니다. 필요한 새 파일이 모두 스테이징됐는지 `git diff --cached`로 확인하고, 체크아웃된 코드의 전체 검증은 기존 CI와 함께 사용합니다.
- 로컬 Git 훅은 `--no-verify`로 우회할 수 있습니다. 여기서의 강제는 일반 커밋에서 자동 실행하고 실패 시 중단하는 의미입니다. 원격 필수 검사·브랜치 보호 설정까지 완료됐다는 뜻은 아닙니다.
- 사용자 요청 범위에 맞춰 GitHub remote·CI·브랜치 보호를 새로 설정하지 않습니다. 기존 Git 초기화와 CI는 유지합니다.

## 개발 루프

1. 관련 PRD·TSD·데이터 설계와 `TC-###`를 읽습니다. 칸반 상태 변경의 TC-037~044는 [KANBAN_API_CHANGES.md](KANBAN_API_CHANGES.md)를 읽습니다. 프론트 작업은 별도 저장소의 `docs/plan.md`와 `FE-###`도 읽습니다.
2. 작은 동작 하나와 기대 결과를 정하고, 실제 동작 또는 오류를 확인하는 테스트로 표현합니다.
3. 필요한 코드만 구현한 뒤 전체 검증을 실행합니다.
4. 실패하면 해당 단계의 원인을 고칩니다. lint·포맷 수정은 직접 검토 가능한 별도 동작으로 수행합니다.

   ```console
   uv run --locked ruff check --fix .
   uv run --locked ruff format .
   ```

5. 최종 diff에서 요구사항 추적·실패 경로·부작용을 확인하고, 최종 변경 후 전체 검증을 다시 실행합니다.
6. 커밋 대상 diff를 확인한 뒤 커밋합니다. 완료 보고에는 통과·실패·건너뜀·수동 테스트 미실행을 구분합니다.

프론트 수동 시나리오는 사용자가 브라우저에서 직접 실행할 항목입니다.
백엔드 자동 검사 통과만으로 해당 시나리오까지 통과했다고 표시하지 않습니다.

## 하네스 자체의 회귀 검증

`tests/test_quality_gate.py`는 임시 Git 저장소에 실제 pre-commit 훅을 설치해
커밋 성공·실패를 확인합니다. 각 도구의 성공·실패는 임시 `uv` 대역으로 제어해
pytest가 자신을 다시 실행하지 않게 합니다. 실제 린터·타입 검사·앱 테스트는
위 전체 검증에서 별도로 실행합니다. 사용자 저장소의 커밋이나 스테이징은 변경하지 않습니다.

| ID | 기대 결과 |
| --- | --- |
| QG-001 | lint·format·mypy·pytest 중 하나라도 실패하면 실제 커밋이 만들어지지 않음 |
| QG-002 | 앱은 있지만 테스트 파일이 없으면 커밋 실패 |
| QG-003 | 모든 검사 성공 시 임시 저장소의 커밋 성공 |
| QG-004 | 스테이징된 오류를 작업 트리에서만 고쳐도 커밋 실패, 검사 뒤 index·작업 트리 내용 보존 |

## 선택 근거

2026-10-25에 공식 문서와 도구 관리자의 공개 논의를 확인했습니다.

- [pre-commit의 스테이징 처리](https://pre-commit.com/#pre-commit): 직접 stash 로직을 만들지 않고 기존 프레임워크를 사용합니다.
- [pre-commit 실행 언어](https://pre-commit.com/#unsupported): 4.4 이상에서 `language: unsupported`로 현재 환경의 검증 명령을 실행합니다.
- [uv 잠금 파일 검사](https://docs.astral.sh/uv/concepts/projects/sync/): 최신성 검사를 생략하는 `--frozen` 대신 불일치를 실패시키는 `--locked`를 사용합니다.
- [Ruff 규칙 선택](https://docs.astral.sh/ruff/linter/#rule-selection), [관리자의 커뮤니티 설명](https://github.com/astral-sh/ruff/discussions/10753): 규칙 전체 선택보다 프로젝트에 맞는 명시적 선택을 유지합니다.
- [Git pre-commit 훅](https://git-scm.com/docs/githooks#_pre_commit), [pytest 종료 코드](https://docs.pytest.org/en/stable/reference/exit-codes.html): 실패 종료 코드를 커밋 차단으로 연결합니다.
