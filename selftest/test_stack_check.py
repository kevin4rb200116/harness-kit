"""Selftests del contrato del stack (``stack_check.py``)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SELFTEST_DIR = Path(__file__).resolve().parent
KIT_ROOT = SELFTEST_DIR.parent
STACK_CHECK = KIT_ROOT / "core" / "bin" / "stack_check.py"

sys.path.insert(0, str(KIT_ROOT / "core" / "bin"))
import stack_check  # noqa: E402  (import después de ajustar sys.path)

COMMANDS = {
    "check": "./init.sh",
    "build": "python3 -m compileall -q src",
    "test": "python3 -m unittest discover -s tests -v",
    "mutation": "python3 tools/mutate.py {file}",
    "clean": "python3 -m compileall -q -f src",
}

DOC_VERIFICATION = """# Verificación

Comandos reales del stack:

```bash
./init.sh
python3 -m compileall -q src
python3 -m unittest discover -s tests -v
python3 tools/mutate.py src/notes.py
python3 -m compileall -q -f src
```
"""

DOC_ARCHITECTURE = """# Arquitectura

`src/` contiene los módulos y `tests/` los tests. Las fronteras se respetan:
la capa de UI no importa persistencia y el modelo no conoce la CLI. Esta
prosa existe para que el judge tenga un estándar contra el que comparar.
"""

DOC_CONVENTIONS = """# Convenciones

Líneas de 100 caracteres, `snake_case` para funciones y módulos, `PascalCase`
para clases, comillas dobles y f-strings. Los imports van ordenados: primero
la stdlib y después los locales del proyecto.
"""


class StackCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "demo"
        (self.root / "docs").mkdir(parents=True)
        self.write_config(COMMANDS)
        self.write_doc("architecture.md", DOC_ARCHITECTURE)
        self.write_doc("conventions.md", DOC_CONVENTIONS)
        self.write_doc("verification.md", DOC_VERIFICATION)

    # -- helpers ---------------------------------------------------------

    def write_config(
        self, commands: dict[str, str], agent_forbidden: list[str] | None = None
    ) -> None:
        config = {
            "project": "demo",
            "commands": commands,
            "documents": {
                "architecture": "docs/architecture.md",
                "conventions": "docs/conventions.md",
                "verification": "docs/verification.md",
            },
        }
        if agent_forbidden is not None:
            config["agent_forbidden"] = agent_forbidden
        (self.root / "harness.config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

    def write_doc(self, name: str, text: str) -> None:
        (self.root / "docs" / name).write_text(text, encoding="utf-8")

    def run_check(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(STACK_CHECK), "--root", str(self.root), *extra],
            capture_output=True,
            text=True,
        )

    def assert_fails(self, *needles: str) -> subprocess.CompletedProcess:
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        for needle in needles:
            self.assertIn(needle, result.stdout + result.stderr)
        return result

    # -- casos -----------------------------------------------------------

    def test_clean_project_passes(self) -> None:
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[OK]", result.stdout)

    def test_missing_verb_fails(self) -> None:
        commands = dict(COMMANDS)
        del commands["build"]
        self.write_config(commands)
        self.assert_fails("commands.build")

    def test_empty_verb_fails(self) -> None:
        self.write_config({**COMMANDS, "clean": "  "})
        self.assert_fails("commands.clean")

    def test_compound_command_with_pipe_fails(self) -> None:
        self.write_config({**COMMANDS, "test": "python3 -m unittest | tail -5"})
        self.assert_fails("orden simple")

    def test_compound_command_with_semicolon_fails(self) -> None:
        self.write_config({**COMMANDS, "check": "./init.sh; echo '$?'"})
        self.assert_fails("orden simple")

    def test_compound_command_with_redirect_fails(self) -> None:
        self.write_config({**COMMANDS, "test": "python3 -m unittest > out.txt"})
        self.assert_fails("orden simple")

    def test_placeholder_is_not_a_compound_command(self) -> None:
        self.write_config({**COMMANDS, "mutation": "python3 tools/mutate.py {file}"})
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_angle_placeholder_is_not_a_compound_command(self) -> None:
        self.write_config(
            {**COMMANDS, "mutation": "python3 tools/mutate.py <archivo>"}
        )
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_input_redirection_is_still_compound(self) -> None:
        self.write_config({**COMMANDS, "test": "python3 -m unittest < notas.txt"})
        self.assert_fails("orden simple")

    def test_angle_placeholder_with_redirection_is_compound(self) -> None:
        self.write_config(
            {**COMMANDS, "mutation": "python3 tools/mutate.py <archivo> > out.txt"}
        )
        self.assert_fails("orden simple")

    def test_angle_placeholder_with_pipe_is_compound(self) -> None:
        self.write_config(
            {**COMMANDS, "mutation": "python3 tools/mutate.py <archivo> | tee log"}
        )
        self.assert_fails("orden simple")

    def test_unknown_agent_forbidden_verb_fails(self) -> None:
        self.write_config(COMMANDS, agent_forbidden=["deploy"])
        self.assert_fails("agent_forbidden", "deploy")

    def test_agent_forbidden_verb_without_command_fails(self) -> None:
        commands = dict(COMMANDS)
        del commands["clean"]
        self.write_config(commands, agent_forbidden=["clean"])
        self.assert_fails("agent_forbidden", "clean")

    def test_agent_forbidden_list_is_accepted(self) -> None:
        self.write_config(COMMANDS, agent_forbidden=["build", "clean"])
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_empty_doc_fails(self) -> None:
        self.write_doc("conventions.md", "   \n")
        self.assert_fails("docs/conventions.md", "placeholder")

    def test_heading_only_doc_fails(self) -> None:
        self.write_doc("architecture.md", "# Arquitectura\n\n## Capas\n\n## Fronteras\n")
        self.assert_fails("docs/architecture.md", "placeholder")

    def test_missing_doc_file_fails(self) -> None:
        (self.root / "docs" / "conventions.md").unlink()
        self.assert_fails("documents.conventions", "no existe")

    def test_comment_line_in_fence_is_not_a_command(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION.replace("./init.sh\n", "# ./init.sh\n"),
        )
        self.assert_fails("commands.check")

    def test_inline_comment_is_not_a_command(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION.replace("./init.sh\n", "")
            + "\nEl gate es `# ./init.sh`.\n",
        )
        self.assert_fails("commands.check")

    def test_python_fence_hiding_a_command_does_not_count(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION.replace("./init.sh\n", "")
            + "\n```python\n./init.sh\n```\n",
        )
        self.assert_fails("commands.check")

    def test_tilde_python_fence_hiding_a_command_does_not_count(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION.replace("./init.sh\n", "")
            + "\n~~~python\n./init.sh\n~~~\n",
        )
        self.assert_fails("commands.check")

    def test_tilde_shell_fence_counts(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION.replace("./init.sh\n", "~~~bash\n./init.sh\n~~~\n"),
        )
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_command_that_is_only_a_placeholder_is_not_documented(self) -> None:
        self.write_config({**COMMANDS, "build": "{file}"})
        self.assert_fails("commands.build")

    def test_failure_exit_code_is_one(self) -> None:
        self.write_doc("architecture.md", "")
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_json_output_is_stable(self) -> None:
        self.write_config({**COMMANDS, "clean": ""})
        result = self.run_check("--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["problems"])
        self.assertIn('\n  "ok":', result.stdout)
        self.assertIn("está", result.stdout)


    def test_undocumented_verb_fails(self) -> None:
        self.write_doc("verification.md", DOC_VERIFICATION.replace("./init.sh\n", ""))
        self.assert_fails("commands.check", "no aparece documentado")

    def test_placeholder_command_matches_any_argument(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION.replace(
                "python3 tools/mutate.py src/notes.py",
                "python3 tools/mutate.py src/cualquiera.py",
            ),
        )
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_python_fence_is_not_treated_as_commands(self) -> None:
        self.write_doc(
            "verification.md",
            DOC_VERIFICATION
            + "\n```python\nimport subprocess\nsubprocess.run([\"ls\"])\n```\n",
        )
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_config_fails(self) -> None:
        (self.root / "harness.config.json").unlink()
        self.assert_fails("harness.config.json")

    def test_invalid_json_fails(self) -> None:
        (self.root / "harness.config.json").write_text("{", encoding="utf-8")
        self.assert_fails("no es JSON válido")

    def test_json_output(self) -> None:
        result = self.run_check("--json")
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["problems"], [])


class ExecutableLinesTest(unittest.TestCase):
    """Unidad: qué cuenta como comando citado en la prosa."""

    def test_bash_fence_counts(self) -> None:
        self.assertEqual(
            stack_check.executable_lines("```bash\n./init.sh\n```"), ["./init.sh"]
        )

    def test_untagged_fence_counts(self) -> None:
        self.assertEqual(
            stack_check.executable_lines("```\n./init.sh\n```"), ["./init.sh"]
        )

    def test_tilde_shell_fence_counts(self) -> None:
        self.assertEqual(
            stack_check.executable_lines("~~~bash\n./init.sh\n~~~"), ["./init.sh"]
        )

    def test_python_fence_is_ignored(self) -> None:
        self.assertEqual(
            stack_check.executable_lines("```python\n./init.sh\n```"), []
        )

    def test_tilde_python_fence_is_ignored(self) -> None:
        self.assertEqual(
            stack_check.executable_lines("~~~python\n./init.sh\n~~~"), []
        )

    def test_comment_line_in_fence_is_ignored(self) -> None:
        text = "```bash\n# ./init.sh\n./init.sh\n```"
        self.assertEqual(stack_check.executable_lines(text), ["./init.sh"])

    def test_inline_span_counts(self) -> None:
        self.assertEqual(stack_check.executable_lines("`./init.sh`"), ["./init.sh"])

    def test_inline_comment_is_ignored(self) -> None:
        self.assertEqual(stack_check.executable_lines("`# ./init.sh`"), [])

    def test_signature_stops_at_brace_placeholder(self) -> None:
        self.assertEqual(
            stack_check.signature("python3 tools/mutate.py {file}"),
            ["python3", "tools/mutate.py"],
        )

    def test_signature_stops_at_angle_placeholder(self) -> None:
        self.assertEqual(
            stack_check.signature("python3 tools/mutate.py <archivo>"),
            ["python3", "tools/mutate.py"],
        )

    def test_empty_signature_is_never_documented(self) -> None:
        self.assertIs(stack_check.documented("{file}", ["./init.sh"]), False)

    def test_documented_matches_leading_tokens(self) -> None:
        self.assertTrue(
            stack_check.documented(
                "python3 tools/mutate.py {file}", ["python3 tools/mutate.py src/a.py"]
            )
        )
        self.assertFalse(
            stack_check.documented("python3 -m unittest discover", ["python3 -m pytest"])
        )

    def test_strip_placeholders_removes_braces_and_angles(self) -> None:
        self.assertEqual(
            stack_check.strip_placeholders("tool {file} <archivo>").split(),
            ["tool"],
        )

    def test_is_compound_accepts_angle_placeholder(self) -> None:
        self.assertIs(
            stack_check.is_compound("python3 tools/mutate.py <archivo>"), False
        )

    def test_is_compound_rejects_redirection_around_placeholder(self) -> None:
        self.assertIs(
            stack_check.is_compound("python3 tools/mutate.py <archivo> > out.txt"),
            True,
        )


if __name__ == "__main__":
    unittest.main()
