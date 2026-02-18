# aida-multimodal-onpremise/agents/local_engine.py
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# True  = GPU conectada y encendida.
# False = portátil (CPU).
USAR_GPU_EXTERNA = True  

MODEL_NLP_PATH = os.path.join(ROOT_DIR, "models", "Meta-Llama-3.1-8B-Instruct-Q8_0.gguf")
MODEL_SQL_PATH = os.path.join(ROOT_DIR, "models", "Qwen2.5-14B-Instruct-Q4_K_M.gguf")

if "AIDA_LLM_CACHE" not in sys.modules:
    sys.modules["AIDA_LLM_CACHE"] = {}

class HybridEngine:
    _is_gpu_mode = USAR_GPU_EXTERNA

    @classmethod
    def get_llm(cls, model_type: str):
        model_type = model_type.strip().lower()
        cache = sys.modules["AIDA_LLM_CACHE"]

        # opuesto = "nlp" if model_type in ["sql", "data"] else "sql"
        # if opuesto in cache:
        #     print(f"\n[ENGINE ANTI-APAGON] Peligro de VRAM. Matando {opuesto.upper()} antes de invocar a {model_type.upper()}...")
        #     cls.unload_llm(opuesto)
        
        if model_type in cache and cache[model_type] is not None:
            return cache[model_type]

        from llama_cpp import Llama

        target_path = MODEL_SQL_PATH if model_type == "sql" else MODEL_NLP_PATH
        print(f"\n[ENGINE] Inicializando modelo: {model_type.upper()}")

        if not os.path.exists(target_path):
            print(f"[ENGINE WARNING] Falta modelo: {target_path}. Se omitirá su carga.")
            return None

        try:
            print(f"[ENGINE] Cargando '{target_path}' en {'GPU RTX 5090' if cls._is_gpu_mode else 'CPU'}...")
            
            # Configuración de contexto (KV Cache)
            ctx_size = 2048 if model_type in ["sql", "data"] else 8192

            batch_size = 256 if cls._is_gpu_mode else 128

            llm_instance = Llama(
                model_path=target_path,
                n_gpu_layers=-1 if cls._is_gpu_mode else 0, # -1 FORZA todo a la VRAM de la 5090
                n_ctx=ctx_size,                             # Contexto reducido para no explotar la RAM
                n_batch=batch_size,                                # Batch más seguro para el puente RAM-VRAM
                use_mmap=False,                             # PROHIBE a Windows usar RAM como buffer de disco
                offload_kqv=True if cls._is_gpu_mode else False, # Mueve la memoria de conversación a la GPU
                flash_attn=True,  # Acelera en GPUs modernas
                verbose=False
            )
            
            cache[model_type] = llm_instance
            print(f"[ENGINE] Modelo {model_type.upper()} cargado EXITOSAMENTE en VRAM.")
            
            return llm_instance
            
        except Exception as e:
            print(f"[ENGINE] Error crítico cargando modelo {model_type}: {e}")
            raise e
        


    @classmethod
    def unload_llm(cls, model_type: str):
        """
        Libera la VRAM descargando el modelo especificado.
        """
        model_type = model_type.strip().lower()
        cache = sys.modules["AIDA_LLM_CACHE"]
        if model_type in cache:
            print(f"\n[ENGINE] Liberando VRAM: Descargando modelo {model_type.upper()}...")
            del cache[model_type]
            import gc
            gc.collect()
            print(f"[ENGINE] VRAM liberada.\n")



    @classmethod
    def generate(cls, messages: list, model_type="nlp", temperature=0.7) -> str:
        #print(f"\n[ENGINE DEBUG] Entrando a generate(). Model_type: {model_type}")

        # Validacion anti access-violation 0x00000000
        if not messages or not isinstance(messages, list):
            #print("[ENGINE ERROR] Messages es nulo o no es una lista.")
            raise ValueError("Messages list is empty or invalid.")
        
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                print(f"[ENGINE ERROR] El mensaje en índice {idx} no es un diccionario.")
            if "content" not in msg or msg["content"] is None:
                #print(f"[ENGINE ERROR] El mensaje en índice {idx} tiene un content NULO.")
                # Parche temporal de emergencia si viene nulo
                msg["content"] = ""

        #print(f"[ENGINE DEBUG] Validación de mensajes pasada. LLamando a get_llm()")
        llm = cls.get_llm(model_type)
        if llm is None:
            return "Error: El modelo no está disponible."
        
        stop_words = None
        max_tokens_run = 1024
        final_temp = temperature

        if model_type.strip().lower() in ["data", "sql"]:
            #print("[ENGINE DEBUG] Reseteando KV Cache para SQL.")
            llm.reset()
            final_temp = 0.0  
            max_tokens_run = 300 
            stop_words = ["```", "```sql", "Para ", "En este", "Explicación", "Explanation:", "Aquí tienes", "El SQL"]

        #print(f"[ENGINE DEBUG] Enviando solicitud a llama_cpp.create_chat_completion...")
            
        try:
            output = llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens_run, 
                temperature=final_temp,
                stop=stop_words 
            )
            #print(f"[ENGINE DEBUG] Generación exitosa.")
            result = output["choices"][0]["message"]["content"]

            # # Si el modelo que acaba de responder es Qwen (SQL), lo descargamos de inmediato
            # if model_type.strip().lower() in ["data", "sql"]:
            #     cls.unload_llm("sql")

            return result        

        except Exception as e:
            print(f"[ENGINE ERROR FATAL DURANTE INFERENCIA]: {e}")
            if model_type.strip().lower() in ["data", "sql"]:
                cls.unload_llm("sql")
            raise e

def generate_response(messages: list, model_type="nlp") -> str:
    safe_type = model_type.strip().lower()
    temp = 0.0 if safe_type == "sql" else 0.7
    return HybridEngine.generate(messages, model_type=safe_type, temperature=temp)

if os.environ.get("AIDA_LLMS_PRELOADED") != "1":
    os.environ["AIDA_LLMS_PRELOADED"] = "1"
    print("\n[PRE-CARGA] Iniciando carga de LLMs en VRAM...")
    
    # Solo cargamos NLP de inicio. DATA se cargará solo si el agente Data lo pide.
    # Esto salva inmediatamente unos ~9GB de tu RAM al arrancar.
    print("[PRE-CARGA] 1/2: Asignando memoria para NLP (Llama 3.1)...")
    HybridEngine.get_llm("nlp")

    print("[PRE-CARGA] 2/2: Asignando memoria para DATA (Qwen 2.5)...")
    # Comentamos la carga automática de Qwen (DATA) 
    HybridEngine.get_llm("sql") 
    
    print("[PRE-CARGA] Carga inicial completada (Modo ahorro de RAM).\n")
