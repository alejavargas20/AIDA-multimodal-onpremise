
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
        # 1. Normalizamos a minúsculas para evitar el bug de "SQL" vs "sql"
        model_type = model_type.strip().lower()
        
        # 2. Consultamos la memoria global de Python
        cache = sys.modules["AIDA_LLM_CACHE"]
        
        # Si ya está en la VRAM, lo devolvemos al instante
        if model_type in cache and cache[model_type] is not None:
            return cache[model_type]

        from llama_cpp import Llama

        target_path = MODEL_SQL_PATH if model_type == "sql" else MODEL_NLP_PATH
        print(f"\n[ENGINE] Inicializando modelo: {model_type.upper()}")

        if not os.path.exists(target_path):
            print(f"[ENGINE WARNING] Falta modelo: {target_path}. Se omitirá su carga inicial.")
            return None

        try:
            print(f"[ENGINE] Cargando '{target_path}' en {'GPU RTX 5090' if cls._is_gpu_mode else 'CPU'}...")
            
            # Inicialización optimizada
            llm_instance = Llama(
                model_path=target_path,
                n_gpu_layers=-1 if cls._is_gpu_mode else 0, 
                n_ctx=8192 if cls._is_gpu_mode else 2048,
                n_batch=2048 if cls._is_gpu_mode else 256, 
                use_mmap=True, 
                offload_kqv=True if cls._is_gpu_mode else False,
                flash_attn=True if cls._is_gpu_mode else False, 
                n_threads=4, 
                verbose=False
            )
            
            # Lo guardamos en el candado global
            cache[model_type] = llm_instance
            print(f"[ENGINE] Modelo {model_type.upper()} cargado y residente en VRAM.")
            
            return llm_instance
            
        except Exception as e:
            print(f"[ENGINE] Error crítico cargando modelo {model_type}: {e}")
            raise e

    # @classmethod
    # def generate(cls, messages: list, model_type="nlp", temperature=0.7) -> str:
    #     llm = cls.get_llm(model_type)
    #     if llm is None:
    #         return "Error: El modelo no está disponible."
            
    #     output = llm.create_chat_completion(
    #         messages=messages,
    #         max_tokens=1024, 
    #         temperature=temperature
    #     )
    #     return output["choices"][0]["message"]["content"]

    @classmethod
    def generate(cls, messages: list, model_type="nlp", temperature=0.7) -> str:
        llm = cls.get_llm(model_type)
        if llm is None:
            return "Error: El modelo no está disponible."
            
        # Forzamos a Qwen a olvidar consultas anteriores 
        if model_type.strip().lower() == "data":
            llm.reset()
            
        output = llm.create_chat_completion(
            messages=messages,
            max_tokens=1024, 
            temperature=temperature
        )
        return output["choices"][0]["message"]["content"]

def generate_response(messages: list, model_type="nlp") -> str:
    safe_type = model_type.strip().lower()
    temp = 0.1 if safe_type == "sql" else 0.7
    return HybridEngine.generate(messages, model_type=safe_type, temperature=temp)

# PRE-CARGA DE LLMs (EAGER LOADING)
if os.environ.get("AIDA_LLMS_PRELOADED") != "1":
    os.environ["AIDA_LLMS_PRELOADED"] = "1"
    print("\n[PRE-CARGA] Iniciando carga de LLMs en VRAM...")
    HybridEngine.get_llm("nlp")
    HybridEngine.get_llm("sql")
    print("[PRE-CARGA] Todos los LLMs están listos.\n")

