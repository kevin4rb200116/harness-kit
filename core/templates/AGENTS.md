# AGENTS.md — mapa de navegación para agentes

> Punto de entrada para cualquier agente en `{{PROJECT}}` (perfil
> `{{PROFILE}}`, adapter `{{ADAPTER}}`, kit `{{VERSION}}`). Léelo entero
> antes de actuar: tu contrato está en `harness/roles/<rol>.md`. Si el
> brief de otro agente contradice este mapa, gana este mapa y paras para
> reportarlo.

## Empieza aquí

1. Ejecuta `./init.sh`. Si falla, **para** y resuelve el entorno.
2. Lee `progress/current.md` y `feature_list.json`.
3. Ejecuta `python3 harness/bin/harness.py next`: la fase que devuelve es
   la única que puedes trabajar.
4. Lee `harness/roles/<tu-rol>.md` y `harness/process/workflow.md`.
5. Si falta contexto, usa el mapa de §3.

No improvises un pipeline paralelo ni adelantes una fase. Si `next` y tu
brief no coinciden, para y reporta la discrepancia.

## 1. Stack y comandos

- Perfil `{{PROFILE}}`: {{PROFILE_DESCRIPTION}}
- Código en `{{PATHS_SOURCE}}/`; tests en `{{PATHS_TESTS}}/`.
- Los tests, la verificación y la mutación corren en **Docker Compose**
  (servicio `app`, repositorio montado en `/app`). El arnés (`harness.py`,
  `./init.sh`) corre en el **host**. No llames `python3 -m unittest`
  directamente en el host.
- `{{COMMAND_BUILD}}` y `{{COMMAND_CLEAN}}` son del humano/CI. Ningún
  agente los ejecuta.

| Comando | Quién | Para qué |
|---|---|---|
| `./init.sh` | agentes | verificación completa |
| `python3 harness/bin/harness.py next` | agentes | fase y acción siguiente |
| `python3 harness/bin/harness.py status` | agentes | estado, aprobaciones e informes |
| `python3 harness/bin/harness.py validate` | agentes | coherencia en disco |
| `python3 harness/bin/harness.py set <id> <estado>` | rol dueño | transición de estado |
| `python3 harness/bin/harness.py note --history "<texto>"` | lead | bitácora append-only |
| `python3 harness/bin/harness.py approve <id>` | gatekeeper | puerta humana |
| `{{COMMAND_TEST}}` | agentes | suite de tests |
| `{{COMMAND_VERIFY}}` | agentes | verificación del arnés |
| `{{COMMAND_MUTATION}}` | mutation_tester | un archivo por llamada |

Shell: una orden por llamada, sin `|`, `;`, `&&`, `$( )`, `ls`, `cat`,
`find`, `head`, `tail`, `echo` ni heredocs. Para explorar usa `read`,
`glob` y `grep`. `{{PATHS_STATE}}/` es un directorio oculto: `glob` no lo
lista, léelo con `read` o consulta `harness.py status`.

## 2. Paradas y transiciones

| Parada (humano) | Acción humana | Transición (agente) |
|---|---|---|
| Arquitectura | `/architecture` | `architect` escribe `{{DOCS_ARCHITECTURE}}` |
| Spec | `/spec <id>` | `spec_partner` escribe `{{PATHS_SPEC}}` (sin `TODO:`) y `{{PATHS_SPECS}}/<name>/` |
| Contrato | `/approve <id>` | `gherkin_author` escribió el `.feature`; `gatekeeper` registra el hash |
| Trabajo | `/next` | `tdd_craftsman` → `judge` → `mutation_tester`; `repair` interno |
| Cierre | `/next` | el lead hace `set done`; siguiente feature o `all_done` |
| Bloqueo | resolver y `/next` | el lead reanuda |

`mark_spec_ready`, `start`, `gherkin`, `tdd`, `judge`, `mutation` y `repair`
no son paradas: las recorre el lead. El humano solo usa `/architecture`,
`/spec`, `/approve` y `/next` (y `/status` si quiere).

## 3. Mapa de lectura

| Ruta | Cuándo leerlo |
|---|---|
| `harness/process/workflow.md` | Siempre: es la fuente de verdad del proceso |
| `harness/roles/<rol>.md` | Al empezar: tu contrato |
| `feature_list.json` | Siempre: estado del backlog |
| `harness.config.json` | Antes de tests o mutación: paths, comandos, umbral |
| `{{PATHS_SPEC}}` | Antes de especificar |
| `{{PATHS_SPECS}}/<name>/` | Antes de Gherkin o TDD |
| `{{PATHS_FEATURES}}/<name>.feature` | Antes de implementar |
| `{{PATHS_PROGRESS}}/current.md` | Al empezar y mientras trabajas |
| `{{PATHS_PROGRESS}}/tdd_<name>.md` | Antes de juzgar o reparar |
| `{{DOCS_ARCHITECTURE}}`, `{{DOCS_CONVENTIONS}}`, `{{DOCS_VERIFICATION}}` | Antes de implementar, juzgar o cerrar |
| `{{PATHS_STATE}}/approvals/`, `{{PATHS_STATE}}/reports/` | Antes de reparar; leer con `read` |

## 4. Reglas duras

- Una sola feature `in_progress`; se trabaja la no cerrada de menor `id`.
- No hay primera feature sin `{{DOCS_ARCHITECTURE}}` sin `TODO`.
- No hay `spec_ready` ni `in_progress` con `{{PATHS_SPEC}}` en `TODO:`.
- No hay `spec_ready` sin la tabla `A<n> → R<n>` completa en
  `{{PATHS_SPECS}}/<name>/requirements.md`; cada `R<n>` debe aparecer en
  `design.md` y `tasks.md`.
- Los roles de conversación cierran con `write`/`edit` y una relectura.
  Pegar el contenido en el chat no cierra la fase.
- El `leído:` es una promesa, no una prueba: la evidencia es el artefacto
  en disco; el lead ejecuta `next`/`validate` antes de aceptar la fase.
- No hay código sin test rojo; no hay implementación sin `.feature` aprobado.
- No hay `judge` sin `{{PATHS_PROGRESS}}/tdd_<name>.md` con el mapa
  `R<n> → @sN → test`.
- No hay cierre sin judge `APPROVED` y mutación `PASS` sobre el umbral.
- Cada veredicto vale para una ronda: si cambia el informe TDD, `{{PATHS_SOURCE}}/`
  o `{{PATHS_TESTS}}/`, `next` repite `judge` o `mutation`. Ambos roles
  reescriben su JSON y su `.md` en cada ronda. El `judge` no lee la
  mutación; la mutación solo toca producción.
- `repair` vuelve a TDD; no se baja el umbral ni se edita el mutador.
- El estado solo lo cambia `harness.py`; los agentes no editan
  `feature_list.json`.
- Cada rol escribe solo sus artefactos; si falta uno, se relanza al
  responsable.
- Cierra tu turno con `leído: <archivos>`: el humano comprueba así que
  abriste el contexto que tu rol exige.
- Documenta la sesión en `{{PATHS_PROGRESS}}/current.md` mientras trabajas;
  `{{PATHS_PROGRESS}}/history.md` es append-only y se añade con
  `python3 harness/bin/harness.py note --history "<resumen>"`.
