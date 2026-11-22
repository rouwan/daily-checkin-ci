"""单习惯打卡业务规则。"""

import sqlite3
from datetime import date, datetime

from app.database import open_database
from app.rules import calculate_current_streak, normalize_habit_name
from app.schemas import HabitOutput, TodayStatus


class HabitNotConfiguredError(Exception):
    """尚未设置唯一习惯。"""


def _local_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read_status(connection: sqlite3.Connection, today: date) -> TodayStatus:
    habit_row = connection.execute("SELECT name FROM habit WHERE id = 1").fetchone()
    check_in_rows = connection.execute(
        """
        SELECT check_in_date
        FROM check_in
        WHERE check_in_date <= ?
        ORDER BY check_in_date DESC
        """,
        (today.isoformat(),),
    ).fetchall()

    checked_dates = {
        date.fromisoformat(row["check_in_date"]) for row in check_in_rows
    }
    checked_in_today = today in checked_dates

    return TodayStatus(
        habit=HabitOutput(name=habit_row["name"]) if habit_row else None,
        date=today,
        checked_in_today=checked_in_today,
        current_streak=calculate_current_streak(checked_dates, today),
    )


def get_today_status(today: date | None = None) -> TodayStatus:
    local_today = today or date.today()
    with open_database() as connection:
        return _read_status(connection, local_today)


def set_habit_name(name: str, today: date | None = None) -> TodayStatus:
    local_today = today or date.today()
    normalized = normalize_habit_name(name)

    with open_database() as connection:
        connection.execute(
            """
            INSERT INTO habit (id, name, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                updated_at = excluded.updated_at
            """,
            (normalized, _local_timestamp()),
        )
        return _read_status(connection, local_today)


def check_in_today(today: date | None = None) -> TodayStatus:
    local_today = today or date.today()
    with open_database() as connection:
        habit_exists = connection.execute("SELECT 1 FROM habit WHERE id = 1").fetchone()
        if habit_exists is None:
            raise HabitNotConfiguredError

        connection.execute(
            """
            INSERT OR IGNORE INTO check_in (check_in_date, created_at)
            VALUES (?, ?)
            """,
            (local_today.isoformat(), _local_timestamp()),
        )
        return _read_status(connection, local_today)


def undo_today_check_in(today: date | None = None) -> TodayStatus:
    local_today = today or date.today()
    with open_database() as connection:
        connection.execute(
            "DELETE FROM check_in WHERE check_in_date = ?",
            (local_today.isoformat(),),
        )
        return _read_status(connection, local_today)
