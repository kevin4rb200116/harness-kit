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

No escribas archivos hasta que el humano haya decidido lo que falta. Cuando
la arquitectura esté cerrada, escribe solo `docs/architecture.md`, verifica
que no queda ningún `TODO` y pide al humano que vuelva al `craftsman_lead`
y ejecute `/next`.
