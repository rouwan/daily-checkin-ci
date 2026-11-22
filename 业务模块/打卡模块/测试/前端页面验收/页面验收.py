from pathlib import Path

from playwright.sync_api import expect, sync_playwright

test_directory = Path(__file__).resolve().parent
screenshot_directory = test_directory / "验收截图"
console_errors: list[str] = []
page_errors: list[str] = []


def assert_no_horizontal_overflow(page, viewport_name: str) -> None:
    sizes = page.evaluate(
        """() => ({
          viewport: window.innerWidth,
          document: document.documentElement.scrollWidth,
          body: document.body.scrollWidth,
        })"""
    )
    assert sizes["document"] <= sizes["viewport"], (
        f"{viewport_name} 出现横向溢出：{sizes}"
    )
    assert sizes["body"] <= sizes["viewport"], (
        f"{viewport_name} 页面主体出现横向溢出：{sizes}"
    )


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True,
        channel="chrome",
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 960},
        locale="zh-CN",
        color_scheme="light",
    )
    page = context.new_page()
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto("http://127.0.0.1:5173")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="每天，只做一件事。")).to_be_visible()
    assert_no_horizontal_overflow(page, "1440 像素")
    page.screenshot(
        path=screenshot_directory / "首次设置-桌面.png",
        full_page=True,
    )
    print("首次设置页面：通过")

    page.keyboard.press("Tab")
    assert "skip-link" in page.evaluate(
        "() => document.activeElement?.className ?? ''"
    )
    assert page.evaluate(
        "() => getComputedStyle(document.activeElement).outlineStyle"
    ) != "none"
    page.keyboard.press("Enter")
    assert page.evaluate(
        "() => document.activeElement?.id ?? ''"
    ) == "main-content"
    print("键盘跳过链接：通过")

    page.get_by_role("button", name="保存名称").click()
    expect(page.get_by_text("请输入习惯名称。")).to_be_visible()
    assert page.evaluate(
        "() => document.activeElement?.getAttribute('name') ?? ''"
    ) == "habit-name"
    print("空名称拒绝：通过")

    page.get_by_label("习惯名称").fill("长" * 41)
    page.get_by_role("button", name="保存名称").click()
    expect(
        page.get_by_text("习惯名称不能超过 40 个字符。")
    ).to_be_visible()
    print("超长名称拒绝：通过")

    page.get_by_label("习惯名称").fill("读书半小时")
    page.get_by_role("button", name="保存名称").click()
    expect(page.get_by_role("heading", name="读书半小时")).to_be_visible()
    expect(page.get_by_text("习惯名称已保存。")).to_be_visible()
    assert page.evaluate(
        "() => document.activeElement?.id ?? ''"
    ) == "habit-heading"
    print("习惯创建：通过")

    page.screenshot(
        path=screenshot_directory / "打卡前-桌面.png",
        full_page=True,
    )

    page.get_by_role("button", name="完成今天打卡").click()
    expect(page.get_by_text("今天已打卡。", exact=True)).to_be_visible()
    expect(page.get_by_text("今天已经完成。", exact=True)).to_be_visible()
    expect(page.locator(".streak-value")).to_have_text("1")
    expect(
        page.get_by_role("button", name="今天已打卡，当前连续 1 天")
    ).to_be_disabled()
    assert page.evaluate(
        "() => document.activeElement?.textContent?.trim() ?? ''"
    ) == "撤销今天的打卡"
    page.wait_for_timeout(250)
    assert_no_horizontal_overflow(page, "1440 像素已打卡")
    page.screenshot(
        path=screenshot_directory / "已打卡-桌面.png",
        full_page=True,
    )
    print("今日打卡：通过")

    page.get_by_role("button", name="撤销今天的打卡").click()
    expect(
        page.get_by_role("group", name="确认撤销今天打卡")
    ).to_be_visible()
    assert page.evaluate(
        "() => document.activeElement?.textContent?.trim() ?? ''"
    ) == "保留打卡"
    page.screenshot(
        path=screenshot_directory / "撤销确认-桌面.png",
        full_page=True,
    )
    page.get_by_role("button", name="确认撤销").click()
    expect(page.get_by_text("已撤销今天的打卡。")).to_be_visible()
    expect(page.get_by_role("button", name="完成今天打卡")).to_be_enabled()
    expect(page.locator(".streak-value")).to_have_text("0")
    assert page.evaluate(
        "() => document.activeElement?.getAttribute('aria-label') ?? ''"
    ) == "完成今天打卡"
    print("撤销打卡：通过")

    page.get_by_role("button", name="修改名称").click()
    assert page.evaluate(
        "() => document.activeElement?.getAttribute('name') ?? ''"
    ) == "habit-name"
    page.get_by_label("习惯名称").fill("阅读二十分钟")
    page.get_by_role("button", name="保存名称").click()
    expect(
        page.get_by_role("heading", name="阅读二十分钟")
    ).to_be_visible()
    print("习惯名称修改：通过")

    page.get_by_role("button", name="修改名称").click()
    page.get_by_label("习惯名称").fill("坚持" * 20)
    page.get_by_role("button", name="保存名称").click()
    expect(page.get_by_role("heading", name="坚持" * 20)).to_be_visible()
    assert_no_horizontal_overflow(page, "1440 像素长名称")
    page.get_by_role("button", name="修改名称").click()
    page.get_by_label("习惯名称").fill("阅读二十分钟")
    page.get_by_role("button", name="保存名称").click()
    expect(
        page.get_by_role("heading", name="阅读二十分钟")
    ).to_be_visible()
    print("超长名称布局：通过")

    page.get_by_role("button", name="完成今天打卡").click()
    expect(page.get_by_text("今天已打卡。", exact=True)).to_be_visible()
    expect(page.locator(".streak-value")).to_have_text("1")
    page.wait_for_timeout(250)
    page.screenshot(
        path=screenshot_directory / "最终状态-桌面.png",
        full_page=True,
    )

    page.set_viewport_size({"width": 768, "height": 1024})
    page.wait_for_timeout(120)
    assert_no_horizontal_overflow(page, "768 像素")
    page.screenshot(
        path=screenshot_directory / "最终状态-平板.png",
        full_page=True,
    )

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(120)
    assert_no_horizontal_overflow(page, "390 像素")
    page.screenshot(
        path=screenshot_directory / "最终状态-窄屏.png",
        full_page=True,
    )
    print("响应式布局：通过")

    page.set_viewport_size({"width": 320, "height": 700})
    page.wait_for_timeout(120)
    assert_no_horizontal_overflow(page, "320 像素")
    print("最窄屏布局：通过")

    assert not console_errors, f"浏览器控制台错误：{console_errors}"
    assert not page_errors, f"页面运行错误：{page_errors}"
    print("浏览器控制台：通过")
    print("Chrome 版本：", browser.version)
    browser.close()
