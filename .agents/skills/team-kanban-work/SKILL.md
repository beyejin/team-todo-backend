---
name: team-kanban-work
description: Use when performing implementation or coordination work for the Team 6 shared Kanban board through the ttodo CLI.
---

# Team Kanban 작업 기록

팀 공유 업무를 시작할 때 실제 작업을 칸반 보드에 등록하고, 완료 상태를 CLI에서 확인합니다.

## 절차

1. `TTODO_BASE_URL`과 `TTODO_API_TOKEN`이 안전한 환경 변수로 설정되어 있는지 확인합니다. 토큰 값을 출력하거나 명령 인수, 문서, 저장소에 기록하지 않습니다.
2. 작업 제목과 범위를 짧게 정리해 `ttodo kanban create --title "..."`로 등록합니다. 작업 설명은 `--description`, 상태는 `--status`로 지정할 수 있습니다.
3. 팀원이 담당자로 지정되어야 하면 검증된 GitHub 사용자명만 `--assignee`에 전달합니다. 확인하지 않은 이름이나 핸들을 추측하지 않습니다.
4. 생성 결과의 UUID를 보관하고 `ttodo kanban get <UUID>`로 저장 결과를 다시 읽습니다. 필요하면 `ttodo kanban list`로 보드 반영을 확인합니다.
5. 작업이 끝나면 지원되는 상태로 업데이트할 수 있는 별도 명령이 있는지 `ttodo kanban --help`에서 먼저 확인합니다. 업데이트 명령이 없으면 완료 상태라고 보고하지 말고 보드에 상태 변경 기능이 필요하다고 기록합니다.

## 연결할 수 없을 때

- 인증, 네트워크, 서버 설정 오류가 나면 오류 종류만 기록하고 토큰이나 데이터베이스 비밀값은 노출하지 않습니다.
- 보드 기록이 확인되지 않은 상태에서 로컬 `ttodo create`를 공유 칸반 등록의 대체로 사용하지 않습니다.
- 보드 데이터가 비어 있거나 대상 보드를 찾을 수 없는 오류가 나면 보드 ID, 작업자 프로필, 프로젝트 초기 설정이 완료됐는지 확인합니다. 원격 데이터베이스에 임의로 스키마 변경이나 샘플 데이터를 넣지 않습니다.
- 사용자가 요청하지 않은 외부 메시지나 팀원 알림은 보내지 않습니다.
