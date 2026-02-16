# # test.py
# import time
# from image_logic import process

# payload = {
#   "action": "extract_text",
#   "file_path": "ejemplo.pdf",
#   "config": {"use_ocr": True, "language": "es", "max_pages": 5}
# }

# start_time = time.time()

# resultado = process(payload)

# # payload_image = {
# #   "action": "extract_text",
# #   "file_path": "desembolsos_ultimo_mes_300dpi.png",
# #   "config": {"use_ocr": True, "language": "es", "max_pages": 5}
# # }

# # print(process(payload_image))

# # payload_image2 = {
# #   "action": "extract_text",
# #   "file_path": "desembolsos_ultimo_mes_letra_grande.png",
# #   "config": {"use_ocr": True, "language": "es", "max_pages": 5}
# # }

# #
# # print(process(payload_image2))

# end_time = time.time()
# duracion = end_time - start_time

# print(resultado) 
# print("\n" + "="*40)
# print(f"TIEMPO TOTAL: {duracion:.2f} segundos")
# print("="*40)