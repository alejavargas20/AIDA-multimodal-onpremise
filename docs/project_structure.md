# Estructura inicial del proyecto

Esta es la estructura base para comenzar el TFM:

```
mcp/
orchestrator/
agents/
docs/
tests/
data/
web/
docker/


## Descripción de cada módulo

mcp
Contiene el servidor Model Context Protocol, herramientas internas y los esquemas de datos que permiten la comunicación con el orquestador.

orchestrator
Contiene la lógica de coordinación entre agentes, flujos LangGraph y procesos CrewAI si se usan.

agents
Contiene los distintos agentes especializados. Cada agente tiene su propia carpeta con su código y documentación interna.

web
Interfaz local del sistema. Puede desarrollarse con Streamlit o FastAPI.

data
Directorio técnico para datos sintéticos, archivos temporales, modelos locales y registros.

docker
Archivos necesarios para empaquetar el sistema en contenedores.

tests
Pruebas unitarias y de integración.

docs
Documentación oficial del proyecto.


