# Agente de Imagen

Este módulo implementa un **Agente de Imagen** dentro de un sistema multiagente, capaz de procesar **PDFs e imágenes (JPG/PNG)** para extraer texto y, opcionalmente, información estructurada mediante modelos de comprensión documental.

El agente está diseñado para ser llamado por un **MCP** u orquestador , exponiendo una única función pública:

```python
process(payload: dict) -> dict

# Flujo general
Imagen / PDF
   ↓
Conversión a imágenes (PDF → páginas)
   ↓
OCR (Tesseract)
   ↓
Texto bruto + JSON estructurado

# Estructura del proyecto
agents/image/
├── image_logic.py          # API pública: process(payload)
├── schemas/                # Modelos Pydantic (contrato MCP ↔ agente)
├── loaders/                # Carga de imágenes y PDFs
├── engines/                # OCR y detección (fase 1)
├── models/                 # Modelos IA (LayoutLMv3 opcional)
├── utils/                  # Normalización, heurísticas, ids
└── test.py                 # Script de prueba local

# Dependencias python
pip install -r requirements.txt

# Tesseract OCR (obligatorio)
Tesseract debe estar instalado a nivel de sistema.
Windows: instalar desde Tesseract OCR – UB Mannheim
Durante la instalación:
    Marcar Add Tesseract to PATH
    Instalar idiomas eng y spa

# Ejemplo de payload enviado por el MCP
{
  "action": "extract_text",
  "file_path": "dummy_document.pdf",
  "config": {
    "use_ocr": true,
    "language": "es",
    "max_pages": 5
  }
}

# Ejemplo de salida
{
  "status": "success",
  "normal_text": "Contenido del documento...",
  "metadata": {
    "page_count": 3,
    "file_type": "pdf",
    "used_ocr": true,
    "language": "es"
  }
}

