"""单模块 HTTP 接口测试。"""

import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.interface


def set_habit(client: TestClient, name: str = "读书半小时") -> dict[str, object]:
    response = client.put("/api/habit", json={"name": name})
    assert response.status_code == 200
    return response.json()


def check_in(client: TestClient) -> dict[str, object]:
    response = client.post("/api/check-ins/today")
    assert response.status_code == 200
    return response.json()


def test_status_without_habit(client: TestClient) -> None:
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["habit"] is None
    assert payload["date"] == date.today().isoformat()
    assert payload["checked_in_today"] is False
    assert payload["current_streak"] == 0


def test_set_habit_normalizes_name(client: TestClient) -> None:
    payload = set_habit(client, "  读书半小时  ")

    assert payload["habit"] == {"name": "读书半小时"}


def test_habit_name_of_forty_characters_is_accepted(client: TestClient) -> None:
    name = "中" * 40
    payload = set_habit(client, name)

    assert payload["habit"] == {"name": name}


@pytest.mark.parametrize(
    "name",
    ["", "   ", "中" * 41],
    ids=["empty", "whitespace", "too-long"],
)
def test_set_habit_rejects_invalid_name(
    client: TestClient,
    name: str,
) -> None:
    response = client.put("/api/habit", json={"name": name})

    assert response.status_code == 422


def test_check_in_requires_habit(client: TestClient) -> None:
    response = client.post("/api/check-ins/today")

    assert response.status_code == 409
    assert response.json() == {"detail": "请先设置习惯名称"}


def test_first_check_in_returns_checked_status(client: TestClient) -> None:
    set_habit(client)

    payload = check_in(client)

    assert payload["checked_in_today"] is True
    assert payload["current_streak"] == 1


def test_duplicate_check_in_keeps_one_database_record(
    client: TestClient,
    database_path: Path,
) -> None:
    set_habit(client)

    first_payload = check_in(client)
    second_payload = check_in(client)

    assert first_payload["checked_in_today"] is True
    assert second_payload["checked_in_today"] is True
    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM check_in").fetchone()[0]
    assert count == 1


def test_undo_without_existing_check_in_still_succeeds(
    client: TestClient,
) -> None:
    set_habit(client)

    response = client.delete("/api/check-ins/today")

    assert response.status_code == 200
    assert response.json()["checked_in_today"] is False
    assert response.json()["current_streak"] == 0


def test_undo_after_check_in_restores_status(client: TestClient) -> None:
    set_habit(client)
    check_in(client)

    response = client.delete("/api/check-ins/today")

    assert response.status_code == 200
    payload = response.json()
    assert payload["checked_in_today"] is False
    assert payload["current_streak"] == 0
    assert payload["habit"] == {"name": "读书半小时"}


def test_renaming_habit_keeps_check_in_status(client: TestClient) -> None:
    set_habit(client, "读书半小时")
    check_in(client)

    payload = set_habit(client, "阅读二十分钟")

    assert payload["habit"] == {"name": "阅读二十分钟"}
    assert payload["checked_in_today"] is True
    assert payload["current_streak"] == 1


def test_new_client_reads_persisted_data(client: TestClient) -> None:
    set_habit(client)
    check_in(client)

    with TestClient(app) as restarted_client:
        response = restarted_client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["habit"] == {"name": "读书半小时"}
    assert payload["checked_in_today"] is True
    assert payload["current_streak"] == 1


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
