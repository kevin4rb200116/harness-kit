#!/usr/bin/env python3
"""bootstrap.py — materializa el harness-kit en un proyecto destino.

La distribución es una **plantilla copiable**: no hay paquete instalable.
Copias esta carpeta a tu máquina (o la clonas) y ejecutas::

    python3 bootstrap.py init --target ../mi-proyecto --profile python-unittest
    python3 bootstrap.py render --target ../mi-proyecto
    python3 bootstrap.py check --target ../mi-proyecto

``init`` crea el layout y los artefactos que falten. ``render`` refresca solo
lo generado (``harness/``, ``init.sh``, ``tools/``) sin tocar la spec, el
estado, los docs ni el código. ``check`` ejecuta la validación completa.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KIT_ROOT = Path(__file__).resolve().parent
VERSION = (KIT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store")

DEFAULT_CONFIG: dict[str, Any] = {
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
    "mutation": {"threshold": 100, "scope": "touched_files", "required": True},
    "agent_forbidden": [],
    "documents": {
        "architecture": "docs/architecture.md",
        "conventions": "docs/conventions.md",
        "verification": "docs/verification.md",
    },
}

FEATURE_LIST_RULES = {
    "one_feature_at_a_time": True,
    "require_tests_to_close": True,
    "require_approved_spec_to_implement": True,
    "valid_status": ["pending", "spec_ready", "in_progress", "done", "blocked"],
    "sdd_required_when": 'feature has "sdd": true',
}


class BootstrapError(Exception):
    pass


# ── utilidades ────────────────────────────────────────────────────────────


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=IGNORE)


def load_profile(profile_id: str) -> tuple[Path, dict]:
    profile_dir = KIT_ROOT / "profiles" / profile_id
    manifest = profile_dir / "profile.json"
    if not manifest.is_file():
        available = sorted(p.name for p in (KIT_ROOT / "profiles").iterdir() if p.is_dir())
        raise BootstrapError(
            f"perfil desconocido '{profile_id}'. Disponibles: {', '.join(available) or '(ninguno)'}"
        )
    return profile_dir, read_json(manifest)


def require_adapter(adapter_id: str) -> Path:
    adapter_dir = KIT_ROOT / "adapters" / adapter_id
    if not adapter_dir.is_dir():
        available = sorted(p.name for p in (KIT_ROOT / "adapters").iterdir() if p.is_dir())
        raise BootstrapError(
            f"adapter desconocido '{adapter_id}'. Disponibles: {', '.join(available) or '(ninguno)'}"
        )
    return adapter_dir


def build_config(project: str, profile_id: str, adapter_id: str, profile: dict) -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    for section in ("paths", "commands", "mutation", "documents"):
        config[section].update(profile.get(section, {}))
    config["agent_forbidden"] = list(profile.get("agent_forbidden", []))
    config["project"] = project
    config["description"] = profile.get("description", "")
    config["profile"] = profile_id
    config["adapter"] = adapter_id
    config["harness_version"] = VERSION
    return config


def render_template(text: str, project: str, profile_id: str, adapter_id: str) -> str:
    return (
        text.replace("{{PROJECT}}", project)
        .replace("{{PROFILE}}", profile_id)
        .replace("{{ADAPTER}}", adapter_id)
        .replace("{{VERSION}}", VERSION)
    )


# ── adapters ──────────────────────────────────────────────────────────────


def adapter_manifests() -> dict[str, dict]:
    """Manifiestos de los adapters que saben renderizar archivos."""
    manifests: dict[str, dict] = {}
    adapters_dir = KIT_ROOT / "adapters"
    for directory in sorted(adapters_dir.iterdir()):
        manifest_path = directory / "adapter.json"
        if not directory.is_dir() or not manifest_path.is_file():
            continue
        manifest = read_json(manifest_path)
        manifests[manifest.get("id", directory.name)] = manifest
    return manifests


def adapter_values(
    project: str, profile_id: str, adapter_id: str, profile: dict
) -> dict[str, str]:
    """Valores que los adapters pueden usar como ``{{CLAVE}}``."""
    commands = profile.get("commands", {})
    shell_allow = profile.get("shell_allow", {})
    paths = profile.get("paths", {})
    documents = profile.get("documents", {})

    def shell(key: str) -> str:
        pattern = shell_allow.get(key)
        if pattern:
            return pattern
        command = commands.get(key, "")
        if not command:
            return "__sin_comando__"
        return command.split("{")[0].rstrip() + " *"

    return {
        "PROJECT": project,
        "PROFILE": profile_id,
        "PROFILE_DESCRIPTION": profile.get("description", ""),
        "ADAPTER": adapter_id,
        "VERSION": VERSION,
        "COMMAND_BUILD": commands.get("build", ""),
        "COMMAND_CLEAN": commands.get("clean", ""),
        "COMMAND_TEST": commands.get("test", ""),
        "COMMAND_VERIFY": commands.get("verify", "./init.sh"),
        "COMMAND_MUTATION": commands.get("mutation", ""),
        "SHELL_TEST": shell("test"),
        "SHELL_VERIFY": shell("verify"),
        "SHELL_MUTATION": shell("mutation"),
        "PATHS_SOURCE": paths.get("source", "src"),
        "PATHS_TESTS": paths.get("tests", "tests"),
        "PATHS_FEATURES": paths.get("features", "features"),
        "PATHS_SPECS": paths.get("specs", "specs"),
        "PATHS_PROGRESS": paths.get("progress", "progress"),
        "PATHS_SPEC": paths.get("spec", "project-spec.md"),
        "PATHS_FEATURE_LIST": paths.get("feature_list", "feature_list.json"),
        "PATHS_STATE": paths.get("state", ".harness"),
        "DOCS_ARCHITECTURE": documents.get("architecture", "docs/architecture.md"),
        "DOCS_CONVENTIONS": documents.get("conventions", "docs/conventions.md"),
        "DOCS_VERIFICATION": documents.get("verification", "docs/verification.md"),
    }


def render_adapter_text(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def has_generated_marker(text: str) -> bool:
    return any(
        "Generated by harness-kit" in line for line in text.splitlines()[:100]
    )


def add_generated_marker(text: str, adapter_id: str) -> str:
    """Marca un archivo generado sin romper el frontmatter de OpenCode."""
    if has_generated_marker(text):
        return text
    marker = (
        f"<!-- Generated by harness-kit {VERSION} | adapter {adapter_id} "
        "| no editar a mano -->"
    )
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                lines.insert(index + 1, "")
                lines.insert(index + 2, marker)
                return "\n".join(lines)
    return marker + "\n\n" + text


def remove_stale_generated(directory: Path, keep: set[Path]) -> None:
    """Elimina .md generados por el kit que ya no están en el adapter."""
    if not directory.is_dir():
        return
    for path in sorted(directory.rglob("*.md")):
        resolved = path.resolve()
        if resolved in keep:
            continue
        try:
            head = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if has_generated_marker(head):
            path.unlink()
    for subdirectory in sorted(
        (p for p in directory.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        if not any(subdirectory.iterdir()):
            subdirectory.rmdir()
    if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()


def strip_jsonc_comments(text: str) -> str:
    """Quita comentarios // y /* */ y comas finales de un JSONC."""
    out: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    escaped = False
    while index < length:
        char = text[index]
        following = text[index + 1] if index + 1 < length else ""
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "/" and following == "/":
            index += 2
            while index < length and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and following == "*":
            index += 2
            while index < length and not (
                text[index] == "*" and index + 1 < length and text[index + 1] == "/"
            ):
                index += 1
            index += 2
            continue
        out.append(char)
        index += 1
    return remove_trailing_commas("".join(out))


def remove_trailing_commas(text: str) -> str:
    """Quita comas antes de ``}`` o ``]`` sin tocar el interior de strings."""
    out: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    escaped = False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == ",":
            following = index + 1
            while following < length and text[following] in " \t\r\n":
                following += 1
            if following < length and text[following] in "}]":
                index += 1
                continue
        out.append(char)
        index += 1
    return "".join(out)


def parse_jsonc(path: Path) -> dict:
    try:
        data = json.loads(strip_jsonc_comments(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise BootstrapError(f"{path.name} no es JSON/JSONC válido: {exc}") from exc
    if not isinstance(data, dict):
        raise BootstrapError(f"{path.name} debe contener un objeto JSON")
    return data


def merge_adapter_config(path: Path, fragment: dict, adapter_id: str) -> None:
    """Fusiona el fragmento en la configuración existente sin duplicar reglas."""
    existing = parse_jsonc(path) if path.is_file() else {}
    merged = deepcopy(fragment)
    for key, value in existing.items():
        if key == "permissions":
            continue
        merged[key] = deepcopy(value)

    current = existing.get("permissions", [])
    if not isinstance(current, list):
        raise BootstrapError(f"{path.name}: 'permissions' debe ser una lista")
    rules = list(current)
    seen = {
        (rule.get("action"), rule.get("resource"), rule.get("effect"))
        for rule in rules
        if isinstance(rule, dict)
    }
    for rule in fragment.get("permissions", []):
        key = (rule.get("action"), rule.get("resource"), rule.get("effect"))
        if key not in seen:
            rules.append(deepcopy(rule))
            seen.add(key)
    merged["permissions"] = rules

    header = (
        f"// Generated by harness-kit {VERSION} | adapter {adapter_id}\n"
        "// bootstrap.py render fusiona este archivo y puede reescribirlo;\n"
        "// conserva tus claves, pero los comentarios propios no sobreviven.\n"
    )
    write_text(
        path, header + json.dumps(merged, indent=2, ensure_ascii=False) + "\n"
    )


def render_adapter(
    target: Path,
    project: str,
    profile_id: str,
    adapter_id: str,
    profile: dict,
) -> None:
    manifest_path = KIT_ROOT / "adapters" / adapter_id / "adapter.json"
    if not manifest_path.is_file():
        return
    manifest = read_json(manifest_path)
    adapter_dir = manifest_path.parent
    values = adapter_values(project, profile_id, adapter_id, profile)

    for entry in manifest.get("render", []):
        source = adapter_dir / entry["source"]
        destination_root = target / entry["target"]
        if not source.is_dir():
            continue
        keep: set[Path] = set()
        for source_file in sorted(source.rglob("*.md")):
            relative = source_file.relative_to(source)
            destination = destination_root / relative
            text = render_adapter_text(
                source_file.read_text(encoding="utf-8"), values
            )
            write_text(destination, add_generated_marker(text, adapter_id))
            keep.add(destination.resolve())
        remove_stale_generated(destination_root, keep)

    config = manifest.get("config")
    if config:
        fragment = read_json(adapter_dir / config["fragment"])
        merge_adapter_config(target / config["target"], fragment, adapter_id)


def cleanup_adapter(target: Path, manifest: dict) -> None:
    """Retira los archivos generados por un adapter que ya no está activo."""
    for entry in manifest.get("render", []):
        remove_stale_generated(target / entry["target"], set())


def sync_adapters(
    target: Path,
    project: str,
    profile_id: str,
    adapter_id: str,
    profile: dict,
) -> None:
    for manifest_id, manifest in adapter_manifests().items():
        if manifest_id == adapter_id:
            render_adapter(
                target, project, profile_id, adapter_id, profile
            )
        else:
            cleanup_adapter(target, manifest)


def adapter_errors(target: Path, adapter_id: str) -> list[str]:
    manifest_path = KIT_ROOT / "adapters" / adapter_id / "adapter.json"
    if not manifest_path.is_file():
        return []
    manifest = read_json(manifest_path)
    adapter_dir = manifest_path.parent
    errors: list[str] = []
    for entry in manifest.get("render", []):
        source = adapter_dir / entry["source"]
        destination_root = target / entry["target"]
        for source_file in sorted(source.rglob("*.md")):
            destination = destination_root / source_file.relative_to(source)
            if not destination.is_file():
                errors.append(
                    f"falta {destination.relative_to(target)} "
                    "(bootstrap.py render --target .)"
                )
    config = manifest.get("config")
    if config and not (target / config["target"]).is_file():
        errors.append(
            f"falta {config['target']} (bootstrap.py render --target .)"
        )
    return errors



def generated_marker(profile_id: str, adapter_id: str) -> str:
    return (
        "# Generated by harness-kit\n\n"
        f"- **Versión del kit:** {VERSION}\n"
        f"- **Perfil:** {profile_id}\n"
        f"- **Adapter:** {adapter_id}\n"
        f"- **Generado:** {utc_now()}\n\n"
        "Esta carpeta se reemplaza con `bootstrap.py render --target <proyecto>`.\n"
        "No edites `harness/` a mano: edita el kit y vuelve a renderizar.\n"
    )


def ensure_gitignore(target: Path, entries: list[str]) -> None:
    if not entries:
        return
    path = target / ".gitignore"
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    missing = [entry for entry in entries if entry not in existing]
    if not missing:
        return
    if existing and existing[-1].strip():
        existing.append("")
    existing.extend(missing)
    path.write_text("\n".join(existing) + "\n", encoding="utf-8")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ── vendorizado ───────────────────────────────────────────────────────────


def vendor_harness(target: Path, profile_id: str, adapter_id: str) -> Path:
    profile_dir, _ = load_profile(profile_id)
    adapter_dir = require_adapter(adapter_id)
    harness_dir = target / "harness"
    if harness_dir.exists():
        shutil.rmtree(harness_dir)

    copy_tree(KIT_ROOT / "core" / "bin", harness_dir / "bin")
    copy_tree(KIT_ROOT / "core" / "process", harness_dir / "process")
    copy_tree(KIT_ROOT / "core" / "roles", harness_dir / "roles")
    copy_tree(KIT_ROOT / "core" / "schemas", harness_dir / "schemas")
    copy_tree(KIT_ROOT / "core" / "templates", harness_dir / "templates")
    copy_tree(profile_dir, harness_dir / "profiles" / profile_id)
    copy_tree(adapter_dir, harness_dir / "adapters" / adapter_id)
    write_text(harness_dir / "VERSION", VERSION + "\n")
    write_text(harness_dir / "GENERATED.md", generated_marker(profile_id, adapter_id))
    (harness_dir / "bin" / "harness.py").chmod(0o755)
    (harness_dir / "bin" / "stack_check.py").chmod(0o755)
    (harness_dir / "bin" / "run_verb.py").chmod(0o755)
    return harness_dir


def install_generated_files(target: Path, profile_dir: Path, profile_id: str) -> None:
    init_src = profile_dir / "init.sh"
    if init_src.is_file():
        lines = init_src.read_text(encoding="utf-8").splitlines()
        header = f"# harness-kit {VERSION} | perfil {profile_id} | generado"
        if lines and lines[0].startswith("#!"):
            lines.insert(1, header)
        else:
            lines.insert(0, header)
        write_text(target / "init.sh", "\n".join(lines) + "\n", executable=True)

    tools_src = profile_dir / "tools"
    if tools_src.is_dir():
        copy_tree(tools_src, target / "tools")
        for tool in (target / "tools").glob("*.py"):
            tool.chmod(0o755)
        for tool in (target / "tools").glob("*.sh"):
            tool.chmod(0o755)


# ── init ──────────────────────────────────────────────────────────────────


def init_project(
    target: Path,
    profile_id: str,
    adapter_id: str,
    project: str,
    force: bool,
) -> None:
    profile_dir, profile = load_profile(profile_id)
    require_adapter(adapter_id)

    if target.exists():
        entries = list(target.iterdir())
        if entries and not force:
            raise BootstrapError(
                f"{target} no está vacío. Usa --force para escribir solo los "
                "archivos generados y conservar los del proyecto."
            )
    target.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Vendorizando harness/ (kit {VERSION})")
    vendor_harness(target, profile_id, adapter_id)

    print("[2/6] Instalando init.sh y tools/")
    install_generated_files(target, profile_dir, profile_id)

    print(f"[3/6] Renderizando adapter {adapter_id}")
    sync_adapters(target, project, profile_id, adapter_id, profile)

    print("[4/6] Creando configuración")
    config_path = target / "harness.config.json"
    if config_path.exists():
        print("      conservado harness.config.json existente")
    else:
        write_json(config_path, build_config(project, profile_id, adapter_id, profile))

    print("[5/6] Creando artefactos del proyecto")
    templates = KIT_ROOT / "core" / "templates"
    values = adapter_values(project, profile_id, adapter_id, profile)

    agents = target / "AGENTS.md"
    if not agents.exists():
        write_text(
            agents,
            render_adapter_text(
                (templates / "AGENTS.md").read_text(encoding="utf-8"), values
            ),
        )
        print("      creado AGENTS.md")

    spec = target / "project-spec.md"
    if not spec.exists():
        write_text(
            spec,
            render_adapter_text(
                (templates / "project-spec.md").read_text(encoding="utf-8"), values
            ),
        )
        print("      creado project-spec.md")

    feature_list = target / "feature_list.json"
    if not feature_list.exists():
        write_json(
            feature_list,
            {
                "project": project,
                "description": profile.get("description", ""),
                "rules": FEATURE_LIST_RULES,
                "features": [],
            },
        )
        print("      creado feature_list.json")

    for name in ("current.md", "history.md"):
        destination = target / "progress" / name
        if not destination.exists():
            write_text(
                destination, (templates / "progress" / name).read_text(encoding="utf-8")
            )

    docs_source = profile_dir / "docs"
    if docs_source.is_dir():
        for source in sorted(docs_source.glob("*.md")):
            destination = target / "docs" / source.name
            if not destination.exists():
                write_text(destination, source.read_text(encoding="utf-8"))
                print(f"      creado docs/{source.name}")

    for directory in (
        profile.get("paths", {}).get("source", "src"),
        profile.get("paths", {}).get("tests", "tests"),
        profile.get("paths", {}).get("features", "features"),
        profile.get("paths", {}).get("specs", "specs"),
        profile.get("paths", {}).get("progress", "progress"),
        profile.get("paths", {}).get("state", ".harness") + "/approvals",
        profile.get("paths", {}).get("state", ".harness") + "/reports",
    ):
        ensure_dir(target / directory)

    for relative, content in profile.get("scaffold", {}).get("files", {}).items():
        destination = target / relative
        if not destination.exists():
            write_text(destination, content)

    copy_scaffold_files(target, profile_dir, profile, profile_id)

    for relative in ("features", "specs"):
        directory = target / profile.get("paths", {}).get(relative, relative)
        if directory.is_dir() and not any(directory.iterdir()):
            write_text(directory / ".gitkeep", "")

    ensure_gitignore(target, profile.get("gitignore", []))

    print("[6/6] Listo")
    print("")
    print(f"Proyecto: {target}")
    print(f"Perfil:   {profile_id}")
    print(f"Adapter:  {adapter_id}")
    print("")
    print("Siguientes pasos:")
    print(f"  cd {target}")
    print("  ./init.sh")
    print("  python3 harness/bin/harness.py status")
    if adapter_id == "opencode":
        print("  # abre el proyecto en OpenCode y ejecuta /next")
    else:
        print("  # edita project-spec.md, docs/ y añade la primera feature")


# ── render / check ────────────────────────────────────────────────────────


def backfill_commands(target: Path, profile: dict) -> None:
    """Añade al config los verbos nuevos del perfil sin pisar los del usuario."""
    config_path = target / "harness.config.json"
    config = read_json(config_path)
    commands = config.setdefault("commands", {})
    added: list[str] = []
    for key, value in profile.get("commands", {}).items():
        if not (commands.get(key) or "").strip() and (value or "").strip():
            commands[key] = value
            added.append(key)
    forbidden = list(profile.get("agent_forbidden", []))
    if "agent_forbidden" not in config and forbidden:
        config["agent_forbidden"] = forbidden
        added.append("agent_forbidden")
    if added:
        write_json(config_path, config)
        print(f"      harness.config.json: +{', +'.join(sorted(added))}")


def copy_scaffold_files(
    target: Path, profile_dir: Path, profile: dict, profile_id: str
) -> None:
    """Copia los archivos de ``scaffold.copy`` que falten, sin pisar los existentes."""
    for relative in profile.get("scaffold", {}).get("copy", []):
        source = profile_dir / relative
        destination = target / relative
        if not source.is_file():
            raise BootstrapError(
                f"el perfil {profile_id} declara scaffold.copy '{relative}' pero no existe"
            )
        if not destination.exists():
            write_text(destination, source.read_text(encoding="utf-8"))
            print(f"      creado {relative}")


def render_target(target: Path) -> None:
    config_path = target / "harness.config.json"
    if not config_path.is_file():
        raise BootstrapError(
            f"{target} no parece un proyecto del kit: falta harness.config.json"
        )
    config = read_json(config_path)
    profile_id = config.get("profile")
    adapter_id = config.get("adapter", "generic")
    project = config.get("project") or target.name
    if not profile_id:
        raise BootstrapError("harness.config.json no define 'profile'")
    profile_dir, profile = load_profile(profile_id)
    require_adapter(adapter_id)

    print(f"[1/4] Re-vendorizando harness/ (kit {VERSION})")
    vendor_harness(target, profile_id, adapter_id)
    print("[2/4] Regenerando init.sh, tools/ y artefactos del perfil")
    backfill_commands(target, profile)
    install_generated_files(target, profile_dir, profile_id)
    copy_scaffold_files(target, profile_dir, profile, profile_id)
    print(f"[3/4] Renderizando adapter {adapter_id}")
    sync_adapters(target, project, profile_id, adapter_id, profile)
    print("[4/4] Hecho")
    print("")
    print("Conservados: harness.config.json, AGENTS.md, project-spec.md,")
    print("feature_list.json, specs/, features/, progress/, docs/, src/, tests/.")


def check_target(target: Path) -> int:
    config_path = target / "harness.config.json"
    if not config_path.is_file():
        raise BootstrapError(
            f"{target} no parece un proyecto del kit: falta harness.config.json"
        )
    adapter_id = read_json(config_path).get("adapter", "generic")
    errors = adapter_errors(target, adapter_id)
    if errors:
        print("[FAIL] adapter incompleto:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    harness = target / "harness" / "bin" / "harness.py"
    if not harness.is_file():
        raise BootstrapError(f"falta {harness}; ejecuta primero bootstrap.py init")
    result = subprocess.run(
        [sys.executable, str(harness), "--root", str(target), "validate", "--verify"],
        cwd=target,
        text=True,
    )
    return result.returncode


# ── CLI ───────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="Materializa el harness-kit en un proyecto destino.",
    )
    parser.add_argument("--version", action="version", version=f"harness-kit {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="crea el layout y los artefactos que falten")
    init.add_argument("--target", required=True, help="directorio del proyecto destino")
    init.add_argument("--profile", default="python-unittest", help="perfil de lenguaje")
    init.add_argument("--adapter", default="generic", help="adapter de harness")
    init.add_argument("--project", default=None, help="nombre del proyecto")
    init.add_argument(
        "--force",
        action="store_true",
        help="permite un destino no vacío; solo reemplaza lo generado",
    )

    render = sub.add_parser("render", help="refresca harness/, init.sh y tools/")
    render.add_argument("--target", required=True, help="directorio del proyecto")

    upgrade = sub.add_parser("upgrade", help="alias de render")
    upgrade.add_argument("--target", required=True, help="directorio del proyecto")

    check = sub.add_parser("check", help="valida el proyecto y ejecuta verify")
    check.add_argument("--target", required=True, help="directorio del proyecto")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target = Path(args.target).expanduser().resolve()
    try:
        if args.command == "init":
            project = args.project or target.name or "unnamed-project"
            init_project(target, args.profile, args.adapter, project, args.force)
            return 0
        if args.command in ("render", "upgrade"):
            render_target(target)
            return 0
        if args.command == "check":
            return check_target(target)
    except BootstrapError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
