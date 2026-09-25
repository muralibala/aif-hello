import json

import pytest

from app import api


def test_greeting() -> None:
    assert api.greeting_for("42") == "hello world id:42"


def test_hello_world_within_budget() -> None:
    assert api.hello_world("7") == "hello world id:7"


def test_hello_world_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    def slow(id_: str) -> str:
        time.sleep(0.35)
        return "late"

    monkeypatch.setattr(api, "greeting_for", slow)
    with pytest.raises(TimeoutError, match="exceeded 200ms budget"):
        api.hello_world("7")


def test_handler_ok_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = api.handler({"rawPath": "/hello", "queryStringParameters": {"id": "9"}})
    assert resp["statusCode"] == 200 and json.loads(resp["body"])["message"] == "hello world id:9"

    def boom(id_: str) -> str:
        raise TimeoutError("helloWorld(id=9) exceeded 200ms budget")

    monkeypatch.setattr(api, "hello_world", boom)
    resp = api.handler({"rawPath": "/hello", "queryStringParameters": {"id": "9"}})
    assert resp["statusCode"] == 504 and "exceeded" in json.loads(resp["body"])["error"]


def test_index_and_404() -> None:
    assert "helloWorld" in api.handler({"rawPath": "/"})["body"]
    assert api.handler({"rawPath": "/nope"})["statusCode"] == 404
