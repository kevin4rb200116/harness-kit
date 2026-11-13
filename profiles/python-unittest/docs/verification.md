# Verificación — cómo demostrar que el trabajo funciona

> Regla de oro: **el agente no dice "funciona", lo demuestra**. Toda feature
> termina con evidencia ejecutable, no con afirmaciones.

## Nivel 1 — Tests unitarios (obligatorio)

Toda función pública de `src/` tiene al menos un test en `tests/` que cubre
el camino feliz y, si puede fallar, al menos un camino de error.

```bash
python3 -m unittest discover -s tests -v
```

## Nivel 2 — Integración (obligatorio para features de UI o CLI)

Las features que añaden un comando o un endpoint se verifican ejecutando el
artefacto real contra un entorno temporal:

```python
import os
import subprocess
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    env = {**os.environ, "APP_DATA": os.path.join(tmp, "data.json")}
    output = subprocess.check_output(
        ["python3", "-m", "src.cli", "list"],
        env=env,
        text=True,
    )
    assert output == ""
```

Adapta el comando y la variable de entorno al contrato del proyecto.

## Nivel 3 — Smoke test (recomendado)

Antes de cerrar la sesión, ejecuta un flujo end-to-end con datos temporales
en `/tmp`. No uses datos reales del usuario.

## Contrato del stack

`harness.config.json` declara cinco verbos y `harness/bin/stack_check.py`
comprueba que existen, que son órdenes simples y que esta prosa los cita
tal cual (los argumentos finales pueden variar).

```bash
python3 harness/bin/stack_check.py
python3 -m compileall -q src
python3 -m unittest discover -s tests -v
python3 tools/mutate.py src/<archivo>.py
find . -name __pycache__ -type d -prune -exec rm -rf {} +
```

Cada verbo es **una sola orden**: la allowlist del agente son cadenas
literales y un pipe o un `;` deniega el comando entero. Los placeholders
`{file}` y `<archivo>` son argumentos, no operadores: no cuentan como
comando compuesto.

`build` y `clean` los ejecuta el humano a cargo o el flujo de integración
(`agent_forbidden` en `harness.config.json`); ningún agente los tiene en su
allowlist. `clean` es destructivo: no debe correr dentro de una sesión de
agente.

## Gate único

```bash
./init.sh
```

`init.sh` valida el estado con `harness.py validate`, ejecuta los tests y
comprueba los archivos base. Debe terminar con exit code 0.

## Mutación

```bash
python3 tools/mutate.py src/<archivo>.py
```

El umbral vive en `harness.config.json` (`mutation.threshold`). El
`mutation_tester` normaliza la salida al contrato de
`harness/process/mutation-testing.md`.

## Qué no es verificación

- "He revisado el código y parece bien".
- "Los tests deberían pasar".
- Un test sin asserts.
- Un `skip` sin razón documentada.
