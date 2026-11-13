# Spec — conversación, EARS y los tres archivos

> La spec no se transcribe: se **debate**. El valor del `spec_partner` está
> en las preguntas incómodas, no en rellenar una plantilla.

## De la conversación al contrato

Para cada feature, el humano y el `spec_partner` cierran estas decisiones:

1. **Propósito y alcance.** Qué queda dentro y qué queda fuera.
2. **Contrato observable.** CLI, HTTP, librería, UI o datos. Qué se puede
   medir: stdout/stderr/exit code, status/body, valor de retorno, evento.
3. **Casos límite.** Lista vacía, id inexistente, entrada inválida, archivo
   corrupto, concurrencia, límites numéricos.
4. **Errores.** Qué excepción, qué código, qué mensaje, qué no se escribe.
5. **Alternativas descartadas.** Qué diseño se consideró y por qué no.
6. **Dependencias.** Si hace falta una dependencia externa, se debate antes
   de aceptarla.

La conversación termina cuando cada criterio de `acceptance` de
`feature_list.json` se puede expresar como un requisito EARS y observarse en
un escenario.

## Estructura

```
project-spec.md                     # decisiones globales del proyecto
specs/<name>/
├── requirements.md                 # QUÉ, en EARS, R1..Rn
├── design.md                       # CÓMO, archivos y decisiones técnicas
└── tasks.md                        # PASOS, T1..Tn con checkbox
```

`<name>` coincide con el campo `name` de `feature_list.json`.

## EARS estricto

Cada requisito tiene **un solo `DEBE`** y un ID estable `R<n>`.

| Tipo | Plantilla |
|---|---|
| Ubicuo | `El sistema DEBE <acción>.` |
| Evento | `CUANDO <disparador>, el sistema DEBE <acción>.` |
| Estado | `MIENTRAS <estado>, el sistema DEBE <acción>.` |
| Opcional | `DONDE <feature opcional>, el sistema DEBE <acción>.` |
| No deseado | `SI <evento no deseado> ENTONCES el sistema DEBE <acción>.` |

Reglas:

- Un requisito = una obligación verificable.
- Nada de "rápido", "amigable" o "razonable" sin una medida.
- Los IDs no se renumeran: si un requisito desaparece, se marca obsoleto.
- Todo `acceptance` original queda cubierto por al menos un `R<n>`.
- Todo `R<n>` aparece en `design.md` y en `tasks.md`.

## `design.md`

Debe contener, como mínimo:

- Archivos y módulos a tocar.
- Firmas o interfaces nuevas.
- Errores y excepciones.
- Una **alternativa descartada** con su justificación.
- Impacto en el contrato observable.

No es código; es la decisión antes del código.

## `tasks.md`

Pasos discretos, en orden, cada uno con checkbox y los `R<n>` que cubre:

```markdown
- [ ] T1 — Crear la interfaz pública (R1, R2)
- [ ] T2 — Implementar el camino feliz (R1)
- [ ] T3 — Implementar el error (R2)
- [ ] T4 — Añadir tests de regresión (R1, R2)
```

El `tdd_craftsman` marca `[x]` al terminar cada task. `set done` falla si
queda alguna `[ ]` sin justificación documentada.

## La puerta

La aprobación humana es sobre el **contrato ejecutable** `.feature`, no
sobre la prosa de la spec. La spec es el material de trabajo; el `.feature`
es lo que se firma. Ver `workflow.md` y `traceability.md`.
