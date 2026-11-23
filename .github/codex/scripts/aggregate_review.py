#!/usr/bin/env python3
"""校验并汇总两个 Codex 审查视角。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

COMMENT_MARKER = "<!-- codex-two-perspective-review -->"
EXPECTED_PERSPECTIVES = ("correctness", "work_necessity")
PERSPECTIVE_LABELS = {
    "correctness": "正确性",
    "work_necessity": "工作必要性",
}


class ReviewValidationError(ValueError):
    """审查输出不符合约定。"""


def _read_output(path: Path, perspective: str) -> dict[str, Any]:
    if not path.is_file():
        raise ReviewValidationError(f"{perspective} 输出文件不存在")

    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise ReviewValidationError(f"{perspective} 输出为空")

    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.DOTALL)
    if fenced:
        raw = fenced.group(1)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ReviewValidationError(
            f"{perspective} 输出不是合法 JSON：{error.msg}"
        ) from error

    if not isinstance(payload, dict):
        raise ReviewValidationError(f"{perspective} 输出必须是 JSON 对象")
    if payload.get("perspective") != perspective:
        raise ReviewValidationError(
            f"{perspective} 输出的 perspective 不匹配"
        )
    if not isinstance(payload.get("summary"), str):
        raise ReviewValidationError(f"{perspective} 输出的 summary 不是字符串")
    if not isinstance(payload.get("findings"), list):
        raise ReviewValidationError(f"{perspective} 输出的 findings 不是数组")
    if not isinstance(payload.get("limitations"), list):
        raise ReviewValidationError(f"{perspective} 输出的 limitations 不是数组")
    if any(not isinstance(item, dict) for item in payload["findings"]):
        raise ReviewValidationError(
            f"{perspective} 输出的 findings 项不是对象"
        )
    return payload


def _escape_markdown(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return (
        compact.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_location(finding: dict[str, Any]) -> str:
    file_name = finding.get("file")
    if file_name is None:
        return "未提供具体文件"
    safe_file = _escape_markdown(str(file_name)).replace("`", "'")
    line = finding.get("line")
    if line is None:
        return f"`{safe_file}`"
    return f"`{safe_file}:{line}`"


def _render_perspective(
    perspective: str,
    payload: dict[str, Any] | None,
    job_result: str,
    error: str | None,
) -> list[str]:
    label = PERSPECTIVE_LABELS[perspective]
    lines = [f"### {label}", ""]

    if payload is None:
        result_text = "执行失败" if job_result != "success" else "结果无效"
        lines.extend([f"**{result_text}**", ""])
        if error:
            lines.extend([_escape_markdown(error), ""])
        return lines

    if job_result != "success":
        lines.extend([f"**执行状态：{_escape_markdown(job_result)}**", ""])
        if error:
            lines.extend([_escape_markdown(error), ""])

    lines.extend([_escape_markdown(str(payload.get("summary", ""))), ""])
    findings = payload.get("findings", [])
    if not findings:
        lines.extend(["未发现需要报告的问题。", ""])
    else:
        for finding in findings:
            lines.extend(
                [
                    f"#### [{finding['priority']}] {_escape_markdown(finding['title'])}",
                    "",
                    f"- 位置：{_format_location(finding)}",
                    f"- 影响：{_escape_markdown(str(finding.get('impact', '')))}",
                    f"- 证据：{_escape_markdown(str(finding.get('evidence', '')))}",
                    f"- 建议：{_escape_markdown(str(finding.get('recommendation', '')))}",
                    "",
                ]
            )

    limitations = payload.get("limitations", [])
    if limitations:
        lines.extend(["审查限制：", ""])
        lines.extend(
            f"- {_escape_markdown(str(limitation))}" for limitation in limitations
        )
        lines.append("")
    return lines


def aggregate(
    *,
    correctness_file: Path,
    work_necessity_file: Path,
    correctness_result: str,
    work_necessity_result: str,
    output_file: Path,
    head_sha: str,
) -> bool:
    files = {
        "correctness": correctness_file,
        "work_necessity": work_necessity_file,
    }
    results = {
        "correctness": correctness_result,
        "work_necessity": work_necessity_result,
    }

    payloads: dict[str, dict[str, Any] | None] = {}
    errors: dict[str, str] = {}

    for perspective in EXPECTED_PERSPECTIVES:
        perspective_errors: list[str] = []
        try:
            payloads[perspective] = _read_output(files[perspective], perspective)
        except ReviewValidationError as error:
            payloads[perspective] = None
            perspective_errors.append(str(error))
        if results[perspective] != "success":
            perspective_errors.append(
                f"agent job result 为 {results[perspective]}"
            )
        if perspective_errors:
            errors[perspective] = "；".join(perspective_errors)

    all_valid = not errors and all(
        result == "success" for result in results.values()
    )
    safe_sha = re.sub(r"[^0-9a-f]", "", head_sha.lower())[:40] or "unknown"
    findings_count = sum(
        len(payload["findings"])
        for payload in payloads.values()
        if payload is not None
    )

    lines = [
        COMMENT_MARKER,
        "## Codex 双视角审查",
        "",
        f"提交：`{safe_sha}`",
        "",
        (
            f"共发现 {findings_count} 个问题。"
            if all_valid
            else "审查未完整完成，请查看下方执行状态。"
        ),
        "",
    ]

    for perspective in EXPECTED_PERSPECTIVES:
        lines.extend(
            _render_perspective(
                perspective,
                payloads[perspective],
                results[perspective],
                errors.get(perspective),
            )
        )

    lines.extend(
        [
            "---",
            "",
            "这是建议型 AI 审查，不替代测试、冒烟验证、分支保护或人工审查。",
            "",
        ]
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")

    return all_valid


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--correctness-file", type=Path, required=True)
    parser.add_argument("--work-necessity-file", type=Path, required=True)
    parser.add_argument("--correctness-result", default="success")
    parser.add_argument("--work-necessity-result", default="success")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--head-sha", default="unknown")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    ok = aggregate(
        correctness_file=args.correctness_file,
        work_necessity_file=args.work_necessity_file,
        correctness_result=args.correctness_result,
        work_necessity_result=args.work_necessity_result,
        output_file=args.output,
        head_sha=args.head_sha,
    )
    print("双视角审查汇总完成" if ok else "双视角审查汇总未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
