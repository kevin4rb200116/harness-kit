#!/usr/bin/env python3
"""stack_check.py — el contrato del stack, verificado contra el manifiesto.

El arnés exige cinco verbos: ``check``, ``build``, ``test``, ``mutation`` y
``clean``. Este script comprueba que el proyecto los declara, que cada uno es
**una orden simple** (la allowlist del agente son cadenas literales: un pipe o
un ``;`` deniega el comando entero) y que la prosa los documenta tal cual.
Los placeholders ``{file}`` y ``<archivo>`` son argumentos, no operadores.
``agent_forbidden`` declara los verbos que ningún agente ejecuta.

Uso::

    python3 harness/bin/stack_check.py [--root DIR] [--json]

Salida: ``[OK]``/``[FAIL]`` por comprobación; exit 1 si algo falla.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERBS = ("check", "build", "test", "mutation", "clean")
OPTIONAL = ("verify",)
SHELL_TAGS = {"bash", "sh", "shell", "console"}

# Operadores que convierten una orden en un comando compuesto: el scanner de
# OpenCode los parte en varios recursos y cualquiera sin regla deniega el todo.
COMPOUND_RE = re.compile(r"\||;|&&|\|\||\$\(|`|>>|>|<")

SNIPPET_RE = re.compile(r"```([^\n]*)\n(.*?)```|~~~([^\n]*)\n(.*?)~~~", re.S)
INLINE_RE = re.compile(r"`([^`\n]+)`")
PLACEHOLDER_RE = re.compile(r"\{[^}]*\}|<[^>]*>")


def has_content(text: str) -> bool:
    """¿El documento aporta algo más que un título?"""
    return any(
        line.strip() and not line.strip().startswith("#")
        for line in text.splitlines()
    )


def executable_lines(text: str) -> list[str]:
    """Líneas de código ejecutable citadas en un documento."""
    lines: list[str] = []
    for match in SNIPPET_RE.finditer(text):
        tag = (match.group(1) or match.group(3) or "").strip().lower()
        body = match.group(2) if match.group(2) is not None else match.group(4)
        if tag and tag.split()[0] not in SHELL_TAGS:
            continue
        for line in (body or "").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    for span in INLINE_RE.findall(text):
        stripped = span.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def signature(command: str) -> list[str]:
    """Tokens que la prosa debe reproducir: hasta el primer placeholder."""
    tokens: list[str] = []
    for token in command.split():
        if PLACEHOLDER_RE.search(token):
            break
        tokens.append(token)
    return tokens


def documented(command: str, lines: list[str]) -> bool:
    """¿La prosa cita el comando? Los argumentos finales pueden variar."""
    sig = signature(command)
    return bool(sig) and any(line.split()[: len(sig)] == sig for line in lines)


def strip_placeholders(command: str) -> str:
    """Quita ``{file}`` y ``<arg>``: son argumentos, no operadores de shell."""
    return PLACEHOLDER_RE.sub("", command)


def is_compound(command: str) -> bool:
    """¿El comando encadena operadores de shell? Los placeholders no cuentan."""
    return bool(COMPOUND_RE.search(strip_placeholders(command)))


def check(root: Path) -> tuple[list[str], list[str]]:
    """Devuelve (problemas, avisos)."""
    problems: list[str] = []
    warnings: list[str] = []

    config_path = root / "harness.config.json"
    if not config_path.is_file():
        return [f"falta {config_path.name}"], warnings
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{config_path.name} no es JSON válido: {exc}"], warnings

    commands = config.get("commands", {})
    for verb in VERBS:
        command = (commands.get(verb) or "").strip()
        if not command:
            problems.append(f"commands.{verb} está vacío o no existe")
            continue
        if is_compound(command):
            problems.append(
                f"commands.{verb} no es una orden simple (pipe, ';', '&&', "
                f"redirección o sustitución): {command!r}"
            )

    agent_forbidden = config.get("agent_forbidden", [])
    if not isinstance(agent_forbidden, list):
        problems.append("agent_forbidden debe ser una lista de verbos")
    else:
        for verb in agent_forbidden:
            if verb not in VERBS and verb not in OPTIONAL:
                problems.append(
                    f"agent_forbidden cita un verbo desconocido: {verb!r}"
                )
            elif not (commands.get(verb) or "").strip():
                problems.append(
                    f"agent_forbidden cita un verbo sin comando: {verb!r}"
                )

    documents = config.get("documents", {})
    doc_lines: dict[str, list[str]] = {}
    for name, relative in documents.items():
        path = root / relative
        if not path.is_file():
            problems.append(f"documents.{name} apunta a un archivo que no existe: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        if not has_content(text):
            problems.append(f"{relative} está vacío o es un placeholder")
            continue
        doc_lines[relative] = executable_lines(text)

    if not problems:
        cited = [line for lines in doc_lines.values() for line in lines]
        for verb in VERBS:
            command = (commands.get(verb) or "").strip()
            if command and not documented(command, cited):
                problems.append(
                    f"commands.{verb} no aparece documentado en la prosa: {command!r}"
                )

    for verb in OPTIONAL:
        if not (commands.get(verb) or "").strip():
            warnings.append(f"commands.{verb} no definido (opcional)")

    return problems, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="contrato del stack")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", help="salida legible por máquina")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    problems, warnings = check(root)

    if args.json:
        print(
            json.dumps(
                {"ok": not problems, "problems": problems, "warnings": warnings},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for warning in warnings:
            print(f"[WARN]  {warning}")
        for problem in problems:
            print(f"[FAIL]  {problem}")
        if not problems:
            print(f"[OK]    contrato del stack: {', '.join(VERBS)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
