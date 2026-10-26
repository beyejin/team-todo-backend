# 공유 칸반 상태 변경 API

기존 공유 보드의 등록·목록·상세 조회에 **기존 작업의 상태 변경**을 추가합니다.
기본 Todo `/api/v1/tasks`와 저장소·ID·응답 계약이 다른 API입니다.

## 확정 계약

```http
PATCH /api/v1/kanban/tasks/{task_id}
Content-Type: application/json

{"status":"in_progress"}
```

- `task_id`는 UUID입니다.
- 본문의 필수 필드는 `status` 하나이며, `assigned`, `in_progress`, `completed`만 허용합니다. 빈 본문·`null`·다른 상태·추가 필드는 `422`입니다.
- 성공은 `200`과 기존 상세 응답입니다. `id`, `issue_number`, `title`, `description`, `status`, `board_id`, `column_id`, `position`, `created_at`, `updated_at`, `assignees`, `labels`를 반환합니다.
- 현재와 같은 상태를 다시 보내면 칼럼·순서·수정 시각을 그대로 유지합니다.
- 다른 상태는 해당 보드에서 대응 상태를 가진 첫 번째 칼럼(`board_columns.position` 순) 끝으로 이동합니다. 기존 칼럼의 빈 순서를 재정렬하지 않습니다.
- 이동 시 `board_items.updated_at`과 `issues.updated_at`을 갱신합니다. 제목·설명·담당자·라벨·생성 시각은 유지합니다.
- 상태는 기존 관계 `board_items → board_columns → workflow_statuses.category`에서 계산하며, 별도 상태 컬럼이나 복제 테이블을 만들지 않습니다.

| 상황 | 응답 |
| --- | --- |
| 설정된 작성자가 해당 workspace 멤버가 아님 | `403` |
| 작업이 없거나 설정된 보드에 배치되지 않음 | `404` |
| 이동할 상태에 대응하는 보드 칼럼이 없음 | `409` |
| UUID·상태·본문 필드가 잘못됨 | `422` |
| 보드·작성자 설정 누락/잘못된 UUID 또는 DB 주소 미설정 | `503` |
| 토큰을 요구하는 서버에 인증이 없거나 다름 | `401` |

인증 경계는 기존 서버와 같습니다. 로컬은 `TTODO_API_TOKEN` 설정 시 bearer 토큰을 요구하며, Worker는 토큰 바인딩 없이 업무 API를 제공하지 않습니다. 작성자는 서버의 `KANBAN_ACTOR_PROFILE_ID`로 결정하며, 팀원별 로그인이나 권한 위임을 새로 제공하지 않습니다.

## 트랜잭션과 최소 권한

기존 등록 API와 같은 프로젝트 단위 transaction advisory lock을 먼저 잡고, 대상 `issues`와 `board_items` 행을 `FOR UPDATE`로 잠급니다. 따라서 이 API의 동시 등록·이동이 같은 마지막 순서를 배정하지 않으며, 뒤 요청은 앞 요청이 저장한 상태를 읽습니다. 두 행의 갱신은 한 트랜잭션으로 커밋하고, 중간 오류는 모두 롤백합니다. 직접 SQL을 쓰는 별도 작성자는 동일한 동시성 규칙을 따라야 합니다. [PostgreSQL 잠금 문서](https://www.postgresql.org/docs/17/explicit-locking.html)

서버 역할과 기존 정책을 준비한 뒤 `migrations/supabase/002_worker_status_update.sql`을 적용합니다. 순서는 기존 `001_worker_access.sql` 다음입니다. 001을 다시 실행하면 권한을 초기화하므로 002도 다시 적용해야 합니다.

- `board_items`: `column_id`, `position`, `updated_at`의 UPDATE만 추가.
- `issues`: `updated_at`의 UPDATE만 추가.
- 기존 001의 RLS 정책을 재사용합니다. `title`·`description` UPDATE나 DELETE 권한을 추가하지 않고, RLS·공개 역할 정책을 완화하지 않습니다.
- 이 변경의 로컬 검증은 원격 Supabase에 migration을 적용했다는 뜻이 아닙니다.

## 지원하지 않는 편집·삭제와 향후 계약

현재 칸반 PATCH는 상태 전용입니다. 제목·설명·담당자·라벨 편집, 보드 간 이동, 삭제·복구는 지원하지 않습니다. 기본 Todo API의 수정·삭제를 공유 칸반에 대신 호출하면 안 됩니다.

편집을 추가할 때는 허용 필드, 생략·비우기 규칙, 담당자의 workspace 소속 검증, 라벨 교체의 원자성과 필요한 열 권한을 먼저 확정해야 합니다. 삭제는 한 보드의 배치만 제거할지 여러 보드가 참조하는 issue까지 처리할지, 소프트 삭제·복구와 연결 데이터의 보존 범위를 별도 계약으로 정해야 합니다. 아직 구현 또는 확정된 기능으로 안내하지 않습니다.

## 격리 검증

기존 `TC-034`의 별도 localhost PostgreSQL fixture에서 다음을 검사합니다. fixture는 테스트 DB의 `public` 스키마를 초기화하므로 실제 공유 DB를 지정하지 않습니다.

| ID | 검증 |
| --- | --- |
| TC-037 | 임의 상태 순서 이동, 상세·목록 재조회, 기존 내용 보존·수정 시각 갱신 |
| TC-038 | 같은 상태 재요청의 응답·순서·수정 시각 불변 |
| TC-039 | 대상 칼럼의 기존 작업 뒤에 추가, 다른 작업 내용·순서 보존 |
| TC-040 | 누락·null·잘못된 상태·추가 필드 422 및 원본 보존 |
| TC-041 | 다른 보드·없는 UUID 404, 멤버가 아닌 작성자 403 |
| TC-042 | 목표 칼럼 누락 409, 두 번째 UPDATE 실패 시 위치·시각 전체 롤백 |
| TC-043 | 생성 4건과 이동 4건 동시 실행 후 마지막 순서 중복 없음 |
| TC-044 | 실제 001·002 migration과 RLS 적용 후 제한 역할 PATCH 성공, 제목 수정·삭제 권한 없음 |

`TEST_KANBAN_DATABASE_URL`과 `TEST_DATABASE_URL`에는 각각 분리된 로컬 테스트 DB를 지정하고 `bash scripts/verify.sh`를 실행합니다. 실제 토큰이나 DB 비밀번호를 명령 인수·문서·로그에 기록하지 않습니다.
