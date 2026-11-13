# harness-kit — arnés SDD portable

Plantilla copiable para llevar el proceso **spec → Gherkin → TDD → judge →
mutación** a cualquier proyecto. El kit separa cuatro capas para que el
método no dependa del lenguaje ni del harness:

| Capa | Qué contiene | Dónde vive en el destino |
|---|---|---|
| **Core** | Proceso, roles, esquema, plantillas | `harness/process`, `harness/roles`, `harness/schemas`, `harness/templates` |
| **Perfil** | Stack: paths, comandos, mutador, docs y checkpoints | `harness/profiles/<id>` |
| **Adapter** | Harness: cómo se exponen los roles y comandos | `harness/adapters/<id>` |
| **Proyecto** | Spec, estado, features, informes, código | raíz del proyecto |

## Estado de esta versión

**Versión 0.3.1 — F0 + F1 + F2 + F2.1 completos.**

- ✅ F0: máquina de estados ejecutable (`harness/bin/harness.py`) + 30 tests.
- ✅ F1: core neutro, perfil `python-unittest`, `bootstrap.py` + 14 tests.
- ✅ F2: adapter OpenCode V2 (7 agentes con permisos, `/next`, `/spec`,
  `/approve`, `/status`) + 17 tests.
- ✅ F2.1: disciplina de shell en los prompts (una orden por llamada),
  contrato de cinco verbos verificado por `harness/bin/stack_check.py` y
  `agent_forbidden` para `build`/`clean` (117 selftests; mutación 100 %
  sobre el checker).
- ⏳ F4: perfil Go.
- ⏳ F5: adapter Claude Code.

El adapter `generic` sigue disponible para cualquier harness que lea
`AGENTS.md`. El adapter `opencode` es el recomendado: expone los roles como
agentes nativos y convierte las puertas en comandos slash.

## Quickstart

Requisitos: Python 3.9+ (runtime del arnés, no del proyecto destino).

```bash
# 1. Copia o clona harness-kit y entra en él
cd harness-kit

# 2. Genera un proyecto nuevo (adapter recomendado: OpenCode)
python3 bootstrap.py init \
  --target ../mi-proyecto \
  --profile python-unittest \
  --adapter opencode \
  --project mi-proyecto

# 3. Verifica
cd ../mi-proyecto
./init.sh
python3 harness/bin/harness.py status
```

Abre el proyecto en OpenCode y ejecuta `/next`. El agente por defecto es
`craftsman_lead`. Para otros harness, usa `--adapter generic`: los roles
quedan en `harness/roles/` para uso manual.

Si el destino ya existe y no está vacío, añade `--force`: solo reemplaza lo
generado (`harness/`, `init.sh`, `tools/`, `.opencode/`, `opencode.jsonc`) y
conserva spec, estado, docs y código.

## Layout generado

```
mi-proyecto/
├── AGENTS.md                     # mapa para agentes (renderizado)
├── harness.config.json           # fuente única de paths/comandos/umbral
├── feature_list.json             # estado (solo lo edita harness.py)
├── project-spec.md               # decisiones globales
├── init.sh                       # gate de verificación
├── opencode.jsonc                # solo adapter opencode: default_agent + denies
├── .opencode/                    # solo adapter opencode
│   ├── agents/*.md               # 7 agentes con permisos por rol
│   └── commands/*.md             # /next, /spec, /approve, /status
├── harness/
│   ├── bin/harness.py            # máquina de estados
│   ├── process/*.md              # workflow, spec, trazabilidad, TDD, Gherkin, mutación, checkpoints
│   ├── roles/*.md                # los seis roles
│   ├── schemas/feature_list.schema.json
│   ├── templates/                # specs, features, informes
│   ├── profiles/python-unittest/ # perfil vendorizado
│   ├── adapters/<id>/            # adapter vendorizado
│   ├── VERSION
│   └── GENERATED.md
├── docs/                         # architecture, conventions, verification
├── specs/<name>/                 # requirements.md, design.md, tasks.md
├── features/<name>.feature       # contrato aprobado
├── progress/                     # current.md, history.md, informes humanos
├── .harness/
│   ├── approvals/<name>.json     # puerta humana + hash
│   └── reports/                  # judge_<name>.json, mutation_<name>.json
├── src/
├── tests/
└── tools/mutate.py
```

## El pipeline

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

La trazabilidad obligatoria es `acceptance → R<n> → @sN → test`. El detalle
está en `harness/process/workflow.md` y `harness/process/traceability.md`.

## La máquina de estados

```bash
python3 harness/bin/harness.py status [--json]
python3 harness/bin/harness.py next [--json]
python3 harness/bin/harness.py set <id> <status> [--force]
python3 harness/bin/harness.py approve <id> [--by NAME]
python3 harness/bin/harness.py block <id> "razón"
python3 harness/bin/harness.py note "texto"
python3 harness/bin/harness.py validate [--verify]
```

`set done` no es una declaración de intenciones: exige, en disco,

1. `specs/<name>/{requirements,design,tasks}.md` con `R<n>`.
2. `features/<name>.feature` con escenarios `@sN`.
3. Aprobación válida (hash del `.feature` al día).
4. Ninguna task `[ ]` en `tasks.md`.
5. `.harness/reports/judge_<name>.json` con `"verdict": "APPROVED"`.
6. `.harness/reports/mutation_<name>.json` con `"verdict": "PASS"` y
   `score >= mutation.threshold`.
7. `commands.verify` en verde.

Si falta cualquiera, la transición falla y explica qué falta. `--force` solo
existe para una emergencia documentada.

## La puerta humana

La aprobación es **conversación + marcador verificable**:

1. El humano lee `features/<name>.feature`.
2. Si aprueba: `harness.py approve <id>`.
3. El comando guarda el SHA-256 normalizado del `.feature` en
   `.harness/approvals/<name>.json` y mueve la feature a `in_progress`.
4. Si el `.feature` cambia después, el hash caduca y `validate` falla hasta
   que se vuelva a aprobar.

La normalización ignora CRLF y espacios finales: un cambio de formato no
invalida la aprobación; un cambio real de escenario sí.

## Adapter OpenCode

El adapter `opencode` genera `.opencode/agents/*.md` y `.opencode/commands/*.md`
y fusiona `opencode.jsonc`. Los detalles están en
`harness/adapters/opencode/README.md` y la demo en
`harness/adapters/opencode/DEMO.md`.

| Comando | Agente | Para qué |
|---|---|---|
| `/next` | `craftsman_lead` | Fase actual y acción exacta; se detiene en la puerta humana. |
| `/spec <id>` | `spec_partner` | Conversación EARS + `specs/<name>/`. |
| `/approve <id>` | `gatekeeper` | Registra la aprobación del `.feature` y arranca `in_progress`. |
| `/status` | `craftsman_lead` | Estado y `validate`, sin escribir nada. |

`craftsman_lead`, `spec_partner` y `gatekeeper` son agentes **primarios**;
el resto son subagentes. El lead no puede editar código ni lanzar la spec o
la aprobación como subagentes: son actos humanos en la sesión actual.

Los denies globales (`edit *`, `shell *`, `subagent *`) también afectan a
los agentes built-in de OpenCode. Es intencional: el arnés no quiere que un
agente built-in esquive la puerta. Ajusta `opencode.jsonc` si necesitas
otra cosa.

Si `opencode.jsonc` ya existía, `bootstrap.py render` conserva tus claves y
añade las reglas globales que falten sin duplicarlas. Los comentarios
propios no sobreviven a la normalización.

## Perfil `python-unittest`

- Python 3.9+, `unittest`, sin dependencias externas.
- Tests en `tests/test_*.py`; código en `src/`.
- `./init.sh` valida estado, ejecuta tests y comprueba el contrato del stack.
- Mutador propio en `tools/mutate.py`; umbral 100 % por defecto.
- Checkpoints de perfil P1–P4 en
  `harness/profiles/python-unittest/checkpoints.md`.

Cambiar el umbral o el alcance de mutación es editar
`harness.config.json`:

```json
"mutation": { "threshold": 90, "scope": "touched_files" }
```

## Contrato del stack

Todo stack declara cinco verbos en `harness.config.json`:

| Verbo | Qué demuestra | Quién lo ejecuta | `python-unittest` |
|---|---|---|---|
| `check` | entorno y contrato listos | agente / CI | `./init.sh` |
| `build` | el código compila | humano / CI | `python3 -m compileall -q src` |
| `test` | la suite pasa | agente / CI | `python3 -m unittest discover -s tests -v` |
| `mutation` | los tests muerden | agente / CI | `python3 tools/mutate.py {file}` |
| `clean` | se borra lo generado | humano / CI | `find . -name __pycache__ -type d -prune -exec rm -rf {} +` |

`agent_forbidden` declara los verbos que ningún agente puede ejecutar:
en `python-unittest` son `build` y `clean`. `stack_check.py` valida que
esos verbos existan y tengan comando; los selftests del adapter comprueban
que no aparezcan en su allowlist. `clean` es destructivo, así que se queda
fuera de las sesiones de agente por diseño.

`harness/bin/stack_check.py` los valida: existen, son **una sola orden**
(sin `|`, `;`, `&&` ni redirecciones — la allowlist del agente son cadenas
literales y un comando compuesto se deniega entero) y la prosa de `docs/`
los cita tal cual. Los placeholders `{file}` y `<archivo>` no cuentan como
operadores. `./init.sh` lo ejecuta como sección 6: un doc vacío o un
comando inventado ponen el entorno en rojo. `verify` se conserva como alias
de `./init.sh`.

## Añadir un perfil

1. Crea `profiles/<id>/profile.json` con `paths`, los cinco verbos
   (`check`, `build`, `test`, `mutation`, `clean`), `mutation`,
   `documents`, `scaffold` y `gitignore`.
2. Añade `init.sh`, `tools/` (mutador o wrapper), `docs/` y
   `checkpoints.md`.
3. Ejecuta `bootstrap.py init --profile <id>` y comprueba que el proyecto
   generado pasa `./init.sh` y `harness.py validate`.

El core no cambia: si un perfil necesita tocar `process/` o `roles/`, la
abstracción está mal y hay que corregirla.

## Añadir un adapter

1. Crea `adapters/<id>/` con un `adapter.json` que declare qué carpetas se
   renderizan (`{"source": "agents", "target": ".opencode/agents"}`), qué
   fragmento de configuración se fusiona y sus valores `{{...}}`.
2. Añade los archivos de agentes, comandos y el `README.md` con las
   capacidades declaradas (subagentes, permisos por rol, hooks).
3. Ejecuta `bootstrap.py init --adapter <id>` y valida que los roles siguen
   apuntando a `harness/process/` y a `harness.py`.

El adapter **no cambia el método**: solo lo expone. Los archivos generados
llevan la marca `Generated by harness-kit`; `render` los reemplaza y borra
los obsoletos, pero respeta los que no llevan marca.

## Actualizar un proyecto

```bash
python3 bootstrap.py render --target ../mi-proyecto
```

Reemplaza `harness/`, `init.sh`, `tools/`, `.opencode/` y fusiona
`opencode.jsonc`. Conserva `harness.config.json`, `AGENTS.md`,
`project-spec.md`, `feature_list.json`, `specs/`, `features/`,
`progress/`, `docs/`, `src/` y `tests/`.

Para cambiar de adapter, edita `"adapter"` en `harness.config.json` y
ejecuta `render`: se retiran los archivos generados del adapter anterior y
se crean los del nuevo.

## Selftests del kit

```bash
python3 -m unittest discover -s harness-kit/selftest -v
```

61 tests cubren:

- Transiciones válidas e inválidas, `--force`, `blocked_reason`.
- Aprobación por hash, normalización de formato, invalidación al editar.
- `set done` sin judge, sin mutación, con score bajo, con tasks abiertas y
  con `verify` roto.
- `validate` (duplicados, dos `in_progress`, aprobaciones caducadas).
- Scaffold completo, `./init.sh` verde, `status`, `next`, `check`, `render`
  idempotente y preservación de artefactos del proyecto.
- Adapter OpenCode: layout, modos, permisos por rol, comandos, denies
  globales, merge de `opencode.jsonc`, limpieza de generados obsoletos y
  cambio a `generic`.

## Decisiones de diseño

- **Plantilla copiable, sin paquete instalable.** El kit es la fuente; el
  destino recibe una copia vendorizada en `harness/`.
- **Estado centralizado.** Los subagentes no editan `feature_list.json`;
  usan `harness.py`. Esto elimina carreras y hace las puertas auditables.
- **Informes machine-readable separados de los humanos.** `.harness/reports/`
  decide; `progress/*.md` explica.
- **Una sola fuente del proceso.** `harness/process/workflow.md`; `AGENTS.md`
  y los roles son punteros, no duplicados.
- **Roles finos, artefactos en disco.** El subagente devuelve una línea; el
  lead lee el disco. Anti-teléfono-descompuesto.
- **Renderizar archivos concretos, no llenar prompts de placeholders.** El
  bootstrap sustituye solo nombre de proyecto, perfil, adapter y versión.

## Limitaciones conocidas

- **Python es runtime del arnés**, no del proyecto. Un repo Go/Node necesita
  Python 3.9+ para `harness.py` y el mutador del perfil. Es una dependencia
  del kit, documentada a propósito.
- **Los permisos del adapter OpenCode no son un sandbox.** El allowlist de
  shell es cooperativo y depende del escáner de OpenCode; sirve para agentes
  que siguen el pipeline, no para un agente adversarial.
- **`opencode.jsonc` se normaliza al renderizar.** Las claves del humano se
  conservan, los comentarios no. Al cambiar a `generic` el archivo se queda;
  bórralo a mano si no lo usas.
- **El umbral de mutación es configurable**, pero el mutador de Python muta
  archivos completos. `scope: touched_files` se implementa en F3/F4 con el
  wrapper del perfil.
- **Los docs del proyecto nacen con `TODO`.** `init.sh` avisa; el humano
  debe completarlos antes de que el judge los use como estándar.
- **Claude Code** conserva sus `.claude/agents` actuales como referencia
  hasta F5.
