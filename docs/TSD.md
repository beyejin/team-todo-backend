# 팀 Todo 백엔드 기술 설계

## 문서 목적과 기준

이 문서는 `PRD.md`의 기능을 제공하는 현재 백엔드의 기술 구성과 API 동작을 설명합니다. 실행 중인 앱의 `/openapi.json`이 API 경로와 요청 형식의 기준이며, 데이터 구조와 저장 규칙은 `database.md`를 따릅니다.

## 기술 구성

- Python 3.13과 `uv`
- FastAPI와 Pydantic
- SQLite와 Python 표준 `sqlite3`
- `pg8000`을 통한 PostgreSQL 연결
- FastAPI가 생성하는 OpenAPI 문서와 Swagger UI

의존성은 루트 `pyproject.toml`에 선언하고 `uv.lock`으로 고정합니다. DB 변경은 `migrations/`의 버전 SQL 파일로 관리합니다.

## 실행과 파일 구조

프로젝트 루트에서 의존성을 설치하고 서버를 실행합니다.

```console
uv sync
uv run uvicorn app.main:app --reload
```

서버는 기본적으로 `http://127.0.0.1:8000`에서 실행합니다. API 문서는 `/docs`, OpenAPI 문서는 `/openapi.json`에서 확인할 수 있습니다.

- `app/main.py`: FastAPI 앱, 요청 모델, 경로 처리와 SQL 호출
- `app/db.py`: SQLite 연결과 마이그레이션 적용
- `app/kanban.py`: 기존 Supabase 칸반 보드 작업 생성 및 조회
- `scripts/build_worker.py`, `wrangler.jsonc`: Cloudflare Python Worker 소스 준비와 실행 설정
- `migrations/`: 버전별 스키마 변경
- `tests/`: API 동작 테스트

## API 공통 규칙

- 업무 API 기본 경로는 `/api/v1`입니다.
- 요청과 응답의 JSON 필드는 `snake_case`를 사용합니다.
- 날짜와 시각은 시간대가 포함된 ISO 8601 형식으로 전달하고 UTC로 저장합니다.
- 목록 응답은 `items`, `total`, `limit`, `offset`을 포함합니다. 기본 `limit`은 20, 허용 범위는 1부터 100까지이며 `offset` 기본값은 0입니다.
- 생성 성공은 `201`, 조회와 변경 성공은 `200`을 반환합니다.

## 업무 API

| Method | 경로 | 동작 |
|---|---|---|
| `POST` | `/api/v1/tasks` | 할 일을 생성합니다. |
| `GET` | `/api/v1/tasks` | 활성 할 일을 필터링해 조회합니다. |
| `GET` | `/api/v1/tasks/{task_id}` | 활성 할 일 하나를 조회합니다. |
| `PATCH` | `/api/v1/tasks/{task_id}` | 전달한 필드만 수정합니다. |
| `DELETE` | `/api/v1/tasks/{task_id}` | 할 일을 소프트 삭제합니다. |
| `GET` | `/api/v1/tasks/deleted` | 삭제된 할 일을 조회합니다. |
| `POST` | `/api/v1/tasks/{task_id}/restore` | 삭제된 할 일을 복구합니다. |
| `POST` | `/api/v1/kanban/tasks` | 기존 공유 보드에 작업을 만들고 배치합니다. |
| `GET` | `/api/v1/kanban/tasks` | 공유 보드 작업을 페이지 단위로 조회합니다. |
| `GET` | `/api/v1/kanban/tasks/{task_id}` | 공유 보드 작업 상세를 조회합니다. |

`/docs`, `/redoc`, `/openapi.json`은 문서 경로이며 업무 API에 포함하지 않습니다.

## 데이터 입력과 상태

- 생성에는 공백이 아닌 `title`이 필요합니다. `description`, `due_at`, `assignees`, `tags`, `labels`는 선택 입력입니다.
- API 상태 값은 `assigned`, `in_progress`, `completed`입니다. 설명에서 각각 `할당`, `진행 중`, `완료`라고 부릅니다.
- API 우선순위 값은 `low`, `medium`, `high`입니다. 설명에서 각각 `낮음`, `보통`, `높음`이라고 부릅니다.
- 생성 시 상태를 생략하면 `assigned`, 우선순위를 생략하면 `medium`을 사용합니다.
- 담당자, 태그, 라벨은 이름 문자열이며 인증된 사용자 계정과 연결하지 않습니다.
- 담당자, 태그, 라벨 값은 앞뒤 공백을 제거하고 빈 값과 중복을 저장하지 않습니다.
- 마감일은 시간대가 필요합니다. 저장 시 UTC ISO 8601 값으로 정규화합니다.

## 목록 필터와 정렬

`GET /api/v1/tasks`는 `status`를 반복 지정할 수 있고, `assignee`, `priority`, `due_from`, `due_to`, `tag`, `label`, `include_completed`, `limit`, `offset`을 지원합니다. 여러 필터를 함께 지정하면 모두 만족하는 할 일만 반환합니다. `include_completed` 기본값은 `true`입니다. 삭제된 항목은 일반 목록에서 제외합니다.

`GET /api/v1/tasks/deleted`는 `limit`과 `offset`만 받습니다. 두 목록 모두 생성 시각과 ID를 기준으로 내림차순 정렬합니다. 마감일 기준 정렬이나 정렬 방향 변경은 제공하지 않습니다.

## 수정, 삭제와 복구

- `PATCH`에서 생략한 필드는 유지합니다.
- `description`과 `due_at`은 `null`로 지울 수 있습니다.
- `assignees`, `tags`, `labels`는 전달한 배열 전체로 교체합니다. 빈 배열은 해당 목록을 비웁니다.
- `title`, `status`, `priority`는 `null`일 수 없습니다.
- 삭제는 `deleted_at`을 기록하는 소프트 삭제입니다. 연결된 담당자, 태그, 라벨은 유지합니다.
- 삭제된 항목은 상세 조회와 수정 대상이 아닙니다. 복구 경로로 복원할 수 있습니다.
- 이미 삭제된 항목을 다시 삭제하거나 활성 항목을 복구하려 하면 `404`를 반환합니다.

## 오류 응답

오류 응답은 `detail`을 포함합니다.

- `400`: 잘못된 상태, 우선순위 필터 또는 유효하지 않은 마감일 범위
- `404`: 존재하지 않거나 현재 동작에서 접근할 수 없는 항목
- `422`: 요청 본문 또는 쿼리 값 검증 실패
- `503`: Worker 설정 또는 기본 Todo 데이터베이스가 없음
- `500`: 예상하지 못한 서버 오류

## 공유 서버 토큰

`TTODO_API_TOKEN`을 설정한 로컬 서버는 `/api/` 경로에 유효한 bearer token이 없는 요청을 `401`로 거부합니다. 토큰을 설정하지 않은 로컬 개발 서버는 기존처럼 토큰 없이 사용할 수 있습니다. Worker는 설정 바인딩이 없으면 `503`, 바인딩이 있지만 요청 토큰이 없거나 다르면 `401`로 거부합니다. 토큰은 서버의 비밀값으로 관리하고 코드, 응답, 로그에 기록하지 않습니다.

## Cloudflare Python Worker

[`Cloudflare FastAPI 가이드`](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)에 따라 `scripts/build_worker.py`는 기존 로컬 `app/`을 `.worker-build/`에 복사하고 ASGI 진입점을 작성합니다. 기존 앱 경로는 그대로 유지합니다. `wrangler.jsonc`는 이 빌드 디렉터리를 Python Worker로 실행하도록 설정합니다. 로컬 Worker는 다음 명령으로 준비하고 실행합니다.

```console
uv run python scripts/build_worker.py
uvx --from "uv>=0.12.3" uv run pywrangler dev
```

Python Workers 도구는 개발 의존성으로 설치하며 uv 0.12.3 이상을 사용합니다. 위 명령은 기존 uv 설치를 변경하지 않고 별도 도구 환경에서 실행합니다.

Worker API에는 `TTODO_API_TOKEN` 비밀값과 PostgreSQL 접속 문자열 `DATABASE_URL`을 설정해야 합니다. 토큰이 없으면 `/api/` 요청은 `503`을 반환하고, DB가 없으면 유효한 토큰을 제공해도 `503`을 반환합니다. Worker는 SQLite 파일로 fallback하지 않습니다.

Worker는 로컬 `migrations/` 파일을 읽거나 자동 적용하지 않습니다. 배포 전에 PostgreSQL 스키마를 별도로 준비해야 합니다. 최초 Todo 스키마는 `migrations/postgres/001_initial.sql`을 사용합니다. `KANBAN_DATABASE_URL` 경로도 마이그레이션을 자동 적용하지 않으며, 기존 공유 보드 스키마가 준비되어 있어야 합니다.

## 기존 Supabase 칸반 보드 연결

`KANBAN_DATABASE_URL`로 지정한 PostgreSQL을 사용하며, 공유 보드 API에서는 기본 Todo 마이그레이션을 적용하지 않습니다. `KANBAN_BOARD_ID`와 `KANBAN_ACTOR_PROFILE_ID`는 대상 보드와 작성자 프로필 UUID입니다.

상태 변경은 `PATCH /api/v1/kanban/tasks/{task_id}`와 `{ "status": "in_progress" }`를 사용합니다. 상태 외 필드를 거부하며 한 트랜잭션으로 배치와 수정 시각을 갱신합니다. 같은 상태는 변경하지 않습니다. 오류·동시성·최소 권한은 [KANBAN_API_CHANGES.md](KANBAN_API_CHANGES.md)에 정의합니다.

작업은 `issues`에 저장하고 보드 칼럼 및 순서는 `board_items`에 기록합니다. 상태는 `board_items.column_id -> board_columns.workflow_status_id -> workflow_statuses.category`에서 계산합니다. 담당자는 workspace의 `profiles.github_username`으로 확인해 `issue_assignees`에 연결하고, 프로젝트 라벨과 `issue_labels`를 사용합니다. 체크리스트 테이블에는 쓰지 않습니다.

원격 RLS·역할 권한은 배포 전에 실제 프로젝트에서 다시 확인합니다. API bearer token은 Supabase Data API의 직접 접근을 막지 않습니다. 기존 `001_worker_access.sql`과 상태 이동용 `002_worker_status_update.sql`의 적용 여부를 구분하며, 로컬 검증만으로 원격 적용 완료라고 보고하지 않습니다.

오류 응답에 내부 SQL이나 로컬 파일 경로를 포함하지 않습니다.

## SQLite와 보안 한계

로컬 DB 파일은 `TODO_DB_PATH`로 지정할 수 있습니다. 지정하지 않으면 프로젝트의 `data/todo.db`를 사용합니다. 요청 처리마다 연결을 열고 닫으며, 연결할 때 미적용 마이그레이션을 확인합니다. 여러 테이블을 함께 변경하는 작업은 요청 단위 트랜잭션으로 처리합니다. Worker는 `DATABASE_URL` PostgreSQL만 사용하며 연결 시 애플리케이션 마이그레이션을 실행하지 않습니다.

계정별 로그인과 역할별 권한 검사는 제공하지 않습니다. 로컬 서버는 신뢰할 수 있는 개발 환경에서 실행하고, 공개 서버는 Worker 토큰과 데이터베이스 설정을 구성한 뒤 사용합니다.

## 완료 기준

- `/docs`에서 API 명세를 확인할 수 있습니다.
- 생성, 조회, 수정, 목록 필터, 소프트 삭제, 삭제 항목 조회와 복구가 동작합니다.
- 재시작 뒤에도 SQLite 파일의 데이터가 유지됩니다.
- 유효하지 않은 입력, 없는 ID, 삭제된 항목에 대한 응답이 위 오류 규칙을 따릅니다.
