# Prueba de mutación — validar que los tests muerden

> Una suite verde dice "el código no explota con estas entradas". **No** dice
> "los tests fallarían si el código estuviera mal".

## El problema

La prueba de mutación introduce un defecto pequeño (un *mutante*) y observa
la suite:

- Si **algún test falla** → el mutante está **muerto** (killed). Bien.
- Si **todos los tests pasan** → el mutante **sobrevive** (survived). Hay un
  agujero: falta un assert o un caso.

**Puntuación** = `killed / total`. Cuanto más alta, más muerden los tests.

## Contrato del comando de mutación

El rol `mutation_tester` no sabe de lenguajes. Ejecuta
`commands.mutation` del `harness.config.json` y parsea esta salida estándar:

```json
{
  "verdict": "PASS",
  "score": 100,
  "threshold": 100,
  "killed": 12,
  "total": 12,
  "survived": []
}
```

- `score` es un porcentaje (0–100).
- `threshold` viene de `mutation.threshold` en la configuración.
- `survived` lista los mutantes que sobrevivieron, con archivo y línea.
- Si el mutador no está disponible, el veredicto es `FAIL` y la feature no
  se puede cerrar. Un perfil puede declarar `mutation.required: false` solo
  con justificación explícita en `design.md`.

Cada perfil envuelve su herramienta (`mutmut`, Stryker, `go-mutesting`,
`cargo-mutants`, o un script propio) y normaliza la salida. El contrato es
el mismo en todos los lenguajes.

## Alcance

- `mutation.scope = "touched_files"`: mutar solo los archivos que toca la
  feature, identificados en `progress/tdd_<name>.md`. Es el valor por
  defecto del kit.
- `mutation.scope = "all"`: mutar todo el código fuente. Más lento y, en
  proyectos grandes, poco práctico.
- El mutador **no debe mutar tests, strings ni comentarios**. Mutar la
  suite mide la suite contra sí misma, no la producción: ensucia el score y
  provoca reparaciones inútiles. La herramienta rechaza rutas bajo
  `tests/`, `test_*.py` y `conftest.py`.

## Umbral

- El umbral vive en `harness.config.json`, no en el rol.
- Un perfil didáctico puede exigir 100 %. Un proyecto real suele usar
  80–90 % o "solo líneas cambiadas".
- `set done` compara `score` con `threshold`. Un `PASS` por debajo del
  umbral no cierra la feature.

## Reglas

- Restaurar siempre el código original **y su mtime**, incluso ante
  interrupción. Un mtime nuevo simula una ronda TDD y caduca el veredicto
  del judge.
- Descartar mutantes que no compilan: no inflan la puntuación.
- Reportar los supervivientes con archivo y línea.
- No mutar tests: el score se calcula solo sobre producción.
- El `mutation_tester` reescribe su JSON y su `.md` en cada ronda, aunque
  el veredicto no cambie.
- No mutar código que la feature no toca si `scope = "touched_files"`.
- Si un superviviente está fuera de alcance, se documenta en
  `progress/mutation_<name>.md`; no se ignora en silencio.
