# ttodo CLI

`ttodo`는 Team Todo API를 터미널에서 사용하는 명령줄 도구입니다. Python 3.13에서 실행하며, 성공 결과는 읽기 쉬운 텍스트로 표시합니다. 기계가 읽을 결과가 필요하면 `--json`을 사용합니다.

## 빠른 사용

먼저 Team Todo 서버를 실행합니다. 서버 사용법과 전체 CLI 예시는 프로젝트 루트의 [`README.md`](../README.md)를 참고하세요.

```console
uv run uvicorn app.main:app --reload
```

새 터미널에서 CLI를 실행합니다.

```console
uvx --from ./cli ttodo --help
uvx --from ./cli ttodo create --title "Send the report"
uvx --from ./cli ttodo --json list
```

기본 API 주소는 `http://127.0.0.1:8000`입니다. `--base-url` 또는 `TTODO_BASE_URL`로 바꿀 수 있습니다. 사용 가능한 명령과 옵션은 각 명령의 `--help`에 설명되어 있습니다.

## 개발

```console
uv sync --project cli
uv run --project cli pytest
uv run --project cli openapi-python-client generate --help
```

생성 API 클라이언트를 갱신하려면 서버를 실행한 뒤 프로젝트 루트에서 다음 명령을 사용합니다.

```console
uv run --project cli python cli/scripts/generate_client.py
```

생성된 클라이언트는 패키지에 포함됩니다. CLI를 사용할 때 서버의 OpenAPI 문서를 다시 내려받지 않습니다.
