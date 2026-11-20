# Checkpoints — evaluar el destino, no el camino

> En un sistema multi-agente no se evalúa la intención, se evalúa el estado
> final en disco. Estos checkpoints son objetivos: un juez humano o IA puede
> comprobarlos con comandos.

Los checkpoints `C*` son **genéricos** (los entiende cualquier perfil). Los
`P*` los define cada perfil de lenguaje. El `judge` referencia los IDs y
registra el resultado en `progress/judge_<name>.md`.

## Genéricos (C)

### C1 — El arnés está completo

- [ ] Existen `AGENTS.md`, `harness.config.json`, `feature_list.json`,
      `progress/current.md`, `project-spec.md`.
- [ ] Existe `harness/bin/harness.py` y responde a `status`.
- [ ] `./init.sh` termina con exit code 0.

### C2 — El estado es coherente

- [ ] Como máximo una feature en `in_progress`.
- [ ] Toda feature `done` tiene tests que pasan.
- [ ] `progress/current.md` describe la sesión activa, no basura anterior.
- [ ] `harness.py validate` está verde.

### C3 — La spec existe y es trazable

- [ ] Toda feature `sdd` no-`pending` tiene
      `specs/<name>/{requirements,design,tasks}.md`.
- [ ] `requirements.md` usa EARS y tiene IDs `R<n>` estables.
- [ ] Cada `acceptance` está cubierto por al menos un `R<n>`.
- [ ] `tasks.md` cita los `R<n>` que cubre.

### C4 — El contrato está aprobado

- [ ] `features/<name>.feature` existe y tiene escenarios `@sN`.
- [ ] El `.feature` incluye la tabla `R<n> → @sN`.
- [ ] `.harness/approvals/<name>.json` existe y su hash coincide con el
      `.feature` actual.
- [ ] Ninguna feature está en `in_progress` sin aprobación válida.

### C5 — La verificación se demuestra

- [ ] `commands.test` está en verde.
- [ ] `commands.verify` está en verde.
- [ ] La evidencia está en un comando reproducible, no en una afirmación.

### C6 — La trazabilidad está completa

- [ ] Cada `R<n>` aparece en al menos un `@sN`.
- [ ] Cada `@sN` tiene al menos un test concreto.
- [ ] `progress/tdd_<name>.md` contiene el mapa `R<n> → @sN → test`.
- [ ] El informe TDD cita las tasks `T<n>` completadas.
- [ ] No hay tests huérfanos sin escenario que los justifique.

### C7 — La disciplina TDD es visible

- [ ] Hay evidencia de ciclos Rojo-Verde-Refactor.
- [ ] No hay producción que ningún test exija.
- [ ] Todas las tasks de `tasks.md` están `[x]` o justificadas.
- [ ] No hay `skip`, tests comentados ni `print()` de debug.

### C8 — La mutación valida la red

- [ ] Existe `.harness/reports/mutation_<name>.json`.
- [ ] `verdict` es `PASS`.
- [ ] `score` alcanza `mutation.threshold`.
- [ ] Los supervivientes están documentados.

## De perfil (P)

Cada perfil añade sus checkpoints en `harness/profiles/<id>/checkpoints.md`.
Por ejemplo, el perfil `python-unittest` añade:

- **P1 — Arquitectura**: `docs/architecture.md` no contiene marcadores
  `TODO:` y el código respeta sus capas y fronteras.
- **P2 — Convenciones**: nombres, formato e imports según
  `docs/conventions.md`.
- **P3 — Dependencias**: no se introducen dependencias externas sin
  decisión documentada.
- **P4 — Higiene de tests**: no hay archivos temporales, asserts débiles ni
  tests acoplados a detalles internos.

## Cómo se usa

- El `judge` recorre C1–C8 + P* de la feature en curso.
- Un checkpoint no cumplido es un rechazo, salvo justificación explícita y
  aprobada por el humano.
- El `mutation_tester` solo puede actuar con C1–C8 en verde.
- `set done` vuelve a comprobar por script los checkpoints mecanizables; los
  de juicio quedan en el informe del judge.
