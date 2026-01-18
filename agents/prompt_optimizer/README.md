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

En `agents/prompt_optimizer/artifacts/`:

- `prompt_optimizer_sample.json` (ejemplo de salida)
- `planner_system_prompt.txt` (prompt del planner)
- `optimizer_flow.txt` (flujo interno del módulo)

## Acciones (contrato actual)

El Prompt Optimizer devuelve planes con `agent` y `action` separados (action = verbo, sin prefijo).
El orquestador/MCP construye el `tool_name` como `<agent>.<action>` (ej.: `data.fetch_metrics`).

Acciones acordadas:

- data: `fetch_metrics`
- nlp: `summarize`, `explain`, `rephrase`, `reason`, `generate`
- image: `normalized_text`

Nota (alineación con NLP):

- Para tareas NLP, `action` debe ser una de las soportadas por el agente NLP.
- Para tareas NLP, `input` debe ser un objeto (dict), no un string.
- El Prompt Optimizer no delega aclaraciones al NLP; si falta información devuelve `status="needs_clarification"` y `tasks=[]`.

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

Cualquier consumidor que solo necesite `{intent, tasks}` puede extraerlos directamente del `intent_plan`.

## Guardrails

- Input demasiado corto → `status="needs_clarification"` y `tasks=[]`
- SQL detectado (select/from/join/...) → `status="needs_clarification"` y `tasks=[]`
  (se pide reformulación a objetivo de negocio, sin SQL)

## LLM Planner (local, Ollama)

El Prompt Optimizer puede usar un LLM local para generar planes más precisos.

### Variables de entorno

- `USE_LLM_PLANNER`: `true|false` (default: `true`)
- `LLM_BASE_URL`: base URL del servidor (recomendado: `http://localhost:11434`)
- `LLM_MODEL`: nombre del modelo (ej.: `llama3.2:3b`)

### Verificar que Ollama está activo

PowerShell:

```powershell
(Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/tags).Content
