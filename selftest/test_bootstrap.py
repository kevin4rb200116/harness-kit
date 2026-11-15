"""Selftests del bootstrap y del proyecto generado."""
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
BOOTSTRAP = KIT_ROOT / "bootstrap.py"


class BootstrapTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.target = self.base / "demo"

    # -- helpers ---------------------------------------------------------

    def bootstrap(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(BOOTSTRAP), *args],
            capture_output=True,
            text=True,
        )

    def init(self, *extra: str) -> subprocess.CompletedProcess:
        return self.bootstrap(
            "init", "--target", str(self.target), "--profile", "python-unittest", *extra
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

    def harness(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(self.target / "harness" / "bin" / "harness.py"),
                "--root",
                str(self.target),
                *args,
            ],
            capture_output=True,
            text=True,
        )

    # -- init ------------------------------------------------------------

    def test_init_creates_expected_layout(self) -> None:
        self.assert_ok(self.init())
        expected = [
            "AGENTS.md",
            "harness.config.json",
            "feature_list.json",
            "project-spec.md",
            "progress/current.md",
            "progress/history.md",
            "harness/bin/harness.py",
            "harness/bin/stack_check.py",
            "harness/bin/run_verb.py",
            "harness/process/workflow.md",
            "harness/process/spec.md",
            "harness/process/traceability.md",
            "harness/roles/craftsman_lead.md",
            "harness/roles/judge.md",
            "harness/schemas/feature_list.schema.json",
            "harness/templates/specs/requirements.md",
            "harness/profiles/python-unittest/profile.json",
            "harness/adapters/generic/README.md",
            "harness/VERSION",
            "harness/GENERATED.md",
            "docs/architecture.md",
            "docs/conventions.md",
            "docs/verification.md",
            "init.sh",
            "compose.yaml",
            "Dockerfile",
            "tools/mutate.py",
            "tools/clean.sh",
            "src/__init__.py",
            "tests/__init__.py",
        ]
        for relative in expected:
            self.assertTrue(
                (self.target / relative).is_file(), f"falta {relative}"
            )

    def test_init_renders_project_name(self) -> None:
        self.assert_ok(self.init("--project", "acme"))
        agents = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        spec = (self.target / "project-spec.md").read_text(encoding="utf-8")
        self.assertIn("acme", agents)
        self.assertIn("python-unittest", agents)
        self.assertIn("acme", spec)
        self.assertNotIn("{{", agents)

    def test_config_reflects_profile(self) -> None:
        self.assert_ok(self.init())
        config = json.loads(
            (self.target / "harness.config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["profile"], "python-unittest")
        self.assertEqual(config["adapter"], "generic")
        self.assertEqual(config["commands"]["verify"], "./init.sh")
        self.assertEqual(config["mutation"]["threshold"], 100)
        self.assertEqual(config["paths"]["source"], "src")

    def test_config_declares_the_five_verbs(self) -> None:
        self.assert_ok(self.init())
        config = json.loads(
            (self.target / "harness.config.json").read_text(encoding="utf-8")
        )
        for verb in ("check", "build", "test", "mutation", "clean"):
            self.assertTrue(
                config["commands"].get(verb), f"commands.{verb} vacío o ausente"
            )
        self.assertEqual(config["commands"]["build"], "docker compose build")
        self.assertTrue(
            config["commands"]["test"].startswith(
                "docker compose run --rm app python3 -m unittest"
            )
        )
        self.assertTrue(
            config["commands"]["mutation"].startswith(
                "docker compose run --rm app python3 tools/mutate.py"
            )
        )
        self.assertEqual(config["commands"]["clean"], "bash tools/clean.sh")
        self.assertEqual(config["agent_forbidden"], ["build", "clean"])

    @unittest.skipUnless(shutil.which("docker"), "docker no disponible")
    def test_init_runs_the_stack_contract(self) -> None:
        self.assert_ok(self.init())
        result = subprocess.run(
            ["./init.sh"], cwd=self.target, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("contrato del stack", result.stdout)

    def test_undocumented_command_breaks_the_contract(self) -> None:
        self.assert_ok(self.init())
        config_path = self.target / "harness.config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["commands"]["build"] = "python3 -m compileall -f src"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(self.target / "harness" / "bin" / "stack_check.py"),
                "--root",
                str(self.target),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("commands.build", result.stdout)

    def test_init_refuses_non_empty_target_without_force(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "keep.txt").write_text("hola", encoding="utf-8")
        self.assert_fails(self.init(), "no está vacío")
        self.assertTrue((self.target / "keep.txt").is_file())

    def test_init_force_preserves_user_files(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "keep.txt").write_text("hola", encoding="utf-8")
        self.assert_ok(self.init("--force"))
        self.assertTrue((self.target / "keep.txt").is_file())
        self.assertTrue((self.target / "AGENTS.md").is_file())

    def test_unknown_profile_fails(self) -> None:
        result = self.bootstrap(
            "init", "--target", str(self.target), "--profile", "cobol"
        )
        self.assert_fails(result, "perfil desconocido", "python-unittest")

    def test_unknown_adapter_fails(self) -> None:
        result = self.bootstrap(
            "init",
            "--target",
            str(self.target),
            "--profile",
            "python-unittest",
            "--adapter",
            "telepathy",
        )
        self.assert_fails(result, "adapter desconocido", "generic")

    # -- proyecto generado ----------------------------------------------

    @unittest.skipUnless(shutil.which("docker"), "docker no disponible")
    def test_scaffolded_init_sh_is_green(self) -> None:
        self.assert_ok(self.init())
        result = subprocess.run(
            ["./init.sh"], cwd=self.target, capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("entorno listo", result.stdout)

    def test_scaffolded_status_and_validate(self) -> None:
        self.assert_ok(self.init())
        self.assert_ok(self.harness("status"))
        self.assert_ok(self.harness("validate"))

    def test_scaffolded_next_without_features(self) -> None:
        self.assert_ok(self.init())
        result = self.harness("next", "--json")
        self.assert_ok(result)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["phase"], "all_done")

    def test_check_command_is_green(self) -> None:
        self.assert_ok(self.init())
        result = self.bootstrap("check", "--target", str(self.target))
        self.assert_ok(result)

    def test_gitignore_created(self) -> None:
        self.assert_ok(self.init())
        text = (self.target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__/", text)
        self.assertIn("*.py[cod]", text)

    # -- render ----------------------------------------------------------

    def test_render_refreshes_generated_and_preserves_project(self) -> None:
        self.assert_ok(self.init())
        spec = self.target / "project-spec.md"
        spec.write_text("# Mi spec a mano\n", encoding="utf-8")
        config = self.target / "harness.config.json"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                '"threshold": 100', '"threshold": 80'
            ),
            encoding="utf-8",
        )
        workflow = self.target / "harness" / "process" / "workflow.md"
        workflow.write_text("pisoteado\n", encoding="utf-8")

        self.assert_ok(self.bootstrap("render", "--target", str(self.target)))

        self.assertEqual(spec.read_text(encoding="utf-8"), "# Mi spec a mano\n")
        self.assertIn(
            '"threshold": 80', config.read_text(encoding="utf-8")
        )
        self.assertNotEqual(workflow.read_text(encoding="utf-8"), "pisoteado\n")
        self.assert_ok(self.bootstrap("check", "--target", str(self.target)))

    def test_render_preserves_compose_and_dockerfile(self) -> None:
        self.assert_ok(self.init())
        compose = self.target / "compose.yaml"
        dockerfile = self.target / "Dockerfile"
        compose.write_text("# compose editado\n", encoding="utf-8")
        dockerfile.write_text("# Dockerfile editado\n", encoding="utf-8")

        self.assert_ok(self.bootstrap("render", "--target", str(self.target)))

        self.assertEqual(compose.read_text(encoding="utf-8"), "# compose editado\n")
        self.assertEqual(
            dockerfile.read_text(encoding="utf-8"), "# Dockerfile editado\n"
        )

    def test_render_restores_missing_compose_files(self) -> None:
        self.assert_ok(self.init())
        (self.target / "compose.yaml").unlink()
        (self.target / "Dockerfile").unlink()

        self.assert_ok(self.bootstrap("render", "--target", str(self.target)))

        self.assertTrue((self.target / "compose.yaml").is_file())
        self.assertTrue((self.target / "Dockerfile").is_file())

    def test_render_backfills_missing_verbs(self) -> None:
        self.assert_ok(self.init())
        config_path = self.target / "harness.config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        del config["commands"]["build"]
        del config["commands"]["clean"]
        del config["agent_forbidden"]
        config_path.write_text(json.dumps(config), encoding="utf-8")

        self.assert_ok(self.bootstrap("render", "--target", str(self.target)))

        updated = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["commands"]["build"], "docker compose build")
        self.assertTrue(updated["commands"]["clean"])
        self.assertEqual(updated["agent_forbidden"], ["build", "clean"])
        self.assert_ok(self.bootstrap("check", "--target", str(self.target)))

    def test_render_requires_config(self) -> None:
        self.target.mkdir(parents=True)
        result = self.bootstrap("render", "--target", str(self.target))
        self.assert_fails(result, "harness.config.json")


if __name__ == "__main__":
    unittest.main()
