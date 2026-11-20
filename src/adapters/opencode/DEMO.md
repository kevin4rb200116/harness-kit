# DEMO — un feature completo con OpenCode

Esta demo recorre el pipeline entero con el perfil `python-unittest`. Sirve
para verificar que el adapter no solo genera archivos: las puertas reales
son las de `harness.py`.

## 0. Crear el proyecto

Desde la raíz del repo del kit:

```bash
python3 src/bootstrap.py init \
  --target ../demo-opencode \
  --profile python-unittest \
  --adapter opencode \
  --project demo-opencode

cd ../demo-opencode
./init.sh
```

Deberías ver `.opencode/agents/`, `.opencode/commands/` y `opencode.jsonc`.

## 1. Arquitectura (`/architecture`)

Antes de la primera feature, el proyecto necesita su estándar de calidad.
`docs/architecture.md` llega con `TODO`; el primer `/next` se detiene en la
fase `architecture`:

```text
/architecture
```

`architect` conversa contigo los módulos, las fronteras de imports, la
estrategia de errores, las dependencias y los no-objetivos. Al terminar
escribe solo `docs/architecture.md` sin `TODO`.

Vuelve al lead:

```text
/next
```

Ahora la fase es `spec` (o `mark_spec_ready` si aún no hay features) y el
pipeline sigue.

## 2. Declarar la feature (humano)

El estado solo lo escribe `harness.py`, pero **añadir** features es una
decisión humana. Edita `feature_list.json`:

```json
{
  "id": 1,
  "name": "greet",
  "title": "Saludo configurable",
  "status": "pending",
  "sdd": true,
  "acceptance": [
    "greet(name) devuelve un saludo con el nombre",
    "un nombre vacío produce un error explícito"
  ]
}
```

Abre OpenCode en `demo-opencode`. El agente por defecto es
`craftsman_lead`.

## 3. Spec (`/spec`)

```text
/spec 1
```

`spec_partner` abre la conversación: pregunta por el contrato exacto, el
caso de nombre vacío, la alternativa descartada y cómo se verifica sin leer
el código. Al terminar escribe:

```text
project-spec.md
specs/greet/requirements.md   # R1, R2
specs/greet/design.md
specs/greet/tasks.md          # T1, T2 con [ ]
```

Vuelve al lead:

```text
/next
```

El lead ejecuta `set 1 spec_ready` y lanza `gherkin_author`.

## 4. Contrato (`/next`)

`gherkin_author` escribe `features/greet.feature` con `@s1`, `@s2` y la
tabla `R1 → @s1`, `R2 → @s2`. El lead devuelve una línea y **se detiene**.

Lee el `.feature`. Si quieres cambios, pídeselos al lead: volverá a lanzar
`gherkin_author`. Si te vale:

```text
/approve 1
```

`gatekeeper` muestra el resumen, ejecuta `approve 1` y deja:

```text
.harness/approvals/greet.json   # sha256 + escenarios
```

La feature pasa a `in_progress`.

## 5. Trabajo (`/next`): TDD → judge → mutación

Un solo `/next` recorre toda la cadena; el lead no te pide que avances fase
a fase. Primero lanza `tdd_craftsman`. El artesano, un test a la vez:

1. escribe un test rojo para `@s1`;
2. implementa lo mínimo en `src/`;
3. refactoriza;
4. marca `[x] T1`;
5. repite con `@s2`.

Deja `progress/tdd_greet.md` con el mapa `R<n> → @sN → test` y ejecuta
test + verify. Sin ese informe, `next` no pasa a `judge`: el lead relanza
al artesano en vez de escribirlo él.

## 6. Judge y mutación (dentro del mismo `/next`)

Cuando el TDD termina, el lead sigue con `judge` y `mutation_tester` sin
devolverte el control. `judge` revisa trazabilidad, tasks, disciplina TDD y
calidad, ejecuta `./init.sh` y escribe:

```text
progress/judge_greet.md
.harness/reports/judge_greet.json     {"verdict": "APPROVED", ...}
```

`mutation_tester` ejecuta `tools/mutate.py`, mata mutantes y escribe:

```text
progress/mutation_greet.md
.harness/reports/mutation_greet.json {"verdict": "PASS", "score": 100, ...}
```

Si `judge` rechaza o la mutación queda por debajo del umbral, `/next`
devuelve `repair` con el motivo. El lead relanza `tdd_craftsman`; el
artesano añade el test que falta y reescribe `progress/tdd_greet.md`.
Después se repiten `judge` y mutación. No se baja el umbral. Tope: 3 rondas;
a la cuarta, el lead bloquea la feature con el motivo.

## 7. Cierre

```text
/next
```

El lead ejecuta `set 1 done`. La puerta comprueba en disco: specs, feature,
aprobación vigente, tasks `[x]`, judge `APPROVED`, mutación `PASS` sobre el
umbral y `verify` verde. Si algo falta, el comando falla y te dice qué.

```text
/status
```

Debe mostrar `greet  done` y `validate` en verde.

## Qué mirar si algo se rompe

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `approve` falla por hash | el `.feature` cambió tras aprobar | vuelve a leerlo y `/approve <id>` |
| `set done` falla por judge | falta o está `REJECTED` | relanza `judge` y corrige el rechazo |
| `set done` falla por mutación | supervivientes o score bajo | añade tests que maten los mutantes |
| el lead no puede lanzar un subagente | no está en su allowlist | usa `/next` y deja que el pipeline decida |
| `opencode.jsonc` pisado | `render` normaliza el archivo | conserva tus claves; los comentarios se pierden |
