"""
get_and_test.py - Lee credenciales del almacenamiento de la app y prueba el stream.
Ejecutar desde la carpeta del proyecto: python get_and_test.py
"""
import sys, subprocess
sys.path.insert(0, "src")

# 1. Leer dispositivo guardado
print("1. Leyendo dispositivos guardados...")
from models.dvr_storage import DVRRepository
repo    = DVRRepository()
devices = repo.all()

if not devices:
    print("No hay dispositivos. Guarda primero desde la app.")
    sys.exit(1)

# Buscar Hik-Connect
dev = next((d for d in devices if "Hik-Connect" in d.brand), devices[0])
print(f"   {dev.alias} | {dev.brand} | canales={dev.num_channels}")

# 2. Obtener URL fresca con las credenciales guardadas
print("\n2. Obteniendo URL fresca...")
from core.dvr.hikconnect import HikConnectStrategy
s = HikConnectStrategy(
    host=dev.host, port=dev.port,
    username=dev.username, password=dev.password, timeout=30,
)
info = s.get_device_info()

url = None
for ch in info.channels:
    if ch.status == "active" and ch.rtsp_main:
        url = ch.rtsp_main
        print(f"   Canal: {ch.name}")
        print(f"   URL:   {url}")
        break

if not url:
    print("Sin URL disponible.")
    sys.exit(1)

# 3. Probar con FFmpeg
print("\n3. Probando con FFmpeg...")
r = subprocess.run(
    ["ffmpeg", "-allowed_extensions", "ALL",
     "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
     "-i", url, "-t", "10", "-f", "null", "-"],
    capture_output=True, text=True, timeout=35,
)
print(f"   Return code: {r.returncode}")
if r.returncode == 0:
    print("✅ FUNCIONA")
    for line in r.stderr.split("\n"):
        if any(k in line for k in ["Video:", "Duration", "fps"]):
            print(f"   {line.strip()}")
else:
    print("❌ Error:")
    for line in r.stderr.strip().split("\n")[-8:]:
        print(f"   {line}")
