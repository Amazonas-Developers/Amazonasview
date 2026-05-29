"""
src/core/dvr/context.py
Contexto del Patrón Estrategia.

  Marca UI         Puerto   Protocolo
  ─────────────────────────────────────────────
  Hikvision HTTP   80       ISAPI REST + XML
  Hikvision SDK    8000     HCNetSDK.dll ctypes
  Dahua HTTP       80       CGI / RPC2
  Dahua SDK        37777    dhnetsdk.dll ctypes
"""
from __future__ import annotations
from .base           import DVRStrategy, DeviceInfo
from .hikvision_http import HikvisionHTTPStrategy
from .dahua_http     import DahuaHTTPStrategy
from .hikconnect     import HikConnectStrategy

# SDK: solo disponibles si la DLL existe
try:
    from .hikvision_sdk import HikvisionSDKStrategy
    _HIK_SDK = True
except Exception as _e:
    _HIK_SDK = False
    print(f"[DVR] Hikvision SDK no disponible: {_e}")

try:
    from .dahua_sdk import DahuaSDKStrategy
    _DAH_SDK = True
except Exception as _e:
    _DAH_SDK = False
    print(f"[DVR] Dahua SDK no disponible: {_e}")


class DVRContext:
    """
    Punto de entrada único del módulo DVR.
    Todos los métodos son @classmethod — no se instancia.

    Uso:
        info = DVRContext.connect("Hikvision HTTP", "192.168.1.64", 80, "admin", "pass")
        info = DVRContext.connect("Hikvision SDK",  "192.168.1.64", 8000, "admin", "pass",
                                  sdk_path="src/sdk/hikvision/HCNetSDK.dll")
    """

    _DEFAULT_PORTS: dict[str, int] = {
        "Hikvision HTTP": 80,
        "Hikvision SDK":  8000,
        "Dahua HTTP":     80,
        "Dahua SDK":      37777,
        "Hik-Connect":    443,  # No se usa realmente, pero para consistencia
    }

    _SDK_BRANDS = {"Hikvision SDK", "Dahua SDK"}

    @classmethod
    def _strategies(cls) -> dict[str, type[DVRStrategy]]:
        s: dict[str, type[DVRStrategy]] = {
            "Hikvision HTTP": HikvisionHTTPStrategy,
            "Dahua HTTP":     DahuaHTTPStrategy,
            "Hik-Connect":    HikConnectStrategy,
        }
        if _HIK_SDK:
            s["Hikvision SDK"] = HikvisionSDKStrategy
        if _DAH_SDK:
            s["Dahua SDK"] = DahuaSDKStrategy
        return s

    @classmethod
    def brands(cls) -> list[str]:
        """Lista para el ComboBox de la UI."""
        return list(cls._strategies().keys())

    @classmethod
    def default_port(cls, brand: str) -> int:
        return cls._DEFAULT_PORTS.get(brand, 80)

    @classmethod
    def needs_sdk(cls, brand: str) -> bool:
        return brand in cls._SDK_BRANDS

    @classmethod
    def connect(
        cls,
        brand:    str,
        host:     str,
        port:     int,
        username: str,
        password: str,
        timeout:  int = 8,
        sdk_path: str = "",
    ) -> DeviceInfo:
        """
        Crea la estrategia correcta y retorna DeviceInfo completo.

        Lanza:
            ValueError        → marca desconocida
            PermissionError   → credenciales incorrectas
            ConnectionError   → fallo de red o protocolo
            TimeoutError      → tiempo agotado
            FileNotFoundError → DLL no encontrada (SDK)
        """
        strategies  = cls._strategies()
        strategy_cls = strategies.get(brand)

        if strategy_cls is None:
            raise ValueError(
                f"Marca '{brand}' no reconocida.\n"
                f"Disponibles: {list(strategies.keys())}"
            )

        strategy: DVRStrategy = strategy_cls(
            host     = host,
            port     = port,
            username = username,
            password = password,
            timeout  = timeout,
            sdk_path = sdk_path,
        )
        return strategy.get_device_info()
