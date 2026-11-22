"""打卡模块 HTTP 接口。"""

from fastapi import APIRouter, HTTPException

from app.schemas import HabitInput, TodayStatus
from app.service import (
    HabitNotConfiguredError,
    check_in_today,
    get_today_status,
    set_habit_name,
    undo_today_check_in,
)

router = APIRouter(prefix="/api", tags=["打卡"])


@router.get("/status", summary="查看今日状态")
def read_today_status() -> TodayStatus:
    return get_today_status()


@router.put("/habit", summary="设置或修改唯一习惯名称")
def update_habit(payload: HabitInput) -> TodayStatus:
    try:
        return set_habit_name(payload.name)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/check-ins/today", summary="完成今天的打卡")
def complete_today() -> TodayStatus:
    try:
        return check_in_today()
    except HabitNotConfiguredError as error:
        raise HTTPException(status_code=409, detail="请先设置习惯名称") from error


@router.delete("/check-ins/today", summary="撤销今天的打卡")
def undo_today() -> TodayStatus:
    return undo_today_check_in()
