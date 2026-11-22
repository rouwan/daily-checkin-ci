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
ALLOWED_PRIORITIES = ("P1", "P2", "P3")


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
    return payload


def _require_string(
    value: Any,
    field: str,
    *,
    max_length: int,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ReviewValidationError(f"{field} 必须是字符串")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise ReviewValidationError(f"{field} 不能为空")
    if len(normalized) > max_length:
        raise ReviewValidationError(f"{field} 超过 {max_length} 个字符")
    return normalized


def _validate_optional_string(
    value: Any,
    field: str,
    *,
    max_length: int,
) -> str | None:
    if value is None:
        return None
    return _require_string(value, field, max_length=max_length)


def _validate_payload(
    payload: dict[str, Any],
    expected_perspective: str,
) -> dict[str, Any]:
    required_keys = {"perspective", "summary", "findings", "limitations"}
    if set(payload) != required_keys:
        missing = sorted(required_keys - set(payload))
        extra = sorted(set(payload) - required_keys)
        details: list[str] = []
        if missing:
            details.append(f"缺少字段 {', '.join(missing)}")
        if extra:
            details.append(f"存在未知字段 {', '.join(extra)}")
        raise ReviewValidationError("；".join(details))

    perspective = _require_string(
        payload["perspective"],
        "perspective",
        max_length=40,
    )
    if perspective != expected_perspective:
        raise ReviewValidationError(
            f"perspective 应为 {expected_perspective}，实际为 {perspective}"
        )

    summary = _require_string(payload["summary"], "summary", max_length=800)

    findings_value = payload["findings"]
    if not isinstance(findings_value, list):
        raise ReviewValidationError("findings 必须是数组")
    if len(findings_value) > 5:
        raise ReviewValidationError("findings 最多允许 5 项")

    findings: list[dict[str, Any]] = []
    finding_keys = {
        "priority",
        "title",
        "file",
        "line",
        "impact",
        "evidence",
        "recommendation",
    }
    for index, finding_value in enumerate(findings_value, start=1):
        if not isinstance(finding_value, dict):
            raise ReviewValidationError(f"第 {index} 个 finding 必须是对象")
        if set(finding_value) != finding_keys:
            raise ReviewValidationError(
                f"第 {index} 个 finding 必须且只能包含约定字段"
            )

        priority = _require_string(
            finding_value["priority"],
            f"findings[{index}].priority",
            max_length=2,
        )
        if priority not in ALLOWED_PRIORITIES:
            raise ReviewValidationError(
                f"findings[{index}].priority 必须是 P1、P2 或 P3"
            )

        line = finding_value["line"]
        if line is not None and (
            isinstance(line, bool) or not isinstance(line, int) or line < 1
        ):
            raise ReviewValidationError(
                f"findings[{index}].line 必须是正整数或 null"
            )

        findings.append(
            {
                "priority": priority,
                "title": _require_string(
                    finding_value["title"],
                    f"findings[{index}].title",
                    max_length=120,
                ),
                "file": _validate_optional_string(
                    finding_value["file"],
                    f"findings[{index}].file",
                    max_length=240,
                ),
                "line": line,
                "impact": _require_string(
                    finding_value["impact"],
                    f"findings[{index}].impact",
                    max_length=500,
                ),
                "evidence": _require_string(
                    finding_value["evidence"],
                    f"findings[{index}].evidence",
                    max_length=800,
                ),
                "recommendation": _require_string(
                    finding_value["recommendation"],
                    f"findings[{index}].recommendation",
                    max_length=500,
                ),
            }
        )

    limitations_value = payload["limitations"]
    if not isinstance(limitations_value, list):
        raise ReviewValidationError("limitations 必须是数组")
    if len(limitations_value) > 3:
        raise ReviewValidationError("limitations 最多允许 3 项")
    limitations = [
        _require_string(
            item,
            f"limitations[{index}]",
            max_length=300,
        )
        for index, item in enumerate(limitations_value, start=1)
    ]

    return {
        "perspective": perspective,
        "summary": summary,
        "findings": findings,
        "limitations": limitations,
    }


def _escape_markdown(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return (
        compact.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_location(finding: dict[str, Any]) -> str:
    file_name = finding["file"]
    if file_name is None:
        return "未提供具体文件"
    safe_file = _escape_markdown(file_name).replace("`", "'")
    if finding["line"] is None:
        return f"`{safe_file}`"
    return f"`{safe_file}:{finding['line']}`"


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

    lines.extend([_escape_markdown(payload["summary"]), ""])
    findings = payload["findings"]
    if not findings:
        lines.extend(["未发现需要报告的问题。", ""])
        return lines

    for finding in findings:
        lines.extend(
            [
                f"#### [{finding['priority']}] {_escape_markdown(finding['title'])}",
                "",
                f"- 位置：{_format_location(finding)}",
                f"- 影响：{_escape_markdown(finding['impact'])}",
                f"- 证据：{_escape_markdown(finding['evidence'])}",
                f"- 建议：{_escape_markdown(finding['recommendation'])}",
                "",
            ]
        )

    limitations = payload["limitations"]
    if limitations:
        lines.extend(["审查限制：", ""])
        lines.extend(
            f"- {_escape_markdown(limitation)}" for limitation in limitations
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
    state_file: Path,
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
        try:
            raw_payload = _read_output(files[perspective], perspective)
            payloads[perspective] = _validate_payload(raw_payload, perspective)
        except ReviewValidationError as error:
            payloads[perspective] = None
            errors[perspective] = str(error)

    all_valid = not errors
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

    state = {
        "ok": all_valid,
        "errors": errors,
        "findings_count": findings_count,
    }
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return all_valid


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--correctness-file", type=Path, required=True)
    parser.add_argument("--work-necessity-file", type=Path, required=True)
    parser.add_argument("--correctness-result", default="success")
    parser.add_argument("--work-necessity-result", default="success")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
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
        state_file=args.state,
        head_sha=args.head_sha,
    )
    print("双视角审查汇总完成" if ok else "双视角审查汇总未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
