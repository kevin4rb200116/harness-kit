# Adapter: generic

Este adapter no genera archivos específicos de ningún harness. Sirve para
cualquier herramienta que sepa leer un `AGENTS.md` y ejecutar comandos:
Codex, Cursor en modo reglas, un chat con acceso a shell, o incluso un
humano.

## Cómo se usa

1. El proyecto generado ya tiene `AGENTS.md` en la raíz y los ocho roles en
   `harness/roles/`.
2. Copia el rol que toque en el system prompt o en la ventana de contexto.
3. Ejecuta el pipeline **secuencialmente en una sola sesión**: no hay
   subagentes nativos, así que el mismo agente cambia de rol cuando el
   `harness.py next` lo indica.
4. Las puertas no dependen del rol: `harness.py` las valida en disco.

## Capacidades declaradas

| Capacidad | Valor |
|---|---|
| Subagentes nativos | no |
| Edición restringida por rol | no (solo disciplina + `harness.py`) |
| Comandos | sí, vía shell |
| Puerta humana en disco | sí |
| Informes machine-readable | sí |

## Regla de oro

Aunque no haya subagentes, **no mezcles roles en un mismo turno**. Un turno
= un rol. El estado en disco (`feature_list.json`, aprobaciones, informes)
es lo que impide que el agente se salte una puerta.
