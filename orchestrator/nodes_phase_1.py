# aida-multimodal-onpremise/orchestrator/nodes_phase_1.py
from orchestrator.state import OrchestratorState
from orchestrator.mcp_client import call_mcp
import base64
import os
import uuid

# Directorio temporal para archivos subidos
TEMP_DIR = os.path.join(os.getcwd(), "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

def phase1_router(state: OrchestratorState) -> OrchestratorState:
    input_type = state["input_type"]
    raw_content = state["content"]

    print("PHASE1")
    state.setdefault("errors", [])

    try:
        if input_type == "text":
            state["normalized_text"] = raw_content
            state["preprocessing_source"] = "text"
            
        elif input_type == "audio":
            # 1. Guardar archivo de audio temporalmente (para evitar pasar base64 crudo)
            temp_audio_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.webm") # O .wav según lo que mande el frontend
            target_path = ""

            # Si viene en Base64 (frontend), lo decodificamos
            if len(raw_content) > 200:
                try:
                    content_to_write = raw_content
                    if "," in raw_content:
                        content_to_write = raw_content.split(",")[1]
                    
                    with open(temp_audio_path, "wb") as f:
                        f.write(base64.b64decode(content_to_write))
                    
                    print(f"Audio guardado en: {temp_audio_path}")
                    target_path = temp_audio_path
                except Exception as e:
                    state["errors"].append(f"Error guardando audio: {e}")
                    return state
            else:
                target_path = raw_content

            # 2. Llamada al MCP 
            print(f"Llamando a voice.process (transcribe) con: {target_path}")
            
            results = call_mcp(
                "voice.process", 
                {
                    "action": "transcribe",  
                    "file_path": target_path
                }
            )
            
            # 3. Procesar resultado
            # El voice_logic devuelve {"result": {"text": "Hola..."}} o aplanado
            text_result = results.get("text") or results.get("result", {}).get("text")
            
            state["normalized_text"] = text_result
            state["preprocessing_source"] = "stt"


        # elif input_type in ("image", "pdf"):
        #     # 1. DECODIFICAR Y GUARDAR ARCHIVO
        #     ext = ".pdf" if input_type == "pdf" else ".jpg"
        #     temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}{ext}")

        #     # Detectar si es base64 (lo que manda el frontend)
        #     try:
        #         # Si el contenido es largo, asumimos que es Base64 del frontend
        #         if len(raw_content) > 200: 
        #             # Limpieza absoluta del string
        #             clean_b64 = raw_content.strip()
                    
        #             # Cortar cabeceras sin importar cómo vengan desde el JS
        #             if "base64," in clean_b64:
        #                 clean_b64 = clean_b64.split("base64,")[-1]
        #             elif "," in clean_b64:
        #                 clean_b64 = clean_b64.split(",")[-1]
                    
        #             # Reparar Padding (Súper crítico porque Javascript a veces lo omite)
        #             clean_b64 += "=" * ((4 - len(clean_b64) % 4) % 4)
                    
        #             # Decodificar a bytes puros
        #             file_bytes = base64.b64decode(clean_b64)
                    
        #             # VERIFICACIÓN DE INTEGRIDAD PARA PDFs
        #             if ext == ".pdf" and not file_bytes.startswith(b'%PDF'):
        #                 print("\n[🚨 ALERTA CRÍTICA] El archivo decodificado NO es un PDF válido. ¡El Frontend está enviando el Base64 corrupto!\n")
                    
        #             with open(temp_path, "wb") as f:
        #                 f.write(file_bytes)
                    
        #             target_path = temp_path
        #         else:
        #             target_path = raw_content

        elif input_type in ("image", "pdf"):
            # 1. DECODIFICAR Y GUARDAR ARCHIVO
            ext = ".pdf" if input_type == "pdf" else ".jpg"
            temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}{ext}")

            try:
                # Si el contenido es largo, asumimos que es Base64 del frontend
                if len(raw_content) > 200: 
                    clean_b64 = raw_content.strip()
                    
                    if "base64," in clean_b64:
                        clean_b64 = clean_b64.split("base64,")[-1]
                    elif "," in clean_b64:
                        clean_b64 = clean_b64.split(",")[-1]
                    
                    # Reparar Padding
                    clean_b64 += "=" * ((4 - len(clean_b64) % 4) % 4)
                    file_bytes = base64.b64decode(clean_b64)
                    
                    if ext == ".pdf" and not file_bytes.startswith(b'%PDF'):
                        print("\n[ALERTA CRÍTICA] El archivo decodificado NO es un PDF válido. ¡El Frontend está enviando el Base64 corrupto!\n")
                    
                    with open(temp_path, "wb") as f:
                        f.write(file_bytes)
                    
                    target_path = temp_path
                else:
                    target_path = raw_content

            except Exception as e:
                state["errors"].append(f"Error decodificando archivo: {e}")
                return state
    
            # # 2. LLAMAR AL AGENTE DE IMAGEN CON LA RUTA
            # print(f"Llamando a image.process con: {target_path}")

            # results = call_mcp(
            #     "image.process", {
            #         "action": "extract_text", # IMPORTANTE: Añadir la acción
            #         "file_path": target_path
            #     })  # Que más necesita el MCP en el payload
            
            # # 3. GUARDAR RESULTADO
            # extracted_text = results.get("normal_text", "")

            # 2. LLAMAR AL AGENTE DE IMAGEN CON LA RUTA
            print(f"Llamando a image.process con: {target_path}")

            results = call_mcp("image.process", {
                "action": "extract_text", 
                "file_path": target_path
            })  
            
            if results.get("status") == "error":
                error_msg = results.get("error")
                print(f"\n[ERROR FATAL EN MCP IMAGEN]: {error_msg}\n")
                state["errors"].append(f"Image Agent Error: {error_msg}")

            # 3. GUARDAR RESULTADO
            extracted_text = results.get("normal_text", "").strip()

            # Si el OCR no detectó nada, ponemos un mensaje de advertencia
            if not extracted_text:
                print("[WARNING] El OCR no detectó texto en la imagen/pdf.")
                extracted_text = "El sistema no pudo extraer texto de este documento. Puede que la resolución sea baja o sea ilegible."
                
            # Guardamos el resultado (o el aviso) en el contexto
            state["file_context"] = extracted_text 
            state["preprocessing_source"] = "ocr"
            
            # Rescatamos la pregunta del usuario (si la hizo)
            user_query = state.get("metadata", {}).get("user_query", "").strip()
            
            if user_query:
                state["normalized_text"] = user_query
            else:
                state["normalized_text"] = extracted_text
        else:
            state["errors"].append(f"Tipo de input no soportado: {input_type}")

        print(f"Texto Normalizado: {state.get('normalized_text')}")
        print(state["preprocessing_source"])
        if not state.get("normalized_text"):
            state["errors"].append("Fase 1: normalized_text vacío.")

    except Exception as e:
        state["errors"].append(f"Error en Fase 1: {e}")

    return state
