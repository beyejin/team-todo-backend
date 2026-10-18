# ttodo CLI 기술 설계

## 목적과 계약 원본

이 문서는 `PRD_CLI.md`에 정의된 `ttodo`의 구현과 API 연결 방식을 설명합니다. 백엔드가 제공하는 `/openapi.json`이 API 계약의 원본입니다. `cli/openapi.json`은 생성 코드와 테스트에서 사용하는 저장된 명세이며, CLI 실행 중에는 서버에서 명세를 내려받지 않습니다.

## 기술 구성

- Python 3.13
- Typer 명령 계층
- `openapi-python-client`가 생성한 동기 Python 클라이언트
- `httpx` 기반 요청, `attrs` 기반 생성 모델
- `uv` 패키지 관리와 `uvx` 실행

실행 패키지는 `cli/pyproject.toml`에 정의되어 있습니다. `ttodo` 실행 진입점은 `ttodo.cli:main`이며 생성 클라이언트도 패키지에 포함됩니다.

## API 연결 표

| CLI 명령 | HTTP 요청 | 동작 |
|---|---|---|
| `create` | `POST /api/v1/tasks` | 필드 옵션으로 할 일을 생성합니다. |
| `list` | `GET /api/v1/tasks` | 필터와 페이지 값을 적용해 조회합니다. |
| `get <task_id>` | `GET /api/v1/tasks/{task_id}` | 활성 할 일 하나를 조회합니다. |
| `update <task_id>` | `PATCH /api/v1/tasks/{task_id}` | 지정한 필드만 수정합니다. |
| `delete <task_id>` | `DELETE /api/v1/tasks/{task_id}` | 소프트 삭제합니다. |
| `deleted` | `GET /api/v1/tasks/deleted` | 삭제된 할 일을 조회합니다. |
| `restore <task_id>` | `POST /api/v1/tasks/{task_id}/restore` | 삭제된 할 일을 복구합니다. |
| `kanban create` | `POST /api/v1/kanban/tasks` | 기존 공유 보드에 작업을 만들고 칼럼에 놓습니다. |
| `kanban list` | `GET /api/v1/kanban/tasks` | 기존 공유 보드에 놓인 작업을 조회합니다. |
| `kanban get <task_id>` | `GET /api/v1/kanban/tasks/{task_id}` | 공유 보드의 작업 상세를 조회합니다. |

현재 명세의 업무 operation ID는 `create_task_api_v1_tasks_post`, `get_tasks_api_v1_tasks_get`, `get_task_detail_api_v1_tasks__task_id__get`, `update_task_api_v1_tasks__task_id__patch`, `delete_task_api_v1_tasks__task_id__delete`, `get_deleted_tasks_api_v1_tasks_deleted_get`, `restore_task_api_v1_tasks__task_id__restore_post`입니다. 테스트는 이 operation 집합과 입력 parameter를 CLI 인수에 대조합니다.

## 명령 입력

### 생성과 수정

- 필드 옵션은 `--title`, `--description`, `--status`, `--priority`, `--due-at`입니다.
- `--assignee`, `--tag`, `--label`은 반복 지정할 수 있습니다. API 본문에는 각각 `assignees`, `tags`, `labels` 배열로 전달합니다.
- 상태는 `assigned`, `in_progress`, `completed`; 우선순위는 `low`, `medium`, `high`를 사용합니다.
- 마감일은 시간대를 포함한 ISO 8601 날짜와 시각이어야 합니다.
- 생성 시 제목이 필요합니다. 상태와 우선순위를 생략하면 서버 기본값을 사용합니다.
- 수정에서는 전달한 필드만 보냅니다. 배열 옵션은 전달한 전체 목록으로 교체합니다.
- `--clear-description`, `--clear-due-at`은 `null`을 보내고, `--clear-assignees`, `--clear-tags`, `--clear-labels`는 빈 배열을 보냅니다. 같은 필드의 값 옵션과 clear 옵션은 함께 쓸 수 없습니다.
- 수정할 필드를 하나도 지정하지 않으면 요청하지 않고 오류를 반환합니다.

OpenAPI의 `TaskPatch`에는 `title`, `status`, `priority`가 nullable로 표현되어 있지만 백엔드는 이 필드의 `null`을 거부합니다. CLI는 해당 값을 허용하지 않습니다. 설명과 마감일은 clear 옵션으로 비우며, 배열은 빈 배열로 비웁니다.

### 목록

| API parameter | CLI 옵션 | 값 |
|---|---|---|
| `status` | 반복 가능한 `--status` | `assigned`, `in_progress`, `completed` |
| `assignee` | `--assignee` | 담당자 이름 |
| `priority` | `--priority` | `low`, `medium`, `high` |
| `due_from`, `due_to` | `--due-from`, `--due-to` | 시간대가 포함된 ISO 8601 값 |
| `tag`, `label` | `--tag`, `--label` | 문자열 |
| `include_completed` | `--include-completed` 또는 `--exclude-completed` | 기본값 `true` |
| `limit` | `--limit` | 1부터 100까지, 기본값 20 |
| `offset` | `--offset` | 0 이상, 기본값 0 |

`deleted`는 `--limit`과 `--offset`을 지원합니다.

## 주소와 요청 동작

- 기본 API 주소는 `http://127.0.0.1:8000`입니다.
- 주소는 `--base-url`, `TTODO_BASE_URL`, 기본 주소 순으로 선택합니다.
- `TTODO_API_TOKEN`이 설정되면 모든 API 요청에 `Authorization: Bearer <token>` 헤더를 추가합니다. 토큰을 설정하지 않으면 인증 헤더를 보내지 않습니다.
- `kanban` 명령은 `/api/v1/kanban/tasks` API를 통해 설정된 보드만 다룹니다. 생성에서 지원하는 필드는 제목, 설명, 상태, 팀 멤버 GitHub 사용자명, 라벨입니다. 기본 `create` 명령의 태그·우선순위·마감일은 현재 칸반 스키마에 쓰지 않습니다.
- 주소 끝의 `/`를 제거하며, 끝에 `/api/v1`이 있으면 한 번만 적용되도록 정규화합니다.
- HTTP와 HTTPS 주소만 허용합니다.
- 요청 timeout은 5초이며 자동 재시도는 하지 않습니다.

## 출력과 오류

- 기본 성공 출력은 사람이 읽기 쉬운 텍스트입니다. 목록이 비어 있으면 결과가 없다고 표시합니다.
- `--json` 성공 출력은 API 응답 본문을 JSON으로 출력하고 응답 구조를 바꾸지 않습니다.
- API 오류에는 HTTP 상태 코드와 `detail`을 표시합니다. 연결 실패는 서버 주소와 실행 여부를 확인하도록 안내합니다.
- 오류는 표준 오류에 출력하고 0이 아닌 종료 코드로 끝냅니다. traceback은 기본 출력에 노출하지 않습니다.
- API는 OpenAPI에 정의된 `422` 외에도 일부 필터 오류에 `400`, 없는 항목이나 상태가 맞지 않는 항목에 `404`를 반환할 수 있습니다. CLI는 이 응답도 처리합니다.

## OpenAPI 갱신과 검증

백엔드를 실행한 뒤 프로젝트 루트에서 다음 명령으로 저장된 명세와 생성 클라이언트를 갱신합니다.

```console
uv run --project cli python cli/scripts/generate_client.py
```

갱신 후에는 `cli/tests/test_openapi_coverage.py`에서 operation 및 입력 parameter 매핑을 확인하고, `cli/tests/` 테스트, Ruff, strict mypy, 패키지 빌드를 실행합니다. 전체 저장소 검증은 다음 명령으로 수행합니다.

```console
bash scripts/verify.sh
```

로컬 패키지 실행은 다음 명령으로 확인합니다.

```console
uvx --from ./cli ttodo --help
```

## 패키지 구조

```text
cli/src/ttodo/
  cli.py       # 명령, 입력 검증, API 요청과 종료 코드
  output.py    # 텍스트와 JSON 출력
  generated/   # OpenAPI에서 생성한 API 클라이언트와 모델
```

## 운영 한계

`TTODO_API_TOKEN`은 단일 공유 토큰이며 팀원별 권한이나 계정 인증을 제공하지 않습니다. 서버와 CLI에 같은 값을 안전하게 설정해야 합니다. 공개 배포에서는 토큰과 데이터베이스 자격 증명을 Worker 비밀값으로 보관하고, 토큰을 Git 저장소나 명령 인수에 넣지 않습니다.
