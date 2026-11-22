"""接口请求与响应数据结构。"""

from datetime import date

from pydantic import BaseModel, field_validator

from app.rules import normalize_habit_name


class HabitInput(BaseModel):
    """设置或修改唯一习惯名称。"""

    name: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_habit_name(value)


class HabitOutput(BaseModel):
    name: str


class TodayStatus(BaseModel):
    """接口返回的完整今日状态。"""

    habit: HabitOutput | None
    date: date
    checked_in_today: bool
    current_streak: int
