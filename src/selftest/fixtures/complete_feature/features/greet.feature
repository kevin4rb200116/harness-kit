Feature: Saludo
  Como usuario quiero una función greet para saludar por nombre.

  Trazabilidad:
  | Requirement | Escenario |
  |-------------|-----------|
  | R1          | @s1       |
  | R2          | @s2       |

  @s1
  Scenario: Saluda a un nombre
    Given el nombre "Ada"
    When llamo a greet con ese nombre
    Then el resultado es exactamente "Hello, Ada!"

  @s2
  Scenario: Saluda a un nombre vacío
    Given el nombre ""
    When llamo a greet con ese nombre
    Then el resultado es exactamente "Hello, !"
