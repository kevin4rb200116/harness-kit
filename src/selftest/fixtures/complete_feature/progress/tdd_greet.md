# TDD — greet

Ciclos Rojo-Verde-Refactor documentados por el fixture.

## Trazabilidad

| Requirement | Escenario | Test |
|-------------|-----------|------|
| R1          | @s1       | `tests/test_greet.py::TestGreet.test_greet_with_name` |
| R2          | @s2       | `tests/test_greet.py::TestGreet.test_greet_with_empty_name` |

## Tasks

- [x] T1 — `greet(name)` devuelve el saludo con nombre.
- [x] T2 — `greet("")` devuelve el saludo por defecto.
