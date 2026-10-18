# ttodo CLI 테스트 케이스

## 공통 기준

- API 계약의 원본은 실행 중인 백엔드 `/openapi.json`이며, 테스트는 `cli/openapi.json` 저장본을 사용한다. 명세를 갱신하면 CLI operation 매핑과 테스트도 함께 확인한다.
- CLI 통합 테스트는 HTTP 요청 method, 경로, query 값, JSON 본문을 검사하고 격리된 테스트 API 또는 테스트용 앱에 연결한다.
- 네트워크 모킹 테스트는 성공 및 오류 출력과 종료 코드를 확인한다. 별도 테스트 API를 사용할 수 없으면 운영 DB나 사용자 데이터에 요청하지 않는다.
- 성공 종료 코드는 `0`, CLI 입력 오류, 연결 오류, API 오류는 `0`이 아닌 코드다.
- 기본 성공 출력은 사람이 읽기 쉬운 텍스트다. `--json` 성공 출력은 표준 출력에 유효한 JSON만 쓴다. 오류는 표준 오류로 보낸다.
- 모든 명령, 인수, 옵션 도움말은 비개발자가 이해할 수 있는 쉬운 영어여야 한다.
- 각 케이스는 `cli/tests/`에 실제로 관찰할 수 있는 동작으로 작성한다.

## OpenAPI와 CLI 범위 완전성

- [ ] **TC-CLI-001 OpenAPI 업무 operation 전체 매핑**
  - 입력: 백엔드 OpenAPI fixture의 업무 operation 목록
  - 기대 결과: operation ID 7개(`create_task_api_v1_tasks_post`, `get_tasks_api_v1_tasks_get`, `get_task_detail_api_v1_tasks__task_id__get`, `update_task_api_v1_tasks__task_id__patch`, `delete_task_api_v1_tasks__task_id__delete`, `get_deleted_tasks_api_v1_tasks_deleted_get`, `restore_task_api_v1_tasks__task_id__restore_post`)가 각각 `create`, `list`, `get`, `update`, `delete`, `deleted`, `restore`에 매핑된다.
  - CLI 매핑이 없는 operation이 추가되면 테스트가 실패합니다.

- [ ] **TC-CLI-002 모든 OpenAPI 입력 parameter가 노출됨**
  - 입력: path, query, body parameter 목록을 명세 fixture와 대조
  - 기대 결과: `task_id`, 생성, 수정 필드, 목록 필터와 페이지 값이 CLI 인수와 옵션에 연결된다. 새 parameter에 매핑이 없으면 실패한다.

- [ ] **TC-CLI-003 명세 및 실제 성공, 오류 응답 처리 커버리지**
  - 입력: OpenAPI의 성공 및 `422` 응답과 구현이 실제 반환하는 `400`, `404` 응답
  - 기대 결과: 성공 결과는 텍스트/JSON으로 출력되고 모든 API 오류는 설명과 0이 아닌 종료 코드가 된다. OpenAPI에 선언되지 않은 실제 `400`, `404`도 처리한다.

- [ ] **TC-CLI-043 요청, 응답 모델을 live OpenAPI와 대조**
  - 입력: 실행 서버에서 새로 가져온 `/openapi.json`
  - 기대 결과: OpenAPI 3.1.0의 `TaskInput` 필드와 필수 title, `TaskPatch` partial 필드, 목록 query parameter와 기본값이 fixture와 CLI 인수에 일치한다. 명세가 바뀌어 대응 테스트가 없으면 실패한다.

- [ ] **TC-CLI-044 OpenAPI nullable 표기와 실제 입력 검증 차이**
  - 입력: `PATCH`의 title/status/priority에 null 지정; description/due_at에 null 지정
  - 기대 결과: 앞 세 필드는 API가 거부하는 동작을 CLI에서 허용하지 않는다. description/due_at null은 clear 동작으로 보낸다. 배열 clear는 빈 배열로 보낸다.

## 시작과 도움말

- [ ] **TC-CLI-004 루트 도움말은 쉬운 영어로 명령을 설명함**
  - 실행: `ttodo --help`
  - 기대 결과: 도구 목적, 사용법, 모든 명령, 기본 서버 주소, `--base-url`, `--json`, 시작 예시를 읽기 쉬운 영어로 보여준다.

- [ ] **TC-CLI-005 각 명령 도움말은 입력, 결과, 예시를 설명함**
  - 실행: 각 명령에 `--help` 지정
  - 기대 결과: 목적, 필수 입력, 선택 입력, 기본 동작, 실행 가능한 예시, 흔한 오류 설명이 쉬운 영어로 표시된다.

- [ ] **TC-CLI-006 각 argument와 option에 설명이 있음**
  - 실행: 루트와 명령 도움말 전체 검사
  - 기대 결과: 필드 의미, 허용 값, 반복 입력 여부, 생략 시 동작이 설명되고 미설명 옵션이 없다.

- [ ] **TC-CLI-007 도움말 실행은 서버 연결을 요구하지 않음**
  - 실행: API 서버가 꺼진 상태에서 루트와 하위 명령 도움말 실행
  - 기대 결과: 성공하고 도움말만 출력한다.

## 설정과 공통 출력

- [ ] **TC-CLI-008 기본 주소 사용**
  - 준비: 명령행 주소와 환경 변수를 지정하지 않음
  - 기대 결과: `http://127.0.0.1:8000`으로 요청한다.

- [ ] **TC-CLI-009 명령행 주소가 환경 변수보다 우선함**
  - 준비: `TTODO_BASE_URL`과 `--base-url`에 서로 다른 주소
  - 기대 결과: `--base-url` 값으로 요청한다.

- [ ] **TC-CLI-010 환경 변수 주소 사용**
  - 준비: `TTODO_BASE_URL`만 지정
  - 기대 결과: 해당 주소로 요청한다.

- [ ] **TC-CLI-011 trailing slash 정규화**
  - 준비: 주소 끝에 `/` 포함
  - 기대 결과: API 경로가 중복 slash 없이 한 번만 붙는다.

- [ ] **TC-CLI-012 공통 JSON 옵션**
  - 실행: 각 명령 성공 응답에 `--json`을 적용
  - 기대 결과: 유효한 JSON이 표준 출력으로 출력되고 envelope와 배열을 임의로 바꾸지 않는다.

- [ ] **TC-CLI-013 기본 텍스트 출력**
  - 실행: 각 명령을 `--json` 없이 실행
  - 기대 결과: 핵심 필드를 읽기 쉬운 text로 표시하며 원시 JSON을 덤프하지 않는다.

- [ ] **TC-CLI-014 연결 실패 설명**
  - 준비: API 서버가 응답하지 않음
  - 기대 결과: 서버 주소와 서버 실행 확인 방법을 안내하고 0이 아닌 종료, traceback 없이 종료한다.

- [ ] **TC-CLI-015 API 오류 출력과 종료 코드**
  - 준비: 서버가 400, 404, 422, 500 및 detail 응답
  - 기대 결과: 상태 코드와 detail을 짧게 표시하고 0이 아닌 종료한다. 내부 traceback은 숨긴다.

- [ ] **TC-CLI-016 JSON 모드 오류 스트림 분리**
  - 준비: `--json`으로 API 오류 호출
  - 기대 결과: 오류 문구는 stderr에 출력하고 stdout에 성공 JSON이나 오류 메시지를 섞지 않는다.

## 생성: `POST /api/v1/tasks`

- [ ] **TC-CLI-017 제목만으로 생성**
  - 실행: `ttodo create --title "Write the report"`
  - 기대 결과: `POST /api/v1/tasks`, body `{"title":"Write the report"}`로 요청하고 생성 리소스를 출력한다.

- [ ] **TC-CLI-018 선택 필드와 반복 배열 전달**
  - 실행: 설명, 상태, 우선순위, 시간대 포함 마감일, 반복 담당자, 태그, 라벨 지정
  - 기대 결과: 해당 필드가 정확한 JSON 타입과 API 이름으로 body에 포함된다.

- [ ] **TC-CLI-019 제목 누락 또는 공백 제목 거부**
  - 실행: 제목 없이 실행하거나 공백 문자열 사용
  - 기대 결과: API를 호출하지 않고 쉬운 영어 입력 도움말 및 0이 아닌 종료를 반환한다.

- [ ] **TC-CLI-020 허용되지 않은 상태, 우선순위, 날짜 거부**
  - 실행: 잘못된 enum 또는 timezone 없는 날짜 지정
  - 기대 결과: API 요청 전에 오류를 알려준다.

- [ ] **TC-CLI-021 생성 API 오류 전달**
  - 준비: 생성 API가 422 반환
  - 기대 결과: 사용자 입력 오류로 안내하고 0이 아닌 종료한다.

## 목록: `GET /api/v1/tasks`

- [ ] **TC-CLI-022 기본 목록과 페이지 값**
  - 실행: `ttodo list`
  - 기대 결과: `GET /api/v1/tasks?limit=20&offset=0`; items와 total을 표시한다.

- [ ] **TC-CLI-023 모든 목록 필터 전달**
  - 실행: 상태 반복 지정, 담당자, 우선순위, 마감일 범위, 태그, 라벨, 완료 포함 여부 지정
  - 기대 결과: 모든 query parameter 이름과 값을 명세대로 전달하고 복수 상태는 반복 query parameter로 보낸다.

- [ ] **TC-CLI-024 목록 페이지 크기 및 offset 경계**
  - 실행: limit 1, 100 및 offset 0, 양수; limit 0/101 또는 음수 offset
  - 기대 결과: 유효 값은 전달하고 범위 밖 값은 API 호출 전에 거부한다.

- [ ] **TC-CLI-025 유효하지 않은 목록 필터 오류**
  - 준비: API가 상태 또는 우선순위 필터 오류 400을 반환
  - 기대 결과: 필터 오류 detail과 0이 아닌 종료 코드를 표시한다.

- [ ] **TC-CLI-026 빈 목록 표시**
  - 준비: `items: []`, `total: 0`
  - 기대 결과: 텍스트 출력은 결과가 없음을 안내하고, JSON은 원래 목록 구조를 보존한다.

## 상세: `GET /api/v1/tasks/{task_id}`

- [ ] **TC-CLI-027 활성 할 일 상세 조회**
  - 실행: `ttodo get 12`
  - 기대 결과: `GET /api/v1/tasks/12` 호출, 상세 필드 출력.

- [ ] **TC-CLI-028 존재하지 않거나 삭제된 할 일 조회 실패**
  - 준비: API 404 응답
  - 기대 결과: 찾지 못했음을 안내하고 0이 아닌 종료한다.

## 수정: `PATCH /api/v1/tasks/{task_id}`

- [ ] **TC-CLI-029 수정은 전달한 필드만 보냄**
  - 실행: `ttodo update 12 --title "New title"`
  - 기대 결과: PATCH body에 title만 포함되어 나머지 필드는 유지된다.

- [ ] **TC-CLI-030 수정 배열은 전달한 목록으로 교체**
  - 실행: 반복 담당자, 태그, 라벨을 지정
  - 기대 결과: 배열 전체가 PATCH body에 들어가고 API에서 교체된다.

- [ ] **TC-CLI-031 선택 필드와 배열 비우기**
  - 실행: 각 `--clear-*` 옵션 사용
  - 기대 결과: nullable field는 JSON `null`, 배열은 빈 배열로 전달한다.

- [ ] **TC-CLI-032 값 옵션과 clear 옵션 충돌**
  - 실행: 같은 필드의 값과 `--clear-*`를 동시에 지정
  - 기대 결과: API 호출 없이 명확한 입력 오류로 종료한다.

- [ ] **TC-CLI-033 잘못된 값 또는 없는 ID 수정 실패**
  - 준비: API가 422 또는 404 반환
  - 기대 결과: detail과 0이 아닌 종료를 표시한다.

## 삭제: `DELETE /api/v1/tasks/{task_id}`

- [ ] **TC-CLI-034 소프트 삭제 실행**
  - 실행: `ttodo delete 12`
  - 기대 결과: `DELETE /api/v1/tasks/12`를 호출하고 삭제 결과를 표시한다. 도움말에서 삭제는 항목을 기본 목록에서 숨기며 복구 명령으로 되돌릴 수 있다고 설명한다.

- [ ] **TC-CLI-035 없는 항목 또는 중복 삭제 실패**
  - 준비: API가 404 반환
  - 기대 결과: 찾을 수 없거나 이미 삭제된 항목으로 안내하고 0이 아닌 종료한다.

## 삭제 목록: `GET /api/v1/tasks/deleted`

- [ ] **TC-CLI-036 삭제 항목 목록과 페이지 값 조회**
  - 실행: `ttodo deleted --limit 10 --offset 20`
  - 기대 결과: `GET /api/v1/tasks/deleted?limit=10&offset=20`; items와 페이지 정보를 출력한다.

- [ ] **TC-CLI-037 삭제 목록 페이지네이션 오류**
  - 준비: 잘못된 페이지 값 또는 API 422 응답
  - 기대 결과: 오류를 설명하고 0이 아닌 종료한다.

## 복구: `POST /api/v1/tasks/{task_id}/restore`

- [ ] **TC-CLI-038 삭제 항목 복구**
  - 실행: `ttodo restore 12`
  - 기대 결과: `POST /api/v1/tasks/12/restore` 호출, 복구 리소스를 출력한다.

- [ ] **TC-CLI-039 활성 항목 또는 없는 ID 복구 실패**
  - 준비: API가 404 반환
  - 기대 결과: 삭제 상태인 항목만 복구 가능하다고 설명하고 0이 아닌 종료한다.

## 패키지와 운영체제

- [ ] **TC-CLI-040 uvx 로컬 패키지 실행**
  - 실행: `uvx --from <local-project> ttodo --help`
  - 기대 결과: 격리 환경에서 실행되고 프로젝트의 현재 Python 환경에 설치를 요구하지 않는다.

- [ ] **TC-CLI-041 macOS, Linux, Windows 설치와 도움말 스모크 테스트**
  - 실행: Python 3.13에서 패키지 설치 및 루트/하위 도움말 호출
  - 기대 결과: 세 운영체제에서 모두 종료 코드 0, Unicode 및 쉬운 영어 도움말이 정상 표시된다.

- [ ] **TC-CLI-042 프로젝트 검증**
  - 실행: `bash scripts/verify.sh` (Windows 개발 환경은 동등한 Ruff, mypy, pytest 명령 실행)
  - 기대 결과: lint, format, 타입 검사, CLI 테스트가 모두 통과한다.

- [ ] **TC-CLI-043 공유 서버 API 토큰 전달**
  - 준비: `TTODO_API_TOKEN` 환경 변수 지정
  - 실행: `ttodo list`
  - 기대 결과: `Authorization: Bearer <token>` 헤더가 전달되고, 토큰 문자열은 stdout/stderr에 표시하지 않는다.

- [ ] **TC-CLI-044 기존 칸반 보드에 작업 생성 및 목록 조회**
  - 실행: `ttodo kanban create --title "Review the demo"` 및 `ttodo kanban list`
  - 기대 결과: 각각 `POST /api/v1/kanban/tasks`, `GET /api/v1/kanban/tasks`를 호출하고 보드 작업 번호, 칼럼 상태, 팀 멤버, 라벨을 보여준다.
