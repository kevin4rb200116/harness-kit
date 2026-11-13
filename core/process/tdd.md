# TDD estricto — la disciplina del `tdd_craftsman`

> Un test a la vez. Nunca toda la batería por delante. El alcance no se
> infla porque cada línea de producción tiene un test rojo que la pidió.

## Las Tres Leyes

1. **No escribes código de producción** salvo para hacer pasar un test que
   está fallando.
2. **No escribes más de un test del necesario para fallar** — y que no
   compile o no importe cuenta como fallar.
3. **No escribes más código de producción del necesario** para pasar el
   único test que falla.

## El ciclo

```
   ┌──────────────────────────────────────────────┐
   │                                                │
   ▼                                                │
 ROJO            VERDE                 REFACTOR      │
 escribe UN  →   mínimo código    →    limpia con   ─┘
 test que        para pasar            la barra
 falla           ese test              verde
```

- **Rojo:** el test falla por la razón correcta, no por un error de sintaxis
  del propio test.
- **Verde:** la implementación más pequeña que pasa. Si sorprende, es que
  hay una suposición escondida.
- **Refactor:** nombres, duplicación, funciones cortas, sin cambiar
  comportamiento. La barra sigue verde.

## Cómo se recorre el `.feature`

Cada escenario `@sN` genera uno o más ciclos. El orden recomendado:

1. Camino feliz primero.
2. Casos límite y errores después.
3. Un test por comportamiento observable, con asserts fuertes.

El `tdd_craftsman` anota el ciclo en `progress/tdd_<name>.md`, no en el
código. La evidencia es el historial de tests, no una promesa.

## Lo que no es TDD

- Escribir todos los tests y luego toda la implementación.
- Añadir producción "por si acaso" o "para que quede bonito".
- Refactorizar con la barra roja.
- Testear detalles internos en vez del contrato observable.
- Cambiar el `.feature` aprobado para que encaje con el código.

## Cierre

Al terminar la feature:

- Todas las tasks de `tasks.md` están `[x]`.
- El mapa `R<n> → @sN → test` está en `progress/tdd_<name>.md`.
- `commands.test` y `commands.verify` están en verde.
- No hay tests comentados, `skip` sin razón ni `print()` de debug.
