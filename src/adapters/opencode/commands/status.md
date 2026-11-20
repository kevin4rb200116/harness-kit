---
description: Muestra el estado del arnés y valida la coherencia en disco
agent: craftsman_lead
subagent: false
---

Actúa como `craftsman_lead`.

1. Ejecuta `python3 harness/bin/harness.py status`.
2. Ejecuta `python3 harness/bin/harness.py validate`.
3. Lee `progress/current.md`.

Resume en una tabla:

| Feature | Estado | Fase siguiente | Bloqueo |
|---|---|---|---|

Después lista, si existen, las incoherencias que haya reportado
`validate` y la acción exacta para corregirlas. No cambies el estado ni
edites artefactos: este comando es de solo lectura.
