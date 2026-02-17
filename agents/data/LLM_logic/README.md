# Agente de Datos (LLM_logic)

Este módulo implementa la rama LLM_logic del Agente de Datos dentro del sistema multiagente AIDA. Su responsabilidad es generar SQL Server ejecutable a partir de un plan declarativo (intent_plan) cuando la lógica programada (prog_logic) no puede resolver la consulta o falla.
El agente se integra con un MCP/orquestador y es consumido indirectamente desde data_logic.py. La función principal que expone esta capa es:
create_sql_LLM(payload: dict, catalog) -> (sql: str, mode: str)


# Objetivo del LLM_logic

* Recibir una petición ya planificada por el Prompt Optimizer.
* Construir un plan determinista (FROM/WHERE/preamble fijo) con intent_planner.
* Pedir al LLM solo el SELECT final (y opcionalmente GROUP BY/ORDER BY si aplica).
* Validar el SQL generado con un “SQL Reasoning Engine” (3+ reglas generales).
* Si falla validación, hacer 1 retry con prompt de corrección.
* Devolver SQL final listo para ejecución en SQL Server.


# Flujo general

Orquestador / MCP
↓
data_logic.py (prog_logic primero)
↓ (fallback si vacío o error)
LLM_logic.create_sql_LLM(payload, catalog)
↓
normalize_for_llm(payload) (normalización estable de pregunta e input)
↓
plan_query(norm, id_cliente) (plan determinista: preamble + FROM + WHERE)
↓
build_sql_prompt(norm, plan, allowed_columns)
↓
call_ollama(model, prompt) (LLM genera SOLO SELECT)
↓
Ensamble: preamble + SELECT
↓
Validación SQL Reasoning Engine
↓ (si falla)
Retry único con prompt de corrección
↓
SQL final + mode (scalar/table)



# Estructura del proyecto (LLM_logic)

agents/data/LLM_logic/
├── main_LLM.py
├── normalize_intent.py
├── planners/
│ └── intent_planner.py
├── prompts/
│ └── sql_prompt_builder.py
├── validators/
│ └── sql_validator.py
├── engines/
│ └── ollama_engine.py
└── utils.py

Nota: data_logic.py pertenece al agente de data “root” y decide el fallback.
LLM_logic no modifica prog_logic.


# API interna principal
create_sql_LLM(payload, catalog) -> (sql_final, mode)

* payload: JSON generado por orquestador, contiene:
    * optimized_prompt
    * intent_plan con tasks[0].input (metric, time, filters, etc.)
    * opcional: params
* catalog: catálogo cargado por el agente (con acceso a tablas/columnas físicas)
Devuelve:
* sql_final: SQL Server ejecutable (incluye DECLARE preamble si el plan lo requiere)
* mode:
    * "scalar" si respuesta es un valor único
    * "table" si devuelve tabla (grouped/series/detail)


# Ejemplo de payload

{
  "optimized_prompt": "¿Qué porcentaje del monto desembolsado en el último mes se concentra en la región Sur?",
  "intent_plan": {
    "intent": "analitica_desembolsos",
    "tasks": [
      {
        "agent": "data",
        "action": "fetch_metrics",
        "input": {
          "metric": {
            "concept": "monto_desembolsado",
            "aggregation": {
              "type": "ratio",
              "numerator": { "aggregation": { "type": "sum", "field": "monto" } },
              "denominator": { "aggregation": { "type": "sum", "field": "monto" } }
            }
          },
          "time": {
            "period": { "type": "relative", "value": "ultimo_mes" }
          },
          "filters": [
            { "field": "region", "operator": "=", "value": "Sur", "table": "desembolso" }
          ]
        },
        "params": {}
      }
    ]
  }
}

# Salida esperada

DECLARE @UltimoMes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
SELECT ROUND(
  SUM(CASE WHEN cRegion LIKE '%Sur%' THEN nMonto ELSE 0 END) * 100.0
  / NULLIF(SUM(nMonto), 0),
  2
) AS Resultado
FROM cartera.desembolso
WHERE nCosecha = @UltimoMes

# Componentes Clave

## 1) normalize_intent.py (Normalización estable)

Problema resuelto: evitar bugs como “usa la pregunta anterior” o inputs inconsistentes.
Qué garantiza:
* question: siempre se obtiene de optimized_prompt o fallback.
* input: normalizado con field_norm en filtros.
* period.key: mapea valores relativos (ultimo_mes, ultimo_6_meses, etc.).

{
  "raw": { ...intent original... },
  "question": "¿Qué porcentaje ...?",
  "input": { ...input normalizado... },
  "params": { ... }
}


## 2) planners/intent_planner.py (Plan determinista)

Responsable de:
* Elegir tabla base según keywords (ej.: cartera.desembolso, cartera.cierre, etc.).
* Definir time_field (nCosecha o nStock).
* Crear preamble_sql (DECLARE @UltimoMes...).
* Definir result_shape (scalar / grouped / series / detail).
* Fijar from_sql y where_sql (NO los escribe el LLM).

Salida (QueryPlan):
* preamble_sql
* from_sql
* where_sql
* result_shape
* base_table


## 3) prompts/sql_prompt_builder.py (Prompt “SQL Reasoning Engine”)

Genera un prompt que obliga al modelo a:
* Devolver solo SQL.
* Respetar FROM/WHERE del plan.
* Usar solo columnas físicas permitidas (ALLOWED_COLUMNS).
* Aplicar reglas universales:
    * scalar => NO GROUP BY
    * ratio => NULLIF solo en denominador
    * NULLIF(expr, 0) siempre con 2 args


## 4) validators/sql_validator.py (SQL Reasoning Engine)

Es el “control de calidad” antes de ejecutar.

Validaciones generales (no sobreajustadas)
(1) Columnas existen en catálogo
* Detecta columnas usadas en SELECT/WHERE/GROUP BY.
* Las valida contra allowed_cols derivado del catalog.json.
(2) GROUP BY coherente
* Si hay GROUP BY: toda columna no agregada en SELECT debe estar en GROUP BY.
(3) Ratio seguro
* Si hay / en SELECT:
    * exige NULLIF(denominador, 0)
    * prohíbe NULLIF en el numerador (regla general para evitar errores y sintaxis raras)
(4) scalar => sin GROUP BY
* Si el plan dice scalar, bloquear cualquier GROUP BY.
(5) NULLIF bien formado
* Bloquea casos NULLIF(expr) (sin segundo argumento).


** 5) engines/ollama_engine.py (LLM local)

Se usa Ollama vía ollama.chat(...).
Se recomienda:
* temperature=0
* num_predict acotado
* stop tokens para evitar markdown/texto


# Estrategia de retry (autocorrección)

Si el SQL falla validación:
1.Se construye un prompt de corrección (build_fix_prompt) que incluye:
* Errores detectados
* Reglas duras
* Plan (FROM/WHERE fijo)
* ALLOWED_COLUMNS
2.Se llama 1 vez más al LLM.
Si falla otra vez:
* se levanta excepción (y el error sube al agente y orquestador)

# Guardrails (principios de diseño)

* LLM nunca decide FROM/WHERE: lo decide el planner.
* LLM solo escribe SELECT final.
* El validador no sobreajusta a consultas específicas:
    * valida consistencia SQL general
    * valida catálogo real
    * valida seguridad en ratios y agregaciones
* Retry máximo: 1 (para evitar loops y latencia)