"""
get_url.py — Obtiene y muestra las URLs completas de Hik-Connect
Ejecutar desde la carpeta del proyecto: python get_url.py
"""
import sys
sys.path.insert(0, 'src')

from core.dvr.hikconnect import HikConnectStrategy

# ── Credenciales ──────────────────────────────────────────────
API_KEY    = "C31f0Ce2UNEnA0WAQhRACnPduUXIQ1Ak"
API_SECRET = "tYagGPNQsPlUu3npOEXwqPb6KP7bgggj"
# ─────────────────────────────────────────────────────────────

print("Conectando a Hik-Connect...")
s = HikConnectStrategy(
    host     = "isa.hik-connect.com",
    port     = 443,
    username = API_KEY,
    password = API_SECRET,
    timeout  = 30,
)

try:
    info = s.get_device_info()
    print(f"✅ {info.device_name} — {info.num_video_channels} canales\n")

    online = [ch for ch in info.channels if ch.status == "active" and ch.rtsp_main]
    print(f"Canales online con URL: {len(online)}\n")

    for ch in online[:5]:
        print(f"Canal: {ch.name}")
        print(f"  URL: {ch.rtsp_main}")
        print()

except Exception as e:
    print(f"Error: {e}")
