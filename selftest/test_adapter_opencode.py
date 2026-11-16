"""Selftests del adapter OpenCode."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SELFTEST_DIR = Path(__file__).resolve().parent
KIT_ROOT = SELFTEST_DIR.parent
BOOTSTRAP = KIT_ROOT / "bootstrap.py"

sys.path.insert(0, str(KIT_ROOT))
import bootstrap  # noqa: E402  (import después de ajustar sys.path)

AGENTS = (
    "craftsman_lead",
    "architect",
    "spec_partner",
    "gherkin_author",
    "tdd_craftsman",
    "judge",
    "mutation_tester",
    "gatekeeper",
)
COMMANDS = {
    "next": "craftsman_lead",
    "architecture": "architect",
    "spec": "spec_partner",
    "approve": "gatekeeper",
    "status": "craftsman_lead",
}
PRIMARY = {"craftsman_lead", "architect", "spec_partner", "gatekeeper"}


def frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("falta el frontmatter")
    end = lines.index("---", 1)
    return "\n".join(lines[1:end])


class OpenCodeAdapterTest(unittest.TestCase):
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
            "init",
            "--target",
            str(self.target),
            "--profile",
            "python-unittest",
            "--adapter",
            "opencode",
            "--project",
            "demo",
            *extra,
        )

    def render(self) -> subprocess.CompletedProcess:
        return self.bootstrap("render", "--target", str(self.target))

    def assert_ok(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def agent(self, name: str) -> str:
        return (self.target / ".opencode" / "agents" / f"{name}.md").read_text(
            encoding="utf-8"
        )

    def command(self, name: str) -> str:
        return (self.target / ".opencode" / "commands" / f"{name}.md").read_text(
            encoding="utf-8"
        )

    def config(self) -> dict:
        return bootstrap.parse_jsonc(self.target / "opencode.jsonc")

    # -- layout ----------------------------------------------------------

    def test_renders_agents_commands_and_manifest(self) -> None:
        self.assert_ok(self.init())
        for name in AGENTS:
            path = self.target / ".opencode" / "agents" / f"{name}.md"
            self.assertTrue(path.is_file(), f"falta el agente {name}")
        for name in COMMANDS:
            path = self.target / ".opencode" / "commands" / f"{name}.md"
            self.assertTrue(path.is_file(), f"falta el comando {name}")
        self.assertTrue(
            (self.target / "harness" / "adapters" / "opencode" / "adapter.json").is_file()
        )
        self.assertTrue((self.target / "opencode.jsonc").is_file())

    def test_no_placeholders_remain(self) -> None:
        self.assert_ok(self.init())
        emitted = list((self.target / ".opencode").rglob("*.md"))
        emitted.append(self.target / "opencode.jsonc")
        for path in emitted:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("{{", text, f"placeholder sin renderizar en {path}")
        self.assertIn("demo", self.agent("craftsman_lead"))

    def test_agent_modes(self) -> None:
        self.assert_ok(self.init())
        for name in AGENTS:
            mode = "primary" if name in PRIMARY else "subagent"
            self.assertIn(
                f"mode: {mode}",
                frontmatter(self.agent(name)),
                f"{name} debería ser {mode}",
            )

    def test_agents_share_the_entry_point(self) -> None:
        self.assert_ok(self.init())
        for name in AGENTS:
            text = self.agent(name)
            self.assertIn("## Entrada", text, f"{name} sin punto de entrada")
            self.assertIn("AGENTS.md", text, f"{name} no remite a AGENTS.md")

    def test_agents_report_what_they_read(self) -> None:
        self.assert_ok(self.init())
        for name in AGENTS:
            text = self.agent(name)
            self.assertIn("leído:", text, f"{name} no pide evidencia de lectura")
        self.assertIn("note --history", self.agent("craftsman_lead"))

    def test_project_roles_share_the_entry_point(self) -> None:
        self.assert_ok(self.init())
        roles = sorted((self.target / "harness" / "roles").glob("*.md"))
        self.assertEqual(len(roles), 8, "faltan roles en harness/roles/")
        for role in roles:
            text = role.read_text(encoding="utf-8")
            self.assertIn("## Entrada", text, f"{role.name} sin punto de entrada")
            self.assertIn("AGENTS.md", text, f"{role.name} no remite a AGENTS.md")

    # -- permisos --------------------------------------------------------

    def test_lead_cannot_edit_or_spawn_the_human_gates(self) -> None:
        self.assert_ok(self.init())
        text = frontmatter(self.agent("craftsman_lead"))
        self.assertIn('resource: "progress/current.md"', text)
        self.assertNotIn('resource: "progress/history.md"', text)
        self.assertIn("python3 harness/bin/harness.py status *", text)
        self.assertIn("python3 harness/bin/harness.py set *", text)
        self.assertIn("python3 harness/bin/harness.py validate *", text)
        self.assertIn(
            'resource: "python3 harness/bin/harness.py approve *"\n    effect: deny',
            text,
        )
        self.assertIn(
            'resource: "python3 harness/bin/harness.py *--force*"\n    effect: deny',
            text,
        )
        self.assertIn("./init.sh *", text)
        for subagent in ("gherkin_author", "tdd_craftsman", "judge", "mutation_tester"):
            self.assertIn(f"resource: {subagent}", text)
        self.assertNotIn("resource: spec_partner", text)
        self.assertNotIn("resource: gatekeeper", text)
        self.assertNotIn("resource: explore", text)
        self.assertNotIn("python3 -m unittest", text)
        self.assertNotIn("docker compose run", text)

    def test_gatekeeper_only_runs_approve(self) -> None:
        self.assert_ok(self.init())
        text = frontmatter(self.agent("gatekeeper"))
        self.assertIn('resource: "python3 harness/bin/harness.py approve *"', text)
        self.assertEqual(text.count("effect: allow"), 1, text)
        self.assertNotIn("action: edit\n    resource: \"progress", text)

    def test_architect_only_writes_the_architecture_document(self) -> None:
        self.assert_ok(self.init())
        text = frontmatter(self.agent("architect"))
        self.assertIn('resource: "docs/architecture.md"', text)
        self.assertEqual(text.count("effect: allow"), 1, text)
        for forbidden in ("src/*", "tests/*", "features/*", "specs/*"):
            self.assertNotIn(f'resource: "{forbidden}"', text)

    def test_tdd_uses_profile_paths_and_commands(self) -> None:
        self.assert_ok(self.init())
        text = frontmatter(self.agent("tdd_craftsman"))
        self.assertIn('resource: "src/*"', text)
        self.assertIn('resource: "tests/*"', text)
        self.assertIn('resource: "specs/*/tasks.md"', text)
        self.assertIn(
            'resource: "docker compose run --rm app python3 -m unittest *"', text
        )
        self.assertIn('resource: "./init.sh *"', text)
        self.assertIn('resource: "python3 harness/bin/harness.py status *"', text)

    def test_judge_and_mutation_can_read_the_status(self) -> None:
        self.assert_ok(self.init())
        for name in ("judge", "mutation_tester"):
            self.assertIn(
                'resource: "python3 harness/bin/harness.py status *"',
                frontmatter(self.agent(name)),
                name,
            )

    def test_agents_are_warned_about_hidden_paths_and_shell(self) -> None:
        self.assert_ok(self.init())
        for name in ("craftsman_lead", "tdd_craftsman", "judge", "mutation_tester"):
            body = self.agent(name)
            self.assertIn("`read`, `glob` y `grep`", body, name)
            self.assertIn("`.harness/`", body, name)
            self.assertIn("No uses `shell` para `ls`", body, name)

    def test_lead_brief_requires_the_tdd_report(self) -> None:
        self.assert_ok(self.init())
        body = self.agent("craftsman_lead")
        self.assertIn("progress/tdd_<name>.md", body)
        self.assertIn("Brief obligatorio", body)
        self.assertIn("no inventes comandos", body.lower())

    def test_next_documents_the_repair_loop(self) -> None:
        self.assert_ok(self.init())
        body = self.command("next")
        self.assertIn("`repair`", body)
        self.assertIn("tdd_craftsman", body)
        self.assertIn("progress/tdd_<name>.md", body)

    def test_mutation_runs_in_the_container(self) -> None:
        self.assert_ok(self.init())
        text = frontmatter(self.agent("mutation_tester"))
        self.assertIn(
            'resource: "docker compose run --rm app python3 tools/mutate.py *"', text
        )

    def test_profile_keeps_human_verbs_out_of_the_agent_allowlist(self) -> None:
        profile = json.loads(
            (KIT_ROOT / "profiles" / "python-unittest" / "profile.json").read_text(
                encoding="utf-8"
            )
        )
        forbidden = set(profile["agent_forbidden"])
        allowed = set(profile["shell_allow"])
        self.assertEqual(forbidden, {"build", "clean"})
        self.assertFalse(
            forbidden & allowed,
            f"verbos humano/CI expuestos al agente: {sorted(forbidden & allowed)}",
        )

    def test_rendered_agents_do_not_allow_human_verbs(self) -> None:
        self.assert_ok(self.init())
        profile = json.loads(
            (KIT_ROOT / "profiles" / "python-unittest" / "profile.json").read_text(
                encoding="utf-8"
            )
        )
        for verb in profile["agent_forbidden"]:
            command = profile["commands"][verb]
            for name in AGENTS:
                self.assertNotIn(
                    command,
                    frontmatter(self.agent(name)),
                    f"{name} expone el verbo humano/CI {verb!r} en su frontmatter",
                )

    def test_judge_and_mutation_only_write_their_reports(self) -> None:
        self.assert_ok(self.init())
        for name, prefix in (("judge", "judge"), ("mutation_tester", "mutation")):
            text = frontmatter(self.agent(name))
            self.assertIn(f'resource: "progress/{prefix}_*"', text)
            self.assertIn(f'resource: ".harness/reports/{prefix}_*"', text)
            self.assertNotIn('resource: "src/*"', text)
            self.assertNotIn('resource: "tests/*"', text)

    # -- comandos --------------------------------------------------------

    def test_commands_bind_agent_and_current_session(self) -> None:
        self.assert_ok(self.init())
        for name, agent in COMMANDS.items():
            text = frontmatter(self.command(name))
            self.assertIn(f"agent: {agent}", text)
            self.assertIn("subagent: false", text)

    def test_spec_and_approve_use_primary_agents(self) -> None:
        self.assert_ok(self.init())
        self.assertIn("agent: spec_partner", frontmatter(self.command("spec")))
        self.assertIn("agent: gatekeeper", frontmatter(self.command("approve")))
        self.assertIn("agent: architect", frontmatter(self.command("architecture")))
        self.assertIn("$ARGUMENTS", self.command("spec"))
        self.assertIn("$ARGUMENTS", self.command("approve"))
        self.assertIn("$ARGUMENTS", self.command("architecture"))

    def test_next_advances_instead_of_only_reporting(self) -> None:
        self.assert_ok(self.init())
        text = re.sub(r"\s+", " ", self.command("next").lower())
        self.assertIn("ejecuta la acción", text)
        self.assertIn("reportar no es avanzar", text)
        for phase in ("mark_spec_ready", "gherkin", "tdd", "judge", "mutation"):
            self.assertIn(phase, text)
        for gate in ("architecture", "spec", "approval", "blocked", "all_done"):
            self.assertIn(gate, text)

    def test_lead_role_requires_executing_the_phase(self) -> None:
        self.assert_ok(self.init())
        for path in (
            self.target / "harness" / "roles" / "craftsman_lead.md",
            self.target / ".opencode" / "agents" / "craftsman_lead.md",
        ):
            text = re.sub(
                r"\s+", " ", path.read_text(encoding="utf-8").lower()
            )
            self.assertIn("reportar no es avanzar", text)

    # -- configuración ---------------------------------------------------

    def test_config_declares_lead_and_global_denies(self) -> None:
        self.assert_ok(self.init())
        config = self.config()
        self.assertEqual(config["default_agent"], "craftsman_lead")
        rules = {(r["action"], r["resource"], r["effect"]) for r in config["permissions"]}
        for action in ("edit", "shell", "subagent"):
            self.assertIn((action, "*", "deny"), rules)
        self.assertIn(("external_directory", "*", "ask"), rules)

    def test_config_merge_preserves_user_keys_and_dedupes(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "opencode.jsonc").write_text(
            """{
  // preferencia local
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "plan",
  "theme": "dark",
  "note": "texto ,} intacto",
  "permissions": [
    { "action": "shell", "resource": "git status *", "effect": "allow" },
  ],
}
""",
            encoding="utf-8",
        )
        self.assert_ok(self.init("--force"))
        config = self.config()
        self.assertEqual(config["default_agent"], "plan")
        self.assertEqual(config["theme"], "dark")
        self.assertEqual(config["note"], "texto ,} intacto")
        rules = config["permissions"]
        keys = [(r["action"], r["resource"], r["effect"]) for r in rules]
        self.assertIn(("shell", "git status *", "allow"), keys)
        self.assertEqual(keys.count(("shell", "*", "deny")), 1)

        self.assert_ok(self.render())
        keys = [
            (r["action"], r["resource"], r["effect"])
            for r in self.config()["permissions"]
        ]
        self.assertEqual(keys.count(("shell", "*", "deny")), 1)
        self.assertEqual(keys.count(("shell", "git status *", "allow")), 1)

    # -- render ----------------------------------------------------------

    def test_render_is_idempotent(self) -> None:
        self.assert_ok(self.init())
        snapshot = {
            path.relative_to(self.target): path.read_bytes()
            for path in sorted((self.target / ".opencode").rglob("*.md"))
        }
        snapshot[Path("opencode.jsonc")] = (self.target / "opencode.jsonc").read_bytes()

        self.assert_ok(self.render())

        for relative, content in snapshot.items():
            self.assertEqual(
                (self.target / relative).read_bytes(),
                content,
                f"{relative} cambió al renderizar dos veces",
            )

    def test_render_removes_stale_generated_files_and_keeps_user_files(self) -> None:
        self.assert_ok(self.init())
        agents = self.target / ".opencode" / "agents"
        (agents / "obsolete.md").write_text(
            "<!-- Generated by harness-kit 0.0.0 | adapter opencode -->\n# viejo\n",
            encoding="utf-8",
        )
        (agents / "mine.md").write_text("# mi agente\n", encoding="utf-8")

        self.assert_ok(self.render())

        self.assertFalse((agents / "obsolete.md").exists())
        self.assertTrue((agents / "mine.md").is_file())

    def test_switching_to_generic_removes_generated_adapter_files(self) -> None:
        self.assert_ok(self.init())
        config_path = self.target / "harness.config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["adapter"] = "generic"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

        self.assert_ok(self.render())

        self.assertFalse((self.target / ".opencode" / "agents" / "judge.md").exists())
        self.assertFalse((self.target / ".opencode" / "commands" / "next.md").exists())
        # El archivo de configuración se conserva: puede contener claves del humano.
        self.assertTrue((self.target / "opencode.jsonc").is_file())

    def test_generic_adapter_creates_no_opencode_files(self) -> None:
        result = self.bootstrap(
            "init",
            "--target",
            str(self.target),
            "--profile",
            "python-unittest",
            "--adapter",
            "generic",
        )
        self.assert_ok(result)
        self.assertFalse((self.target / ".opencode").exists())
        self.assertFalse((self.target / "opencode.jsonc").exists())

    # -- proyecto generado ----------------------------------------------

    def test_scaffolded_init_and_check_are_green(self) -> None:
        self.assert_ok(self.init())
        result = subprocess.run(
            ["./init.sh"], cwd=self.target, capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode,
            0,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assert_ok(self.bootstrap("check", "--target", str(self.target)))

    def test_check_detects_missing_rendered_file(self) -> None:
        self.assert_ok(self.init())
        (self.target / ".opencode" / "agents" / "judge.md").unlink()
        result = self.bootstrap("check", "--target", str(self.target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("judge.md", result.stdout + result.stderr)


class ShellDisciplineTest(unittest.TestCase):
    """La allowlist son cadenas literales: los prompts no pueden enseñar pipes.

    Un comando compuesto se parte en varios recursos ``shell`` y cualquier
    tramo sin regla deniega la operación entera. El modelo copia lo que ve en
    el prompt, así que el prompt solo muestra órdenes simples.
    """

    MARKER = "Una sola orden por llamada"
    BASH_BLOCK = re.compile(r"```bash\n(.*?)```", re.S)

    def agents_with_shell(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for name in AGENTS:
            text = (KIT_ROOT / "adapters" / "opencode" / "agents" / f"{name}.md").read_text(
                encoding="utf-8"
            )
            blocks = frontmatter(text).split("- action:")
            allows = [
                block for block in blocks if "shell" in block and "effect: allow" in block
            ]
            if allows:
                found.append((name, text))
        return found

    def test_every_shell_agent_teaches_simple_commands(self) -> None:
        agents = self.agents_with_shell()
        self.assertTrue(agents, "ningún agente con shell: revisa el frontmatter")
        for name, text in agents:
            self.assertIn(self.MARKER, text, f"{name} no explica la regla de shell")

    def test_no_bash_example_chains_commands(self) -> None:
        for path in sorted((KIT_ROOT / "adapters" / "opencode" / "agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for block in self.BASH_BLOCK.findall(text):
                for line in block.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    for operator in ("|", ";", "&&", "$("):
                        self.assertNotIn(
                            operator,
                            stripped,
                            f"{path.name} enseña un comando compuesto: {stripped}",
                        )

    def test_core_role_repeats_the_rule(self) -> None:
        text = (KIT_ROOT / "core" / "roles" / "craftsman_lead.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(self.MARKER, text)

    def test_scaffolded_lead_includes_the_rule(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / "demo"
        subprocess.run(
            [
                sys.executable,
                str(BOOTSTRAP),
                "init",
                "--target",
                str(target),
                "--profile",
                "python-unittest",
                "--adapter",
                "opencode",
                "--project",
                "demo",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        text = (target / ".opencode" / "agents" / "craftsman_lead.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(self.MARKER, text)


if __name__ == "__main__":
    unittest.main()
