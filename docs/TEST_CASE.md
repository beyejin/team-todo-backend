# 백엔드 테스트 케이스

## 공통 기준

- [ ] API 기본 경로는 `/api/v1`이며 JSON 필드명은 `snake_case`를 사용한다.
- [ ] 아래 요청은 별도 표시가 없으면 `Content-Type: application/json`을 사용한다.
- [ ] 성공 응답은 리소스 또는 목록을 반환한다. 목록 응답은 `items`, `total`, `limit`, `offset`을 포함한다.
- [ ] 할 일 상태와 우선순위는 API에서 각각 `assigned`, `in_progress`, `completed`와 `low`, `medium`, `high`를 사용한다. 사용자 표시명은 각각 `할당`, `진행 중`, `완료` 및 `낮음`, `보통`, `높음`이다.
- [ ] 오류 응답은 `detail`을 포함하며 내부 SQL이나 로컬 파일 경로를 노출하지 않는다.
- [ ] TSD에서 응답 필드 전체 형태와 일부 검증 오류 코드가 확정되지 않은 항목은 구현 계약에 맞춰 확인한다. 이 문서는 명시된 TSD 규칙(필터 오류 400, 리소스 없음 404, 본문 검증 실패 422)을 기준으로 한다.

## 할 일 생성

- [ ] **TC-001 필수 제목만으로 생성 성공**
  - 경로: `POST /api/v1/tasks`
  - 요청: `{"title":"기획서 작성"}`
  - 기대 응답: `201 Created`; 생성된 리소스에 `id`, `title`이 포함되고, 생략된 상태는 `assigned`, 우선순위는 `medium`으로 반환된다. 설명, 마감일, 담당자, 태그, 라벨은 비어 있다.

- [ ] **TC-002 선택 필드를 포함해 생성 성공**
  - 경로: `POST /api/v1/tasks`
  - 요청: `{"title":"API 구현","description":"Task CRUD","status":"in_progress","priority":"high","due_at":"2026-10-20T09:00:00+09:00","assignees":["민수","지윤"],"tags":["backend"," sprint "],"labels":["이번 주"]}`
  - 기대 응답: `201 Created`; 요청 값이 저장되어 반환된다. 날짜는 UTC ISO 8601로 정규화되고, 배열 문자열은 앞뒤 공백을 제거해 저장된다.

- [ ] **TC-003 담당자, 태그, 라벨 중복 및 공백 정리**
  - 경로: `POST /api/v1/tasks`
  - 요청: `{"title":"중복 정리","assignees":[" 민수 ","민수"],"tags":[" api ","api"],"labels":["중요"," 중요 "]}`
  - 기대 응답: `201 Created`; 각 목록에는 공백 제거 후 중복이 제거된 값이 한 번씩만 포함된다.

- [ ] **TC-004 제목 누락 또는 공백 제목 생성 실패**
  - 경로: `POST /api/v1/tasks`
  - 요청: `{"description":"제목 없음"}` 또는 `{"title":"   "}`
  - 기대 응답: `422 Unprocessable Entity`; `detail`에 입력 오류가 포함되고 할 일은 생성되지 않는다.

- [ ] **TC-005 허용되지 않는 상태 또는 우선순위 생성 실패**
  - 경로: `POST /api/v1/tasks`
  - 요청: `{"title":"잘못된 값","status":"blocked"}` 또는 `{"title":"잘못된 값","priority":"urgent"}`
  - 기대 응답: `422 Unprocessable Entity`; `detail`에 허용 값 오류가 포함되고 할 일은 생성되지 않는다.

- [ ] **TC-006 잘못된 날짜 형식 생성 실패**
  - 경로: `POST /api/v1/tasks`
  - 요청: `{"title":"날짜 오류","due_at":"다음 주"}`
  - 기대 응답: `422 Unprocessable Entity`; `detail`에 날짜 형식 오류가 포함되고 할 일은 생성되지 않는다.

## 목록 및 상세 조회

- [ ] **TC-007 기본 목록 조회 및 기본 페이지 값**
  - 경로: `GET /api/v1/tasks`
  - 요청: 쿼리 없음
  - 기대 응답: `200 OK`; 활성 할 일만 `items`에 반환되고 응답에 `total`, `limit`(기본 20), `offset`(기본 0)이 포함된다. 기본 정렬은 생성 시각 내림차순이다.

- [ ] **TC-008 상태 복수 필터 조회 성공**
  - 경로: `GET /api/v1/tasks?status=assigned&status=in_progress`
  - 요청: 위 쿼리
  - 기대 응답: `200 OK`; 지정한 상태 중 하나에 해당하는 활성 할 일만 반환된다.

- [ ] **TC-009 담당자, 우선순위, 태그, 라벨 복합 필터 조회 성공**
  - 경로: `GET /api/v1/tasks?assignee=%EB%AF%BC%EC%88%98&priority=high&tag=backend&label=%EC%9D%B4%EB%B2%88%20%EC%A3%BC`
  - 요청: 위 쿼리
  - 기대 응답: `200 OK`; 네 조건을 모두 만족하는 할 일만 반환된다. 결과가 없으면 빈 `items`와 `total: 0`을 반환한다.

- [ ] **TC-010 마감일 범위 필터 조회 성공**
  - 경로: `GET /api/v1/tasks?due_from=2026-10-01T00:00:00Z&due_to=2026-10-31T23:59:59Z`
  - 요청: 위 쿼리
  - 기대 응답: `200 OK`; 마감일이 범위 안에 있는 항목만 반환된다. 마감일이 없는 항목은 제외된다.

- [ ] **TC-011 완료 항목 포함 여부 필터 성공**
  - 경로: `GET /api/v1/tasks?include_completed=false`
  - 요청: 위 쿼리
  - 기대 응답: `200 OK`; `completed` 상태 항목은 제외된다. `include_completed`를 생략하면 완료 항목도 포함된다.

- [ ] **TC-012 페이지네이션 성공**
  - 경로: `GET /api/v1/tasks?limit=2&offset=1`
  - 요청: 위 쿼리
  - 기대 응답: `200 OK`; `limit: 2`, `offset: 1`을 반환하며 전체 정렬 결과에서 두 번째 항목부터 최대 2개를 `items`에 반환한다.

- [ ] **TC-013 유효하지 않은 목록 필터 실패**
  - 경로: `GET /api/v1/tasks?status=blocked` 또는 `GET /api/v1/tasks?priority=urgent`
  - 요청: 위 쿼리 중 하나
  - 기대 응답: `400 Bad Request`; `detail`에 잘못된 필터 값이 표시된다.

- [ ] **TC-014 페이지네이션 범위 초과 실패**
  - 경로: `GET /api/v1/tasks?limit=101`
  - 요청: 위 쿼리
  - 기대 응답: 요청이 거부된다(`limit` 최대 100). TSD에 따라 `422 Unprocessable Entity`와 검증 오류 `detail`을 반환한다.

- [ ] **TC-015 활성 할 일 상세 조회 성공**
  - 경로: `GET /api/v1/tasks/{task_id}`
  - 요청: `GET /api/v1/tasks/1`
  - 기대 응답: `200 OK`; ID가 1인 활성 할 일의 상세 리소스를 반환한다.

- [ ] **TC-016 존재하지 않는 할 일 상세 조회 실패**
  - 경로: `GET /api/v1/tasks/{task_id}`
  - 요청: `GET /api/v1/tasks/999999`
  - 기대 응답: `404 Not Found`; `detail`을 반환한다.

## 수정

- [ ] **TC-017 전달한 필드만 수정 성공**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: `PATCH /api/v1/tasks/1` 본문 `{"title":"기획서 초안 작성"}`
  - 기대 응답: `200 OK`; 제목과 `updated_at`은 변경되고, 본문에서 생략한 나머지 값은 기존 값을 유지한다.

- [ ] **TC-018 배열 교체 및 빈 배열로 값 비우기 성공**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: `PATCH /api/v1/tasks/1` 본문 `{"assignees":["지윤"],"tags":[]}`
  - 기대 응답: `200 OK`; 담당자 전체가 `지윤`으로 교체되고 태그 전체가 비워진다. 라벨 등 생략한 필드는 유지된다.

- [ ] **TC-019 null 허용 필드 초기화 성공**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: `PATCH /api/v1/tasks/1` 본문 `{"description":null,"due_at":null}`
  - 기대 응답: `200 OK`; 설명과 마감일이 지워지고 그 외 필드는 유지된다.

- [ ] **TC-020 상태를 임의 순서로 변경 성공**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: `PATCH /api/v1/tasks/1` 본문 `{"status":"completed"}`
  - 기대 응답: `200 OK`; 상태가 `completed`로 변경된다. 이후 `assigned` 등 다른 유효 상태로도 다시 변경할 수 있다.

- [ ] **TC-021 유효하지 않은 수정 값 실패**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: `PATCH /api/v1/tasks/1` 본문 `{"status":"blocked"}`
  - 기대 응답: `422 Unprocessable Entity`; `detail`에 검증 오류가 포함되고 기존 리소스는 변경되지 않는다.

- [ ] **TC-022 존재하지 않는 할 일 수정 실패**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: `PATCH /api/v1/tasks/999999` 본문 `{"title":"변경"}`
  - 기대 응답: `404 Not Found`; `detail`을 반환한다.

## 소프트 삭제와 복구

- [ ] **TC-023 할 일 소프트 삭제 성공**
  - 경로: `DELETE /api/v1/tasks/{task_id}`
  - 요청: `DELETE /api/v1/tasks/1`
  - 기대 응답: `200 OK`; 삭제 결과를 응답한다. 해당 항목은 기본 목록 및 상세 조회에서 더 이상 보이지 않는다.

- [ ] **TC-024 삭제된 할 일 목록 조회 성공**
  - 경로: `GET /api/v1/tasks/deleted`
  - 요청: 쿼리 없음
  - 기대 응답: `200 OK`; 삭제된 항목만 목록으로 반환하며 목록 메타데이터(`items`, `total`, `limit`, `offset`)를 포함한다.

- [ ] **TC-025 삭제된 할 일 상세 조회 실패**
  - 경로: `GET /api/v1/tasks/{task_id}`
  - 요청: 삭제된 ID로 `GET /api/v1/tasks/1`
  - 기대 응답: `404 Not Found`; 삭제된 항목은 일반 상세 조회에서 접근할 수 없다.

- [ ] **TC-026 삭제된 할 일 수정 실패**
  - 경로: `PATCH /api/v1/tasks/{task_id}`
  - 요청: 삭제된 ID로 `PATCH /api/v1/tasks/1` 본문 `{"title":"수정 시도"}`
  - 기대 응답: `404 Not Found`; 삭제된 항목은 수정되지 않는다.

- [ ] **TC-027 삭제된 할 일 복구 성공**
  - 경로: `POST /api/v1/tasks/{task_id}/restore`
  - 요청: `POST /api/v1/tasks/1/restore`
  - 기대 응답: `200 OK`; 복구된 리소스를 반환하고 `deleted_at`이 비워진다. 항목이 기본 목록과 상세 조회에 다시 나타난다.

- [ ] **TC-028 이미 삭제된 할 일 재삭제 실패**
  - 경로: `DELETE /api/v1/tasks/{task_id}`
  - 요청: 이미 삭제된 ID로 `DELETE /api/v1/tasks/1`
  - 기대 응답: `404 Not Found`; 삭제 상태가 중복 변경되지 않는다.

- [ ] **TC-029 활성 할 일 복구 시도 실패**
  - 경로: `POST /api/v1/tasks/{task_id}/restore`
  - 요청: 삭제되지 않은 ID로 `POST /api/v1/tasks/1/restore`
  - 기대 응답: `404 Not Found`; 활성 항목의 상태는 변경되지 않는다.

- [ ] **TC-030 존재하지 않는 할 일 삭제 및 복구 실패**
  - 경로: `DELETE /api/v1/tasks/{task_id}` 또는 `POST /api/v1/tasks/{task_id}/restore`
  - 요청: `task_id=999999`
  - 기대 응답: `404 Not Found`; `detail`을 반환한다.

- [ ] **TC-031 신규 DB 동시 첫 연결에서 마이그레이션 1회 적용**
  - 상황: 스키마가 없는 SQLite 파일에 여러 연결이 동시에 처음 접근한다.
  - 기대 결과: 모든 연결이 성공하고 테이블 및 마이그레이션 기록이 중복 생성되지 않는다.

- [ ] **TC-032 PostgreSQL에 저장한 할 일 생성 후 조회 성공**
  - 경로: `POST /api/v1/tasks`, `GET /api/v1/tasks/{task_id}`
  - 상황: `DATABASE_URL`로 지정한 PostgreSQL 테스트 DB에서 생성 API를 호출한 뒤 별도 조회 요청을 보낸다.
  - 기대 결과: 생성 응답은 `201`, 조회 응답은 `200`이며 제목, 담당자, 태그가 유지된다. SQLite fallback이 아니라 PostgreSQL에 저장되어야 한다.

- [ ] **TC-033 설정된 팀 API 토큰으로 보호**
  - 경로: `/api/v1/tasks`
  - 준비: 서버에 `TTODO_API_TOKEN`을 설정한다.
  - 기대 결과: 토큰이 없거나 다르면 `401`을 반환하고, `Authorization: Bearer <token>`이 맞으면 목록을 조회할 수 있다.

- [ ] **TC-034 기존 칸반 보드에 저장하고 다시 조회**
  - 경로: `POST /api/v1/kanban/tasks`, `GET /api/v1/kanban/tasks/{task_id}`, `GET /api/v1/kanban/tasks`
  - 준비: 별도 로컬 PostgreSQL에 기존 보드 테이블과 멤버, 프로젝트, 보드, 칼럼을 만들고 연결한다.
  - 기대 결과: 작업, 보드 배치, 멤버, 라벨을 저장한다. 새 요청의 상세 조회와 보드 목록에 같은 작업이 나타난다. SQLite나 별도 `tasks` 테이블에 저장하지 않는다.

- [ ] **TC-035 Worker 토큰 바인딩을 fail-closed로 검사**
  - 상황: Worker ASGI scope에 토큰 바인딩이 없거나 요청 토큰이 다르다.
  - 기대 결과: 토큰 바인딩이 없으면 `503`, 잘못된 토큰이면 `401`을 반환한다. Worker 외부 프로세스 환경변수에만 설정한 토큰을 바인딩으로 간주하지 않는다.

- [ ] **TC-036 Worker DB 설정 누락 시 SQLite fallback 차단**
  - 상황: Worker scope에 올바른 API 토큰은 있지만 PostgreSQL 연결 바인딩이 없다.
  - 기대 결과: `503`을 반환하고 SQLite 파일이나 로컬 마이그레이션을 만들지 않는다.
