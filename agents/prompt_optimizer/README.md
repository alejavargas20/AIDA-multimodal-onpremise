# Prompt Optimizer Module

Este módulo implementa el Prompt Optimizer del sistema multimodal de IA desarrollado
en el Trabajo Fin de Máster.

Su función es actuar como capa de planificación entre la entrada del usuario y el
orquestador de agentes.

## Rol del módulo

El Prompt Optimizer:
- NO ejecuta tareas
- NO consulta bases de datos
- NO responde directamente al usuario

Su responsabilidad es:
- interpretar la intención del usuario
- reformular la petición de forma clara
- generar un plan estructurado de tareas en formato JSON

Este plan es consumido posteriormente por el orquestador (CrewAI / LangGraph),
que decide qué agentes ejecutar.

## Encaje en la arquitectura

El Prompt Optimizer se integra como una tool del MCP (Model Context Protocol).
Recibe peticiones normalizadas desde el orquestador y devuelve un JSON estructurado.

La ejecución real de las tareas queda delegada en los agentes especializados:
- NLP
- Datos
- Imagen
- Voz
- Reportes

## Estructura del módulo

prompt_optimizer/
├── optimizer.py # Clase principal PromptOptimizer
├── planner_prompt.py # System prompt + few-shot examples
├── preprocessing.py # Limpieza, regex y detección de idioma
├── schema.py # Definición del contrato JSON (Pydantic)
├── baseline.py # Reglas y keywords como baseline clásico
├── exceptions.py # Excepciones propias del módulo
└── README.md


## Flujo de funcionamiento

1. Recepción del input desde MCP
2. Preprocesamiento del texto
3. Ejecución de baseline clásico
4. Generación del plan mediante LLM
5. Validación estricta del JSON
6. Logging y trazabilidad
7. Devolución del plan al orquestador

## Data Abstraction Layer

El Prompt Optimizer utiliza un Data Abstraction Layer (DAL) como contexto conceptual
para conocer:
- tipos de datos disponibles
- conceptos de negocio
- granularidades
- restricciones de privacidad

El DAL no contiene datos reales ni esquemas físicos.

## Estado del desarrollo

- Diseño del módulo: completado
- Contrato JSON: definido (v1.0)
- Planner prompt: implementado
- Integración MCP/orquestador: pendiente
- Ejecución end-to-end: pendiente

## Objetivo académico

Este módulo permite:
- desacoplar planificación y ejecución
- mejorar la explicabilidad del sistema
- reforzar privacidad y control
- facilitar la evaluación del TFM