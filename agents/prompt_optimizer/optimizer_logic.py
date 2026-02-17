# aida-multimodal-onpremise/agents/prompt_optimizer/optimizer_logic.py
from __future__ import annotations

import json
import os
import re

from typing import Any, Dict, List

from pydantic import ValidationError as PydanticValidationError

from .baseline import baseline_intent, baseline_action_stub
from .exceptions import ValidationError
from .preprocessing import preprocess
from .schema import PromptOptimizerResponse, IntentPlan, Task

from .llm_client import call_llm_chat
# Importamos AMBOS prompts
from .planner_prompt import PLANNER_SYSTEM_PROMPT, DATA_INTENT_SYSTEM_PROMPT 

def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extracts a JSON object from model output.
    Strict: returns dict or raises ValueError.
    """
    t = (text or "").strip()
    
    # Intento 1: Parseo directo (por si el modelo fue buen chico y devolvió JSON puro)
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Intento 2: Limpieza de bloques de código Markdown (```json ... ```)
    t_clean = re.sub(r"```(?:json)?(.*?)```", r"\1", t, flags=re.DOTALL).strip()
    try:
        obj = json.loads(t_clean)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Intento 3: Extracción por fuerza bruta (busca desde el primer '{' hasta el último '}')
    start_idx = t.find('{')
    end_idx = t.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        candidate = t[start_idx:end_idx+1]
        try:
            obj2 = json.loads(candidate)
            if isinstance(obj2, dict):
                return obj2
        except Exception as e:
            raise ValueError(f"Found braces but content is not valid JSON: {e}")
            
    raise ValueError("No valid JSON object found in LLM output.")

def _llm_messages(system_prompt: str, user_text: str, metadata: Dict[str, Any], chat_history: str) -> List[Dict[str, str]]:
    # Extraemos seguridad para el Planner general también
    user_role = metadata.get("user_role", "analista")
    client_id = metadata.get("client_id", "")
    
    # Historial 
    formatted_system = system_prompt.replace(
        "{chat_history}", chat_history
    ).replace(
        "{user_role}", str(user_role)
    ).replace(
        "{client_id}", str(client_id)   
    )

    user_payload = {
        "user_text": user_text,
        "metadata": metadata,
        "constraints": {"output_format": "json_only", "max_tasks": 1},
    }
    return [
        {"role": "system", "content": formatted_system.strip()},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

def _normalize_plan_for_nlp(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aligns LLM output with NLP agent contract (Naty).
    """
    supported = {"summarize", "explain", "rephrase", "reason", "generate"}
    action_map = {
        "answer": "reason",
        "ask_clarification": None,
    }

    tasks = (plan.get("intent_plan", {}) or {}).get("tasks", [])
    if not isinstance(tasks, list):
        return plan

    normalized_tasks = []
    for t in tasks:
        if not isinstance(t, dict):
            continue

        agent = (t.get("agent") or "").strip().lower()
        action = (t.get("action") or "").strip().lower()
        inp = t.get("input")

        if agent == "nlp":
            if action in action_map:
                action = action_map[action]
                if action is None:
                    continue

            if action not in supported:
                action = "reason"

            if isinstance(inp, str):
                if action == "summarize": inp = {"text": inp}
                elif action == "explain": inp = {"question": inp}
                elif action == "rephrase": inp = {"text": inp}
                elif action == "generate": inp = {"instructions": inp}
                else: inp = {"question": inp}

            if inp is None or not isinstance(inp, dict):
                inp = {"question": "Falta input estructurado; usar la petición original como fallback."}

            t["action"] = action
            t["input"] = inp

        normalized_tasks.append(t)
    
    if normalized_tasks:
        plan["intent_plan"]["tasks"] = [normalized_tasks[0]]
    else:
        plan["intent_plan"]["tasks"] = []
        
    return plan


def _build_tasks(intent: str, user_text: str) -> List[Task]:
    stub = baseline_action_stub(intent)
    agent = stub["agent"]
    action = stub["action"]

    if agent == "data":
        task_input = {"text": user_text} 
    else:
        task_input = {
            "text": user_text,
            "style": "ejecutivo",
            "audience": "general",
            "constraints": {"length": "short"}
        }

    return [
        Task(
            agent=agent, 
            action=action,
            input=task_input,
            params={},
        )
    ]


def process_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Public stable function to be called by MCP tool layer.
    """
    # 1. Recuperar historial del payload (que viene del Orquestador)
    chat_history = payload.get("chat_history", "") 

    fase1 = preprocess(payload)
    user_text = fase1.get("user_text") or fase1.get("content") or "Consulta financiera"
    input_source = fase1["input_source"]
    language = fase1["language"]
    # Recupera el contexto del agregado de archivo (si existe)
    file_context = payload.get("context", "")
    
    raw_meta = payload.get("metadata", {})

    metadata = {
        "language": language, 
        "input_source": input_source,
        "user_role": raw_meta.get("user_role", "cliente"),
        "client_id": raw_meta.get("client_id", "")
    }
    # # Baseline intent
    # intent, base_conf = baseline_intent(user_text)
    
    # # Detectamos si es intención de datos para usar el Prompt DATA
    # is_data_intent = intent in ["analitica_desembolsos", "analitica_sistema", "analitica_cartera", "info_cliente", "analitica_general"]

    use_llm = os.getenv("USE_LLM_PLANNER", "true").lower() in ("1", "true", "yes", "y", "on")

    # Clarification guardrail (very short/empty)    
    if not user_text or len(user_text) < 4:
        # Excepción: Si hay un archivo adjunto, permitimos texto corto (ej: "Resume")
        if not file_context: 
            response = PromptOptimizerResponse(
                optimized_prompt="Necesito más contexto para planificar la petición.",
                intent_plan=IntentPlan(
                    intent="otro_ayuda",
                    confidence=0.2,
                    tasks=[],
                    metadata=metadata,
                    conductual_state=None,
                    conductual_notes="Input demasiado corto o vacío.",
                ),
                status="needs_clarification",
                errors=["Input demasiado corto para planificar."],
            )
            return response.model_dump()

    # Guardrail explícito: SQL detectado → no construir tasks
    lowered = user_text.lower()
    if any(k in lowered for k in ["select ", " from ", " join ", " where ", " group by", "insert ", "update ", "delete "]):
        safe_response = {
            "optimized_prompt": (
                "Reformula la petición sin incluir SQL ni nombres de tablas. "
                "Indica el objetivo de negocio (qué quieres analizar) y el periodo."
            ),
            "intent_plan": {
                "intent": "needs_clarification",
                "confidence": 0.0,
                "tasks": [],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Entrada contenía SQL u otro patrón no permitido.",
            },
            "status": "needs_clarification",
            "errors": [],
        }
        json.dumps(safe_response)
        return safe_response
    
    
    # MANEJO DE DOCUMENTO - Agente de IMAGEN (Prioridad Alta)
    if file_context and len(file_context) > 10:
        try:
            doc_task = Task(
                agent="nlp",
                action="reason",
                input={
                    "question": user_text if user_text else "Resume el documento.",
                    "context": file_context,
                    "goal": "Analiza el documento adjunto y responde."
                },
                params={}
            )
            return PromptOptimizerResponse(
                optimized_prompt=user_text,
                intent_plan=IntentPlan(
                    intent="procesar_documento",
                    confidence=1.0,
                    tasks=[doc_task],
                    metadata=metadata
                ),
                status="ok",
                errors=[]
            ).model_dump()
        except Exception as e:
            return {"status": "error", "errors": [str(e)]}


    try:
        # 1) Try LLM planner
        if use_llm:

            planner_msgs = _llm_messages(PLANNER_SYSTEM_PROMPT, user_text, metadata, chat_history)
            
            # SELECCIÓN DE PROMPT (DATA vs GENERAL)
            #messages = []
            # if is_data_intent:
            #     print(f"[DEBUG] Detectado Intent de DATOS: {intent}")
            #     # PROMPT DE DATOS y el Contexto de Tablas
            #     # Extraemos seguridad del metadata
            #     user_role = metadata.get("user_role", "analista")
            #     client_id = metadata.get("client_id", "")

            #     tables_context = """
            #     CONTEXT - TABLES:
            #     - desembolso (idSolicitud, monto, fecha)
            #     - cosecha_sal (idCliente, periodo, saldo, mora)
            #     - desembolso_comportamiento (idCuenta, reprogramado)
            #     - cierre (idCuenta, periodo, saldo_capital)
            #     """
                
            #     full_data_prompt = DATA_INTENT_SYSTEM_PROMPT + "\n" + tables_context
            #     # messages = [
            #     #     {"role": "system", "content": full_data_prompt, "chat_history": chat_history},
            #     #     {"role": "user", "content": user_text, "chat_history": chat_history}
            #     # ]

            #     formatted_data_prompt = full_data_prompt.replace(
            #                         "{chat_history}", chat_history
            #                     ).replace(
            #                         "{user_role}", str(user_role)
            #                     ).replace(
            #                         "{client_id}", str(client_id)
            #                     )
                

            #     messages = [
            #         {"role": "system", "content": formatted_data_prompt},
            #         {"role": "user", "content": user_text}
            #     ]

            # else:
            #     metadata_for_llm = {"language": language, "input_source": input_source}
            #     messages = _llm_messages(PLANNER_SYSTEM_PROMPT, user_text, metadata_for_llm, chat_history)

            #last_err = None
            for attempt in range(2):  
                try:
                    # LLAMADA AL LLM
                    #raw = call_llm_chat(messages)

                    raw_planner = call_llm_chat(planner_msgs)
                    planner_dict = _extract_json_object(raw_planner)

                    # Validación Estructural del Planner
                    if not isinstance(planner_dict, dict):
                        raise ValueError("Planner did not return dict.")
                    
                    # Normalizamos la salida del Planner para asegurar compatibilidad con NLP
                    planner_dict = _normalize_plan_for_nlp(planner_dict)
                                        
                    intent_plan = planner_dict.get("intent_plan")
                    if not isinstance(intent_plan, dict):
                        raise ValueError("intent_plan inválido")

                       
                    tasks = intent_plan.get("tasks", [])

                    if not isinstance(tasks, list) or not tasks:
                        raise ValueError("Fallo al extraer tasks del intent_plan.")
                        
                    supervisor_intent = intent_plan.get("intent", "consulta_datos") 
                    
                    first_task = tasks[0]
                    chosen_agent = first_task.get("agent", "nlp").lower()

                    # GUARDRAIL 2: Control estricto de agentes permitidos
                    if chosen_agent not in ["nlp", "data"]:
                        print(f"Agente inválido '{chosen_agent}'. Forzando a 'nlp'.")
                        chosen_agent = "nlp"
                        first_task["agent"] = "nlp"

                    # AGENTE DE DATOS 
                    if chosen_agent == "data":
                        print("\nAGENTE DE DATOS SOLICITADO")

                        tables_context = """
                        CATALOGO DE TABLAS REALES (Esquemas: cartera, dbo):

                        1. [cartera].[cierre] (Saldos Mensuales):
                        - Uso: Consultar saldos actuales, mora acumulada y estado de cartera por mes.
                        - Columnas Clave: idCuenta, idCliente, nSaldoCap (Saldo Capital), nMora (Días Atraso), dFechaCie (Fecha Corte), cProducto, cRegion, nSaldoVen (Saldo Vencido).

                        2. [cartera].[desembolso] (Ventas / Originación):
                        - Uso: Consultar montos prestados, préstamos nuevos, plazos y tasas.
                        - Columnas Clave: idCuenta, idCliente, nMonto (Monto Desembolsado), dFechaDes (Fecha Desembolso), nPlazo, cOficina, nClienteNue (1 si es nuevo).

                        3. [cartera].[desembolso_comportamiento] (Eventos y Reestructuraciones):
                        - Uso: Seguimiento de reprogramaciones, condonaciones y programas como IMPULSO.
                        - Columnas Clave: idCuentaOrig, nMora, nSaldoCap, monto_condonado, tipo_ope_repro (Reprogramados).

                        """
                        data_system = DATA_INTENT_SYSTEM_PROMPT + tables_context
                        
                        data_msgs = _llm_messages(data_system, user_text, metadata, chat_history)
                        raw_data = call_llm_chat(data_msgs)
                        data_dict = _extract_json_object(raw_data)
                        
                        # Validación Estructural del agente de datos
                        if not isinstance(data_dict, dict):
                            raise ValueError("Agente de datos no responde return dict.")
                        if "agent" not in data_dict:
                            raise ValueError("Agente de datos no tiene campo 'agent'.")
                            
                        specialist_agent = data_dict.get("agent", "data").lower()

                        # Validación estricta de la acción del Agente de Datos (debe ser 'fetch_metrics')
                        if specialist_agent == "data" and data_dict.get("action") != "fetch_metrics":
                            raise ValueError(f"Accion Invalida agente de datos: {data_dict.get('action')}. Expected 'fetch_metrics'.")
                        
                        # RUTA DE ESCAPE (HATCH)
                        if specialist_agent == "nlp":
                            print("[AGENTE DE DATOS] -> Era una definición. Ruta de escape a NLP.")
                            plan_dict = {
                                "optimized_prompt": user_text,
                                "intent_plan": {
                                    "intent": "educacion_financiera", 
                                    "confidence": 0.9,
                                    "tasks": [{
                                        "agent": "nlp",
                                        "action": data_dict.get("action", "explain"),
                                        "input": data_dict.get("input", {"concept": user_text})
                                    }],
                                    "metadata": metadata
                                }
                            }
                        else:
                            # JSON Normal de Datos
                            print("[AGENTE DE DATOS] -> JSON SQL Generado.")
                            plan_dict = {
                                "optimized_prompt": user_text,  
                                "intent_plan": {
                                    "intent": supervisor_intent,
                                    "confidence": 0.9,
                                    "tasks": [{
                                        "agent": "data",
                                        "action": "fetch_metrics",
                                        "input": data_dict.get("input", data_dict) 
                                    }],
                                    "metadata": metadata
                                }
                            }
                    else:
                        # Ruta NLP directa
                        print(f"\nSolicitó NLP (Acción: {first_task.get('action')}). Evitando Data Parser.\n")
                        plan_dict = planner_dict

                    # Normalización finaL
                    plan_dict = _normalize_plan_for_nlp(plan_dict)

                    if not plan_dict.get("optimized_prompt"):
                        plan_dict["optimized_prompt"] = user_text

                    # Aseguramos límites
                    t_list = plan_dict.get("intent_plan", {}).get("tasks", [])
                    if isinstance(t_list, list) and len(t_list) > 3:
                        plan_dict["intent_plan"]["tasks"] = t_list[:3]
                    

                    validated = PromptOptimizerResponse.model_validate(plan_dict)
                    return validated.model_dump()

                except Exception as e:
                    print(f"[OPTIMIZER] Intento {attempt+1} fallido por error estructural: {e}")

        # SALVAVIDAS BASELINE (Solo si el LLM falla por JSON roto)
        print("[OPTIMIZER] Fallo total de IA (Estructuras rotas). Activando Salvavidas Baseline.")
        fallback_intent, base_conf = baseline_intent(user_text)
        tasks = _build_tasks(fallback_intent, user_text)

        response = PromptOptimizerResponse(
            optimized_prompt=user_text,
            intent_plan=IntentPlan(intent=fallback_intent, confidence=base_conf, tasks=tasks, metadata=metadata),
            status="ok", errors=[]
        )
        return response.model_dump()

    except Exception as exc:
        return {"optimized_prompt": "Error crítico.", "intent_plan": {"intent": "error", "confidence": 0.0, "tasks": [], "metadata": metadata}, "status": "error", "errors": [str(exc)]}    
                    
                    # # DEBUGGING PRINT ACTIVADO SI ES DATA 
                    # if is_data_intent:
                    #     print(f"\n[DEBUG] RESPUESTA DE LLAMA 3.1 (Intento {attempt+1}):")
                    #     print("--------------------------------------------------")
                    #     print(raw) 
                    #     print("--------------------------------------------------\n")

                    # plan_dict = _extract_json_object(raw)
                    
                    # # ADAPTACIÓN SI ES DATA INTENT 
                    # if is_data_intent:
                    #     if "input" in plan_dict:
                    #         # Envolvemos el resultado y AGREGAMOS optimized_prompt
                    #         plan_dict = {
                    #             "optimized_prompt": user_text,  
                    #             "intent_plan": {
                    #                 "intent": intent,
                    #                 "confidence": 0.9,
                    #                 "tasks": [{
                    #                     "agent": "data",
                    #                     "action": "fetch_metrics",
                    #                     "input": plan_dict["input"]
                    #                 }],
                    #                 "metadata": metadata
                    #             }
                    #         }
                    #     # # O si Llama lo devolvió dentro de otro objeto
                    #     elif "intent_plan" not in plan_dict: 
                    #          print("[DEBUG] JSON recibido no tiene estructura conocida.")
                    #          raise ValueError("Estructura JSON desconocida")
                    # if not plan_dict.get("optimized_prompt"):
                    #     plan_dict["optimized_prompt"] = user_text

        #             plan_dict = _normalize_plan_for_nlp(plan_dict)

        #             # Enforce max_tasks defensively
        #             tasks_list = plan_dict.get("intent_plan", {}).get("tasks", [])
        #             if isinstance(tasks_list, list) and len(tasks_list) > 3:
        #                 plan_dict["intent_plan"]["tasks"] = tasks_list[:3]

        #             # Validate strictly with Pydantic schema
        #             validated = PromptOptimizerResponse.model_validate(plan_dict)
        #             data = validated.model_dump()

        #             try:
        #                 tasks_list = data.get("intent_plan", {}).get("tasks", []) or []
        #                 if isinstance(tasks_list, list):
        #                     metric = None
        #                     period = None
        #                     for t in tasks_list:
        #                         if isinstance(t, dict) and (t.get("agent") == "data") and (t.get("action") == "fetch_metrics"):
        #                             inp = t.get("input") or {}
        #                             if isinstance(inp, dict):
        #                                 metric = inp.get("metric")
        #                                 period = inp.get("period")

        #                     if metric and period:
        #                         data["optimized_prompt"] = f"Resume de forma ejecutiva las {metric} del {period}."
        #                     else:
        #                         data["optimized_prompt"] = user_text
        #             except Exception:
        #                 data["optimized_prompt"] = user_text

        #             json.dumps(data)
        #             return data

        #         except Exception as e:
        #             last_err = e
        #             print(f"[OPTIMIZER] Error procesando JSON (Intento {attempt+1}): {e}")
        #             pass

        # # 2) Baseline fallback (keeps system resilient)
        # print("[OPTIMIZER] Falló el LLM o el parseo JSON. Usando Fallback Básico.")
        # tasks = _build_tasks(intent, user_text)

        # response = PromptOptimizerResponse(
        #     optimized_prompt=user_text,
        #     intent_plan=IntentPlan(
        #         intent=intent,
        #         confidence=base_conf,
        #         tasks=tasks,
        #         metadata=metadata,
        #         conductual_state=None,
        #         conductual_notes=None,
        #     ),
        #     status="ok",
        #     errors=[],
        # )

        # data = response.model_dump()
        # json.dumps(data)
        # return data


    except PydanticValidationError as e:
        safe_response = {
            "optimized_prompt": user_text,
            "intent_plan": {
                "intent": "needs_clarification",
                "confidence": 0.0,
                "tasks": [],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Validation Error.",
            },
            "status": "needs_clarification",
            "errors": [str(e)],
        }
        try:
            json.dumps(safe_response)
        except Exception as exc:
            raise ValidationError(f"Safe response not JSON-serializable: {exc}") from exc

        return safe_response

    except Exception as exc:
        safe_error = {
            "optimized_prompt": "Se produjo un error al planificar la petición.",
            "intent_plan": {
                "intent": "error",
                "confidence": 0.0,
                "tasks": [],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Error interno no esperado.",
            },
            "status": "error",
            "errors": [str(exc)],
        }
        try:
            json.dumps(safe_error)
        except Exception as exc2:
            raise ValidationError(f"Error response not JSON-serializable: {exc2}") from exc2

        return safe_error


