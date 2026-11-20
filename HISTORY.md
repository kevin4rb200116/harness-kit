# Historial de harness-kit

> Entradas de tooling del repositorio original `betta-tech/harness-sdd`
> (2026-11-12 → 2026-11-20). Las entradas anteriores de ese archivo eran
> del proyecto CLI, no del kit. Además del historial narrativo, este repo
> conserva los commits filtrados en `git log` (hashes reescritos).

## 2026-11-12 — Tooling: harness-kit F0 + F1 + F2
- **Ámbito:** rama `uncle-bob-harness`, carpeta `harness-kit/`. No se tocó `src/`, `tests/` ni `.claude/agents/`.
- **F0:** máquina de estados `core/bin/harness.py` (`status`, `next`, `set`, `approve`, `block`, `note`, `validate`); hash SHA-256 normalizado del `.feature`, aprobaciones en `.harness/approvals/`, informes en `.harness/reports/`, `set done` con todas las puertas; 30 selftests.
- **F1:** core neutro (`process/`, `roles/`, `schemas/`, plantillas), perfil `python-unittest` (init.sh, mutador propio, docs, checkpoints) y `bootstrap.py` (`init`/`render`/`check`/`upgrade`); 14 selftests.
- **F2:** adapter OpenCode V2: 7 agentes con permisos por rol, 4 comandos (`/next`, `/spec`, `/approve`, `/status`), `opencode.fragment.json`, merge idempotente de `opencode.jsonc` y limpieza de generados; 17 selftests.
- **Decisiones:** `spec_partner` y `gatekeeper` son `primary`; el lead no puede aprobar, no puede usar `--force` y no puede lanzar `explore`; `verify` es el gate de sesión.
- **Verificación:** 61 selftests del kit y `./init.sh` del repo (43 tests) en verde; scaffolds reales en `/tmp/opencode`.
- **Cierre:** `VERSION` 0.2.0. Siguiente: F2.1 (disciplina de shell) y stack de referencia Python.

## 2026-11-15 — Tooling: harness-kit F2.2 + F3 + F3.5 + F4
- **Ámbito:** rama `uncle-bob-harness`, carpeta `harness-kit/`. No se tocó `src/`, `tests/` ni `.claude/agents/`.
- **F3 — stack Docker Compose:** `compose.yaml` (servicio `app`, bind mount `.:/app`, uid/gid del host), `Dockerfile` (`python:3.12-slim`) y `tools/clean.sh`. Los cinco verbos del perfil pasan a `docker compose`; el arnés (`harness.py`, `init.sh`) sigue en el host. `core/bin/run_verb.py` ejecuta un verbo del manifiesto con `shlex.split` + `subprocess.run(..., cwd=root)` y sin shell. `render` restaura `compose.yaml`, `Dockerfile` y `tools/clean.sh` si faltan y no pisa ediciones.
- **F3.5 — puerta de arquitectura:** rol `architect`, comando `/architecture` y fase `architecture` en `next` mientras `docs/architecture.md` falte o conserve un `TODO`. `has_todo_marker()` distingue `TODO:` de la palabra citada en prosa o en código. `architect` solo edita `docs/architecture.md` y es agente primario.
- **F4 — correcciones de la prueba de campo:** gate de informe TDD (`R<n>`, `@sN`, mapa de trazabilidad) antes de `judge` y en `set done`; fase `repair` con los motivos vigentes del judge o de la mutación; el mtime del informe TDD es el epoch de la ronda; `as_float` acepta `"94.12%"`; `gatekeeper` completa los ocho roles.
- **F2.2 — un solo `/next`:** el lead recorre `tdd → judge → mutation → repair` en el mismo turno y solo para en puertas humanas (`architecture`, `spec`, `approval`, `blocked`, `all_done`). Tope de **3 rondas** de reparación; a la cuarta se bloquea la feature con el motivo.
- **Punto de entrada común:** `AGENTS.md` es el mapa único (stack, comandos, paradas/transiciones, mapa de lectura, reglas duras) y cada rol y agente abre con una cabecera compacta `## Entrada` (herramientas, fase, escritura). Se eliminó la tabla de herramientas por rol y su duplicación en los prompts.
- **Commits:** `0c5dd25` F3, `48cbf76` F3.5 + F4, `8126b60` F2.2 + prompts/docs/punto de entrada. Cada uno verificado en un worktree aislado: 130, 155 y 165 selftests en verde.
- **Verificación:** 165 selftests del kit en verde, `./init.sh` del repo en verde (43 tests) y mutación focalizada del motor **16/16 (100 %)** (`/tmp/opencode/mutate_harness_fieldfix.py`).
- **Cierre:** `VERSION` 0.5.0. Próximo: repetir la prueba de campo desde cero en `demo-hk` con los prompts nuevos; después, diseñar el `cartographer` integrado.

## 2026-11-15 — Tooling: harness-kit F5 (ajustes tras la prueba de campo)
- **Ámbito:** rama `uncle-bob-harness`, carpeta `harness-kit/`. No se tocó `src/`, `tests/` ni `.claude/agents/`.
- **Fuente:** revisión de las sesiones de `demo-hk` en `~/.local/share/opencode/opencode.db` (`ses_e27bc8fc…`, `ses_e1eba6084…` y sus subsesiones).
- **Diagnóstico:** los subagentes recibieron briefs de una línea; con el brief humano que listaba `docs/`, `progress/`, `specs/` y el `.feature`, el mismo modelo leyó los siete archivos y mató el mutante. El lead releyó informes viejos y se estancó; el TDD no reescribió su informe; el lead reescribió `history.md` desde cero; `current.md` obsoleto confundió a dos agentes mientras `validate` decía `[OK]`; el TDD mutiló `src/main.py` para probar un test.
- **Motor:** `tdd_round_epoch` mide el mayor mtime entre informe TDD, `src/` y `tests/` (sin `__pycache__`), así un cambio de código caduca el veredicto aunque falte reescribir el informe. `note --history` añade a `progress/history.md` sin reescribirlo. `validate` separa errores de avisos: informe TDD heredado en `done` y `current.md` sin la feature `in_progress` son `[WARN]`.
- **Prompts:** el lead ya no puede editar `history.md`; brief obligatorio con lista de lecturas; todos los roles y agentes cierran con `leído: <archivos>`; el `tdd_craftsman` no mutila producción y no usa `replaceAll`.
- **Commits:** `52979e2` motor, `547c942` prompts/docs. Cada uno verde en un worktree aislado (61 y 173 selftests).
- **Verificación:** 173 selftests en verde, `./init.sh` verde (43 tests), mutación focalizada **22/22 (100 %)** y scaffold 0.6.0 con `note --history` y `validate` en verde. `demo-hk` pasa de `[FAIL]` a `[OK] + [WARN]` por su informe TDD heredado.
- **Cierre:** `VERSION` 0.6.0. Próximo: repetir la prueba de campo desde cero con el kit 0.6.0.

## 2026-11-17 — Tooling: harness-kit 0.6.1 (segunda prueba de campo)
- **Ámbito:** rama `uncle-bob-harness`, carpeta `harness-kit/`. No se tocó `src/`, `tests/` ni `.claude/agents/`.
- **Fuente:** transcripción y artefactos de la prueba de campo 0.6.0 en `demo-hk` (feature `cli_hello` a `done`, mutación 100 %).
- **Diagnóstico:** (1) el restore del mutador cambiaba el mtime de `src/` y `next` devolvía `judge` en vez de `repair`; (2) el judge escribió su JSON una sola vez y los veredictos posteriores no llegaron a disco; (3) el judge rechazaba por el informe de mutación, duplicando la puerta; (4) la mutación incluía `tests/` y gastaba una reparación; (5) `spec_partner` no cerró `project-spec.md` y `validate` decía `[OK]`; (6) el gatekeeper no podía ejecutar `harness.py status`.
- **Motor:** `tools/mutate.py` conserva el mtime original y rechaza `tests/`, `test_*.py` y `conftest.py`. `phase()` exige judge `APPROVED` y mutación frescos (posteriores a la ronda TDD) antes de avanzar; `set done` repite la comprobación. `project_spec_errors()`/`project_spec_pending()` cierran la fase `spec`, bloquean `spec_ready`/`in_progress` y avisan en `validate`.
- **Prompts:** judge independiente de la mutación y reescritura obligatoria de JSON+MD; mutation_tester solo producción y reescritura obligatoria; spec_partner y `/spec` cierran `project-spec.md`; architect aclara que no es suyo; lead verifica frescura; gatekeeper consulta `status`; workflow, mutation-testing y AGENTS lo documentan.
- **Commits:** `6b0a3b1` mutador, `a46f45f` motor, `d9a0ee7` prompts/docs, `12a2fce` versión, `91442ba` test de frescura. Cada uno verde.
- **Verificación:** 190 selftests del kit en verde, `./init.sh` del repo en verde (43 tests), mutación focalizada **12/12 (100 %)** (`/tmp/opencode/mutate_harness_freshness.py`), y scaffold 0.6.1 en `demo-hk` con la puerta de `project-spec.md` comprobada (falla con `TODO`, pasa sin él).
- **Cierre:** `VERSION` 0.6.1. `demo-hk` regenerado en limpio con el backlog sembrado (4 features `pending`); respaldo de la corrida 0.6.0 en `/tmp/opencode/demo-hk-0.6.0-fieldtest.tar.gz`. Próximo: repetir la prueba de campo completa desde `/next → /architecture → /next → /spec → /next → /approve → /next`.

## 2026-11-20 — Tooling: harness-kit 0.6.2 (tercera prueba de campo)
- **Ámbito:** rama `uncle-bob-harness`, carpeta `harness-kit/`. No se tocó `src/`, `tests/` ni `.claude/agents/`.
- **Fuente:** prueba de campo 0.6.1 en `demo-hk` (feature `cli_hello`). El `spec_partner` no hizo ni una llamada a `write`/`edit`: describió la spec, afirmó haberla escrito y su `leído:` listaba archivos inexistentes. `/next` detectó el vacío y pidió `/spec` otra vez, sin corromper el estado.
- **Diagnóstico:** no fue un problema de permisos (en OpenCode V2 `*` cruza `/`, así que `specs/*` cubre rutas anidadas). El spec recuperado de la base de datos (`/tmp/opencode/demo-hk-spec-recovered`) habría pasado `spec_ready` pese a no cubrir el criterio de subcomando desconocido: el motor no comprobaba la cadena acceptance → R<n>.
- **Motor:** `acceptance_ids()` deriva `A1..An` por posición (sin cambiar `feature_list.json`); `spec_coverage_errors()` exige la tabla `A<n> → R<n>` en `requirements.md` y cada `R<n>` en `design.md` y `tasks.md`; `spec_errors(require_coverage)` y `validate` fallan en `spec_ready`/`in_progress` y solo avisan en `done` heredado.
- **Prompts y proceso:** `spec_partner` crea los cuatro esqueletos al abrir, escribe cada decisión y relee antes de cerrar (`escrito:` + `leído:`); pegar en el chat no cierra la fase. `architect` cierra con `write`/`read` y deja «Contexto para la spec» en `docs/architecture.md` como traspaso durable. El lead y `/next` tratan el `leído:` como promesa, no como prueba. `AGENTS.md`, `workflow.md`, `spec.md` y `traceability.md` recogen la regla.
- **Commits:** `d4244b7` motor y fixtures (199 selftests), `f91b4de` prompts/docs (202), `37721fa` versión. Cada uno verificado en aislamiento con `git stash`; ninguno depende de otro.
- **Verificación:** 202 selftests del kit en verde, `./init.sh` del repo en verde (43 tests), mutación focalizada **9/9 (100 %)** (`/tmp/opencode/mutate_harness_coverage.py`) y scaffold 0.6.2 en `/tmp/opencode/kit-0.6.2-check`: `set 1 spec_ready` falla por `A1`/`A2` sin la tabla y pasa al añadirla.
- **Cierre:** `VERSION` 0.6.2. Próximo: repetir la prueba de campo completa en `demo-hk` con el kit 0.6.2 (el humano sigue esa spec en otra sesión, sin tocar desde aquí); después, diseñar el `cartographer` integrado.
