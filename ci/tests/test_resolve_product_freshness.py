from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ci/scripts/resolve_product_freshness.py"
EXPECTED_MATRIX = {
    "include": [{"platform": "alibabacloud", "skill": "aliyun-product-freshness"}]
}


class ResolveProductFreshnessTests(unittest.TestCase):
    def run_resolver(self, event: str, selected: str) -> dict[str, str]:
        with tempfile.NamedTemporaryFile(mode="r+", encoding="utf-8") as output:
            env = os.environ | {
                "GITHUB_EVENT_NAME": event,
                "SELECTED_PLATFORM": selected,
                "GITHUB_OUTPUT": output.name,
            }
            subprocess.run([sys.executable, str(SCRIPT)], env=env, check=True)
            output.seek(0)
            return dict(line.rstrip("\n").split("=", 1) for line in output)

    def test_schedule_selects_all_configured_skills(self) -> None:
        result = self.run_resolver("schedule", "")
        self.assertEqual(json.loads(result["matrix"]), EXPECTED_MATRIX)
        self.assertEqual(result["skipped"], "azure,aws,huaweicloud,googlecloud")

    def test_manual_all_selects_only_configured_skills(self) -> None:
        result = self.run_resolver("workflow_dispatch", "all")
        self.assertEqual(json.loads(result["matrix"]), EXPECTED_MATRIX)

    def test_manual_platform_selects_its_skill(self) -> None:
        result = self.run_resolver("workflow_dispatch", "alibabacloud")
        self.assertEqual(json.loads(result["matrix"]), EXPECTED_MATRIX)
        self.assertEqual(result["skipped"], "")

    def test_manual_selection_without_skill_fails_clearly(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            env=os.environ | {
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "SELECTED_PLATFORM": "azure",
            },
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No skill is configured for azure", result.stderr)


if __name__ == "__main__":
    unittest.main()
