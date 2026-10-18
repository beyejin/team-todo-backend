# 팀 Todo

팀 Todo는 로컬 FastAPI 서버와 `ttodo` 명령줄 도구로 할 일을 관리하는 프로젝트입니다. 할 일을 만들고, 조건에 따라 찾고, 수정하고, 삭제하거나 복구할 수 있습니다.

## 준비

- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)

프로젝트 루트에서 의존성을 설치합니다.

```console
uv sync
```

## 서버 실행

```console
uv run uvicorn app.main:app --reload
```

기본 API 주소는 `http://127.0.0.1:8000`입니다. API 문서는 `http://127.0.0.1:8000/docs`에서 볼 수 있습니다. 기본 SQLite 파일은 `data/todo.db`입니다.

## Cloudflare Python Worker

Worker용 소스는 `scripts/build_worker.py`가 기존 `app/`을 `.worker-build/` 아래에 복사해 준비합니다. Python Workers 도구에는 uv 0.12.3 이상이 필요하므로, 별도 도구 환경에서 실행합니다.

```console
uv sync
uv run python scripts/build_worker.py
uvx --from "uv>=0.12.3" uv run pywrangler dev
```

배포 환경에는 `TTODO_API_TOKEN`이 필요합니다. 기본 Todo API는 PostgreSQL 접속 문자열 `DATABASE_URL`을 사용하고, 공유 칸반 API는 아래의 별도 연결 설정을 사용합니다. Worker는 필수 설정이 없으면 해당 업무 API에 `503`을 반환하며 SQLite로 전환하지 않습니다. DB 스키마는 Worker 밖에서 미리 적용해야 합니다. Todo의 첫 스키마는 `migrations/postgres/001_initial.sql`을 사용합니다. 실제 Worker 배포는 아직 완료되지 않았습니다.

### 기존 Supabase 공유 보드 연결

기존 보드와 데이터를 보존하며 다음 SQL을 순서대로 적용합니다.

1. `migrations/supabase/000_create_worker_role.sql`: 새 서버 전용 계정과 무작위 자격 증명을 생성합니다. 기존 DB 관리자 비밀번호는 변경하지 않습니다. 반환된 비밀번호와 API 토큰을 Git이나 쿼리 결과 파일에 저장하지 마세요.
2. `migrations/supabase/001_worker_access.sql`: 기존 14개 테이블의 RLS를 켜고, 서버 계정에 칸반 API에 필요한 읽기와 쓰기만 허용합니다. 익명 Data API 접근은 차단됩니다. 테이블과 기존 행을 삭제하거나 초기화하지 않습니다.

Worker에는 `TTODO_API_TOKEN`, `KANBAN_DATABASE_URL`을 비밀값으로 설정하고, `KANBAN_BOARD_ID`, `KANBAN_ACTOR_PROFILE_ID`를 기존 보드와 멤버 UUID로 설정합니다. Session Pooler 접속 시 사용자명은 `ttodo_worker.<project-ref>`이며, Connect 화면의 호스트와 포트 및 TLS 설정을 사용합니다. 공유 칸반 API만 사용할 때는 `DATABASE_URL`이 필요하지 않습니다.

## CLI 사용

서버를 실행한 터미널은 그대로 두고, 새 터미널을 프로젝트 루트에서 엽니다. 별도 전역 설치 없이 `uvx`로 실행할 수 있습니다.

```console
uvx --from ./cli ttodo --help
uvx --from ./cli ttodo create --title "주간 보고서 작성" --assignee "Jin" --tag "업무"
uvx --from ./cli ttodo list --status assigned --tag "업무"
```

공유 Supabase 칸반 보드에 작업을 저장하거나 목록을 보려면 `kanban` 명령을 사용합니다. 이 API는 기존 `issues`, `board_items`, `issue_assignees`, `issue_labels` 관계를 사용합니다.

```console
uvx --from ./cli ttodo kanban create --title "데모 리뷰" --assignee han-yejin --label Testing
uvx --from ./cli ttodo kanban list
uvx --from ./cli ttodo kanban get <작업-UUID>
```

공유 서버에는 `TTODO_BASE_URL`과 `TTODO_API_TOKEN`을 설정해야 합니다. 서버는 `KANBAN_DATABASE_URL`, `KANBAN_BOARD_ID`, `KANBAN_ACTOR_PROFILE_ID`를 별도 환경 설정으로 사용합니다. 데이터베이스 비밀번호와 토큰은 명령 인수나 저장소에 넣지 않습니다. 현재 공유 서버 배포와 원격 보드 초기 데이터 설정은 완료되지 않아, 설정된 서버에서만 이 명령을 사용할 수 있습니다.

자주 쓰는 명령은 다음과 같습니다.

```console
# 상세 조회
uvx --from ./cli ttodo get 1

# 일부 필드 수정
uvx --from ./cli ttodo update 1 --status in_progress --priority high

# 설명과 담당자 비우기
uvx --from ./cli ttodo update 1 --clear-description --clear-assignees

# 삭제된 할 일 확인 및 복구
uvx --from ./cli ttodo deleted
uvx --from ./cli ttodo restore 1

# 할 일을 기본 목록에서 숨기기
uvx --from ./cli ttodo delete 1
```

삭제는 소프트 삭제입니다. 항목을 기본 목록에서 숨기며 `deleted`로 확인한 뒤 `restore`로 복구할 수 있습니다.

각 명령의 입력과 예시는 `ttodo <명령> --help`에서 확인합니다. 성공 결과를 프로그램에서 처리하려면 전역 `--json` 옵션을 명령 앞에 지정합니다.

```console
uvx --from ./cli ttodo --json list --limit 10
uvx --from ./cli ttodo --json get 1
```

기본 서버 대신 다른 주소를 사용하려면 `--base-url` 또는 `TTODO_BASE_URL`을 지정합니다. 명령행 옵션이 환경 변수보다 우선합니다.

```console
uvx --from ./cli ttodo --base-url http://127.0.0.1:9000 list
```

서버에 `TTODO_API_TOKEN`이 설정된 경우 CLI에서도 같은 값을 환경 변수로 설정합니다. 토큰을 셸 명령에 직접 적지 마세요.

```console
export TTODO_API_TOKEN="팀에서 안전하게 전달한 토큰"
uvx --from ./cli ttodo list
```

## 개발과 검증

CLI 의존성을 설치하고 테스트를 실행합니다.

```console
uv sync --project cli
uv run --project cli pytest
```

백엔드와 CLI의 lint, 포맷, 타입 및 테스트를 함께 확인합니다.

```console
bash scripts/verify.sh
```

## 동작 범위

기본 서버는 로컬 SQLite로 실행됩니다. 공유 보드 명령은 별도 보드 DB 설정이 완료된 서버에서 사용합니다. 세부 요구사항과 API 계약은 [`docs/PRD.md`](docs/PRD.md), [`docs/TSD.md`](docs/TSD.md), [`docs/PRD_CLI.md`](docs/PRD_CLI.md), [`docs/TSD_CLI.md`](docs/TSD_CLI.md)를 참고합니다.
