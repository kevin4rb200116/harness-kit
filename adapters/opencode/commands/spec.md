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
colisiones con decisiones previas. No escribas archivos hasta que el
humano haya respondido a lo que falta.

Cuando la conversación esté cerrada, escribe `requirements.md`,
`design.md` y `tasks.md` en `specs/<name>/`, revisa la trazabilidad
`acceptance → R<n>` y resume en 5 líneas. Al final, pide al humano que
vuelva al `craftsman_lead` y ejecute `/next` para marcar `spec_ready`.
