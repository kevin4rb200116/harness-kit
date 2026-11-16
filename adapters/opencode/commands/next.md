---
description: Avanza la fase del pipeline; reporta la acción y la ejecuta, salvo en puertas humanas
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

**Después de responder, ejecuta la acción de la fase en el mismo turno.**
No te limites a describirla: `next` avanza el pipeline. **Reportar no es
avanzar.**

- `mark_spec_ready` / `start` / `done`: ejecuta el `harness.py set`
  correspondiente.
- `gherkin` / `tdd` / `judge` / `mutation`: lanza el subagente indicado y
  espera su línea de resumen. En `tdd`, exige `progress/tdd_<name>.md` con
  el mapa `R<n> → @sN → test`; sin él, `next` no pasa a `judge`.
- `repair`: relanza `tdd_craftsman` con los motivos del informe fallido
  (`judge` rechazó o mutación por debajo del umbral). No relances judge ni
  mutación antes de que el TDD repare y reescriba su informe.
- `spec`: **PARA**. Pide al humano que ejecute `/spec`.
- `architecture`: **PARA**. Pide al humano que ejecute `/architecture`.
- `approval`: **PARA**. Pide al humano que lea el `.feature` y ejecute
  `/approve <id>`.
- `blocked`: explica la razón y pide al humano cómo desbloquear.
- `all_done`: informa y no ejecutes nada.

En `in_progress`, recorre la cadena completa en este turno: `tdd` → `judge`
→ `mutation`; si aparece `repair`, relanza TDD y vuelve a juzgar y mutar.
Para en `done` o `blocked`. Tope de 3 reparaciones; a la cuarta, ejecuta
`python3 harness/bin/harness.py block <id> "reparación sin converger"` y
reporta los motivos.

Al lanzar un subagente, el brief incluye: `Actúa como <rol>. Lee AGENTS.md
y harness/roles/<rol>.md`, la feature, los artefactos exactos, la línea de
resumen y, si es `repair`, la ruta del informe fallido y sus motivos.
