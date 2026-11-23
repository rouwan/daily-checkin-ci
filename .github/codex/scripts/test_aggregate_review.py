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
    ) -> tuple[bool, str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            correctness_file = root / "correctness.json"
            work_necessity_file = root / "work_necessity.json"
            output_file = root / "summary.md"
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
                head_sha="ABCDEF1234",
            )
            summary = output_file.read_text(encoding="utf-8")
            return ok, summary

    def test_valid_results_are_combined(self) -> None:
        ok, summary = self.run_aggregate(
            valid_payload("correctness"),
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertEqual(summary.count(COMMENT_MARKER), 1)
        self.assertIn("### 正确性", summary)
        self.assertIn("### 工作必要性", summary)
        self.assertIn("`abcdef1234`", summary)

    def test_wrong_perspective_makes_summary_invalid(self) -> None:
        ok, summary = self.run_aggregate(
            valid_payload("work_necessity"),
            valid_payload("work_necessity"),
        )

        self.assertFalse(ok)
        self.assertIn("结果无效", summary)
        self.assertIn("perspective 不匹配", summary)

    def test_invalid_json_is_reported_without_crashing(self) -> None:
        ok, summary = self.run_aggregate(
            "{not-json",
            valid_payload("work_necessity"),
        )

        self.assertFalse(ok)
        self.assertIn("不是合法 JSON", summary)

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

        ok, summary = self.run_aggregate(
            correctness,
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertNotIn("<script>", summary)
        self.assertIn("&lt;script&gt;", summary)
        self.assertIn("app.py:12", summary)

    def test_limitations_are_rendered_without_findings(self) -> None:
        correctness = valid_payload("correctness")
        correctness["limitations"] = ["未验证运行时行为"]

        ok, summary = self.run_aggregate(
            correctness,
            valid_payload("work_necessity"),
        )

        self.assertTrue(ok)
        self.assertIn("未发现需要报告的问题", summary)
        self.assertIn("审查限制", summary)
        self.assertIn("未验证运行时行为", summary)

    def test_failed_job_result_invalidates_valid_payload(self) -> None:
        ok, summary = self.run_aggregate(
            valid_payload("correctness"),
            valid_payload("work_necessity"),
            correctness_result="failure",
        )

        self.assertFalse(ok)
        self.assertIn("执行状态：failure", summary)
        self.assertIn("agent job result 为 failure", summary)

    def test_missing_output_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            work_necessity_file = root / "work_necessity.json"
            work_necessity_file.write_text(
                json.dumps(valid_payload("work_necessity")),
                encoding="utf-8",
            )
            output_file = root / "summary.md"

            ok = aggregate(
                correctness_file=root / "missing.json",
                work_necessity_file=work_necessity_file,
                correctness_result="failure",
                work_necessity_result="success",
                output_file=output_file,
                head_sha="unknown",
            )

            self.assertFalse(ok)
            self.assertIn("输出文件不存在", output_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
