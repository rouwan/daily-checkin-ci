"""后端请求数据校验规则单元测试。"""

import pytest
from pydantic import ValidationError

from app.schemas import HabitInput

pytestmark = pytest.mark.unit


def test_habit_input_uses_normalized_name() -> None:
    payload = HabitInput(name="  读书半小时  ")
    assert payload.name == "读书半小时"


@pytest.mark.parametrize("name", ["", "   ", "中" * 41])
def test_habit_input_rejects_invalid_name(name: str) -> None:
    with pytest.raises(ValidationError):
        HabitInput(name=name)
