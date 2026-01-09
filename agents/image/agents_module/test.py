from image_agent import build_image_agent, ImageAgentRequest

agent = build_image_agent()

# Probar PDF
req_pdf = ImageAgentRequest(
    input_type="pdf",
    path="dummy_document.pdf",
    user_prompt="Extrae los datos importantes y dime qué tipo de documento es"
)

res_pdf = agent.run(req_pdf)
print(res_pdf.model_dump())

# Probar imagen
req_img = ImageAgentRequest(
    input_type="image",
    path="dummy_image.png",
    user_prompt="Resume el contenido del documento"
)

res_img = agent.run(req_img)
print(res_img.model_dump())
