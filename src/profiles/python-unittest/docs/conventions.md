# Convenciones de código — Python

> Homogeneidad extrema. La IA predice mejor cuando el repositorio se parece
> a sí mismo en todas partes.

## Estilo

- **Versión:** Python 3.9+ (`list[str]` permitido).
- **Formato:** PEP 8. Líneas de máximo 100 caracteres.
- **Imports:** stdlib primero, luego locales. Una línea por módulo.
- **Strings:** comillas dobles `"..."`. Comillas simples solo para escapar
  comillas dobles dentro.
- **Interpolación:** f-strings. Nada de `.format()` ni `%`.
- **Tipos:** anotaciones en funciones públicas y en los límites de módulo.

## Nombres

| Tipo | Convención | Ejemplo |
|---|---|---|
| Módulos | `snake_case` | `notes.py` |
| Clases | `PascalCase` | `Note` |
| Funciones / variables | `snake_case` | `load_notes` |
| Constantes | `UPPER_SNAKE` | `DEFAULT_PATH` |
| Privadas | prefijo `_` | `_atomic_write` |

## Estructura de archivo

1. Docstring del módulo.
2. `from __future__ import annotations` si se usan tipos modernos.
3. Imports stdlib.
4. Imports locales.
5. Constantes.
6. Funciones/clases públicas.
7. Helpers privados.

## Errores

- Excepciones propias que hereden de `Exception` (o de una base del dominio).
- Mensajes en el idioma del proyecto, con el dato que falló.
- No silenciar excepciones con `pass`.

## Tests

- `unittest`, un archivo `tests/test_<modulo>.py` por módulo.
- Un test por comportamiento observable; nombre `test_<que>_<condicion>`.
- Asserts específicos (`assertEqual`, `assertRaises`), no `assertTrue`.
- Sin dependencias de red ni de estado global entre tests.
