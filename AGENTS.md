# AGENTS.md — mantenimiento de harness-kit

> Este repositorio **es** el kit. La plantilla que reciben los proyectos
> destino está en `core/templates/AGENTS.md`; no confundas ambas.

## Origen

- Separado de `betta-tech/harness-sdd` (rama `uncle-bob-harness`, commit
  `4df4bc1`) el **2026-11-20**.
- El split se hizo con `git filter-branch --subdirectory-filter harness-kit`
  sobre una copia. El historial de este repo empieza en el primer commit del
  kit y no contiene el proyecto CLI (`src/`, `tests/`, `feature_list.json`).
- El repo original queda como archivo; este repo no depende de él.
- Contenido equivalente a la versión **0.6.2** (commit original `37721fa`).
- Rama `main`, sin remoto configurado.

## Estado

- **202 selftests** del kit en verde.
- Completos F0…F4.2. Pendientes: **F5 perfil Go** y **F6 adapter Claude Code**.
- El kit **no tiene `feature_list.json` propio**: el roadmap vive en
  `README.md` y este archivo.
- `./init.sh` de la raíz del repo original (43 tests) era del proyecto CLI,
  no del kit; aquí no existe ni aplica.

## Comandos

```bash
python3 -m unittest discover -s selftest -q   # suite del kit
python3 bootstrap.py --version                # 0.6.2

python3 bootstrap.py init --target ../mi-proyecto \
  --profile python-unittest --adapter opencode --project mi-proyecto
python3 bootstrap.py render  --target ../mi-proyecto   # upgrade es alias
python3 bootstrap.py check   --target ../mi-proyecto
```

## Mapa

| Ruta | Qué es |
|---|---|
| `core/bin/harness.py` | máquina de estados (`status`, `next`, `set`, `approve`, `block`, `note`, `validate`) |
| `core/process/` | workflow, spec, tdd, gherkin, traceability, mutation-testing, checkpoints |
| `core/roles/` | 8 roles del pipeline |
| `core/templates/` | plantillas para el proyecto destino (AGENTS, specs, progress) |
| `profiles/python-unittest/` | stack Python + Docker Compose, `init.sh`, `mutate.py`, docs |
| `adapters/opencode/` | 8 agentes, 5 comandos, fragmento de permisos, README y DEMO |
| `adapters/generic/` | fallback para cualquier harness que lea `AGENTS.md` |
| `selftest/` | 202 tests de harness, bootstrap, adapter, mutador y stack |
| `bootstrap.py` | `init`, `render`, `upgrade` (alias), `check` |

## Decisiones tomadas (contexto para retomar)

- **0.6.2:** `spec_ready` exige la tabla `A<n> → R<n>` en `requirements.md`
  y cada `R<n>` en `design.md` y `tasks.md`; en una feature `done` heredada
  la falta de cobertura solo avisa en `validate`.
- Los roles conversacionales cierran con `write`/`read` y declaran
  `escrito:` + `leído:`; el lead verifica el artefacto, no la promesa.
- `docs/architecture.md` incluye «Contexto para la spec» como traspaso
  durable entre sesiones.
- Se evaluó convertir `architect`/`spec_partner` en subagentes para aislar
  contexto. **Descartado por ahora:** en OpenCode V2 un subagente no tiene
  turno de conversación con el humano. Se mantiene `architect`,
  `spec_partner` y `gatekeeper` como primarios, y `gherkin_author`,
  `tdd_craftsman`, `judge` y `mutation_tester` como subagentes.
- El experimento alternativo `agents-sdd-tdd-template` (con el rol
  `cartographer`, de solo lectura) vive fuera de este repo, en
  `/home/adrian/Descargas/Codigo/betta-tech/agents-sdd-tdd-template`.
  No forma parte del kit.
- El `cartographer` todavía no está integrado en el kit.

## Deuda y pendientes

- `README.md` dice «173 tests cubren»; ya son **202**.
- `README.md` → «Limitaciones conocidas» dice que Claude Code se conserva
  «hasta F5»; el adapter es **F6**.
- F5 (perfil Go) y F6 (adapter Claude Code) sin empezar.
- `demo-hk` (en `/home/adrian/Workspace/AI/demo-hk`) sigue en **0.6.1**:
  falta el `upgrade` a 0.6.2 y la feature `sha256sum` con `hello` ya
  presente. `upgrade` conserva `AGENTS.md`, así que las reglas nuevas hay
  que añadirlas a mano si se quieren allí.

## Primeros pasos si retomas

1. `python3 -m unittest discover -s selftest -q` → 202 OK.
2. Lee `README.md` (estado, quickstart, contrato del stack) y `HISTORY.md`.
3. Si tocas el kit: una rama por cambio, tests verdes y mutación focalizada
   sobre lo tocado antes de cerrar.
