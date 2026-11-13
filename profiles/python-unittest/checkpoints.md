# Checkpoints de perfil — python-unittest

> Se suman a los checkpoints genéricos `C1–C8` de
> `harness/process/checkpoints.md`. El judge los referencia como `P<n>`.

## P1 — Arquitectura

- [ ] `src/` solo contiene los módulos previstos en `docs/architecture.md`.
- [ ] Las fronteras entre capas se respetan (imports permitidos).
- [ ] No hay lógica de negocio en la capa de UI ni persistencia en el modelo.

## P2 — Convenciones

- [ ] Nombres según `docs/conventions.md`.
- [ ] Líneas <= 100 caracteres.
- [ ] Imports ordenados y sin comodines.
- [ ] f-strings para interpolación.
- [ ] Anotaciones de tipo en funciones públicas.

## P3 — Dependencias

- [ ] No se añaden dependencias externas sin decisión en `design.md`.
- [ ] `requirements.txt` (si existe) está justificado.
- [ ] El código nuevo usa solo stdlib salvo excepción aprobada.

## P4 — Higiene de tests

- [ ] Un archivo `tests/test_<modulo>.py` por módulo tocado.
- [ ] Asserts específicos, no `assertTrue` genéricos.
- [ ] Sin `skip`, tests comentados ni `print()` de debug.
- [ ] Sin archivos temporales fuera de `tempfile`.
- [ ] Los tests se pueden ejecutar en cualquier orden.
