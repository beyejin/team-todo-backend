# Vercel 배포 준비

2026-10-26 기준 [Vercel 백엔드](https://team-todo-backend-pied.vercel.app)는 Python 3.13으로 배포되어 READY 상태입니다. `DATABASE_URL`과 `KANBAN_DATABASE_URL`은 아직 설정되지 않았으며 원격 SQL도 미실행입니다. 일반 Todo와 공유 칸반은 서로 다른 저장소 계약을 유지합니다.

## Python과 진입점

- `.python-version`의 `3.13`과 `pyproject.toml`의 `>=3.13,<3.14`를 유지합니다. Vercel은 Python 3.13을 지원합니다.
- `app/main.py`가 내보내는 `app = FastAPI(...)`는 자동 인식 대상입니다. Framework Preset은 FastAPI, 프로젝트 루트는 이 저장소 루트이며 별도 Build Command, Output Directory, 엔트리포인트 래퍼, `vercel.json`은 필요하지 않습니다.
- `pyproject.toml`과 `uv.lock`으로 설치합니다. 현재 Vercel Python 빌더는 `uv sync --no-dev`를 사용하므로 `workers-py`, `workers-runtime-sdk`, 검사 도구는 배포 의존성에 포함하지 않습니다. 빌드 로그에서도 Python 3.13과 개발 의존성 제외를 확인합니다.
- `.vercelignore`는 `app/`, `pyproject.toml`, `uv.lock`, `.python-version`만 업로드하도록 제한합니다. 따라서 환경 파일, 로컬 DB, Cloudflare 산출물, 가상 환경, CLI, 문서, 테스트는 업로드 대상이 아닙니다. 배포 전에 로컬 또는 CI에서 전체 검사를 실행합니다.

근거: [FastAPI 진입점](https://vercel.com/docs/frameworks/backend/fastapi), [Python 버전·의존성](https://vercel.com/docs/functions/runtimes/python), [Vercel 빌더의 개발 의존성 제외](https://github.com/vercel/vercel/blob/17ee73663e30c0ddd91cdf5fcf134c55a0a6ea0a/packages/python/src/uv.ts), [업로드 제외 설정](https://vercel.com/docs/deployments/vercel-ignore).

## 배포 환경변수

Vercel의 **Automatically expose System Environment Variables**를 켭니다. 플랫폼이 빌드와 런타임에 제공하는 `VERCEL=1`로 배포 환경을 판별합니다. Preview와 Production의 DB·토큰은 각각 명시적으로 설정하고, Preview에서 운영 데이터를 쓰지 않습니다. [공식 시스템 환경변수](https://vercel.com/docs/environment-variables/system-environment-variables)

| 키 | 용도 |
| --- | --- |
| `TTODO_API_TOKEN` | 모든 `/api/` 요청을 보호하는 서버 비밀값. 없으면 503, 잘못된 Bearer 토큰이면 401 |
| `DATABASE_URL` | 일반 Todo 전용 PostgreSQL 연결. 없으면 일반 Todo API는 503 |
| `KANBAN_DATABASE_URL` | 기존 공유 칸반의 제한 역할 `ttodo_worker` 연결 |
| `KANBAN_BOARD_ID` | 확인된 공유 보드 UUID |
| `KANBAN_ACTOR_PROFILE_ID` | 확인된 작성자 프로필 UUID |
| `TTODO_CORS_ORIGINS` | 브라우저가 백엔드에 직접 접근할 때 허용할 정확한 Origin 목록 |

연결 문자열과 API 토큰은 Vercel의 비밀 환경변수로 설정합니다. 저장소, 브라우저 번들, `NEXT_PUBLIC_*`, 문서, 명령 인수에 넣지 않습니다. 프론트엔드 서버가 API를 대리 호출하는 경우 토큰은 프론트엔드 서버 환경에만 둡니다. 이는 사용자별 로그인·권한 관리를 제공하는 구조는 아닙니다.

Vercel과 Cloudflare Worker에서는 SQLite 대체 연결과 요청 중 자동 마이그레이션을 모두 금지합니다. `/docs`, `/openapi.json`은 DB 연결 확인을 대신하지 않습니다. 로컬 uvicorn 실행은 기존 SQLite 및 자동 마이그레이션 동작을 유지합니다.

## 일반 Todo의 원격 DB 준비 초안

현재 공유 칸반 스키마가 있다는 사실만으로 일반 Todo CRUD가 준비되지는 않습니다. 일반 Todo는 `tasks`, `task_assignees`, `task_tags`, `task_labels`를 사용합니다. 칸반의 `public.issues`, `public.labels`, `public.board_items`와 별도입니다.

실행 가능한 SQL은 [`migrations/supabase/003_todo_app.sql`](../migrations/supabase/003_todo_app.sql)에 있습니다. 관리자 연결에서 파일 전체를 한 번 실행하는 트랜잭션이며, 기존 [`001_initial.sql`](../migrations/postgres/001_initial.sql)의 일반 Todo 테이블 정의와 최소 권한·RLS 설정을 결합했습니다. **원격에는 아직 적용하지 않았습니다.**

새 `todo_app` 스키마와 새 제한 역할만 만들며, 기존 `ttodo_worker` 역할과 공유 보드 테이블은 수정하지 않습니다. 역할·스키마가 이미 존재하면 실행을 중단하므로 재실행 전에 현재 상태를 확인합니다. `SET LOCAL search_path`에 의해 일반 Todo 테이블과 인덱스는 `todo_app`에 생성됩니다.

`tasks`의 실제 DELETE, 연결 테이블의 UPDATE, 스키마 CREATE, 테이블 소유권은 런타임 역할에 주지 않습니다. 현재 IDENTITY 자동 생성과 `RETURNING id`에는 직접 sequence 권한이 필요하지 않아 sequence GRANT도 생략합니다. 소프트 삭제·복구는 UPDATE이므로 RLS에 `deleted_at IS NULL` 제한을 추가하지 않습니다. RLS는 서버 역할 경계이며 사용자별 접근 제어는 아닙니다.

초안 역할은 `NOLOGIN`입니다. 자격증명 발급·LOGIN 활성화는 별도 승인된 작업으로 처리하고 비밀번호를 이 SQL이나 저장소에 기록하지 않습니다. 새 역할의 Supabase Session Pooler 연결을 `DATABASE_URL`로 설정한 뒤 새 연결에서 `current_user`, `current_schema()`와 실제 CRUD를 확인합니다. 현재 연결 코드는 URL의 `options`를 처리하지 않으므로 `?options=...`로 search_path를 설정하려고 하지 않습니다. `todo_app`을 Supabase Data API의 노출 스키마에 추가하지 않습니다.

배포 모드에서는 자동 마이그레이션을 실행하지 않아 `schema_migrations`가 필요 없습니다. 이 제한 역할을 로컬 자동 마이그레이션 실행에 사용하지 않습니다. 공유 DB의 기존 PUBLIC 권한까지 이번 초안이 격리하는 것은 아니므로 원격 적용 전 기존 권한을 확인합니다. [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [Supabase 연결](https://supabase.com/docs/guides/database/connecting-to-postgres)

## 공유 칸반 연결

`KANBAN_DATABASE_URL`에는 기존 `ttodo_worker` 자격증명을 사용하고 일반 Todo 역할과 혼용하지 않습니다. 상태 변경에는 [`002_worker_status_update.sql`](../migrations/supabase/002_worker_status_update.sql)의 열 단위 UPDATE 권한이 필요합니다. 원격 적용 여부는 별도로 확인합니다. `001_worker_access.sql`을 무조건 재실행하면 이후 추가한 권한이 회수될 수 있으므로 기존 역할·정책을 먼저 대조합니다.

## 검증 기준과 실행 기록

| ID | 완료 조건 | 로컬 결과 |
| --- | --- | --- |
| TC-045 | Vercel 토큰 누락은 503, 누락·오류 Bearer는 401, OpenAPI는 조회 가능 | 자동 테스트 통과 |
| TC-046 | Vercel DB 누락은 503이며 SQLite 파일을 만들지 않음 | 자동 테스트 통과 |
| TC-047 | RLS·열 단위 권한만 가진 PostgreSQL 역할로 생성·조회·수정·소프트 삭제·복구; CREATE 권한 및 자동 마이그레이션 없음 | 격리 PostgreSQL 테스트 통과 |

`tests/test_deployment.py`가 위 동작을 검증합니다. TC-047은 명시적인 로컬 `TEST_DATABASE_URL`이 필요하며 원격 DB 주소를 거부합니다. 전체 검사는 `bash scripts/verify.sh`로 실행합니다. 별도 Python 3.13 환경에서 `uv sync --locked --no-dev`와 앱 import/OpenAPI 생성도 성공했고 Worker·검사 도구가 설치되지 않음을 확인했습니다.

`003_todo_app.sql` 전체 파일을 별도 임시 PostgreSQL 17.11 서버에 한 번 적용했습니다. NOLOGIN 역할과 4개 RLS 테이블, 금지 권한, 익명·공개 역할의 스키마 접근 거부를 확인했습니다. 해당 역할로 실제 API 생성·조회·수정·소프트 삭제·복구가 성공했고, 기존 칸반 fixture 행과 `ttodo_worker` 권한은 그대로였습니다. 이 임시 서버는 검증 후 제거했습니다.

실제 Vercel 검증에서는 `/openapi.json` 200, 토큰 없는 API 요청 401, 설정된 서버 토큰을 보낸 일반 Todo·공유 칸반 API의 DB 미설정 응답 503을 확인했습니다. 따라서 앱 배포와 인증 보호는 확인했으며, DB 연결·일반 Todo CRUD·공유 칸반 상태 변경·프론트엔드 연결의 운영 검증은 남아 있습니다. 로컬 DB 결과를 원격 성공으로 기록하지 않습니다.
