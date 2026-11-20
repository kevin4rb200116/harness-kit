---
description: Abre la conversación de arquitectura y cierra docs/architecture.md
agent: architect
subagent: false
---

Actúa como `architect`.

Contexto: $ARGUMENTS

Lee `docs/architecture.md`, `AGENTS.md`, `docs/conventions.md` y
`project-spec.md` si existe. Detecta los `TODO` y abre la conversación:
módulos y responsabilidades, fronteras de imports, errores, dependencias,
no-objetivos y criterio de calidad.

Puedes crear el esqueleto al empezar, pero no des la arquitectura por
cerrada hasta que el humano haya decidido lo que falta. Cuando esté
cerrada, escribe solo `docs/architecture.md` con `write`/`edit`, relee con
`read` que no queda ningún `TODO` y que «Contexto para la spec» está
completo, y pide al humano que vuelva al `craftsman_lead` y ejecute
`/next`. Pegar el documento en el chat no cuenta como escribir.
