# Workflow — el pipeline SDD del arnés

> Esta es la **única fuente de verdad del proceso**. Los roles, adapters y
> documentos del proyecto apuntan aquí; no repiten el pipeline.

El arnés fusiona cuatro ideas que se refuerzan entre sí:

- **EARS** dice *qué* debe ser verdad (requisitos verificables).
- **Gherkin** dice *cómo se observa* esa verdad (contrato ejecutable).
- **TDD** dice *cómo se construye* (un test a la vez).
- **Mutación** dice *si los tests muerden* (no basta con verde).

## Estados y fases

```
pending
  │  spec            spec_partner escribe project-spec.md +
  │                  specs/<name>/{requirements,design,tasks}.md
  ▼
spec_ready  ◄── set <id> spec_ready
  │  gherkin         gherkin_author destila requirements.md en .feature
  │  approval        el humano aprueba el .feature
  ▼
in_progress ◄── approve <id>  (registra hash + aprobación)
  │  tdd             tdd_craftsman ejecuta tasks.md con Rojo → Verde → Refactor
  │  judge           judge verifica acceptance → R<n> → @sN → test
  │  mutation        mutation_tester comprueba que los tests muerden
  ▼
done        ◄── set <id> done
```

Cualquier estado puede pasar a `blocked` con una razón. `blocked → pending`
se permite para reanudar. El resto de transiciones exige `--force` y debe
quedar justificado en `progress/current.md`.

## Una sola feature a la vez

- Como máximo **una** feature en `in_progress`.
- Se trabaja la feature no cerrada de **menor `id`**.
- El estado vive en `feature_list.json` y solo lo modifica `harness.py`.

## Artefactos por feature

| Artefacto | Ruta | Quién lo escribe |
|---|---|---|
| Spec global | `project-spec.md` | `spec_partner` |
| Requirements | `specs/<name>/requirements.md` | `spec_partner` |
| Design | `specs/<name>/design.md` | `spec_partner` |
| Tasks | `specs/<name>/tasks.md` | `spec_partner` |
| Contrato | `features/<name>.feature` | `gherkin_author` |
| Aprobación | `.harness/approvals/<name>.json` | `harness.py approve` |
| Informe TDD | `progress/tdd_<name>.md` | `tdd_craftsman` |
| Veredicto | `.harness/reports/judge_<name>.json` | `judge` |
| Mutación | `.harness/reports/mutation_<name>.json` | `mutation_tester` |
| Informes humanos | `progress/{judge,mutation}_<name>.md` | `judge`, `mutation_tester` |

Los informes machine-readable de `.harness/reports/` son los que verifican
las puertas. Los `.md` de `progress/` son para el humano: explican el
razonamiento, no sustituyen al JSON.

## La puerta humana

La aprobación del contrato es **conversación + marcador en disco**:

1. El `gherkin_author` termina `features/<name>.feature`.
2. El lead pide al humano que lea los escenarios y apruebe o pida cambios.
3. Si aprueba: `python3 harness/bin/harness.py approve <id>`.
4. El comando guarda el SHA-256 normalizado del `.feature` en
   `.harness/approvals/<name>.json` y mueve la feature a `in_progress`.

Si el `.feature` cambia después, el hash deja de coincidir, la aprobación
caduca y `validate` (y por tanto `init.sh`) falla hasta que el humano vuelva
a aprobar. Un cambio de formato (LF/CRLF, espacios finales) no invalida la
aprobación.

## La máquina de estados

```bash
python3 harness/bin/harness.py status           # tabla de estado
python3 harness/bin/harness.py next             # fase siguiente + pistas
python3 harness/bin/harness.py set <id> <st>    # transición validada
python3 harness/bin/harness.py approve <id>     # puerta humana
python3 harness/bin/harness.py block <id> "…"   # bloqueo con razón
python3 harness/bin/harness.py note "…"         # bitácora de sesión
python3 harness/bin/harness.py validate         # coherencia global
```

`set done` exige, en este orden:

1. Los tres archivos de `specs/<name>/` y al menos un `R<n>`.
2. `features/<name>.feature` con escenarios `@sN`.
3. Aprobación válida (hash al día).
4. Ninguna task `[ ]` en `tasks.md`.
5. `.harness/reports/judge_<name>.json` con `"verdict": "APPROVED"`.
6. `.harness/reports/mutation_<name>.json` con `"verdict": "PASS"` y
   `score >= mutation.threshold`.
7. `commands.verify` en verde (por defecto `./init.sh`).

## Reglas duras

- No hay código de producción sin un test rojo que lo pida.
- No hay implementación sin `.feature` aprobado.
- No hay cierre sin judge aprobado y mutación por encima del umbral.
- Los subagentes no editan `feature_list.json`: usan `harness.py`.
- Los roles no editan artefactos de otro rol (ver permisos del adapter).
- Una sola feature a la vez; un solo contrato aprobado a la vez.

## Cierre de sesión

1. `./init.sh` verde.
2. `harness.py validate` verde.
3. Si la feature terminó: `harness.py set <id> done`.
4. Mueve el resumen de `progress/current.md` al final de
   `progress/history.md` y deja `current.md` con la plantilla.
5. No dejes archivos temporales, `print()` de debug ni TODOs sin contexto.
