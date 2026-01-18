from image_logic import process

payload = {
  "action": "extract_text",
  "file_path": "dummy_document.pdf",
  "config": {"use_ocr": True, "language": "es", "max_pages": 5}
}

print(process(payload))

payload_image = {
  "action": "extract_text",
  "file_path": "dummy_ocr_image.png",
  "config": {"use_ocr": True, "language": "es", "max_pages": 5}
}

print(process(payload_image))