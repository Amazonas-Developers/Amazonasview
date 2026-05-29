"""
src/models/dvr_storage.py
Almacenamiento cifrado de dispositivos DVR.

• Cifrado Fernet (AES-128 + HMAC) derivado del hardware de la máquina.
• Guarda en: %APPDATA%/window_manager/dvr_devices.enc
"""
from __future__ import annotations

import base64
import json
import os
import platform
import socket
import uuid
from dataclasses import asdict, dataclass, field
from pathlib     import Path
from typing      import Dict, List, Optional

from cryptography.fernet              import Fernet
from cryptography.hazmat.primitives   import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

APP_NAME  = "window_manager"
FILE_NAME = "dvr_devices.enc"
_SALT     = b"DVRManager_Salt_2024_wm"


# ── Modelo de datos ───────────────────────────────────────────

@dataclass
class DVRDevice:
    id:           str  = field(default_factory=lambda: str(uuid.uuid4()))
    alias:        str  = ""
    brand:        str  = "Hikvision HTTP"
    host:         str  = ""
    port:         int  = 80
    username:     str  = ""
    password:     str  = ""
    sdk_path:     str  = ""
    num_channels: int  = 0
    channels:     List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DVRDevice":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def display_label(self) -> str:
        return self.alias or f"{self.host}:{self.port}"


# ── Cifrado ───────────────────────────────────────────────────

class _Cipher:
    @staticmethod
    def _machine_secret() -> bytes:
        hostname = socket.gethostname().encode()
        try:
            mac = str(uuid.getnode()).encode()
        except Exception:
            mac = b"00000000"
        return hostname + b":" + mac

    @classmethod
    def get_fernet(cls) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm  = hashes.SHA256(),
            length     = 32,
            salt       = _SALT,
            iterations = 100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(cls._machine_secret()))
        return Fernet(key)


# ── Repositorio ───────────────────────────────────────────────

class DVRRepository:
    """CRUD cifrado de DVRDevice."""

    def __init__(self):
        self._fernet  = _Cipher.get_fernet()
        self._path    = self._storage_path()
        self._devices: Dict[str, DVRDevice] = {}
        self._load()

    @staticmethod
    def _storage_path() -> Path:
        system = platform.system()
        if system == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home()))
        elif system == "Darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        folder = base / APP_NAME
        folder.mkdir(parents=True, exist_ok=True)
        return folder / FILE_NAME

    def _load(self):
        if not self._path.exists():
            return
        try:
            plain        = self._fernet.decrypt(self._path.read_bytes())
            data         = json.loads(plain.decode())
            self._devices = {
                did: DVRDevice.from_dict(dev)
                for did, dev in data.items()
            }
        except Exception:
            self._devices = {}

    def _save(self):
        data         = {did: dev.to_dict() for did, dev in self._devices.items()}
        plain        = json.dumps(data, ensure_ascii=False).encode()
        self._path.write_bytes(self._fernet.encrypt(plain))

    def all(self) -> List[DVRDevice]:
        return list(self._devices.values())

    def get(self, device_id: str) -> Optional[DVRDevice]:
        return self._devices.get(device_id)

    def add(self, device: DVRDevice) -> DVRDevice:
        self._devices[device.id] = device
        self._save()
        return device

    def update(self, device: DVRDevice) -> DVRDevice:
        self._devices[device.id] = device
        self._save()
        return device

    def remove(self, device_id: str) -> bool:
        if device_id in self._devices:
            del self._devices[device_id]
            self._save()
            return True
        return False

    def update_channels(self, device_id: str, channels: list, num: int):
        if device_id in self._devices:
            self._devices[device_id].channels    = channels
            self._devices[device_id].num_channels = num
            self._save()
