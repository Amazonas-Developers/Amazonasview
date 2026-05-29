"""
src/core/dvr/base.py
Clases base del patrón estrategia DVR.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChannelInfo:
    id:         str
    name:       str
    resolution: str = ""
    status:     str = "active"
    rtsp_main:  str = ""
    rtsp_sub:   str = ""

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "name":       self.name,
            "resolution": self.resolution,
            "status":     self.status,
            "rtsp_main":  self.rtsp_main,
            "rtsp_sub":   self.rtsp_sub,
        }


@dataclass
class DeviceInfo:
    brand:              str  = ""
    model:              str  = ""
    serial_number:      str  = ""
    firmware_version:   str  = ""
    device_name:        str  = ""
    mac_address:        str  = ""
    ip_address:         str  = ""
    num_video_channels: int  = 0
    num_audio_channels: int  = 0
    channels: List[ChannelInfo] = field(default_factory=list)
    extra:    dict              = field(default_factory=dict)

    def to_display_dict(self) -> dict:
        return {
            "Marca":              self.brand,
            "Modelo":             self.model,
            "Nombre dispositivo": self.device_name,
            "Dirección IP":       self.ip_address,
            "MAC":                self.mac_address,
            "Número de serie":    self.serial_number,
            "Firmware":           self.firmware_version,
            "Canales de video":   str(self.num_video_channels),
            "Canales de audio":   str(self.num_audio_channels),
        }


class DVRStrategy(ABC):
    """Interfaz base que deben implementar todas las estrategias."""

    def __init__(
        self,
        host:     str,
        port:     int,
        username: str,
        password: str,
        timeout:  int = 8,
        sdk_path: str = "",
    ):
        self.host     = host
        self.port     = port
        self.username = username
        self.password = password
        self.timeout  = timeout
        self.sdk_path = sdk_path

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """Conecta al dispositivo y retorna DeviceInfo completo."""

    @abstractmethod
    def build_rtsp_url(self, channel: int, sub_stream: bool = False) -> str:
        """Construye la URL RTSP para el canal indicado."""

    @property
    def base_http_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _check_http_status(self, response) -> None:
        code = response.status_code
        if code == 401:
            raise PermissionError("Credenciales incorrectas (HTTP 401).")
        if code == 403:
            raise PermissionError("Acceso denegado (HTTP 403).")
        if code == 404:
            raise ConnectionError("Endpoint no encontrado (HTTP 404). Verifica la marca seleccionada.")
        if code >= 400:
            raise ConnectionError(f"Error HTTP {code}.")
