# Arquitectura — qué significa "hacer un buen trabajo" (Python)

> Este documento define el estándar de calidad del proyecto. El judge evalúa
> contra este archivo. Si no está aquí, no es un requisito.

## Principios

1. **Capas claras.** TODO: enumera los módulos de `src/` y qué responsabilidad
   tiene cada uno. No introduzcas capas nuevas sin una decisión documentada
   en `project-spec.md`.
2. **Sin dependencias externas por defecto.** Solo stdlib. Si una feature
   necesita una dependencia, se debate antes y se documenta en `design.md`.
3. **Errores explícitos.** Las funciones que pueden fallar lanzan
   excepciones nombradas; no devuelven `None` para señalar error.
4. **Inmutabilidad por defecto.** Los modelos de dominio son inmutables
   (`@dataclass(frozen=True)`) salvo razón documentada.
5. **Funciones pequeñas.** Una función hace una cosa y se puede leer de
   arriba abajo.

## Fronteras

TODO: qué puede importar cada módulo. Por ejemplo, la UI no importa detalles
de persistencia.

## Lo que no se permite

- Dependencias externas sin justificación.
- `print()` para depurar en código de producción.
- Estado global mutable.
- Excepciones genéricas sin mensaje.
- Tests que dependen del orden de ejecución.
