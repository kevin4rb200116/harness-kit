# Requirements — <name>

> Feature `<name>` de `feature_list.json`. Cada requirement está en EARS
> estricto, tiene un ID estable y es verificable por al menos un escenario
> `@sN` y un test concreto.

## Cobertura de acceptance

> `A<n>` es el criterio n de `acceptance` en `feature_list.json`, en orden.
> Cada fila debe apuntar al menos a un `R<n>`. `harness.py` no deja avanzar
> si falta un `A<n>` o si un `R<n>` no aparece en `design.md` y `tasks.md`.

| Acceptance | Requisitos |
|---|---|
| A1 | R1 |

## R1
CUANDO <disparador>, el sistema DEBE <acción verificable>.

## R2
El sistema DEBE <acción ubicua verificable>.

## R3
SI <evento no deseado> ENTONCES el sistema DEBE <acción verificable>.
