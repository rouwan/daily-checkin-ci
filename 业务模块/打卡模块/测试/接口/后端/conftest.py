"""单模块接口测试夹具。"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def database_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """为每个接口测试提供独立的临时数据库。"""
    path = tmp_path / "interface-test.sqlite3"
    monkeypatch.setenv("CHECKIN_DATABASE_PATH", str(path))
    return path


@pytest.fixture
def client(database_path: Path) -> Iterator[TestClient]:
    """启动应用生命周期，但不启动真实 HTTP 服务。"""
    with TestClient(app) as test_client:
        yield test_client
