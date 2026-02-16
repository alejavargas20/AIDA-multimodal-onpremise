# # aida-multimodal-onpremise/test.py

# import json
# import re
# from agents.local_engine import generate_response

# # 1. Cargar archivos
# # (Si fallan, el programa se detendrá con el error estándar de Python, como querías)
# with open('intent_json.json', encoding='utf-8') as f: intent_data = json.load(f)
# with open('tables_catalog.json', encoding='utf-8') as f: catalog = json.load(f)

# # Transformar a string para los prompts
# intent_json = json.dumps(intent_data, ensure_ascii=False, indent=2)
# tables_catalog = json.dumps(catalog, ensure_ascii=False, indent=2)

# print("\nEjecutando Paso 1 (Selección de tablas)...")

# # =================================================================================
# # PASO 1: Prompt de Selección
# # (He añadido el campo "schemas" en el ejemplo para que el Paso 2 funcione bien)
# # =================================================================================
# prompt_step1 = f"""
# Eres un experto en bases de datos. Del JSON de catálogo de tablas, extrae SOLO las tablas y campos relevantes para esta consulta.

# Consulta JSON:
# {intent_json}

# Catálogo completo:
# {tables_catalog}

# Responde en JSON estricto:
# {{
#     "relevant_tables": ["tabla1", "tabla2"],
#     "relevant_fields": {{
#         "tabla1": ["campo1", "campo2"],
#         "tabla2": ["campo3"]
#     }},
#     "schemas": {{ "tabla1": "nombre_esquema", "tabla2": "nombre_esquema" }},
#     "time_field": "nombre_campo_tiempo",
#     "reason": "breve explicación"
# }}
# No agregues nada más.
# """

# # Generar respuesta Paso 1
# raw_response_1 = generate_response([
#     {"role": "user", "content": prompt_step1}
# ])

# # Limpieza básica
# cleaned_response = re.sub(r"```json\s*|```", "", raw_response_1).strip()

# # Decodificar JSON (Sin fallback, si falla dará error aquí mismo)
# relevant_data = json.loads(cleaned_response)

# # Preparamos el string para el siguiente paso
# relevant_info_str = json.dumps(relevant_data, indent=2, ensure_ascii=False)

# print("\nEjecutando Paso 2 (Generación SQL con Esquemas)...")

# # =================================================================================
# # PASO 2: Prompt de SQL (Con las reglas estrictas de tu compañero)
# # =================================================================================
# prompt_step2 = f"""
# Eres un experto en SQL Server para analítica de desembolsos crediticios.
# Genera SOLO la consulta SQL. Sin explicaciones, sin markdown, sin bloques de código, sin comentarios.

# REGLA PRINCIPAL (SIEMPRE OBLIGATORIA):
# - Usa SIEMPRE el esquema de cada tabla según el campo "schema" del catálogo.
# - Ejemplos: cartera.desembolso, rcc.cosecha_sal, cartera.cierre
# - NUNCA uses solo el nombre de la tabla sin esquema.

# PASO 0 Lee y clasifica primero (no escribas esto):
# 1. Mira la pregunta principal: {json.loads(intent_json).get('optimized_prompt', 'no disponible')}
# 2. Determina el tipo de métrica mirando "concept", "aggregation.type", "numerator/denominator":
#     - Si es "suma", "monto total", "total desembolsado", "monto desembolsado" → suma simple → SOLO SUM(campo)
#     - Si es "porcentaje", "ratio", "% del monto", "proporción" → ratio → SUM(CASE WHEN ...) / SUM(...) * 100.0
#     - Si es "promedio", "media" → AVG(...)
#     - Si es "conteo", "cantidad", "número de" → COUNT(...)
#     - Si no está claro → infiere del "optimized_prompt" y qué pide el usuario
# 3. SI NO ES PORCENTAJE NI RATIO → NO uses CASE WHEN, NO dividas, NO multipliques por 100, NO uses ROUND

# Reglas generales (siempre):
# - Para "ultimo_mes": usa DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
# - Campo de monto por defecto: nMonto (en desembolso)
# - Campo temporal por defecto para último mes: nCosecha
# - Usa WHERE nCosecha = @ultimo_mes para filtrar último mes
# - Evita división entera → usa * 1.0 si es necesario (solo en ratios)
# - Un solo SELECT siempre que sea posible

# Reglas para filtros (muy importante):
# - Cuando el operador es "=" pero el valor parece ser una palabra o frase descriptiva (ej: "Sur", "Campaña", "Personal", "Refinanciamiento", "Capital de Trabajo"):
#     - Cambia automáticamente a LIKE '%valor%'
#     - Ejemplos:
#     - "Sur" → LIKE '%Sur%'
#     - "Campaña" → LIKE '%Campaña%'
#     - "PYME" → LIKE '%PYME%'
# - Solo usa = 'valor' si el valor es un código exacto, número o bandera (ej: 1, 0, "A", "05:Mensual")

# Reglas SOLO cuando sea porcentaje o ratio:
# - Usa SUM(CASE WHEN condición THEN nMonto ELSE 0 END) / NULLIF(SUM(nMonto), 0) * 100.0
# - Redondea solo porcentajes: ROUND(..., 2)
# - Pon el cálculo completo en el SELECT sin alias innecesarios

# JSON completo de la métrica:
# {intent_json}

# Tablas y campos relevantes (usa SOLO estos, con su esquema):
# {relevant_info_str}

# Ejemplos (copia el estilo exacto según el tipo):

# --- suma simple (monto total) ---
# DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
# SELECT SUM(nMonto) AS MontoTotalDesembolsado
# FROM cartera.desembolso
# WHERE nCosecha = @ultimo_mes;

# --- conteo simple ---
# DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
# SELECT COUNT(*) AS CantidadCreditos
# FROM cartera.desembolso
# WHERE nCosecha = @ultimo_mes;

# --- promedio ---
# DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
# SELECT AVG(nMonto) AS PromedioMonto
# FROM cartera.desembolso
# WHERE nCosecha = @ultimo_mes;

# --- porcentaje (solo cuando sea necesario) ---
# DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
# SELECT ROUND(SUM(CASE WHEN nPlazo > 36 THEN nMonto ELSE 0 END) * 100.0 / NULLIF(SUM(nMonto), 0), 2) AS PorcentajePlazoMayor36
# FROM cartera.desembolso
# WHERE nCosecha = @ultimo_mes;

# --- porcentaje en campaña (ejemplo de filtro con LIKE) ---
# DECLARE @ultimo_mes INT = (SELECT MAX(nCosecha) FROM cartera.desembolso);
# SELECT ROUND(
#     SUM(CASE WHEN cTipoCamp LIKE '%Campaña%' THEN nMonto ELSE 0 END) * 100.0 /
#     NULLIF(SUM(nMonto), 0),
#     2
# ) AS PorcentajeCampaña
# FROM cartera.desembolso
# WHERE nCosecha = @ultimo_mes;

# IMPORTANTE DECISIÓN FINAL:
# - Siempre califica las tablas con su esquema (ej: cartera.desembolso, rcc.cosecha_sal)
# - Si la métrica es suma, conteo o promedio → genera SOLO eso. Sin CASE, sin división, sin *100.
# - Si y solo si es porcentaje/ratio → entonces usa el patrón con CASE WHEN y *100.0
# - Sé lo más simple y directo posible.

# Ahora genera SOLO el SQL para esta consulta.
# """

# # Generar SQL Paso 2
# sql_generated = generate_response([
#     {"role": "user", "content": prompt_step2}
# ])

# # Limpieza final
# sql_final = re.sub(r"```sql\s*|```", "", sql_generated).strip()

# print("\n" + "="*60)
# print("RESULTADO SQL (Qwen 2.5 14B):")
# print("="*60)
# print(sql_final)
# print("="*60)