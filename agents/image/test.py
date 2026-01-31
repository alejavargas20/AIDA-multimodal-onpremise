from image_logic import process

payload = {
  "action": "extract_text",
  "file_path": "desembolsos_ultimo_mes.pdf",
  "config": {"use_ocr": True, "language": "es", "max_pages": 5}
}

print(process(payload))

payload_image = {
  "action": "extract_text",
  "file_path": "desembolsos_ultimo_mes_300dpi.png",
  "config": {"use_ocr": True, "language": "es", "max_pages": 5}
}

print(process(payload_image))