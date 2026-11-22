from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggregate_review import COMMENT_MARKER, aggregate


def valid_payload(perspective: str) -> dict[str, object]:
    return {
        "perspective": perspective,
        "summary": "完成本次范围审查。",
        "findings": [],
        "limitations": [],
    }


class AggregateReviewTests(unittest.TestCase):
    def run_aggregate(
        self,
        correctness: object,
        work_necessity: object,
        *,
        correctness_result: str = "success",
        work_necessity_result: str = "success",
    ) -> tuple[bool, str, dict[str, object]]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            correctness_file = root / "correctness.json"
            work_necessity_file = root / "work_necessity.json"
            output_file = root / "summary.md"
            state_file = root / "state.json"
            correctness_file.write_text(
                correctness
                if isinstance(correctness, str)
                else json.dumps(correctness, ensure_ascii=False),
                encoding="utf-8",
            )
            work_necessity_file.write_text(
                work_necessity
                if isinstance(work_necessity, str)
                else json.dumps(work_necessity, ensure_ascii=False),
                encoding="utf-8",
            )

            ok = aggregate(
                correctness_file=correctness_file,
                work_necessity_file=work_necessity_file,
                correctness_result=correctness_result,
                work_necessity_result=work_necessity_result,
                output_file=output_file,
                state_file=state_file,
                head_sha="ABCDEF1234",
            )
            summary = output_file.read_text(encoding="utf-8")
            state = json.loads(state_file.read_text(encoding="utf-8"))
            return ok, summary, state

    def test_valid_results_are_combined(self) -> None:
        ok, summary, state = self.run_aggregate(
            valid_payload("correctness"),
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertEqual(summary.count(COMMENT_MARKER), 1)
        self.assertIn("### 正确性", summary)
        self.assertIn("### 工作必要性", summary)
        self.assertIn("`abcdef1234`", summary)
        self.assertTrue(state["ok"])

    def test_wrong_perspective_makes_summary_invalid(self) -> None:
        ok, summary, state = self.run_aggregate(
            valid_payload("work_necessity"),
            valid_payload("work_necessity"),
        )

        self.assertFalse(ok)
        self.assertIn("结果无效", summary)
        self.assertFalse(state["ok"])
        self.assertIn("correctness", state["errors"])

    def test_invalid_json_is_reported_without_crashing(self) -> None:
        ok, summary, state = self.run_aggregate(
            "{not-json",
            valid_payload("work_necessity"),
        )

        self.assertFalse(ok)
        self.assertIn("不是合法 JSON", summary)
        self.assertIn("correctness", state["errors"])

    def test_findings_are_escaped_and_rendered(self) -> None:
        correctness = valid_payload("correctness")
        correctness["findings"] = [
            {
                "priority": "P1",
                "title": "<script>危险</script>",
                "file": "业务模块/打卡模块/app.py",
                "line": 12,
                "impact": "影响连续天数",
                "evidence": "`today` 比较缺失",
                "recommendation": "恢复日期比较",
            }
        ]

        ok, summary, state = self.run_aggregate(
            correctness,
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertNotIn("<script>", summary)
        self.assertIn("&lt;script&gt;", summary)
        self.assertIn("app.py:12", summary)
        self.assertEqual(state["findings_count"], 1)

    def test_limitations_are_rendered_without_findings(self) -> None:
        correctness = valid_payload("correctness")
        correctness["limitations"] = ["未验证运行时行为"]

        ok, summary, _ = self.run_aggregate(
            correctness,
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertIn("未发现需要报告的问题", summary)
        self.assertIn("审查限制", summary)
        self.assertIn("未验证运行时行为", summary)

    def test_failed_job_result_invalidates_valid_payload(self) -> None:
        ok, summary, state = self.run_aggregate(
            valid_payload("correctness"),
            valid_payload("work_necessity"),
            correctness_result="failure",
        )

        self.assertFalse(ok)
        self.assertIn("执行状态：failure", summary)
        self.assertFalse(state["ok"])
        self.assertIn("job result 为 failure", state["errors"]["correctness"])

    def test_integral_float_line_is_accepted(self) -> None:
        correctness = valid_payload("correctness")
        correctness["findings"] = [
            {
                "priority": "P2",
                "title": "日期比较缺失",
                "file": "app.py",
                "line": 1.0,
                "impact": "连续天数错误",
                "evidence": "比较条件为空",
                "recommendation": "恢复比较",
            }
        ]

        ok, summary, _ = self.run_aggregate(
            correctness,
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertIn("app.py:1", summary)

    def test_empty_file_name_matches_schema_constraint(self) -> None:
        correctness = valid_payload("correctness")
        correctness["findings"] = [
            {
                "priority": "P2",
                "title": "位置缺失",
                "file": "",
                "line": None,
                "impact": "无法定位",
                "evidence": "空文件字段",
                "recommendation": "提供文件路径",
            }
        ]

        ok, _, state = self.run_aggregate(
            correctness,
            valid_payload("work_necessity"),
        )

        self.assertFalse(ok)
        self.assertIn("file 不能为空", state["errors"]["correctness"])

    def test_missing_output_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            work_necessity_file = root / "work_necessity.json"
            work_necessity_file.write_text(
                json.dumps(valid_payload("work_necessity")),
                encoding="utf-8",
            )
            output_file = root / "summary.md"
            state_file = root / "state.json"

            ok = aggregate(
                correctness_file=root / "missing.json",
                work_necessity_file=work_necessity_file,
                correctness_result="failure",
                work_necessity_result="success",
                output_file=output_file,
                state_file=state_file,
                head_sha="unknown",
            )

            self.assertFalse(ok)
            self.assertIn("输出文件不存在", output_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
