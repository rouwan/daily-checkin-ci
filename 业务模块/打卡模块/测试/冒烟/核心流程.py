"""核心用户路径冒烟测试。"""

import os
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

APP_URL = "http://127.0.0.1:5173"
HABIT_NAME = "冒烟测试习惯"


def require_isolated_database() -> Path:
    """确认冒烟测试没有配置到正式数据库。"""
    configured = os.getenv("CHECKIN_DATABASE_PATH")
    if not configured or os.getenv("CHECKIN_SMOKE_TEST") != "1":
        raise RuntimeError("请通过测试/冒烟/运行冒烟测试.ps1 启动冒烟测试")

    database_path = Path(configured).resolve()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    if not database_path.is_relative_to(temporary_root):
        raise RuntimeError(f"冒烟数据库不在系统临时目录中：{database_path}")
    return database_path


def run_core_check_in(page) -> None:
    """P0：首次设置、打卡，并确认刷新后数据仍然存在。"""
    expect(
        page.get_by_role("heading", name="每天，只做一件事。")
    ).to_be_visible()
    page.get_by_label("习惯名称").fill(HABIT_NAME)
    page.get_by_role("button", name="保存名称").click()
    expect(page.get_by_role("heading", name=HABIT_NAME)).to_be_visible()

    page.get_by_role("button", name="完成今天打卡").click()
    expect(page.get_by_text("今天已打卡。", exact=True)).to_be_visible()
    expect(page.locator(".streak-value")).to_have_text("1")
    expect(
        page.get_by_role("button", name="今天已打卡，当前连续 1 天")
    ).to_be_disabled()

    page.reload(wait_until="networkidle")
    expect(page.get_by_role("heading", name=HABIT_NAME)).to_be_visible()
    expect(page.get_by_text("今天已经完成。", exact=True)).to_be_visible()
    expect(page.locator(".streak-value")).to_have_text("1")
    expect(
        page.get_by_role("button", name="今天已打卡，当前连续 1 天")
    ).to_be_disabled()
    print("P0 冒烟路径：首次设置并打卡，刷新后数据保留，通过")


def run_undo_check_in(page) -> None:
    """P1：撤销打卡，并确认刷新后未打卡状态仍然存在。"""
    page.get_by_role("button", name="撤销今天的打卡").click()
    expect(
        page.get_by_role("group", name="确认撤销今天打卡")
    ).to_be_visible()
    page.get_by_role("button", name="确认撤销").click()

    expect(page.get_by_text("已撤销今天的打卡。", exact=True)).to_be_visible()
    expect(page.locator(".streak-value")).to_have_text("0")
    expect(page.get_by_role("button", name="完成今天打卡")).to_be_enabled()

    page.reload(wait_until="networkidle")
    expect(page.get_by_role("heading", name=HABIT_NAME)).to_be_visible()
    expect(page.get_by_text("今天是新的开始。", exact=True)).to_be_visible()
    expect(page.locator(".streak-value")).to_have_text("0")
    expect(page.get_by_role("button", name="完成今天打卡")).to_be_enabled()
    print("P1 冒烟路径：撤销打卡，刷新后状态恢复，通过")


def main() -> None:
    database_path = require_isolated_database()
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser_channel = os.getenv(
            "CHECKIN_SMOKE_BROWSER_CHANNEL",
            "chrome",
        ).strip()
        launch_options: dict[str, object] = {"headless": True}
        if browser_channel.lower() != "bundled":
            launch_options["channel"] = browser_channel

        browser = playwright.chromium.launch(**launch_options)
        try:
            context = browser.new_context(
                viewport={"width": 1440, "height": 960},
                locale="zh-CN",
                color_scheme="light",
            )
            page = context.new_page()
            page.set_default_timeout(10_000)
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            page.goto(APP_URL)
            page.wait_for_load_state("networkidle")
            run_core_check_in(page)
            run_undo_check_in(page)

            assert not console_errors, f"浏览器控制台错误：{console_errors}"
            assert not page_errors, f"页面运行错误：{page_errors}"
            print(f"本次冒烟数据库：{database_path}")
            print("两条冒烟路径全部通过")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
