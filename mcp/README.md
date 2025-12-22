**MCP Server**



El servidor MCP (Model Context Protocol) proporciona una interfaz estandarizada para la ejecución de herramientas de agentes de IA locales dentro del sistema AIDA.



El MCP actúa como una capa intermedia entre el Orquestador y los Agentes, permitiendo la comunicación desacoplada entre componentes y evitando dependencias directas entre ellos.



-------------------------------------------------------------------------------



**Responsabilidades del MCP**



El MCP es responsable de:



Exponer los agentes como herramientas accesibles vía HTTP



Validar las entradas y salidas mediante contratos definidos



Desacoplar la lógica de orquestación de la implementación de los agentes



Proveer una capa única y centralizada de ejecución de herramientas



Facilitar trazabilidad, control y escalabilidad del sistema



El MCP no planifica tareas, no toma decisiones y no contiene lógica de negocio.





-------------------------------------------------------------------------------



**Endpoint principal**



POST /call



Este es el único endpoint utilizado por el Orquestador para interactuar con los agentes.



Payload esperado:



{

"tool\_name": "string",

"payload": {}

}



Donde:



tool\_name es el nombre de la herramienta registrada en el MCP



payload contiene los datos de entrada necesarios para esa herramienta



-----------------------------------------------------------------------------------------



**Registro de herramientas (Tools)**



Cada herramienta debe definirse dentro de la carpeta:



mcp/tools/



Cada archivo de tools debe exponer un diccionario llamado TOOL\_REGISTRY.



El MCP escanea dinámicamente esta carpeta al iniciar y registra todas las herramientas encontradas.



Ejemplo de registro de una tool:



TOOL\_REGISTRY = {

"prompt.optimize": prompt\_optimize

}



En este ejemplo, la herramienta prompt.optimize queda disponible para ser llamada por el Orquestador mediante el endpoint /call.



--------------------------------------------------------------------------------------------



**Principio fundamental de diseño**



El MCP no contiene lógica de negocio.





Toda la lógica específica vive dentro de los agentes, por ejemplo:



* Interpretación de lenguaje natural
* Generación de SQL
* Ejecución de modelos de Machine Learning
* Procesamiento de voz o imágenes
* Adaptación conductual (COM-B)





El MCP únicamente:



* Recibe la solicitud
* Localiza la herramienta correspondiente
* Ejecuta la función asociada
* Devuelve el resultado al Orquestador



-----------------------------------------------------------------------------------------------



**Rol del MCP dentro de la arquitectura del sistema**



* El Orquestador nunca llama directamente a los agentes
* El Orquestador siempre llama al MCP
* Los agentes no conocen al Orquestador
* Los agentes no se comunican entre sí directamente





Este diseño garantiza modularidad, escalabilidad y facilidad de mantenimiento del sistema.

