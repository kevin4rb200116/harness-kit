Feature: <propósito en una frase>
  Como <rol> quiero <capacidad> para <beneficio>.

  Trazabilidad:
  | Requirement | Escenario |
  |-------------|-----------|
  | R1          | @s1       |
  | R2          | @s2       |

  @s1
  Scenario: <comportamiento observable>
    Given <estado de partida>
    When <acción concreta>
    Then <resultado medible>

  @s2
  Scenario: <caso límite o error>
    Given <estado de partida>
    When <acción concreta>
    Then <resultado medible>
