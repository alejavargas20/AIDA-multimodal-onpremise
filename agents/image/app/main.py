from schemas.image_models import ImageAgentRequest
from agents_module.image_agent import ImageAgent
from engines.ocr_engine import OcrEngine
from llm.llm_client import LlmClient

def build_agent() -> ImageAgent:
    return ImageAgent(ocr=OcrEngine(), llm=LlmClient())

def main():
    agent = build_agent()

    # Cambia la ruta por tu dummy pdf/imagen
    req = ImageAgentRequest(
        input_type="pdf",
        path="dummy_document.pdf",
        user_prompt="Extrae lo importante y dime qué tipo de documento es"
    )

    res = agent.run(req)
    print(res.model_dump())

if __name__ == "__main__":
    main()
