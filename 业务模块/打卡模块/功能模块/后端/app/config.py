"""本地运行路径配置。"""

import os
from pathlib import Path

FUNCTION_MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = FUNCTION_MODULE_ROOT / "数据库" / "打卡.sqlite3"
SCHEMA_PATH = FUNCTION_MODULE_ROOT / "数据库" / "建表.sql"


def get_database_path() -> Path:
    """返回数据库文件路径；相对路径以功能模块根目录为基准。"""
    configured = os.getenv("CHECKIN_DATABASE_PATH")
    if not configured:
        return DEFAULT_DATABASE_PATH

    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = FUNCTION_MODULE_ROOT / path
    return path.resolve()
