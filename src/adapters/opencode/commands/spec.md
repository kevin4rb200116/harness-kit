---
description: Abre la conversación de spec EARS para una feature
agent: spec_partner
subagent: false
---

Actúa como `spec_partner`.

Contexto: $ARGUMENTS

Si el contexto identifica una feature, trabaja esa. Si no, lee
`feature_list.json` y toma la feature `pending` de menor `id`.

Abre la conversación de spec: pregunta por alcance, contrato de salida,
casos límite, errores, alternativas descartadas, dependencias y posibles
colisiones con decisiones previas. No des los archivos por cerrados hasta
que el humano haya respondido a lo que falta.

## Escritura

- Al empezar, crea con `write` `project-spec.md` y los tres
  `specs/<name>/*.md` desde la plantilla, con sus `TODO:` visibles. No
  esperes al final: un corte de sesión debe dejar un parcial, no cero.
- Cada decisión cerrada se escribe en el acto.
- Al cerrar, escribe la tabla `A<n> → R<n>` en `requirements.md` y
  comprueba que cada `R<n>` aparece en `design.md` y `tasks.md`.
- Antes de responder, `read` los cuatro archivos y confirma que no queda
  `TODO:` y que están todos los `R<n>`/`T<n>`.
- El entregable son los archivos, no el texto de tu respuesta. Si no hubo
  `write`/`edit`, no has cerrado la spec; no pidas `/next`.

Cuando la conversación esté cerrada, escribe `project-spec.md` (sin ningún
`TODO:`) y `requirements.md`, `design.md` y `tasks.md` en
`specs/<name>/`, revisa la cobertura `A<n> → R<n>` y resume en 5 líneas.
Termina con `escrito: <archivos>` y `leído: <archivos>`. Al final, pide al
humano que vuelva al `craftsman_lead` y ejecute `/next` para marcar
`spec_ready`.

`project-spec.md` es tu artefacto: si queda un `TODO:`, `next` vuelve a
`spec` y `set spec_ready` falla. No lo dejes para la arquitectura ni para
el lead.
