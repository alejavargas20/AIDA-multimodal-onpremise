import torch
import sys

print(f"Python Version: {sys.version}")
print(f"PyTorch Version: {torch.__version__}")
print("-" * 30)
print(f"¿CUDA disponible?: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"Cantidad de GPUs: {torch.cuda.device_count()}")
    print(f"GPU Actual: {torch.cuda.get_device_name(0)}")
    print(f"Versión de CUDA compilada: {torch.version.cuda}")
    
    # Prueba de fuego: Mover un tensor a la GPU
    try:
        x = torch.tensor([1.0, 2.0]).cuda()
        print("El tensor se movió a la memoria VRAM.")
    except Exception as e:
        print(f"ERROR: CUDA está disponible pero falló al usarlo: {e}")
else:
    print("ERROR: PyTorch NO está viendo tu tarjeta gráfica.")
    print("Estás usando la versión de CPU (lenta).")