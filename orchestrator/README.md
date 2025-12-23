# Orchestrator Module
#Descripción general
Este proyecto implementa un orquestador modular basado en LangGraph, estructurado en tres fases principales:

Fase 1 – Preprocesamiento del input
Normaliza la entrada del usuario según sea texto, audio, imagen o PDF (via mocks STT/OCR).

Fase 2 – Planificación
Clasifica la intención del usuario y construye un plan de agentes que deben ejecutarse.

Fase 3 – Ejecución y ensamblado
Ejecuta los agentes del plan (mock), ensambla los resultados y adapta el mensaje final según el perfil del usuario (técnico o no técnico).

El sistema funciona como un grafo de estados: cada nodo recibe el estado, lo transforma y lo pasa al siguiente.

# Arquitectura del proyecto:
.
├── graph.py                # Definición del grafo con LangGraph
├── state.py                # Modelo de estado compartido entre nodos
├── nodes_phase_1.py        # Preprocesamiento de input (text/audio/ocr)
├── nodes_phase_2.py        # Planificador e intención
├── nodes_phase_3.py        # Ejecución de agentes + ensamblado + adaptación
├── run_orchestrator.py     # Script/demo de ejecución
└── README.md               # Este archivo

# Cómo ejecutar la demo
python run_orchestrator.py

El script construye un estado inicial como este:

initial_state = {
    "user_id": "123",
    "session_id": "abc",
    "input_type": "pdf",
    "raw_input": "Explícame qué es la mora",
    "user_profile": "no_tecnico",
}

y ejecuta:

output = orchestrator_app.invoke(initial_state)
print(output["final_text"])

Ejemplo de salida:
[Modo sencillo]
Explicación simulada de: texto extraído simulado de imagen/pdf