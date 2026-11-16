# Workflow — el pipeline SDD del arnés

> Esta es la **única fuente de verdad del proceso**. Los roles, adapters y
> documentos del proyecto apuntan aquí; no repiten el pipeline.

El arnés fusiona cuatro ideas que se refuerzan entre sí:

- **EARS** dice *qué* debe ser verdad (requisitos verificables).
- **Gherkin** dice *cómo se observa* esa verdad (contrato ejecutable).
- **TDD** dice *cómo se construye* (un test a la vez).
- **Mutación** dice *si los tests muerden* (no basta con verde).

## Estados y fases

```
pending
  │  architecture    architect cierra docs/architecture.md (solo la primera vez)
  │  spec            spec_partner escribe project-spec.md +
  │                  specs/<name>/{requirements,design,tasks}.md
  ▼
spec_ready  ◄── set <id> spec_ready
  │  gherkin         gherkin_author destila requirements.md en .feature
  │  approval        el humano aprueba el .feature
  ▼
in_progress ◄── approve <id>  (registra hash + aprobación)
  │  tdd             tdd_craftsman ejecuta tasks.md con Rojo → Verde → Refactor
  │                  y escribe progress/tdd_<name>.md
  │  judge           judge verifica acceptance → R<n> → @sN → test
  │  mutation        mutation_tester comprueba que los tests muerden
  │  repair          si judge rechaza o mutación no llega al umbral,
  │                  tdd_craftsman repara y reescribe el informe TDD
  ▼
done        ◄── set <id> done
```

Cualquier estado puede pasar a `blocked` con una razón. `blocked → pending`
se permite para reanudar. El resto de transiciones exige `--force` y debe
quedar justificado en `progress/current.md`.

### Paradas y transiciones

| Parada (humano) | Acción humana | Transición (agente) |
|---|---|---|
| Arquitectura | `/architecture` | `architect` escribe `docs/architecture.md` |
| Spec | `/spec <id>` | `spec_partner` escribe `project-spec.md` y `specs/<name>/` |
| Contrato | `/approve <id>` | `gherkin_author` escribió el `.feature`; `gatekeeper` registra el hash |
| Trabajo | `/next` | `tdd_craftsman` → `judge` → `mutation_tester`; `repair` interno |
| Cierre | `/next` | `set done`; siguiente feature o `all_done` |
| Bloqueo | resolver y `/next` | el lead reanuda |

`mark_spec_ready`, `start`, `gherkin`, `tdd`, `judge`, `mutation` y `repair`
son transiciones internas: el lead las recorre sin pedir intervención. Las
paradas son las puertas humanas.

## Una sola feature a la vez

- Como máximo **una** feature en `in_progress`.
- Se trabaja la feature no cerrada de **menor `id`**.
- El estado vive en `feature_list.json` y solo lo modifica `harness.py`.

## Artefactos por feature

| Artefacto | Ruta | Quién lo escribe |
|---|---|---|
| Arquitectura | `docs/architecture.md` | `architect` |
| Spec global | `project-spec.md` | `spec_partner` |
| Requirements | `specs/<name>/requirements.md` | `spec_partner` |
| Design | `specs/<name>/design.md` | `spec_partner` |
| Tasks | `specs/<name>/tasks.md` | `spec_partner` |
| Contrato | `features/<name>.feature` | `gherkin_author` |
| Aprobación | `.harness/approvals/<name>.json` | `harness.py approve` |
| Informe TDD | `progress/tdd_<name>.md` | `tdd_craftsman` |
| Veredicto | `.harness/reports/judge_<name>.json` | `judge` |
| Mutación | `.harness/reports/mutation_<name>.json` | `mutation_tester` |
| Informes humanos | `progress/{judge,mutation}_<name>.md` | `judge`, `mutation_tester` |

Los informes machine-readable de `.harness/reports/` son los que verifican
las puertas. Los `.md` de `progress/` son para el humano: explican el
razonamiento, no sustituyen al JSON.

## La puerta de arquitectura

Antes de la primera feature, `docs/architecture.md` debe estar cerrado:

1. `next` devuelve `architecture` si el documento falta o conserva un
   `TODO`.
2. El lead se detiene y pide al humano que ejecute `/architecture`.
3. El `architect` conversa las decisiones (módulos, fronteras, errores,
   dependencias, no-objetivos) y escribe **solo** ese documento.
4. Cuando no quedan `TODO`, `next` deja de devolver `architecture` y el
   pipeline sigue con la spec.

La puerta solo aplica a features `pending`: una feature ya aprobada o en
curso no se bloquea retroactivamente.

## La puerta de la spec global

`project-spec.md` se cierra en la fase `spec`, no en la arquitectura:

1. Si falta o conserva un `TODO:`, `next` devuelve `spec` para una feature
   `pending` con `sdd: true`.
2. `set spec_ready` e `in_progress` fallan mientras queden `TODO:`.
3. `validate` avisa si una feature ya iniciada arrastra una spec global
   pendiente (proyectos heredados).

El `architect` no escribe `project-spec.md`; solo el `spec_partner` lo
cierra, junto con `specs/<name>/`.

## La puerta humana

La aprobación del contrato es **conversación + marcador en disco**:

1. El `gherkin_author` termina `features/<name>.feature`.
2. El lead pide al humano que lea los escenarios y apruebe o pida cambios.
3. Si aprueba: `python3 harness/bin/harness.py approve <id>`.
4. El comando guarda el SHA-256 normalizado del `.feature` en
   `.harness/approvals/<name>.json` y mueve la feature a `in_progress`.

Si el `.feature` cambia después, el hash deja de coincidir, la aprobación
caduca y `validate` (y por tanto `init.sh`) falla hasta que el humano vuelva
a aprobar. Un cambio de formato (LF/CRLF, espacios finales) no invalida la
aprobación.

## El informe TDD y el bucle de reparación

`progress/tdd_<name>.md` es el handoff del `tdd_craftsman` al `judge`.
`next` no devuelve `judge` si el informe falta o no contiene el mapa
`R<n> → @sN → test`; devuelve `tdd` con el hueco concreto.

Cuando el `judge` rechaza o la mutación queda por debajo del umbral:

1. `next` devuelve `repair` y muestra el motivo vigente (rechazo o
   supervivientes).
2. El lead relanza `tdd_craftsman` con ese motivo; no lanza `judge` ni
   `mutation_tester` todavía.
3. El TDD corrige tests/código y **reescribe** `progress/tdd_<name>.md`.
4. Al ser la ronda más reciente que el veredicto, `next` vuelve a `judge`;
   tras aprobar, vuelve a `mutation`.

La ronda se mide por lo más reciente entre el informe TDD, `src/` y
`tests/`: cualquier cambio de código o de test caduca el veredicto, aunque
el artesano olvide reescribir el informe. Los `__pycache__` no cuentan. No
se baja el umbral ni se edita el mutador para salir del bucle.

Cada veredicto vale para **una ronda**. `next` compara el mtime del JSON
con la ronda TDD: si el TDD cambió algo después, el veredicto caduca y
`next` vuelve a pedir `judge` o `mutation`. Por eso ambos roles reescriben
su JSON y su `.md` en cada ronda, aunque el veredicto no cambie.

El `judge` no lee el informe de mutación: son puertas independientes. Un
rechazo por score bajo duplica la mutación y gasta una reparación extra.

La mutación cubre **solo código de producción** (`src/`). Mutar `tests/` no
demuestra nada y ensucia el score: el mutador rechaza esas rutas y conserva
el mtime original al restaurar, para no caducar el veredicto del judge.

Tope: **3 rondas de reparación**. Si la cuarta vuelve a fallar, el lead
bloquea la feature (`harness.py block <id> "reparación sin converger"`) y
reporta los motivos; no se gira en bucle.

## La máquina de estados

```bash
python3 harness/bin/harness.py status           # tabla de estado
python3 harness/bin/harness.py next             # fase siguiente + pistas
python3 harness/bin/harness.py set <id> <st>    # transición validada
python3 harness/bin/harness.py approve <id>     # puerta humana
python3 harness/bin/harness.py block <id> "…"   # bloqueo con razón
python3 harness/bin/harness.py note "…"         # bitácora de sesión
python3 harness/bin/harness.py validate         # coherencia global
```

`set done` exige, en este orden:

1. Los tres archivos de `specs/<name>/` y al menos un `R<n>`.
2. `features/<name>.feature` con escenarios `@sN`.
3. Aprobación válida (hash al día).
4. Ninguna task `[ ]` en `tasks.md`.
5. `progress/tdd_<name>.md` con el mapa `R<n> → @sN → test`.
6. `.harness/reports/judge_<name>.json` con `"verdict": "APPROVED"`.
7. `.harness/reports/mutation_<name>.json` con `"verdict": "PASS"` y
   `score >= mutation.threshold`.
8. `commands.verify` en verde (por defecto `./init.sh`).

## Reglas duras

- No hay código de producción sin un test rojo que lo pida.
- No hay implementación sin `.feature` aprobado.
- No hay primera feature sin `docs/architecture.md` cerrado (sin `TODO`).
- No hay cierre sin judge aprobado y mutación por encima del umbral.
- Los subagentes no editan `feature_list.json`: usan `harness.py`.
- Los roles no editan artefactos de otro rol (ver permisos del adapter).
- Una sola feature a la vez; un solo contrato aprobado a la vez.

## Cierre de sesión

1. `./init.sh` verde.
2. `harness.py validate` verde; atiende los `[WARN]` (por ejemplo,
   `progress/current.md` sin la feature activa).
3. Si la feature terminó: `harness.py set <id> done`.
4. Deja `current.md` con la plantilla. Añade el resumen de cierre a
   `progress/history.md` con `harness.py note --history "<resumen>"`:
   el historial es append-only y no se reescribe.
5. No dejes archivos temporales, `print()` de debug ni TODOs sin contexto.
