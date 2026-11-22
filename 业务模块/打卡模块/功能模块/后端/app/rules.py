"""可脱离数据库运行的核心业务规则。"""

from collections.abc import Collection
from datetime import date, timedelta

MAX_HABIT_NAME_LENGTH = 40
HABIT_NAME_LENGTH_ERROR = "习惯名称需为 1 至 40 个字符"


def normalize_habit_name(name: str) -> str:
    """去除首尾空白，并校验习惯名称长度。"""
    normalized = name.strip()
    if not 1 <= len(normalized) <= MAX_HABIT_NAME_LENGTH:
        raise ValueError(HABIT_NAME_LENGTH_ERROR)
    return normalized


def calculate_current_streak(
    checked_dates: Collection[date],
    today: date,
) -> int:
    """根据已打卡日期计算当前连续天数。"""
    checked_date_set = set(checked_dates)
    yesterday = today - timedelta(days=1)

    if today in checked_date_set:
        cursor = today
    elif yesterday in checked_date_set:
        cursor = yesterday
    else:
        return 0

    current_streak = 0
    while cursor in checked_date_set:
        current_streak += 1
        cursor -= timedelta(days=1)

    return current_streak
