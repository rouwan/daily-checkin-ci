"""后端纯业务规则单元测试。"""

from datetime import date

import pytest

from app.rules import calculate_current_streak, normalize_habit_name

pytestmark = pytest.mark.unit


def test_habit_name_removes_surrounding_whitespace() -> None:
    assert normalize_habit_name("  读书半小时 \t") == "读书半小时"


def test_habit_name_preserves_internal_whitespace() -> None:
    assert normalize_habit_name("读书 半小时") == "读书半小时"


def test_habit_name_accepts_one_character() -> None:
    assert normalize_habit_name("读") == "读"


def test_habit_name_accepts_forty_characters() -> None:
    name = "中" * 40
    assert normalize_habit_name(name) == name


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_habit_name_rejects_blank_value(name: str) -> None:
    with pytest.raises(ValueError, match="习惯名称"):
        normalize_habit_name(name)


def test_habit_name_rejects_more_than_forty_characters() -> None:
    with pytest.raises(ValueError, match="习惯名称"):
        normalize_habit_name("中" * 41)


def test_streak_is_zero_without_check_ins() -> None:
    assert calculate_current_streak(set(), date(2026, 11, 22)) == 0


def test_streak_starts_at_today_when_today_is_checked() -> None:
    today = date(2026, 11, 22)
    assert calculate_current_streak({today}, today) == 1


def test_streak_counts_consecutive_days_ending_today() -> None:
    today = date(2026, 11, 22)
    checked_dates = {
        date(2026, 11, 22),
        date(2026, 11, 21),
        date(2026, 11, 20),
    }
    assert calculate_current_streak(checked_dates, today) == 3


def test_streak_starts_yesterday_when_today_is_not_checked() -> None:
    today = date(2026, 11, 22)
    checked_dates = {
        date(2026, 11, 21),
        date(2026, 11, 20),
    }
    assert calculate_current_streak(checked_dates, today) == 2


def test_streak_is_zero_when_today_and_yesterday_are_not_checked() -> None:
    today = date(2026, 11, 22)
    checked_dates = {
        date(2026, 11, 20),
        date(2026, 11, 19),
        date(2026, 11, 18),
    }
    assert calculate_current_streak(checked_dates, today) == 0


def test_streak_stops_at_the_first_gap() -> None:
    today = date(2026, 11, 22)
    checked_dates = {
        date(2026, 11, 22),
        date(2026, 11, 21),
        date(2026, 11, 19),
        date(2026, 11, 18),
    }
    assert calculate_current_streak(checked_dates, today) == 2


def test_future_check_ins_do_not_affect_current_streak() -> None:
    today = date(2026, 11, 22)
    checked_dates = {
        date(2026, 11, 21),
        date(2026, 11, 23),
        date(2026, 11, 24),
    }
    assert calculate_current_streak(checked_dates, today) == 1


def test_only_future_check_ins_produce_zero_streak() -> None:
    today = date(2026, 11, 22)
    checked_dates = {
        date(2026, 11, 23),
        date(2026, 11, 24),
    }
    assert calculate_current_streak(checked_dates, today) == 0


def test_streak_crosses_a_month_boundary() -> None:
    today = date(2026, 12, 1)
    checked_dates = {
        date(2026, 12, 1),
        date(2026, 11, 30),
        date(2026, 11, 29),
    }
    assert calculate_current_streak(checked_dates, today) == 3


def test_streak_crosses_a_leap_day() -> None:
    today = date(2024, 3, 1)
    checked_dates = {
        date(2024, 3, 1),
        date(2024, 2, 29),
        date(2024, 2, 28),
    }
    assert calculate_current_streak(checked_dates, today) == 3


def test_streak_crosses_a_year_boundary() -> None:
    today = date(2026, 1, 1)
    checked_dates = {
        date(2026, 1, 1),
        date(2025, 12, 31),
        date(2025, 12, 30),
    }
    assert calculate_current_streak(checked_dates, today) == 3
