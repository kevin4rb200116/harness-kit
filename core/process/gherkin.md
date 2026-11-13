# Gherkin — el contrato ejecutable

> Los `.feature` son lo que el humano aprueba en la puerta y el mapa que el
> `tdd_craftsman` recorre. Un escenario = uno o más ciclos
> Rojo-Verde-Refactor.

Los archivos viven en `features/<name>.feature`, donde `<name>` coincide con
el campo `name` de `feature_list.json`.

## Estructura

```gherkin
Feature: <propósito en una frase>
  Como <rol> quiero <capacidad> para <beneficio>.   # contexto opcional

  Trazabilidad:
  | Requirement | Escenario |
  |-------------|-----------|
  | R1          | @s1       |
  | R2          | @s2       |

  @s1
  Scenario: <comportamiento observable>
    Given <estado de partida>
    When <acción concreta del usuario>
    Then <resultado medible>
    And <otro resultado medible>

  @s2
  Scenario: <caso límite o error>
    Given ...
    When ...
    Then ...
```

## Reglas duras

- **Un `Scenario` por comportamiento observable**, incluidos los caminos de
  error. Si `requirements.md` menciona un caso límite, tiene su escenario.
- **Tags estables `@s1`, `@s2`, …** Son el identificador que usan el judge,
  el tdd_craftsman y la mutación. No se renumeran.
- **Cada `Then` es medible**: un valor exacto, un código de salida, un
  status HTTP, una excepción concreta, una línea de log. Nada de "funciona
  correctamente".
- **Sin detalles de implementación**: no se nombran funciones privadas,
  clases internas ni rutas de módulos. Se describe el contrato.
- **Sin pasos ambiguos**: "dado un almacén con 3 notas" es válido; "dado un
  estado válido" no.
- **La tabla de trazabilidad es obligatoria** y cubre todos los `R<n>` de
  `requirements.md`.

## Del `.feature` al test

Cada `@sN` debe poder mapearse a al menos un test concreto del proyecto.
El `tdd_craftsman` escribe ese mapa en `progress/tdd_<name>.md`; el judge lo
verifica. Ver `traceability.md`.

## La puerta

El humano aprueba el `.feature`, no la prosa. Cuando el archivo está listo:

1. El lead lo muestra y pide aprobación explícita.
2. Si hay cambios, se edita el `.feature` y se vuelve a pedir aprobación.
3. Si se aprueba, se registra con `harness.py approve <id>`.

Cualquier edición posterior invalida el hash y obliga a re-aprobar.
