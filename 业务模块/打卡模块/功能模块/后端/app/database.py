"""SQLite 连接与初始化。"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.config import SCHEMA_PATH, get_database_path


def initialize_database() -> None:
    """创建数据库目录，并执行可重复运行的建表脚本。"""
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(database_path, timeout=5) as connection:
        connection.executescript(schema)


@contextmanager
def open_database() -> Iterator[sqlite3.Connection]:
    """为一次请求提供独立的 SQLite 连接。"""
    connection = sqlite3.connect(get_database_path(), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
