#!/usr/bin/env python3
"""run_verb.py — ejecuta un verbo del manifiesto sin pasar por un shell.

Uso::

    python3 harness/bin/run_verb.py test [--root DIR] [--file RUTA]

Lee ``harness.config.json``, sustituye ``{file}`` si se pasa ``--file`` y
ejecuta el comando con ``shlex.split`` + ``subprocess.run``. No usa shell:
los comandos compuestos ya están prohibidos por ``stack_check.py``.
``--root`` fija el directorio del proyecto y el cwd del proceso.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


def load_command(root: Path, verb: str) -> str:
    """Comando declarado para ``verb`` en ``harness.config.json``."""
    config_path = root / "harness.config.json"
    if not config_path.is_file():
        raise SystemExit(f"falta {config_path.name}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{config_path.name} no es JSON válido: {exc}")
    command = (config.get("commands", {}).get(verb) or "").strip()
    if not command:
        raise SystemExit(f"commands.{verb} está vacío o no existe")
    return command


def render_command(command: str, file: str | None) -> list[str]:
    """Tokeniza el comando y sustituye ``{file}`` cuando toca."""
    if "{file}" in command:
        if file is None:
            raise SystemExit("el comando espera --file")
        command = command.replace("{file}", file)
    return shlex.split(command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ejecuta un verbo del stack")
    parser.add_argument("verb")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--file", default=None)
    args = parser.parse_args(argv)

    command = load_command(args.root, args.verb)
    argv_command = render_command(command, args.file)
    print(f"$ {' '.join(argv_command)}", flush=True)
    return subprocess.run(argv_command, cwd=args.root).returncode


if __name__ == "__main__":
    sys.exit(main())
