# Estructura inicial del proyecto

Esta es la estructura base para comenzar el TFM:

```
mcp/
orchestrator/
nlp_agent/
prompt_optimizer/
docs/
tests/
```

## Descripción de cada módulo

### mcp/
Módulo central que define:
- Tools
- Server
- Schemas
- Comunicación con el Orchestrator

### orchestrator/
Gestiona:
- Flujo entre módulos
- Recepción y envío de mensajes
- Decisiones de alto nivel

### nlp_agent/
Agente de lenguaje:
- Llama modelos LLM
- Extrae información
- Resume o traduce

### prompt_optimizer/
Optimiza prompts y contexto para mejorar respuestas.

### docs/
Documentación técnica del equipo.

### tests/
Pruebas unitarias e integración.


