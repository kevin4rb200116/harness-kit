"""Selftests de la máquina de estados (``core/bin/harness.py``).

Ejecutar desde la raíz del repo::

    python3 -m unittest discover -s harness-kit/selftest -v
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SELFTEST_DIR = Path(__file__).resolve().parent
KIT_ROOT = SELFTEST_DIR.parent
HARNESS = KIT_ROOT / "core" / "bin" / "harness.py"
FIXTURE = SELFTEST_DIR / "fixtures" / "complete_feature"


class HarnessCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "project"
        shutil.copytree(FIXTURE, self.root)
        (self.root / "init.sh").chmod(0o755)

    # -- helpers ---------------------------------------------------------

    def harness(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(HARNESS), "--root", str(self.root), *args],
            capture_output=True,
            text=True,
        )

    def assert_ok(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def assert_fails(self, result: subprocess.CompletedProcess, *needles: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        blob = result.stdout + result.stderr
        for needle in needles:
            self.assertIn(needle.lower(), blob.lower(), blob)

    def read_json(self, relative: str) -> dict:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def write_json(self, relative: str, data: dict) -> None:
        path = self.root / relative
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def feature(self) -> dict:
        data = self.read_json("feature_list.json")
        return data["features"][0]

    def set_raw_status(self, status: str) -> None:
        data = self.read_json("feature_list.json")
        data["features"][0]["status"] = status
        self.write_json("feature_list.json", data)

    def approve(self) -> None:
        result = self.harness("approve", "1")
        self.assert_ok(result)

    # -- status / next ---------------------------------------------------

    def test_status_lists_features(self) -> None:
        result = self.harness("status")
        self.assert_ok(result)
        self.assertIn("greet", result.stdout)
        self.assertIn("spec_ready", result.stdout)

    def test_next_reports_approval_phase(self) -> None:
        result = self.harness("next", "--json")
        self.assert_ok(result)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["phase"], "approval")
        self.assertEqual(payload["feature"]["id"], 1)

    def test_next_reports_tdd_after_approval(self) -> None:
        self.approve()
        tasks = self.root / "specs" / "greet" / "tasks.md"
        tasks.write_text(
            tasks.read_text(encoding="utf-8").replace("- [x]", "- [ ]"),
            encoding="utf-8",
        )
        result = self.harness("next", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["phase"], "tdd")

    def test_next_reports_done_when_artifacts_complete(self) -> None:
        self.approve()
        result = self.harness("next", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["phase"], "done")

    # -- approve ---------------------------------------------------------

    def test_approve_writes_hash_and_moves_to_in_progress(self) -> None:
        self.approve()
        self.assertEqual(self.feature()["status"], "in_progress")
        approval = self.read_json(".harness/approvals/greet.json")
        self.assertEqual(approval["feature"], "greet")
        self.assertEqual(approval["scenarios"], ["@s1", "@s2"])
        self.assertEqual(len(approval["feature_sha256"]), 64)
        self.assertEqual(approval["approved_by"], "human")

    def test_approve_requires_feature_file(self) -> None:
        (self.root / "features" / "greet.feature").unlink()
        result = self.harness("approve", "1")
        self.assert_fails(result, "contrato ejecutable", "greet.feature")

    def test_approve_requires_specs(self) -> None:
        (self.root / "specs" / "greet" / "requirements.md").unlink()
        result = self.harness("approve", "1")
        self.assert_fails(result, "spec", "requirements.md")

    def test_second_approve_refreshes_without_error(self) -> None:
        self.approve()
        self.assert_ok(self.harness("approve", "1"))
        self.assertEqual(self.feature()["status"], "in_progress")

    def test_approval_tolerates_format_noise(self) -> None:
        self.approve()
        path = self.root / "features" / "greet.feature"
        text = path.read_text(encoding="utf-8")
        path.write_bytes(
            text.replace("\n", "   \r\n").encode("utf-8")
        )
        result = self.harness("status", "--json")
        row = json.loads(result.stdout)["features"][0]
        self.assertEqual(row["approval"], "valid")

    def test_editing_feature_invalidates_approval(self) -> None:
        self.approve()
        path = self.root / "features" / "greet.feature"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n  @s3\n  Scenario: nuevo\n",
            encoding="utf-8",
        )
        row = json.loads(self.harness("status", "--json").stdout)["features"][0]
        self.assertEqual(row["approval"], "stale")
        self.assert_fails(self.harness("validate"), "aprobación", "caducada")

    # -- set -------------------------------------------------------------

    def test_spec_ready_requires_spec_files(self) -> None:
        self.set_raw_status("pending")
        shutil.rmtree(self.root / "specs" / "greet")
        result = self.harness("set", "1", "spec_ready")
        self.assert_fails(result, "requirements.md", "design.md", "tasks.md")

    def test_spec_ready_succeeds_with_specs(self) -> None:
        self.set_raw_status("pending")
        self.assert_ok(self.harness("set", "1", "spec_ready"))
        self.assertEqual(self.feature()["status"], "spec_ready")

    def test_in_progress_requires_approval(self) -> None:
        result = self.harness("set", "1", "in_progress")
        self.assert_fails(result, "aprobación", "approve")

    def test_in_progress_after_approval(self) -> None:
        self.approve()
        self.assert_ok(self.harness("set", "1", "in_progress"))

    def test_illegal_transition_needs_force(self) -> None:
        self.set_raw_status("pending")
        result = self.harness("set", "1", "done")
        self.assert_fails(result, "transición no permitida")
        forced = self.harness("set", "1", "done", "--force")
        self.assert_ok(forced)
        self.assertEqual(self.feature()["status"], "done")

    def test_done_requires_judge_report(self) -> None:
        self.approve()
        (self.root / ".harness" / "reports" / "judge_greet.json").unlink()
        result = self.harness("set", "1", "done")
        self.assert_fails(result, "judge")

    def test_done_requires_mutation_pass(self) -> None:
        self.approve()
        self.write_json(
            ".harness/reports/mutation_greet.json",
            {"verdict": "FAIL", "score": 100},
        )
        result = self.harness("set", "1", "done")
        self.assert_fails(result, "mutación", "pass")

    def test_done_requires_mutation_above_threshold(self) -> None:
        self.approve()
        self.write_json(
            ".harness/reports/mutation_greet.json",
            {"verdict": "PASS", "score": 50, "threshold": 100},
        )
        result = self.harness("set", "1", "done")
        self.assert_fails(result, "umbral")

    def test_done_requires_all_tasks_checked(self) -> None:
        self.approve()
        tasks = self.root / "specs" / "greet" / "tasks.md"
        tasks.write_text(
            tasks.read_text(encoding="utf-8").replace("- [x]", "- [ ]"),
            encoding="utf-8",
        )
        result = self.harness("set", "1", "done")
        self.assert_fails(result, "task")

    def test_done_runs_verify(self) -> None:
        self.approve()
        init = self.root / "init.sh"
        init.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
        result = self.harness("set", "1", "done")
        self.assert_fails(result, "verify")

    def test_full_pipeline_reaches_done(self) -> None:
        self.approve()
        self.assert_ok(self.harness("set", "1", "done"))
        self.assertEqual(self.feature()["status"], "done")
        self.assert_ok(self.harness("validate"))

    # -- blocked ---------------------------------------------------------

    def test_block_requires_reason(self) -> None:
        result = self.harness("block", "1", "")
        self.assert_fails(result, "razón")

    def test_block_and_unblock(self) -> None:
        self.assert_ok(self.harness("block", "1", "falta decisión de API"))
        feature = self.feature()
        self.assertEqual(feature["status"], "blocked")
        self.assertEqual(feature["blocked_reason"], "falta decisión de API")
        self.assert_ok(self.harness("set", "1", "pending"))
        self.assertNotIn("blocked_reason", self.feature())

    def test_approve_rejects_blocked_feature(self) -> None:
        self.assert_ok(self.harness("block", "1", "esperando decisión"))
        result = self.harness("approve", "1")
        self.assert_fails(result, "bloqueada")

    # -- validate / note ------------------------------------------------

    def test_validate_blocked_requires_reason(self) -> None:
        data = self.read_json("feature_list.json")
        data["features"][0]["status"] = "blocked"
        self.write_json("feature_list.json", data)
        result = self.harness("validate")
        self.assert_fails(result, "blocked_reason")

    def test_non_sdd_in_progress_still_requires_contract(self) -> None:
        data = self.read_json("feature_list.json")
        data["features"][0]["sdd"] = False
        data["features"][0]["status"] = "in_progress"
        self.write_json("feature_list.json", data)
        result = self.harness("validate")
        self.assert_fails(result, "aprobación")

    def test_validate_detects_two_in_progress(self) -> None:
        data = self.read_json("feature_list.json")
        data["features"].append(
            {
                "id": 2,
                "name": "other",
                "title": "Otra",
                "description": "",
                "acceptance": [],
                "sdd": False,
                "status": "in_progress",
            }
        )
        self.write_json("feature_list.json", data)
        self.approve()
        data = self.read_json("feature_list.json")
        data["features"][1]["status"] = "in_progress"
        self.write_json("feature_list.json", data)
        result = self.harness("validate")
        self.assert_fails(result, "in_progress", "máximo 1")

    def test_validate_detects_duplicate_names(self) -> None:
        data = self.read_json("feature_list.json")
        data["features"].append(dict(data["features"][0], id=2, sdd=False, status="pending"))
        self.write_json("feature_list.json", data)
        result = self.harness("validate")
        self.assert_fails(result, "name duplicado")

    def test_validate_ok_after_approval(self) -> None:
        self.approve()
        self.assert_ok(self.harness("validate"))

    def test_note_appends_to_current(self) -> None:
        self.assert_ok(self.harness("note", "empezando el TDD"))
        text = (self.root / "progress" / "current.md").read_text(encoding="utf-8")
        self.assertIn("empezando el TDD", text)


if __name__ == "__main__":
    unittest.main()
