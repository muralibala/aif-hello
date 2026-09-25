"""Hello API. `GET /hello?id=<id>` -> "hello world id:<id>" within a 200 ms budget.

Every request runs `greeting_for` under a 200 ms deadline; when it is missed the handler
logs `ERROR TimeoutError ...` and returns 504. `GET /` serves the demo page.
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any

BUDGET_MS = 200
log = logging.getLogger("hello")
log.setLevel(logging.INFO)

_INDEX = Path(__file__).resolve().parent / "index.html"


def personalization_lookup(id_: str) -> dict[str, str]:
    """Fetch the caller's personalization profile."""
    return {"id": id_, "greeting": "hello world"}


def greeting_for(id_: str) -> str:
    profile = personalization_lookup(id_)
    return f"{profile['greeting']} id:{id_}"


def hello_world(id_: str) -> str:
    """Return the greeting or raise TimeoutError if it takes longer than BUDGET_MS."""
    executor = ThreadPoolExecutor(max_workers=1)
    started = time.perf_counter()
    future = executor.submit(greeting_for, id_)
    try:
        return future.result(timeout=BUDGET_MS / 1000)
    except FutureTimeout as err:
        elapsed_ms = (time.perf_counter() - started) * 1000
        raise TimeoutError(
            f"helloWorld(id={id_}) exceeded {BUDGET_MS}ms budget (still running after {elapsed_ms:.0f}ms)"
        ) from err
    finally:
        executor.shutdown(wait=False)


def _response(status: int, body: Any, content_type: str = "application/json") -> dict[str, Any]:
    text = body if isinstance(body, str) else json.dumps(body)
    return {"statusCode": status, "headers": {"content-type": content_type, "cache-control": "no-store"}, "body": text}


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    path = str(event.get("rawPath") or event.get("path") or "/")
    if path == "/hello":
        params = event.get("queryStringParameters") or {}
        id_ = str(params.get("id") or "anonymous")
        started = time.perf_counter()
        try:
            message = hello_world(id_)
        except TimeoutError as err:
            log.error("TimeoutError: %s", err)
            return _response(504, {"error": str(err), "id": id_})
        log.info("ok id=%s took=%.0fms", id_, (time.perf_counter() - started) * 1000)
        return _response(200, {"message": message, "id": id_})
    if path == "/":
        return _response(200, _INDEX.read_text(), "text/html; charset=utf-8")
    return _response(404, {"error": "not found"})
