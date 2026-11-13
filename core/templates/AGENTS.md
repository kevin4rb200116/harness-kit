# AGENTS.md — mapa de navegación para agentes

> Punto de entrada para cualquier agente que trabaje en `{{PROJECT}}`.
> Este proyecto usa el arnés SDD (`{{PROFILE}}` / adapter `{{ADAPTER}}`,
> versión del kit `{{VERSION}}`).

## Antes de empezar (obligatorio)

1. Ejecuta `./init.sh`. Si falla, **para** y resuelve el entorno.
2. Lee `progress/current.md`.
3. Ejecuta `python3 harness/bin/harness.py next`.
4. Lee `harness/process/workflow.md` antes de coordinar nada.

## Mapa

| Ruta | Qué contiene | Cuándo leerlo |
|---|---|---|
| `harness/process/` | El método: workflow, spec, trazabilidad, TDD, Gherkin, mutación, checkpoints | Siempre |
| `harness/roles/` | Los seis roles del pipeline | Antes de actuar |
| `harness/templates/` | Plantillas de specs, features e informes | Al crear artefactos |
| `feature_list.json` | Estado de las features | Siempre |
| `harness.config.json` | Paths, comandos y umbral de mutación | Al ejecutar tests o mutación |
| `project-spec.md` | Decisiones globales | Antes de especificar |
| `specs/<name>/` | Requirements EARS, design y tasks | Antes de Gherkin o TDD |
| `features/<name>.feature` | Contrato ejecutable aprobado | Antes de implementar |
| `progress/current.md` | Bitácora de la sesión | Al empezar y mientras trabajas |
| `docs/architecture.md` | Estándar de calidad | Antes de implementar |
| `docs/conventions.md` | Estilo y nombres | Antes de escribir código |
| `docs/verification.md` | Cómo demostrar que funciona | Antes de cerrar |

## Pipeline

```
pending
  → spec_partner      → project-spec.md + specs/<name>/{requirements,design,tasks}.md
  → gherkin_author    → features/<name>.feature
  → ⏸ aprobación humana (harness.py approve <id>)
  → in_progress
  → tdd_craftsman     → código + tests + tasks [x]
  → judge             → .harness/reports/judge_<name>.json
  → mutation_tester   → .harness/reports/mutation_<name>.json
  → done
```

Detalle completo: `harness/process/workflow.md`.

## Reglas duras

- Una sola feature en `in_progress`.
- No hay código sin test rojo que lo pida.
- No hay implementación sin `.feature` aprobado.
- No hay cierre sin judge `APPROVED` y mutación `PASS` sobre el umbral.
- El estado solo lo cambia `harness.py`; los subagentes no editan
  `feature_list.json`.
- La aprobación humana se registra en `.harness/approvals/<name>.json`; si
  el `.feature` cambia, caduca.

## Comandos

```bash
./init.sh                                  # verificación completa
python3 harness/bin/harness.py status      # estado
python3 harness/bin/harness.py next        # siguiente fase
python3 harness/bin/harness.py validate    # coherencia
```
