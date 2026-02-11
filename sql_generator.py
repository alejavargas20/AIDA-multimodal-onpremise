"""
Módulo principal para generar SQL basado en intent y catalog.
"""

from __future__ import annotations
from typing import Any, Dict
import json

from loaders.json_loader import load_json_file
from engines.ollama_engine import call_ollama
from utils.helpers import parse_json_response
from schemas.payloads import AgentPayload

MODEL = 'mistral:latest'

def process(payload: AgentPayload) -> Dict[str, Any]:
    try:
        action = payload.get("action")
        if action != "generate_sql":
            return {"status": "error", "error": "Solo se soporta action='generate_sql'."}
        
        intent_path = payload.get("intent_path")
        catalog_path = payload.get("catalog_path")
        
        if not intent_path or not catalog_path:
            return {"status": "error", "error": "Falta intent_path o catalog_path."}
        
        intent_json = load_json_file(intent_path)
        tables_catalog = load_json_file(catalog_path)
        
        # Paso 1: Prompt para seleccionar tablas y campos relevantes
        prompt_step1 = f"""
        Eres un experto en bases de datos. Del JSON de catálogo de tablas, extrae SOLO las tablas y campos relevantes para esta consulta.

        Consulta JSON:
        {intent_json}

        Catálogo completo:
        {tables_catalog}

        Responde en JSON estricto:
        {{
          "relevant_tables": ["tabla1", "tabla2"],
          "relevant_fields": {{
            "tabla1": ["campo1", "campo2"],
            "tabla2": ["campo3"]
          }},
          "time_field": "nombre_campo_tiempo",
          "reason": "breve explicación"
        }}

        No agregues nada más.
        """
        
        response_step1 = call_ollama(MODEL, prompt_step1)
        raw_response = response_step1["message"]["content"].strip()
        relevant_data = parse_json_response(raw_response)
        relevant_info_str = json.dumps(relevant_data, indent=2, ensure_ascii=False)
        
        # Paso 2: Prompt para generar SQL (versión optimizada con esquema al inicio)
        prompt_step2 = f"""
        Eres un experto en SQL Server para analítica de desembolsos crediticios.
        Genera SOLO la consulta SQL. Sin explicaciones, sin markdown, sin bloques de código, sin comentarios.

        REGLA PRINCIPAL (SIEMPRE OBLIGATORIA):
        - Usa SIEMPRE el esquema de cada tabla según el campo "schema" del catálogo.
        - Ejemplos: cartera.desembolso, rcc.cosecha_sal, cartera.cierre
        - NUNCA uses solo el nombre de la tabla sin esquema.

        PASO 0 Lee y clasifica primero (no escribas esto):
        1. Mira la pregunta principal: {json.loads(intent_json).get('optimized_prompt', 'no disponible')}
        2. Determina el tipo de métrica mirando "concept", "aggregation.type", "numerator/denominator":
           - Si es "suma", "monto total", "total desembolsado", "monto desembolsado" → suma simple → SOLO SUM(campo)
           - Si es "porcentaje", "ratio", "% del monto", "proporción" → ratio → SUM(CASE WHEN ...) / SUM(...) * 100.0
           - Si es "promedio", "media" → AVG(...)
           - Si es "conteo", "cantidad", "número de" → COUNT(...)
           - Si no está claro → infiere del "optimized_prompt" y qué pide el usuario
        3. SI NO ES PORCENTAJE NI RATIO → NO uses CASE WHEN, NO dividas, NO multipliques por 100, NO uses ROUND

        Reglas generales (siempre):
        - Para "ultimo_mes": usa DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
        - Campo de monto por defecto: nMonto (en desembolso)
        - Campo temporal por defecto para último mes: nCosecha
        - Usa WHERE nCosecha = @ultimo_mes para filtrar último mes
        - Evita división entera → usa * 1.0 si es necesario (solo en ratios)
        - Un solo SELECT siempre que sea posible

        Reglas para filtros (muy importante):
        - Cuando el operador es "=" pero el valor parece ser una palabra o frase descriptiva (ej: "Sur", "Campaña", "Personal", "Refinanciamiento", "Capital de Trabajo"):
          - Cambia automáticamente a LIKE '%valor%'
          - Ejemplos:
            - "Sur" → LIKE '%Sur%'
            - "Campaña" → LIKE '%Campaña%'
            - "PYME" → LIKE '%PYME%'
        - Solo usa = 'valor' si el valor es un código exacto, número o bandera (ej: 1, 0, "A", "05:Mensual")

        Reglas SOLO cuando sea porcentaje o ratio:
        - Usa SUM(CASE WHEN condición THEN nMonto ELSE 0 END) / NULLIF(SUM(nMonto), 0) * 100.0
        - Redondea solo porcentajes: ROUND(..., 2)
        - Pon el cálculo completo en el SELECT sin alias innecesarios

        JSON completo de la métrica:
        {intent_json}

        Tablas y campos relevantes (usa SOLO estos, con su esquema):
        {relevant_info_str}

        Ejemplos (copia el estilo exacto según el tipo):

        --- suma simple (monto total) ---
        DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
        SELECT SUM(nMonto) AS MontoTotalDesembolsado
        FROM cartera.desembolso
        WHERE nCosecha = @ultimo_mes;

        --- conteo simple ---
        DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
        SELECT COUNT(*) AS CantidadCreditos
        FROM cartera.desembolso
        WHERE nCosecha = @ultimo_mes;

        --- promedio ---
        DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
        SELECT AVG(nMonto) AS PromedioMonto
        FROM cartera.desembolso
        WHERE nCosecha = @ultimo_mes;

        --- porcentaje (solo cuando sea necesario) ---
        DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
        SELECT ROUND(SUM(CASE WHEN nPlazo > 36 THEN nMonto ELSE 0 END) * 100.0 / NULLIF(SUM(nMonto), 0), 2) AS PorcentajePlazoMayor36
        FROM cartera.desembolso
        WHERE nCosecha = @ultimo_mes;

        --- porcentaje en campaña (ejemplo de filtro con LIKE) ---
        DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
        SELECT ROUND(
            SUM(CASE WHEN cTipoCamp LIKE '%Campaña%' THEN nMonto ELSE 0 END) * 100.0 /
            NULLIF(SUM(nMonto), 0),
            2
        ) AS PorcentajeCampaña
        FROM cartera.desembolso
        WHERE nCosecha = @ultimo_mes;

        IMPORTANTE DECISIÓN FINAL:
        - Siempre califica las tablas con su esquema (ej: cartera.desembolso, rcc.cosecha_sal)
        - Si la métrica es suma, conteo o promedio → genera SOLO eso. Sin CASE, sin división, sin *100.
        - Si y solo si es porcentaje/ratio → entonces usa el patrón con CASE WHEN y *100.0
        - Sé lo más simple y directo posible.

        Ahora genera SOLO el SQL para esta consulta.
        """
        
        response_step2 = call_ollama(MODEL, prompt_step2)
        sql_generated = response_step2["message"]["content"].strip()
        
        return {
            "status": "success",
            "sql": sql_generated
        }
    
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Para probar en el script
if __name__ == "__main__":
    test_payload = {
        "action": "generate_sql",
        "intent_path": "intent_json.json",
        "catalog_path": "tables_catalog.json"
    }
    result = process(test_payload)
    print(json.dumps(result, indent=2))