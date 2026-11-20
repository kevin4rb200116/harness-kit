# Trazabilidad — acceptance → R&lt;n&gt; → @sN → test

> Sin trazabilidad, una suite verde solo demuestra que el código no explota.
> La cadena completa demuestra que se construyó lo que se pidió y que se
> puede observar.

## La cadena

```
acceptance A<n> (feature_list.json)
   │  cada criterio se convierte en…
   ▼
R<n> (specs/<name>/requirements.md)
   │  cada requisito se observa en…
   ▼
@sN (features/<name>.feature)
   │  cada escenario tiene al menos…
   ▼
test (tests del proyecto)
```

## Quién verifica cada eslabón

| Eslabón | Quién | Cómo |
|---|---|---|
| `A<n> → R<n>` | `spec_partner` | Tabla de cobertura en `requirements.md` |
| `R<n> → design/tasks` | `spec_partner` | Cada `R<n>` citado en ambos archivos |
| `R<n> → @sN` | `gherkin_author` | Tabla de trazabilidad en el `.feature` |
| `@sN → test` | `tdd_craftsman` | Mapa en `progress/tdd_<name>.md` |
| Cadena completa | `judge` | Revisa los tres mapas y ejecuta la suite |
| Los tests muerden | `mutation_tester` | Mutación sobre el código de la feature |

## Formato del mapa

En `specs/<name>/requirements.md`:

```markdown
| Acceptance | Requisitos |
|---|---|
| A1 | R1 |
| A2 | R2, R3 |
```

`A<n>` es el criterio n de `acceptance` en `feature_list.json`, en orden.

En `features/<name>.feature`:

```gherkin
Feature: <propósito>

  Trazabilidad:
  | Requirement | Escenario |
  |-------------|-----------|
  | R1          | @s1       |
  | R2          | @s2       |
```

En `progress/tdd_<name>.md`:

```markdown
| Requirement | Escenario | Test |
|-------------|-----------|------|
| R1          | @s1       | `<ruta-del-test>::<nombre-del-test>` |
| R2          | @s2       | `<ruta-del-test>::<nombre-del-test>` |

## Tasks

- [x] T1 — ...
- [x] T2 — ...
```

`harness.py next` no pasa a `spec_ready` si falta la cobertura `A<n> → R<n>`
o si un `R<n>` no aparece en `design.md`/`tasks.md`. Tampoco pasa a `judge`
si el informe TDD falta o no contiene al menos un `R<n>`, un `@sN` y una
referencia a un test.

## Reglas

- Todo `A<n>` de `feature_list.json` aparece en la tabla de cobertura y
  apunta al menos a un `R<n>`. `harness.py` falla si falta.
- Todo `R<n>` aparece en `design.md` y `tasks.md`; un requisito huérfano de
  diseño o de tarea no pasa la puerta de `spec_ready`.
- Un `R<n>` puede cubrirse con varios `@sN`; un `@sN` puede verificar varios
  `R<n>`. Lo que no se permite es un requisito o un escenario huérfano.
- Un `@sN` sin test es un escenario decorativo: el judge rechaza.
- Un test que no se puede mapear a ningún `@sN` es alcance no pedido: el
  judge lo señala y, si no está justificado, rechaza.
- Las tasks de `tasks.md` citan sus `R<n>` para que no haya trabajo huérfano.
- El judge produce el mapa completo en `progress/judge_<name>.md`; el JSON
  `.harness/reports/judge_<name>.json` solo lleva el veredicto y el mapa
  machine-readable.
