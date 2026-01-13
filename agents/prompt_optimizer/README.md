# Prompt Optimizer Module

Este módulo implementa el Prompt Optimizer del sistema AIDA multimodal on-premise.

## Alcance (importante)

El Prompt Optimizer:

- **NO ejecuta tareas**
- **NO consulta bases de datos**
- **NO responde directamente al usuario**
- **NO decide el flujo de ejecución** (eso es del orquestador)

Su objetivo es **planificar**: transformar la petición del usuario en un **plan declarativo** (JSON) con:

- `intent` (intención detectada)
- `tasks` (tareas a ejecutar por agentes)

El orquestador (LangGraph) consume este plan y ejecuta herramientas vía MCP.

## API pública

Función pública estable:

- `process_request(payload: dict) -> dict`

Debe devolver **solo JSON**.

## Artefactos (contrato)

En `agents/prompt_optimizer/artifacts/` se incluye un ejemplo de salida (`prompt_optimizer_schema.json`) y el prompt del planner (`planner_system_prompt.txt`) para alinear el contrato con el equipo sin necesidad de leer el código.

## Acciones (contrato actual)

El Prompt Optimizer devuelve planes con `agent` y `action` separados (action = verbo, sin prefijo).
El orquestador/MCP construye el `tool_name` como `<agent>.<action>` (ej.: `data.fetch_metrics`).

Acciones acordadas:

- data: `fetch_metrics`
- nlp: `summarize`, `answer`, `ask_clarification`
- image: `extract_text`

## Estructura del output (extendida, compatible con mínima)

Extendida:

- `optimized_prompt`
- `intent_plan.intent`
- `intent_plan.tasks`
- `status`
- `errors`

### Compatibilidad con contrato mínimo

Aunque el módulo devuelve un formato extendido (con `optimized_prompt`, `status`, `errors`), se mantiene compatibilidad con el contrato mínimo porque:

- `intent_plan.intent` equivale a `intent`
- `intent_plan.tasks` equivale a `tasks`

Así, cualquier consumidor que solo necesite `{intent, tasks}` puede extraerlos directamente del `intent_plan`.

## Tests

Tests mínimos en:

- `agents/prompt_optimizer/tests/`

Ejecutar:

- `pytest -q`
