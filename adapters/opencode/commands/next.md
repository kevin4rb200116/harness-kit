---
description: Muestra la fase siguiente del pipeline y qué hacer
agent: craftsman_lead
subagent: false
---

Actúa como `craftsman_lead`.

1. Si aún no lo has hecho en esta sesión, ejecuta `./init.sh`.
2. Ejecuta `python3 harness/bin/harness.py next --json`.
3. Lee `progress/current.md` y, si hace falta contexto, el `.feature` o la
   spec de la feature activa.

Responde con:

- feature activa (id y nombre) y estado;
- fase devuelta por `next`;
- la acción concreta siguiente, citando el comando o el subagente exacto.

Si la fase es `approval`, **detente** y pide al humano que lea el
`.feature` y ejecute `/approve <id>`. No avances por tu cuenta.
