---
description: Registra la aprobación humana del .feature (puerta)
agent: gatekeeper
subagent: false
---

Actúa como `gatekeeper`.

Feature solicitada: $ARGUMENTS

Trata esta invocación como la **aprobación explícita** del humano, pero
solo si:

1. la feature existe y está en `spec_ready` (o ya en `in_progress` para
   refrescar la aprobación);
2. `features/<name>.feature` existe y tiene escenarios `@sN`.

Muestra un resumen breve del contrato (título y escenarios) y ejecuta:

```bash
python3 harness/bin/harness.py approve <id>
```

Si el comando falla, muestra el error completo y no intentes arreglarlo.
Si no hay id en `$ARGUMENTS`, busca la feature en `spec_ready`; si hay más
de una o ninguna, pide el id al humano en lugar de adivinar.
