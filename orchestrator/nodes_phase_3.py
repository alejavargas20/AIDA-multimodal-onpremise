# aida-multimodal-onpremise/orchestrator/nodes_phase_3.py

from orchestrator.state import OrchestratorState
from typing import TypedDict, List, Literal, Dict, Any, Optional
from orchestrator.mcp_client import call_mcp
import json

def execute_plan(state: OrchestratorState) -> OrchestratorState:
    print("\nEXECUTE PLAN")
    state.setdefault("errors", [])
    plan = state.get("plan", [])
    results = []

    if not plan:
        state["errors"].append("ExecutePlan: plan vacío.")
        state["agent_results"] = []
        return state

    # Usamos el mejor texto para pasar como contexto
    base_text = state.get("optimized_text") or state.get("normalized_text") or ""
    source = state.get("preprocessing_source", "text")

    for step in plan:
        tool_name = step.get("agent")  # <-- lo que viene del prompt optimizer
        action = step.get("action", "run")
        inp = step.get("input", {}) if isinstance(step.get("input", {}), dict) else {}
        step_metadata = step.get("metadata", {})

        if not tool_name:
            step["status"] = "error"
            state["errors"].append("ExecutePlan: step sin 'agent' (tool_name).")
            continue

        
        # 1. Recuperar historial
        historial = state.get("chat_history", "").strip()
        if not historial:
            from backend.db.history import get_recent_history
            session_id = str(state.get("session_id", ""))
            if session_id:
                historial = get_recent_history(session_id, limit=2)

        if len(historial) > 1500:
            historial = "..." + historial[-1500:]

        # ANTI CUDA-ERROR (AHORA CUBRE AUDIOS Y PDFs) ===
        MAX_CHARS = 7000 
        
        # Protección A: Para PDFs e Imágenes
        safe_file_context = state.get("file_context", "")
        if isinstance(safe_file_context, str) and len(safe_file_context) > MAX_CHARS:
            safe_file_context = safe_file_context[:MAX_CHARS] + "\n\n... [DOCUMENTO OMITIDO PARA NO SATURAR VRAM]"

        # Protección B: Para Audios Largos (STT) y Textos Gigantes
        safe_base_text = base_text
        if isinstance(safe_base_text, str) and len(safe_base_text) > MAX_CHARS:
            safe_base_text = safe_base_text[:MAX_CHARS] + "\n\n... [AUDIO/TEXTO TRUNCADO PARA NO SATURAR VRAM]"

        print(f"\n[DEBUG HISTORIAL FINAL ENVIADO AL LLM]:\n{historial if historial else 'SIN HISTORIAL'}\n")

        # 2. Identificamos si el usuario habló o escribió
        tipo_input = "Transcripción de Audio del usuario" if source == "stt" else "Mensaje del usuario"

        # 3. Construimos LA PREGUNTA / INSTRUCCIÓN
        mensaje_final = (
            f"Instrucción Estricta: Eres AIDA. Responde de forma natural y conversacional. "
            f"Háblale directamente al usuario tratándolo de 'tú'. PROHIBIDO hablar en tercera persona.\n\n"
            f"{tipo_input}:\n{safe_base_text}"
        )

        # 4. Construimos EL CONTEXTO UNIFICADO
        contexto_combinado = ""
        if historial:
            contexto_combinado += f"--- HISTORIAL DE LA CONVERSACIÓN ---\n{historial}\n\n"
        if safe_file_context:
            contexto_combinado += f"--- DOCUMENTO ADJUNTO A ANALIZAR ---\n{safe_file_context}"

        inp["text"] = mensaje_final
        inp["question"] = mensaje_final
        inp["instructions"] = mensaje_final
        inp["prompt"] = mensaje_final
        inp["context"] = contexto_combinado if contexto_combinado else None            

        # Construimos payload para MCP (incluye action + contexto)
        payload = {
            **inp,
            "task": action,
            "input": inp,
            "metadata": step_metadata,
            "context": {
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
                "text": safe_base_text, #base_text,
                "intent": state.get("intent"),
                "user_role": step_metadata.get("user_role"),
                "file_context": safe_file_context, #state.get("file_context"), # Inyectamos el OCR si existe
                "source": source #state.get("preprocessing_source") 
            },
        }
        

        try:
            print(tool_name)
            tool_result = call_mcp(tool_name, payload)
            results.append(
                {
                    "type": "tool_result",
                    "role": tool_name,
                    "action": action,
                    "content": tool_result,
                }
            )

            # GUARDAR DATOS CRUDOS PARA SÍNTESIS
            if tool_name == "data.process":
                # Verificamos tanto el status general como el status interno
                inner_result = tool_result.get("execution_result", {})
                if tool_result.get("status") == "success" and inner_result.get("status") == "success":
                    # Extraemos el valor real ('result' o 'rows') para la síntesis
                    data_to_save = inner_result.get("result") or inner_result.get("rows")
                    state["last_data_execution"] = data_to_save
                    print(f"[FASE 3] Dato guardado para síntesis: {data_to_save}")


        except Exception as e:
            step["status"] = "error"
            err = f"ExecutePlan: error llamando a {tool_name}: {e}"
            state["errors"].append(err)
            results.append(
                {
                    "type": "error",
                    "role": tool_name,
                    "action": action,
                    "content": str(e),
                }
            )

    state["agent_results"] = results
    print(state["agent_results"])
    return state

def assemble_results(state: OrchestratorState) -> OrchestratorState:
    print("\nASSEMBLE RESULTS")
    user_metadata = state.get("metadata", {})
    blocks = state.get("agent_results", [])
    state.setdefault("errors", [])

    assembled_parts = []

    if not blocks:
        state["assembled_text"] = "No se generaron resultados por parte de los agentes."
        return state
    
    # Extraemos el dato directo de los resultados, sin depender de variables borradas 
    data_raw = None
    for block in blocks:
        if block.get("role") == "data.process" and block.get("type") == "tool_result":
            content = block.get("content", {})
            if content.get("status") == "success":
                inner = content.get("execution_result", {})
                data_raw = inner.get("result") or inner.get("rows")
            break

    # 2. Si tenemos un resultado numérico de la DB, obligamos al NLP a explicarlo.
    if data_raw is not None:
        print(f"Invocando NLP para completar respuesta de los datos obtenidos: {data_raw}")
        
        question_user = state.get("normalized_text", "")
        
        # prompt_sintesis = (
        #     f"El usuario te ha preguntó: '{question_user}'.\n"
        #     f"La base de datos respondio: {data_raw}.\n"
        #     f"Tu tarea: Comunícale este dato al usuario de forma natural, sin mencionar bases de datos ni que el sistema lo buscó. Habla como si tú mismo supieras el dato."
        # )

        prompt_sintesis = (
            f"Pregunta del usuario: '{question_user}'\n"
            f"Datos EXACTOS extraídos del sistema: {data_raw}\n\n"
            f"INSTRUCCIONES CRÍTICAS Y OBLIGATORIAS:\n"
            f"1. Eres un PRESENTADOR de datos, NO un asesor teórico. Tu ÚNICA base de la verdad son los 'Datos EXACTOS extraídos del sistema'.\n"
            f"2. TIENES ESTRICTAMENTE PROHIBIDO inventar valores, dar ejemplos genéricos (como 30, 60, 90 días) o usar tu conocimiento previo. Si el dato extraído es un número, ESE es el número que debes dar.\n"
            f"3. Si los 'Datos extraídos' contienen múltiples registros, DEBES enumerarlos TODOS en una lista o viñetas.\n"
            f"4. Si los 'Datos extraídos' contienen un solo valor numérico o de texto, dalo directamente en una frase natural y concisa.\n"
            f"5. Habla en primera persona, con seguridad, y NUNCA menciones bases de datos, SQL, ni que el sistema lo buscó."
        )
        
        synthesis_payload = {
            "action": "reason", 
            "input": {
                "question": prompt_sintesis,
                "context": "",
                "goal": "Sintetizar respuesta humana"
            },
            "metadata": user_metadata
        }

        try:
            # Llamamos a Llama 3.1
            synthesis_result = call_mcp("nlp.process", synthesis_payload)
            final_answer = synthesis_result.get("answer") or synthesis_result.get("content")
            
            if final_answer:
                print(f"[ÉXITO SÍNTESIS]: {final_answer}")
                state["assembled_text"] = final_answer
                state["final_text"] = final_answer # Evitamos que se le pegue la etiqueta "[Modo sencillo]"
                return state
        except Exception as e:
            print(f"[ERROR SÍNTESIS NLP]: {e}")
            state["errors"].append(f"Assemble: error en síntesis final: {e}")

    # 3. Fallback: Si no hubo datos o Llama falló, unimos el texto crudo
    for block in blocks:
        block_type = block.get("type")
        role = block.get("role")
        action = block.get("action")
        content = block.get("content", {})

        if block_type == "tool_result" and role == "data.process":
            status = content.get("status", "unknown")
            inner_result = content.get("execution_result", {})
            data = inner_result.get("result") or inner_result.get("rows")

            if status == "success" and data is not None:
                data_str = json.dumps(data, indent=2, ensure_ascii=False)
                assembled_parts.append(f"Los datos extraídos son:\n{data_str}")
            else:
                error_msg = inner_result.get("error", "Error desconocido")
                print(f"\n[ERROR INTERNO DE SQL OCULTO AL USUARIO]: {error_msg}\n") # Se queda en la consola
                
                # Respuesta limpia para el chat:
                assembled_parts.append("Lo siento, hubo un problema técnico al analizar esa información específica. Por favor, intenta reformular la pregunta.")

        elif block_type == "tool_result" and role == "nlp.process":
            output = content.get("answer") or content.get("content")
            if output:
                assembled_parts.append(output)

        elif block_type == "tool_result" and role == "image.process":
            output = content.get("normal_text")
            if output:
                assembled_parts.append(f"Texto extraído del documento:\n{output}")

        elif block_type == "tool_result" and role == "voice.process":
            output = content.get("text") or content.get("result", {}).get("text")
            if output:
                assembled_parts.append(f"Transcripción de audio:\n{output}")

        elif block_type == "error":
            assembled_parts.append(f"Se produjo un error en el sistema: {content}")

    state["assembled_text"] = "\n\n".join(assembled_parts)
    
    if not state.get("final_text"):
        state["final_text"] = state["assembled_text"]

    return state

def behaviour_adaptation(state: OrchestratorState) -> OrchestratorState:
    profile = state.get("user_profile", "no_tecnico")
    text = state.get("assembled_text", "")

    if profile == "tecnico":
        # Perfil técnico: dejamos más detalle
        adapted = f"[Modo técnico]\n{text}"
    else:
        # Perfil no técnico: simplificar un poco (mock)
        adapted = f"[Modo sencillo]\n{text}"

    state["final_text"] = adapted
    return state
