# 팀 Todo 데이터베이스 설계

## 목적과 공통 규칙

SQLite에 할 일과 담당자, 태그, 라벨을 저장합니다. 삭제는 행을 제거하지 않고 `deleted_at`에 시각을 기록하는 소프트 삭제입니다.

- 기본 키는 SQLite `INTEGER PRIMARY KEY`를 사용합니다.
- 날짜와 시각은 UTC ISO 8601 문자열로 저장합니다.
- 외래 키 제약을 활성화합니다.
- 담당자는 인증 계정이 아니라 입력된 이름 문자열입니다.
- 태그와 라벨은 할 일별 연결 테이블에 저장하며 같은 할 일 안에서 중복을 허용하지 않습니다.

## 테이블

### `tasks`

할 일의 본문과 상태를 저장합니다.

- `id`: 정수 기본 키
- `title`: 필수 제목이며 공백만 있는 값은 허용하지 않습니다.
- `description`: 선택 설명
- `status`: `assigned`, `in_progress`, `completed` 중 하나이며 기본값은 `assigned`입니다.
- `priority`: `low`, `medium`, `high` 중 하나이며 기본값은 `medium`입니다.
- `due_at`: 선택 마감 시각
- `created_at`: 생성 시각
- `updated_at`: 마지막 수정 시각
- `deleted_at`: 소프트 삭제 시각이며 활성 항목은 `NULL`입니다.

### `task_assignees`

할 일에 지정된 담당자 이름을 저장합니다.

- `task_id`: `tasks.id`를 참조하는 외래 키
- `assignee_name`: 앞뒤 공백을 제거한 담당자 이름
- 기본 키는 `(task_id, assignee_name)` 복합 키입니다.
- 실제 행을 제거할 때 연결 행도 함께 제거됩니다. 일반 삭제 API는 소프트 삭제이므로 연결 행을 유지합니다.

### `task_tags`

할 일에 지정된 태그를 저장합니다.

- `task_id`: `tasks.id`를 참조하는 외래 키
- `tag`: 태그 문자열
- 기본 키는 `(task_id, tag)` 복합 키입니다.

### `task_labels`

할 일에 지정된 라벨을 저장합니다.

- `task_id`: `tasks.id`를 참조하는 외래 키
- `label`: 라벨 문자열
- 기본 키는 `(task_id, label)` 복합 키입니다.

## 관계와 인덱스

할 일 하나에는 여러 담당자, 태그, 라벨을 지정할 수 있습니다. 담당자 이름은 사용자 테이블과 연결하지 않습니다.

조회에 사용하는 인덱스는 다음과 같습니다.

- `tasks(status, deleted_at, created_at)`: 목록과 상태 조회
- `tasks(due_at)`: 마감일 범위 조회
- `task_assignees(assignee_name, task_id)`: 담당자 필터
- `task_tags(tag, task_id)`: 태그 필터
- `task_labels(label, task_id)`: 라벨 필터

각 연결 테이블의 복합 기본 키는 같은 할 일에서 담당자, 태그, 라벨이 중복 저장되는 것을 막습니다.

## 조회 규칙

- 기본 목록은 `deleted_at IS NULL`인 할 일만 반환합니다.
- `include_completed`가 `false`이면 완료 상태를 제외합니다.
- 삭제 목록은 `deleted_at IS NOT NULL`인 할 일만 반환합니다.
- 담당자, 태그, 라벨 필터는 해당 값이 있는 할 일을 찾습니다. 여러 필터를 함께 지정하면 모든 조건을 만족해야 합니다.
- 목록은 `created_at DESC, id DESC`로 정렬합니다.

## 변경 규칙

- 생성 시각은 처음 생성할 때 기록하고 이후 변경하지 않습니다.
- 본문이나 연결 값이 바뀌면 `updated_at`을 갱신합니다.
- 삭제할 때 `deleted_at`과 `updated_at`을 현재 UTC 시각으로 설정합니다.
- 복구할 때 `deleted_at`을 `NULL`로 바꾸고 `updated_at`을 갱신합니다.
- 담당자, 태그, 라벨 배열은 전달한 목록으로 트랜잭션 안에서 교체합니다.
- 첫 버전 API는 실제 행 삭제를 제공하지 않습니다.

## 정합성 제약

- 제목은 필수이며 빈 문자열과 공백 문자열을 허용하지 않습니다.
- 상태와 우선순위는 정해진 값만 저장합니다.
- 마감 시각은 시간대를 포함해 입력하고 UTC ISO 8601로 정규화합니다.
- 담당자, 태그, 라벨은 앞뒤 공백을 제거하고 빈 문자열을 저장하지 않습니다.
- 복합 키로 같은 할 일 안의 중복 값을 방지합니다.

## 현재 범위와 추후 결정

제목, 설명, 태그, 라벨의 최대 길이는 아직 정하지 않았습니다. DB 파일의 백업과 초기화는 로컬 실행 환경에서 별도로 관리합니다. 사용자 계정 테이블은 인증 기능을 도입할 때 설계합니다.

## Supabase 공유 칸반 보드 연결

공유 API는 별도의 `tasks` 복제 테이블을 만들지 않습니다.

- 작업 제목과 설명은 `issues`에 저장합니다.
- 보드와 칼럼 및 순서는 `board_items`에 저장합니다.
- 상태는 `board_items`에서 `board_columns`와 `workflow_statuses`로 이어지는 관계에서 계산합니다. `issues.status` 컬럼은 사용하지 않습니다.
- 담당자는 `profiles`와 `workspace_members`에서 팀 멤버인지 확인하고 `issue_assignees`로 연결합니다.
- 라벨은 프로젝트별 `labels`와 `issue_labels`로 연결합니다.
- 체크리스트 테이블에는 쓰지 않습니다.

이 연결은 `KANBAN_DATABASE_URL`을 사용하고 기본 Todo API의 SQLite/PostgreSQL 마이그레이션과 분리됩니다. 공유 서버에서는 `TTODO_API_TOKEN`을 요구해야 하며, Supabase Data API의 공개 역할도 별도로 보호해야 합니다.
