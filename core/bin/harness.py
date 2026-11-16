#!/usr/bin/env python3
"""harness.py — máquina de estados ejecutable del arnés SDD.

Solo stdlib. Lee ``harness.config.json`` del root del proyecto y opera sobre
``feature_list.json``. La fuente de verdad del proceso es
``harness/process/workflow.md``.

Uso::

    python3 harness/bin/harness.py [--root DIR] status [--json]
    python3 harness/bin/harness.py [--root DIR] next [--json]
    python3 harness/bin/harness.py [--root DIR] set <id> <status> [--force]
    python3 harness/bin/harness.py [--root DIR] approve <id> [--by NAME]
    python3 harness/bin/harness.py [--root DIR] block <id> <razón>
    python3 harness/bin/harness.py [--root DIR] note <texto> [--history]
    python3 harness/bin/harness.py [--root DIR] validate [--verify]

El script nunca confía en el estado de ánimo del modelo: cada transición
comprueba los artefactos que la justifican en disco.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = ("pending", "spec_ready", "in_progress", "done", "blocked")
SPEC_FILES = ("requirements.md", "design.md", "tasks.md")
REPORTS = ("judge", "mutation")

DEFAULT_CONFIG: dict[str, Any] = {
    "project": "unnamed-project",
    "profile": "generic",
    "adapter": "generic",
    "paths": {
        "source": "src",
        "tests": "tests",
        "features": "features",
        "specs": "specs",
        "progress": "progress",
        "spec": "project-spec.md",
        "feature_list": "feature_list.json",
        "state": ".harness",
    },
    "commands": {
        "check": "./init.sh",
        "build": "",
        "test": "",
        "mutation": "",
        "clean": "",
        "verify": "./init.sh",
    },
    "mutation": {
        "threshold": 100,
    },
    "documents": {
        "architecture": "docs/architecture.md",
        "conventions": "docs/conventions.md",
        "verification": "docs/verification.md",
    },
}


# ── utilidades ────────────────────────────────────────────────────────────


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def deep_merge(base: dict, override: dict) -> dict:
    """Fusiona ``override`` sobre ``base`` sin mutar ninguno de los dos."""
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def normalize_text(text: str) -> str:
    """Normaliza para hashear: LF, sin espacios finales, un solo \\n final."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip("\n") + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def scenarios(text: str) -> list[str]:
    tags: list[str] = []
    for match in re.finditer(r"@s(\d+)\b", text):
        tag = f"@s{match.group(1)}"
        if tag not in tags:
            tags.append(tag)
    return tags


def requirements(text: str) -> list[str]:
    return sorted(set(re.findall(r"\bR\d+\b", text)), key=lambda r: int(r[1:]))


def tasks_count(text: str) -> int:
    return len(re.findall(r"(?m)^\s*[-*]\s+\[[ xX]\]", text))


def unchecked_tasks(text: str) -> list[str]:
    return re.findall(r"(?m)^\s*[-*]\s+\[ \].*$", text)


def has_todo_marker(text: str) -> bool:
    """Detecta marcadores ``TODO`` sin confundirlos con la palabra citada."""
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    for line in text.splitlines():
        stripped = line.strip().lstrip(">#*-+ ").strip()
        if stripped.startswith("TODO"):
            return True
        if re.search(r"\bTODO\s*:", line):
            return True
    return False


def as_float(value: Any, default: float = 0.0) -> float:
    """Convierte números o cadenas tipo ``"94.12%"`` sin romper la puerta."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().rstrip("%").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def report_reason(report: dict) -> str:
    """Extrae un motivo legible de un informe del judge."""
    parts: list[str] = []
    reason = report.get("reason")
    if reason:
        parts.append(str(reason))
    notes = report.get("notes")
    if isinstance(notes, list):
        parts.extend(str(note) for note in notes if str(note).strip())
    elif notes:
        parts.append(str(notes))
    return "; ".join(parts) or "sin motivo detallado"


# ── proyecto ──────────────────────────────────────────────────────────────


class HarnessError(Exception):
    """Error de uso o de validación, con mensaje para el humano."""


class Project:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.config = self._load_config()

    # -- configuración y estado ------------------------------------------

    def _load_config(self) -> dict:
        config_path = self.root / "harness.config.json"
        override: dict = {}
        if config_path.is_file():
            try:
                override = read_json(config_path)
            except json.JSONDecodeError as exc:
                raise HarnessError(f"harness.config.json inválido: {exc}") from exc
        return deep_merge(DEFAULT_CONFIG, override)

    @property
    def paths(self) -> dict:
        return self.config["paths"]

    def path(self, key: str) -> Path:
        return self.root / self.paths[key]

    @property
    def feature_list_path(self) -> Path:
        return self.root / self.paths["feature_list"]

    @property
    def state_dir(self) -> Path:
        return self.root / self.paths["state"]

    def document(self, key: str) -> Path:
        return self.root / self.config["documents"][key]

    def load_state(self) -> dict:
        if not self.feature_list_path.is_file():
            raise HarnessError(
                f"no existe {self.feature_list_path.relative_to(self.root)}"
            )
        try:
            data = read_json(self.feature_list_path)
        except json.JSONDecodeError as exc:
            raise HarnessError(
                f"{self.feature_list_path.name} inválido: {exc}"
            ) from exc
        if not isinstance(data.get("features"), list):
            raise HarnessError(
                f"{self.feature_list_path.name} no tiene una lista 'features'"
            )
        return data

    def save_state(self, data: dict) -> None:
        write_json(self.feature_list_path, data)

    # -- features ---------------------------------------------------------

    def features(self, data: dict | None = None) -> list[dict]:
        return list((data if data is not None else self.load_state())["features"])

    def find(self, identifier: str, data: dict | None = None) -> dict:
        features = self.features(data)
        for feature in features:
            if str(feature.get("id")) == str(identifier):
                return feature
        for feature in features:
            if feature.get("name") == identifier:
                return feature
        raise HarnessError(f"no existe la feature '{identifier}'")

    @staticmethod
    def name(feature: dict) -> str:
        name = feature.get("name")
        if not name:
            raise HarnessError(f"la feature {feature.get('id')} no tiene 'name'")
        return name

    @staticmethod
    def is_sdd(feature: dict) -> bool:
        return bool(feature.get("sdd", False))

    @staticmethod
    def status(feature: dict) -> str:
        return feature.get("status", "")

    # -- rutas de artefactos ---------------------------------------------

    def spec_dir(self, feature: dict) -> Path:
        return self.path("specs") / self.name(feature)

    def spec_path(self, feature: dict, filename: str) -> Path:
        return self.spec_dir(feature) / filename

    def feature_path(self, feature: dict) -> Path:
        return self.path("features") / (self.name(feature) + ".feature")

    def approval_path(self, feature: dict) -> Path:
        return self.state_dir / "approvals" / (self.name(feature) + ".json")

    def report_path(self, kind: str, feature: dict) -> Path:
        return self.state_dir / "reports" / f"{kind}_{self.name(feature)}.json"

    def progress_path(self, prefix: str, feature: dict) -> Path:
        return self.path("progress") / f"{prefix}_{self.name(feature)}.md"

    # -- lecturas ---------------------------------------------------------

    def read_feature_text(self, feature: dict) -> str | None:
        path = self.feature_path(feature)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def spec_errors(self, feature: dict) -> list[str]:
        errors: list[str] = []
        for filename in SPEC_FILES:
            path = self.spec_path(feature, filename)
            if not path.is_file():
                errors.append(f"falta {self.rel(path)}")
        req_path = self.spec_path(feature, "requirements.md")
        if req_path.is_file():
            found = requirements(req_path.read_text(encoding="utf-8"))
            if not found:
                errors.append(f"{self.rel(req_path)} no contiene ningún R<n>")
        tasks_path = self.spec_path(feature, "tasks.md")
        if tasks_path.is_file():
            text = tasks_path.read_text(encoding="utf-8")
            if not re.search(r"\bT\d+\b", text):
                errors.append(f"{self.rel(tasks_path)} no contiene ninguna T<n>")
            if tasks_count(text) == 0:
                errors.append(
                    f"{self.rel(tasks_path)} no contiene tasks con checkbox '- [ ]'"
                )
        return errors

    def feature_errors(self, feature: dict) -> list[str]:
        text = self.read_feature_text(feature)
        if text is None:
            return [f"falta {self.rel(self.feature_path(feature))}"]
        if not scenarios(text):
            return [
                f"{self.rel(self.feature_path(feature))} no contiene escenarios @sN"
            ]
        return []

    def approval_state(self, feature: dict) -> tuple[str, dict | None]:
        text = self.read_feature_text(feature)
        if text is None:
            return "missing_feature", None
        path = self.approval_path(feature)
        if not path.is_file():
            return "missing", None
        try:
            data = read_json(path)
        except json.JSONDecodeError:
            return "invalid", None
        if data.get("feature_sha256") != sha256_text(text):
            return "stale", data
        return "valid", data

    def report(self, kind: str, feature: dict) -> dict | None:
        path = self.report_path(kind, feature)
        if not path.is_file():
            return None
        try:
            return read_json(path)
        except json.JSONDecodeError:
            return None

    def tasks_file(self, feature: dict) -> str | None:
        path = self.spec_path(feature, "tasks.md")
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def tdd_report_path(self, feature: dict) -> Path:
        return self.progress_path("tdd", feature)

    def tdd_report_errors(self, feature: dict) -> list[str]:
        """El informe TDD debe existir y contener el mapa R → @s → test."""
        if not self.is_sdd(feature):
            return []
        path = self.tdd_report_path(feature)
        if not path.is_file():
            return [
                f"falta {self.rel(path)} (informe TDD con el mapa "
                "R<n> → @sN → test)"
            ]
        text = path.read_text(encoding="utf-8")
        errors: list[str] = []
        if not re.search(r"\bR\d+\b", text):
            errors.append(f"{self.rel(path)} no contiene ningún R<n>")
        if not re.search(r"@s\d+\b", text):
            errors.append(f"{self.rel(path)} no contiene ningún @sN")
        if not re.search(r"(?i)test", text):
            errors.append(f"{self.rel(path)} no referencia ningún test")
        return errors

    def tdd_report_ready(self, feature: dict) -> bool:
        return not self.tdd_report_errors(feature)

    def newest_mtime(self, paths: list[str]) -> int:
        """mtime más reciente de los archivos bajo los directorios indicados."""
        newest = 0
        for relative in paths:
            base = self.root / relative
            if base.is_file():
                newest = max(newest, base.stat().st_mtime_ns)
                continue
            if not base.is_dir():
                continue
            for item in base.rglob("*"):
                if not item.is_file():
                    continue
                if "__pycache__" in item.parts or ".pytest_cache" in item.parts:
                    continue
                newest = max(newest, item.stat().st_mtime_ns)
        return newest

    def tdd_round_epoch(self, feature: dict) -> int:
        """La ronda de TDD cambia si cambia su informe, el código o los tests."""
        tdd = self.tdd_report_path(feature)
        epoch = tdd.stat().st_mtime_ns if tdd.is_file() else 0
        return max(
            epoch,
            self.newest_mtime(
                [
                    self.paths.get("source", "src"),
                    self.paths.get("tests", "tests"),
                ]
            ),
        )

    def tdd_is_newer_than(self, feature: dict, kind: str) -> bool:
        """El veredicto caduca si el TDD tocó informe, código o tests después."""
        report = self.report_path(kind, feature)
        if not report.is_file():
            return False
        return self.tdd_round_epoch(feature) > report.stat().st_mtime_ns

    def mutation_ok(self, report: dict) -> bool:
        if str(report.get("verdict", "")).upper() != "PASS":
            return False
        threshold = as_float(
            self.config.get("mutation", {}).get("threshold", 100), 100
        )
        return as_float(report.get("score", 0)) >= threshold

    def repair_details(self, feature: dict) -> list[str]:
        """Motivos legibles del informe vigente que bloquea la fase."""
        judge = self.report("judge", feature)
        if judge is not None:
            verdict = str(judge.get("verdict", "")).upper()
            if verdict != "APPROVED" and not self.tdd_is_newer_than(feature, "judge"):
                return [f"judge {verdict or 'sin veredicto'}: {report_reason(judge)}"]
        mutation = self.report("mutation", feature)
        if mutation is not None and not self.mutation_ok(mutation):
            threshold = as_float(
                self.config.get("mutation", {}).get("threshold", 100), 100
            )
            survived = mutation.get("survived") or []
            if not isinstance(survived, list):
                survived = [survived]
            detail = ", ".join(str(item) for item in survived) or "no listados"
            return [
                f"mutación FAIL: score {as_float(mutation.get('score', 0)):g} "
                f"< umbral {threshold:g}; supervivientes: {detail}"
            ]
        return []

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    # -- verificación -----------------------------------------------------

    def verify(self) -> tuple[bool, str]:
        command = self.config.get("commands", {}).get("verify", "")
        if not command:
            return False, "harness.config.json no define commands.verify"
        result = subprocess.run(
            command,
            shell=True,
            cwd=self.root,
            text=True,
            capture_output=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    # -- reglas de transición --------------------------------------------

    def gate_errors(
        self, feature: dict, target: str, reason: str | None = None
    ) -> list[str]:
        """Devuelve los errores que impiden llegar a ``target``."""
        errors: list[str] = []
        sdd = self.is_sdd(feature)

        if target == "spec_ready" and sdd:
            errors.extend(self.spec_errors(feature))

        if target == "in_progress":
            if sdd:
                errors.extend(self.spec_errors(feature))
            errors.extend(self.feature_errors(feature))
            approval_status, _ = self.approval_state(feature)
            if approval_status != "valid":
                errors.append(
                    "la aprobación humana no es válida "
                    f"({self.approval_label(approval_status)}); "
                    f"ejecuta: harness.py approve {feature.get('id')}"
                )

        if target == "done":
            if sdd:
                errors.extend(self.spec_errors(feature))
                errors.extend(self.tdd_report_errors(feature))
                tasks_text = self.tasks_file(feature)
                if tasks_text is not None:
                    pending = unchecked_tasks(tasks_text)
                    if pending:
                        errors.append(
                            f"{self.rel(self.spec_path(feature, 'tasks.md'))} "
                            f"tiene {len(pending)} task(s) sin marcar"
                        )
            errors.extend(self.feature_errors(feature))
            approval_status, _ = self.approval_state(feature)
            if approval_status != "valid":
                errors.append(
                    "la aprobación humana no es válida "
                    f"({self.approval_label(approval_status)})"
                )
            judge = self.report("judge", feature)
            if judge is None:
                errors.append(
                    f"falta {self.rel(self.report_path('judge', feature))}"
                )
            elif str(judge.get("verdict", "")).upper() != "APPROVED":
                errors.append(
                    f"el informe del judge no está APPROVED "
                    f"(verdict={judge.get('verdict')!r})"
                )
            mutation = self.report("mutation", feature)
            threshold = as_float(
                self.config.get("mutation", {}).get("threshold", 100), 100
            )
            if mutation is None:
                errors.append(
                    f"falta {self.rel(self.report_path('mutation', feature))}"
                )
            elif str(mutation.get("verdict", "")).upper() != "PASS":
                errors.append(
                    f"el informe de mutación no está PASS "
                    f"(verdict={mutation.get('verdict')!r})"
                )
            elif as_float(mutation.get("score", 0)) < threshold:
                errors.append(
                    f"score de mutación {mutation.get('score')} < umbral {threshold:g}"
                )
            if not errors:
                ok, output = self.verify()
                if not ok:
                    errors.append("commands.verify falló:\n" + output)

        if target == "blocked":
            if not (reason or "").strip():
                errors.append("la transición a 'blocked' exige una razón")

        return errors

    @staticmethod
    def approval_label(state: str) -> str:
        return {
            "missing_feature": "no existe el .feature",
            "missing": "no registrada",
            "invalid": "ilegible",
            "stale": "caducada (el .feature cambió)",
            "valid": "válida",
        }.get(state, state)

    def allowed_transition(self, current: str, target: str) -> bool:
        if target == "blocked":
            return True
        if current == target:
            return True
        return (current, target) in {
            ("pending", "spec_ready"),
            ("spec_ready", "in_progress"),
            ("in_progress", "done"),
            ("blocked", "pending"),
            ("spec_ready", "pending"),
        }

    # -- fases ------------------------------------------------------------

    def architecture_pending(self) -> bool:
        """La arquitectura falta o conserva un marcador ``TODO`` sin resolver."""
        path = self.document("architecture")
        if not path.is_file():
            return True
        return has_todo_marker(path.read_text(encoding="utf-8"))

    def phase(self, feature: dict) -> str:
        status = self.status(feature)
        if status == "blocked":
            return "blocked"
        if status == "pending":
            if self.architecture_pending():
                return "architecture"
            if not self.is_sdd(feature):
                return "mark_spec_ready"
            if self.spec_errors(feature):
                return "spec"
            return "mark_spec_ready"
        if status == "spec_ready":
            if self.feature_errors(feature):
                return "gherkin"
            if self.approval_state(feature)[0] != "valid":
                return "approval"
            return "start"
        if status == "in_progress":
            tasks_text = self.tasks_file(feature)
            if tasks_text is not None and unchecked_tasks(tasks_text):
                return "tdd"
            if not self.tdd_report_ready(feature):
                return "tdd"
            judge = self.report("judge", feature)
            if judge is None:
                return "judge"
            if str(judge.get("verdict", "")).upper() != "APPROVED":
                if self.tdd_is_newer_than(feature, "judge"):
                    return "judge"
                return "repair"
            mutation = self.report("mutation", feature)
            if mutation is None:
                return "mutation"
            if not self.mutation_ok(mutation):
                if self.tdd_is_newer_than(feature, "judge"):
                    # El TDD reparó después del judge: hay que volver a juzgar.
                    return "judge"
                if self.tdd_is_newer_than(feature, "mutation"):
                    # El judge ya re-aprobó: la mutación es de la ronda anterior.
                    return "mutation"
                return "repair"
            return "done"
        if status == "done":
            return "done"
        return "unknown"

    def active_feature(self, data: dict) -> dict | None:
        features = self.features(data)
        for feature in features:
            if self.status(feature) == "in_progress":
                return feature
        for feature in sorted(features, key=lambda f: int(f.get("id", 0))):
            if self.status(feature) not in ("done", "blocked"):
                return feature
        for feature in features:
            if self.status(feature) == "blocked":
                return feature
        return None


# ── comandos ──────────────────────────────────────────────────────────────


def cmd_status(project: Project, args: argparse.Namespace) -> int:
    data = project.load_state()
    features = project.features(data)
    if args.json:
        rows = []
        for feature in features:
            approval_status, _ = project.approval_state(feature)
            rows.append(
                {
                    "id": feature.get("id"),
                    "name": feature.get("name"),
                    "status": project.status(feature),
                    "sdd": project.is_sdd(feature),
                    "approval": approval_status,
                    "phase": project.phase(feature),
                }
            )
        print(json.dumps({"project": project.config.get("project"), "features": rows}, indent=2))
        return 0

    print(f"Proyecto: {project.config.get('project')}")
    print(f"Perfil:   {project.config.get('profile')}  Adapter: {project.config.get('adapter')}")
    print("")
    header = f"{'ID':>3}  {'NOMBRE':<28} {'ESTADO':<12} {'APROBACIÓN':<18} FASE"
    print(header)
    print("-" * len(header))
    for feature in features:
        approval_status, _ = project.approval_state(feature)
        print(
            f"{feature.get('id'):>3}  {project.name(feature):<28} "
            f"{project.status(feature):<12} "
            f"{project.approval_label(approval_status):<18} "
            f"{project.phase(feature)}"
        )
    active = project.active_feature(data)
    print("")
    if active is None:
        if project.architecture_pending():
            print("No hay features todavía. Falta la arquitectura: /architecture")
        else:
            print("No hay features pendientes. Todo cerrado.")
    else:
        print(
            f"Siguiente: feature {active.get('id')} ({project.name(active)}) "
            f"→ fase {project.phase(active)}"
        )
    return 0


PHASE_HINTS = {
    "architecture": [
        "La arquitectura falta o sigue con un marcador TODO:.",
        "Detente y pide al humano:",
        "/architecture",
        "Cierra docs/architecture.md (capas, fronteras, errores, calidad)",
        "antes de abrir la spec de la primera feature.",
    ],
    "spec": [
        "Conversa la spec con el humano y escribe project-spec.md y",
        "specs/<name>/{requirements,design,tasks}.md (EARS, R<n>, T<n>).",
        "Después: python3 harness/bin/harness.py set <id> spec_ready",
    ],
    "mark_spec_ready": [
        "Los artefactos previos ya existen. Marca el contrato listo:",
        "python3 harness/bin/harness.py set <id> spec_ready",
    ],
    "gherkin": [
        "Destila requirements.md en features/<name>.feature con tags @sN",
        "y la tabla de trazabilidad R<n> → @sN.",
    ],
    "approval": [
        "Escenarios listos. Pide aprobación humana y regístrala:",
        "python3 harness/bin/harness.py approve <id>",
    ],
    "start": [
        "Aprobación válida. Arranca la implementación:",
        "python3 harness/bin/harness.py set <id> in_progress",
        "(approve ya hace esta transición; set es idempotente)",
    ],
    "tdd": [
        "Implementa tasks.md con Rojo → Verde → Refactor, un test a la vez.",
        "Marca cada task como [x] al terminarla y reescribe",
        "progress/tdd_<name>.md con el mapa R<n> → @sN → test.",
    ],
    "judge": [
        "Ejecuta el rol judge y escribe:",
        ".harness/reports/judge_<name>.json  {\"verdict\": \"APPROVED\"}",
    ],
    "mutation": [
        "Ejecuta el rol mutation_tester y escribe:",
        ".harness/reports/mutation_<name>.json  {\"verdict\": \"PASS\", \"score\": ...}",
    ],
    "repair": [
        "La última revisión falló (judge REJECTED o mutación FAIL).",
        "Relanza tdd_craftsman con el id/name y los motivos del informe.",
        "Debe corregir tests/código y reescribir progress/tdd_<name>.md.",
        "No bajes el umbral de mutación ni edites el mutador.",
    ],
    "done": [
        "Todos los artefactos están listos. Cierra la feature:",
        "python3 harness/bin/harness.py set <id> done",
    ],
    "blocked": [
        "Feature bloqueada. Resuelve la razón, luego:",
        "python3 harness/bin/harness.py set <id> pending",
    ],
}


def phase_hints(project: Project, feature: dict, phase: str) -> list[str]:
    """Pistas estáticas + el hueco concreto que bloquea la fase."""
    hints = list(PHASE_HINTS.get(phase, []))
    if phase == "tdd":
        holes = project.tdd_report_errors(feature)
        if holes:
            hints = [
                "Implementa tasks.md y cierra el informe TDD antes de judge.",
                "Relanza tdd_craftsman y exige reescribir",
                "progress/tdd_<name>.md con el mapa R<n> → @sN → test.",
                *[f"- {hole}" for hole in holes],
            ]
    elif phase == "repair":
        details = project.repair_details(feature)
        if details:
            hints.append("Motivo vigente:")
            hints.extend(f"- {detail}" for detail in details)
    return hints


def cmd_next(project: Project, args: argparse.Namespace) -> int:
    data = project.load_state()
    active = project.active_feature(data)
    if active is None:
        if project.architecture_pending():
            payload = {
                "phase": "architecture",
                "feature": None,
                "hints": PHASE_HINTS["architecture"],
            }
        else:
            payload = {"phase": "all_done", "feature": None, "hints": []}
    else:
        phase = project.phase(active)
        payload = {
            "phase": phase,
            "feature": {
                "id": active.get("id"),
                "name": project.name(active),
                "status": project.status(active),
            },
            "hints": phase_hints(project, active, phase),
        }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if payload["feature"] is None:
        if payload["phase"] == "architecture":
            print("No hay features todavía, pero la arquitectura no está definida.")
            for hint in payload["hints"]:
                print("  " + hint)
        else:
            print("No hay features pendientes. Todo cerrado.")
        return 0
    print(
        f"Siguiente: feature {payload['feature']['id']} "
        f"({payload['feature']['name']}) → fase {payload['phase']}"
    )
    for hint in payload["hints"]:
        print("  " + hint.replace("<id>", str(payload["feature"]["id"]))
                  .replace("<name>", payload["feature"]["name"]))
    return 0


def cmd_set(project: Project, args: argparse.Namespace) -> int:
    if args.status not in STATUSES:
        raise HarnessError(
            f"estado inválido '{args.status}' (válidos: {', '.join(STATUSES)})"
        )
    data = project.load_state()
    feature = project.find(args.id, data)
    current = project.status(feature)
    target = args.status

    if not args.force and not project.allowed_transition(current, target):
        raise HarnessError(
            f"transición no permitida: {current} → {target}. "
            "Usa --force solo para una emergencia documentada."
        )

    errors = []
    if not args.force:
        errors = project.gate_errors(feature, target, args.reason)
    if errors:
        raise HarnessError(
            f"no se puede pasar {current} → {target}:\n  - " + "\n  - ".join(errors)
        )

    feature["status"] = target
    feature["updated_at"] = utc_now()
    if target == "blocked":
        feature["blocked_reason"] = args.reason
    else:
        feature.pop("blocked_reason", None)
    project.save_state(data)
    print(
        f"[OK] feature {feature.get('id')} ({project.name(feature)}): "
        f"{current} → {target}"
    )
    if target == "blocked":
        print(f"     razón: {args.reason}")
    return 0


def cmd_approve(project: Project, args: argparse.Namespace) -> int:
    data = project.load_state()
    feature = project.find(args.id, data)
    current = project.status(feature)

    if current == "done":
        raise HarnessError("la feature ya está done; no hay nada que aprobar")
    if current == "blocked":
        raise HarnessError(
            "la feature está bloqueada; resuélvela y vuelve a spec_ready/in_progress"
        )
    if current == "pending":
        raise HarnessError(
            "la feature sigue en pending; primero: "
            f"harness.py set {feature.get('id')} spec_ready"
        )
    if project.is_sdd(feature):
        errors = project.spec_errors(feature)
        if errors:
            raise HarnessError(
                "la spec no está completa; no se puede aprobar el contrato:\n  - "
                + "\n  - ".join(errors)
            )
    feature_errors = project.feature_errors(feature)
    if feature_errors:
        raise HarnessError(
            "el contrato ejecutable no está listo:\n  - " + "\n  - ".join(feature_errors)
        )

    text = project.read_feature_text(feature) or ""
    approval = {
        "feature_id": feature.get("id"),
        "feature": project.name(feature),
        "scenarios": scenarios(text),
        "feature_sha256": sha256_text(text),
        "approved_by": args.by,
        "approved_at": utc_now(),
        "channel": "chat",
    }
    write_json(project.approval_path(feature), approval)

    if current == "spec_ready":
        errors = project.gate_errors(feature, "in_progress")
        if errors:
            raise HarnessError(
                "la aprobación se registró, pero no se puede iniciar:\n  - "
                + "\n  - ".join(errors)
            )
        feature["status"] = "in_progress"
        feature["updated_at"] = utc_now()
        feature.pop("blocked_reason", None)
        project.save_state(data)
        print(
            f"[OK] aprobación registrada para {project.name(feature)} "
            f"({len(approval['scenarios'])} escenarios)"
        )
        print("[OK] feature movida a in_progress")
    else:
        print(
            f"[OK] aprobación refrescada para {project.name(feature)} "
            f"({len(approval['scenarios'])} escenarios)"
        )
    print(f"     sha256: {approval['feature_sha256']}")
    return 0


def cmd_block(project: Project, args: argparse.Namespace) -> int:
    if not hasattr(args, "force"):
        args.force = False
    args.status = "blocked"
    return cmd_set(project, args)


def cmd_note(project: Project, args: argparse.Namespace) -> int:
    progress_dir = project.path("progress")
    progress_dir.mkdir(parents=True, exist_ok=True)
    if getattr(args, "history", False):
        target = progress_dir / "history.md"
        header = "# Bitácora histórica (append-only)\n\n"
    else:
        target = progress_dir / "current.md"
        header = "# Sesión actual\n\n## Bitácora\n\n"
    if not target.is_file():
        target.write_text(header, encoding="utf-8")
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"- {utc_now()} — {args.text}\n")
    print(f"[OK] nota añadida a {project.rel(target)}")
    return 0


def validate_reports(
    project: Project, feature: dict, fid: str, name: str
) -> list[str]:
    """Valida los informes machine-readable que exige `done`."""
    errors: list[str] = []
    judge = project.report("judge", feature)
    if judge is None:
        errors.append(f"feature {fid} ({name}): falta informe del judge")
    elif str(judge.get("verdict", "")).upper() != "APPROVED":
        errors.append(
            f"feature {fid} ({name}): judge no APPROVED "
            f"({judge.get('verdict')!r})"
        )
    mutation = project.report("mutation", feature)
    threshold = as_float(project.config.get("mutation", {}).get("threshold", 100), 100)
    if mutation is None:
        errors.append(f"feature {fid} ({name}): falta informe de mutación")
    elif str(mutation.get("verdict", "")).upper() != "PASS":
        errors.append(
            f"feature {fid} ({name}): mutación no PASS "
            f"({mutation.get('verdict')!r})"
        )
    elif as_float(mutation.get("score", 0)) < threshold:
        errors.append(
            f"feature {fid} ({name}): score de mutación "
            f"{mutation.get('score')} < umbral {threshold:g}"
        )
    return errors


def validate_project(
    project: Project, run_verify: bool = False
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = project.load_state()
    except HarnessError as exc:
        return [str(exc)], []

    features = project.features(data)
    ids: set[str] = set()
    names: set[str] = set()
    in_progress = 0

    for feature in features:
        fid = str(feature.get("id", ""))
        if not fid:
            errors.append("hay una feature sin 'id'")
        elif fid in ids:
            errors.append(f"id duplicado: {fid}")
        ids.add(fid)

        name = feature.get("name")
        if not name:
            errors.append(f"la feature {fid} no tiene 'name'")
            continue
        if name in names:
            errors.append(f"name duplicado: {name}")
        names.add(name)

        status = project.status(feature)
        if status not in STATUSES:
            errors.append(f"feature {fid} ({name}): estado inválido '{status}'")
            continue
        if status == "in_progress":
            in_progress += 1
        if status == "blocked" and not str(feature.get("blocked_reason", "")).strip():
            errors.append(f"feature {fid} ({name}): blocked sin 'blocked_reason'")

        if not project.is_sdd(feature):
            # `sdd: false` solo exime de las specs EARS y de tasks.md.
            # El contrato observable, la aprobación, el judge y la mutación
            # siguen siendo obligatorios para llegar a done.
            if status in ("in_progress", "done"):
                errors.extend(
                    f"feature {fid} ({name}): {e}"
                    for e in project.feature_errors(feature)
                )
                approval_status, _ = project.approval_state(feature)
                if approval_status != "valid":
                    errors.append(
                        f"feature {fid} ({name}): aprobación "
                        f"{project.approval_label(approval_status)}"
                    )
            if status == "done":
                errors.extend(
                    validate_reports(project, feature, fid, name)
                )
            continue
        if status in ("spec_ready", "in_progress", "done"):
            errors.extend(f"feature {fid} ({name}): {e}" for e in project.spec_errors(feature))
        if status in ("in_progress", "done"):
            errors.extend(f"feature {fid} ({name}): {e}" for e in project.feature_errors(feature))
            approval_status, _ = project.approval_state(feature)
            if approval_status != "valid":
                errors.append(
                    f"feature {fid} ({name}): aprobación "
                    f"{project.approval_label(approval_status)}"
                )
        if status == "done":
            tasks_text = project.tasks_file(feature)
            if tasks_text is not None:
                pending = unchecked_tasks(tasks_text)
                if pending:
                    errors.append(
                        f"feature {fid} ({name}): {len(pending)} task(s) sin marcar"
                    )
            errors.extend(validate_reports(project, feature, fid, name))
            warnings.extend(
                f"feature {fid} ({name}): informe TDD heredado: {error}"
                for error in project.tdd_report_errors(feature)
            )

    if in_progress > 1:
        errors.append(
            f"hay {in_progress} features en in_progress (máximo 1); "
            "una sola feature a la vez"
        )

    if not (project.root / project.paths["spec"]).is_file():
        errors.append(f"falta {project.paths['spec']}")
    current = project.path("progress") / "current.md"
    if not current.is_file():
        errors.append(f"falta {project.paths['progress']}/current.md")
    elif in_progress:
        text = current.read_text(encoding="utf-8").lower()
        for feature in features:
            if project.status(feature) != "in_progress":
                continue
            name = str(feature.get("name", "")).lower()
            if name and name not in text:
                warnings.append(
                    f"feature {feature.get('id')} ({feature.get('name')}): "
                    "está in_progress pero progress/current.md no la menciona; "
                    "el lead debe registrar la sesión"
                )

    if run_verify:
        ok, output = project.verify()
        if not ok:
            errors.append("commands.verify falló:\n" + output)

    return errors, warnings


def cmd_validate(project: Project, args: argparse.Namespace) -> int:
    errors, warnings = validate_project(project, run_verify=args.verify)
    if errors:
        print("[FAIL] el arnés no es coherente:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
    else:
        print("[OK] feature_list.json, specs, features y approvals coherentes")
        if args.verify:
            print("[OK] commands.verify en verde")
    for warning in warnings:
        print(f"[WARN] {warning}")
    return 1 if errors else 0


# ── CLI ───────────────────────────────────────────────────────────────────


def extract_root(argv: list[str]) -> tuple[Path | None, list[str]]:
    """Permite ``--root DIR`` en cualquier posición."""
    root: Path | None = None
    rest: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--root":
            if index + 1 >= len(argv):
                raise HarnessError("--root necesita un directorio")
            root = Path(argv[index + 1])
            index += 2
        elif arg.startswith("--root="):
            root = Path(arg.split("=", 1)[1])
            index += 1
        else:
            rest.append(arg)
            index += 1
    return root, rest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness.py",
        description="Máquina de estados ejecutable del arnés SDD.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="muestra el estado de las features")
    status.add_argument("--json", action="store_true", help="salida machine-readable")
    status.set_defaults(func=cmd_status)

    nxt = sub.add_parser("next", help="dice la siguiente fase y cómo avanzar")
    nxt.add_argument("--json", action="store_true", help="salida machine-readable")
    nxt.set_defaults(func=cmd_next)

    set_cmd = sub.add_parser("set", help="cambia el estado de una feature")
    set_cmd.add_argument("id", help="id o nombre de la feature")
    set_cmd.add_argument("status", choices=STATUSES, help="estado destino")
    set_cmd.add_argument(
        "--force",
        action="store_true",
        help="salta las puertas (emergencia documentada)",
    )
    set_cmd.add_argument("--reason", default=None, help="razón si el destino es blocked")
    set_cmd.set_defaults(func=cmd_set)

    approve = sub.add_parser(
        "approve", help="registra la aprobación humana del .feature"
    )
    approve.add_argument("id", help="id o nombre de la feature")
    approve.add_argument("--by", default="human", help="quién aprueba")
    approve.set_defaults(func=cmd_approve)

    block = sub.add_parser("block", help="bloquea una feature con una razón")
    block.add_argument("id", help="id o nombre de la feature")
    block.add_argument("reason", help="razón del bloqueo")
    block.set_defaults(func=cmd_block)

    note = sub.add_parser(
        "note", help="añade una nota a progress/current.md o a history.md"
    )
    note.add_argument("text", help="texto de la nota")
    note.add_argument(
        "--history",
        action="store_true",
        help="añade a progress/history.md (append-only) en vez de current.md",
    )
    note.set_defaults(func=cmd_note)

    validate = sub.add_parser("validate", help="valida el arnés completo")
    validate.add_argument(
        "--verify", action="store_true", help="ejecuta también commands.verify"
    )
    validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        root, rest = extract_root(argv)
    except HarnessError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    parser = build_parser()
    args = parser.parse_args(rest)
    args.root = root
    try:
        project = Project(root or Path.cwd())
        return args.func(project, args)
    except HarnessError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
