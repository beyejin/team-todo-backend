"""Request-scoped Worker bindings and local environment settings."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar

_LOCAL_ENVIRONMENT = object()
_request_environment: ContextVar[object] = ContextVar(
    "request_environment", default=_LOCAL_ENVIRONMENT
)


@contextmanager
def bind_request_environment(scope: Mapping[str, object]) -> Iterator[None]:
    """Bind Worker settings from an ASGI scope for the current request."""
    environment = scope.get("env", _LOCAL_ENVIRONMENT)
    token = _request_environment.set(environment)
    try:
        yield
    finally:
        _request_environment.reset(token)


def get_setting(name: str) -> str | None:
    """Read a Worker binding or, for local requests, a process environment value."""
    environment = _request_environment.get()
    if environment is _LOCAL_ENVIRONMENT:
        return os.environ.get(name)
    value = getattr(environment, name, None)
    return value if isinstance(value, str) else None


def is_worker_request() -> bool:
    """Return whether the current ASGI request has a Worker environment scope."""
    return _request_environment.get() is not _LOCAL_ENVIRONMENT
