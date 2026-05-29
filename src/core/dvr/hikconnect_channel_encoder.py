"""
src/core/dvr/hikconnect_channel_encoder.py
Codificador de canales Hik-Connect para serialización compatible.

Permite pasar canales Hik-Connect como datos serializados sin romper
compatibilidad con canales IP que se renderizarán desde ventanas.
"""
from __future__ import annotations
import json
import base64
from typing import Any


class HikConnectChannelEncoder:
    """
    Codifica/decodifica datos de canales Hik-Connect manteniendo
    compatibilidad con el formato de drag&drop existente.
    
    Formato serializado:
    {
        "device_alias": "Cuenta Hik-Connect",
        "channel_name": "Cámara Sala",
        "rtsp_main": "https://...",
        "rtsp_sub": "https://...",
        "channel_id": "resource_id",
        "device_serial": "SERIAL123",
        "is_hikconnect": True,
        "encrypted_key": "base64_encoded_key"
    }
    """
    
    @staticmethod
    def encode_channel(
        device_alias: str,
        channel_name: str,
        rtsp_main: str,
        rtsp_sub: str = "",
        channel_id: str = "",
        device_serial: str = "",
    ) -> dict:
        """
        Codifica un canal Hik-Connect con todos los metadatos necesarios.
        
        Returns:
            dict: Datos del canal listos para serializar/arrastrar.
        """
        return {
            "device_alias": device_alias,
            "channel_name": channel_name,
            "rtsp_main": rtsp_main,
            "rtsp_sub": rtsp_sub,
            "channel_id": channel_id,
            "device_serial": device_serial,
            "is_hikconnect": True,
            # Clave de encriptación (placeholder — en producción usar real)
            "encrypted_key": base64.b64encode(b"hik_channel_key").decode("ascii"),
        }

    @staticmethod
    def decode_channel(data: dict) -> dict:
        """
        Decodifica datos de un canal Hik-Connect.
        
        Retorna información del canal manteniendo compatibilidad.
        """
        if not isinstance(data, dict):
            raise ValueError("Canal debe ser un diccionario")
        
        is_hik = data.get("is_hikconnect", False)
        if not is_hik:
            raise ValueError("No es un canal Hik-Connect")
        
        return {
            "device_alias": data.get("device_alias", ""),
            "channel_name": data.get("channel_name", ""),
            "rtsp_main": data.get("rtsp_main", ""),
            "rtsp_sub": data.get("rtsp_sub", ""),
            "channel_id": data.get("channel_id", ""),
            "device_serial": data.get("device_serial", ""),
            "is_hikconnect": True,
        }

    @staticmethod
    def to_json(channel_data: dict) -> str:
        """Convierte canal a JSON para drag&drop."""
        try:
            return json.dumps(channel_data, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"No se puede serializar el canal: {e}")

    @staticmethod
    def from_json(json_str: str) -> dict:
        """Recupera canal desde JSON."""
        try:
            data = json.loads(json_str)
            return HikConnectChannelEncoder.decode_channel(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido: {e}")


class ChannelTypeDetector:
    """
    Detector automático del tipo de canal (IP vs Hik-Connect).
    """
    
    @staticmethod
    def is_hikconnect_channel(data: dict | Any) -> bool:
        """Determina si los datos corresponden a un canal Hik-Connect."""
        if not isinstance(data, dict):
            return False
        return data.get("is_hikconnect", False) is True

    @staticmethod
    def is_ip_channel(data: dict | Any) -> bool:
        """Determina si los datos corresponden a un canal por IP."""
        if not isinstance(data, dict):
            return False
        # Tiene propiedades típicas de IP pero no es Hik-Connect
        return not data.get("is_hikconnect", False)

    @staticmethod
    def get_channel_type(data: dict | Any) -> str:
        """Retorna 'hikconnect' o 'ip' o 'unknown'."""
        if not isinstance(data, dict):
            return "unknown"
        if data.get("is_hikconnect", False):
            return "hikconnect"
        if data.get("rtsp_main") or data.get("device_alias"):
            return "ip"
        return "unknown"
