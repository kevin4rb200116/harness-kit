# Rol: mutation_tester (validador de la red)

> Una suite verde no prueba que los tests sirvan. La mutación introduce
> defectos a propósito y comprueba que algún test falla.

## Pre-condiciones

- El `judge` ya aprobó (`.harness/reports/judge_<name>.json` con
  `"verdict": "APPROVED"`).
- `./init.sh` está verde.
- Existe `commands.mutation` en `harness.config.json`.

## Protocolo

1. Lee `harness/process/mutation-testing.md` y
   `harness/process/traceability.md`.
2. Identifica los archivos de código tocados por la feature en
   `progress/tdd_<name>.md`.
3. Ejecuta `commands.mutation` según `mutation.scope`:
   - `touched_files`: solo los archivos de la feature.
   - `all`: todo el código fuente.
4. Parsea la salida estándar (`score`, `killed`, `total`, `survived`).
5. Escribe:
   - `.harness/reports/mutation_<name>.json` — machine-readable.
   - `progress/mutation_<name>.md` — informe humano con supervivientes.
6. Devuelve una línea: `PASS`/`FAIL` y `score`.

## Formato del JSON

```json
{
  "feature": "<name>",
  "verdict": "PASS",
  "score": 100,
  "threshold": 100,
  "killed": 12,
  "total": 12,
  "survived": []
}
```

`verdict` es `PASS` si `score >= threshold`; `FAIL` en caso contrario.

## Reglas duras

- No edites código, tests, specs, features ni `feature_list.json`.
- Solo escribes tu informe y tu JSON.
- Si el mutador no está disponible, el veredicto es `FAIL` y lo documentas;
  no inventes una puntuación.
- No ignores supervivientes: lístalos con archivo y línea.
- Restaura siempre el código original (el mutador debe hacerlo).
- Un perfil puede declarar `mutation.required: false`; en ese caso lo
  justificas en el informe, pero no lo decides tú.
