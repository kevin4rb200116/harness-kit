"""Selftests de ``run_verb.py``: ejecuta verbos del manifiesto sin shell."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SELFTEST_DIR = Path(__file__).resolve().parent
KIT_ROOT = SELFTEST_DIR.parent
RUN_VERB = KIT_ROOT / "core" / "bin" / "run_verb.py"
PY = sys.executable


class RunVerbTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "demo"
        self.root.mkdir(parents=True)

    def write_config(self, commands: dict[str, str]) -> None:
        (self.root / "harness.config.json").write_text(
            json.dumps({"commands": commands}), encoding="utf-8"
        )

    def run_verb(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [PY, str(RUN_VERB), *args, "--root", str(self.root)],
            capture_output=True,
            text=True,
        )

    def test_runs_the_configured_command(self) -> None:
        self.write_config({"test": f"{PY} -c pass"})
        result = self.run_verb("test")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prints_the_command(self) -> None:
        self.write_config({"test": f"{PY} -c pass"})
        result = self.run_verb("test")
        self.assertIn(f"$ {PY} -c pass", result.stdout)

    def test_command_echo_precedes_the_output(self) -> None:
        self.write_config({"test": f'{PY} -c "print(\'salida\')"'})
        result = self.run_verb("test")
        lines = result.stdout.splitlines()
        self.assertTrue(lines and lines[0].startswith("$ "), result.stdout)
        self.assertIn("salida", lines[1:], result.stdout)

    def test_propagates_the_exit_code(self) -> None:
        self.write_config({"test": f'{PY} -c "raise SystemExit(7)"'})
        result = self.run_verb("test")
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)

    def test_replaces_the_file_placeholder(self) -> None:
        self.write_config(
            {"mutation": f'{PY} -c "import sys; print(sys.argv[1])" {{file}}'}
        )
        result = self.run_verb("mutation", "--file", "src/notes.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("src/notes.py", result.stdout)

    def test_file_placeholder_requires_the_file(self) -> None:
        self.write_config({"mutation": "tool {file}"})
        result = self.run_verb("mutation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--file", result.stderr + result.stdout)

    def test_missing_verb_fails(self) -> None:
        self.write_config({})
        result = self.run_verb("test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commands.test", result.stderr + result.stdout)

    def test_empty_verb_fails(self) -> None:
        self.write_config({"test": "   "})
        result = self.run_verb("test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commands.test", result.stderr + result.stdout)

    def test_unknown_verb_fails(self) -> None:
        self.write_config({"test": f"{PY} -c pass"})
        result = self.run_verb("deploy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commands.deploy", result.stderr + result.stdout)

    def test_missing_config_fails(self) -> None:
        result = self.run_verb("test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("harness.config.json", result.stderr + result.stdout)

    def test_invalid_json_fails(self) -> None:
        (self.root / "harness.config.json").write_text("{", encoding="utf-8")
        result = self.run_verb("test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JSON válido", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
