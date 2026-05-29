"""
src/core/dvr/dahua_sdk.py
Estrategia Dahua via NetSDK nativo (ctypes).
Puerto por defecto: 37777.

Requiere DLL en: src/sdk/dahua/dhnetsdk.dll
"""
import ctypes
import ctypes.util
import os
import platform
import sys
from pathlib import Path

from .base import DVRStrategy, DeviceInfo, ChannelInfo

# ── Constantes ───────────────────────────────────────────────
DH_DEV_SERIALNO_LEN  = 48
DH_COMMON_STRING_64  = 64
DH_CONFIG_CHANNELTITLE = 4


# ── Estructuras ctypes ───────────────────────────────────────

class NET_DEVICEINFO_Ex(ctypes.Structure):
    _pack_   = 1
    _fields_ = [
        ("sSerialNumber",    ctypes.c_char * DH_DEV_SERIALNO_LEN),
        ("nAlarmInPortNum",  ctypes.c_int),
        ("nAlarmOutPortNum", ctypes.c_int),
        ("nDiskNum",         ctypes.c_int),
        ("nDVRType",         ctypes.c_int),
        ("nChanNum",         ctypes.c_int),
        ("byLimitLoginTime", ctypes.c_byte),
        ("byLeftLogTimes",   ctypes.c_byte),
        ("byRes",            ctypes.c_byte * 2),
        ("bNewWordLen",      ctypes.c_bool),
        ("byPasswordVersion",ctypes.c_byte),
        ("byRes1",           ctypes.c_byte * 2),
        ("stuVideoInputChanS", ctypes.c_int),
    ]


class DHDEV_CHANNEL_CFG(ctypes.Structure):
    _pack_   = 1
    _fields_ = [
        ("szChannelName",  ctypes.c_char * DH_COMMON_STRING_64),
        ("szManufacturer", ctypes.c_char * DH_COMMON_STRING_64),
        ("szTypeNo",       ctypes.c_char * DH_COMMON_STRING_64),
        ("byRes",          ctypes.c_byte * 64),
    ]


# ── Estrategia ───────────────────────────────────────────────

class DahuaSDKStrategy(DVRStrategy):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sdk      = None
        self._login_id = 0

    def _load_sdk(self):
        sdk_path = Path(self.sdk_path) if self.sdk_path else None

        if not sdk_path or not sdk_path.is_file():
            base = Path(sys.argv[0]).parent
            for candidate in [
                base / "sdk" / "dahua" / "dhnetsdk.dll",
                base.parent / "sdk" / "dahua" / "dhnetsdk.dll",
                Path("src/sdk/dahua/dhnetsdk.dll"),
            ]:
                if candidate.exists():
                    sdk_path = candidate
                    break
            else:
                raise FileNotFoundError(
                    "No se encontró dhnetsdk.dll.\n\n"
                    "Copia las DLLs de Dahua NetSDK a:\n"
                    "  src/sdk/dahua/\n\n"
                    "O indica la ruta en el campo 'Ruta SDK'."
                )

        lib_dir = str(sdk_path.parent.resolve())
        if platform.system() == "Windows":
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(lib_dir)
            else:
                os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")

        try:
            if platform.system() == "Windows":
                return ctypes.WinDLL(str(sdk_path.resolve()))
            return ctypes.CDLL(str(sdk_path.resolve()))
        except OSError as e:
            raise FileNotFoundError(
                f"No se pudo cargar dhnetsdk.dll:\n{e}\n\n"
                "Verifica que dhnetsdk.dll, dhconfigsdk.dll y dhplay.dll\n"
                "estén todos en src/sdk/dahua/"
            )

    def _init_sdk(self):
        self._sdk.CLIENT_Init.restype = ctypes.c_bool
        self._sdk.CLIENT_Init(None, 0)
        try:
            self._sdk.CLIENT_SetConnectTime(3000, 3)
        except Exception:
            pass

    def _login(self):
        dev_info = NET_DEVICEINFO_Ex()
        err_code = ctypes.c_int(0)
        self._sdk.CLIENT_LoginEx2.restype = ctypes.c_long

        login_id = self._sdk.CLIENT_LoginEx2(
            self.host.encode(),
            self.port,
            self.username.encode(),
            self.password.encode(),
            0,
            None,
            ctypes.byref(dev_info),
            ctypes.byref(err_code),
        )
        if not login_id:
            self._raise_error(err_code.value)
        return login_id, dev_info

    def _logout(self):
        if self._sdk and self._login_id:
            self._sdk.CLIENT_Logout(self._login_id)
            self._login_id = 0

    def _cleanup(self):
        self._logout()
        if self._sdk:
            try:
                self._sdk.CLIENT_Cleanup()
            except Exception:
                pass

    def get_device_info(self) -> DeviceInfo:
        self._sdk = self._load_sdk()
        self._init_sdk()
        try:
            login_id, dv  = self._login()
            self._login_id = login_id
            return self._build_info(login_id, dv)
        finally:
            self._cleanup()

    def _build_info(self, login_id: int, dv: NET_DEVICEINFO_Ex) -> DeviceInfo:
        info = DeviceInfo(brand="Dahua SDK", ip_address=self.host)
        info.serial_number      = dv.sSerialNumber.decode(errors="replace").rstrip("\x00")
        info.num_video_channels = int(dv.nChanNum)

        ch_arr   = (DHDEV_CHANNEL_CFG * max(info.num_video_channels, 1))()
        ret_size = ctypes.c_int(0)
        got      = self._sdk.CLIENT_GetDevConfig(
            login_id, DH_CONFIG_CHANNELTITLE, 0,
            ctypes.byref(ch_arr), ctypes.sizeof(ch_arr),
            ctypes.byref(ret_size),
        )

        for i in range(info.num_video_channels):
            ch_num = i + 1
            if got and i < len(ch_arr):
                ch_name = ch_arr[i].szChannelName.decode(errors="replace").rstrip("\x00")
            else:
                ch_name = f"Canal {ch_num}"
            info.channels.append(ChannelInfo(
                id        = str(ch_num),
                name      = ch_name or f"Canal {ch_num}",
                rtsp_main = self.build_rtsp_url(ch_num, False),
                rtsp_sub  = self.build_rtsp_url(ch_num, True),
            ))

        info.model = "Dahua DVR/NVR"
        return info

    def _raise_error(self, code: int):
        errors = {
            1:   "Parámetro inválido.",
            4:   "Contraseña incorrecta.",
            5:   "Usuario bloqueado.",
            6:   "Máximo de conexiones alcanzado.",
            516: "Timeout. Verifica IP y puerto 37777.",
            783: "Error de conexión TCP.",
        }
        msg = errors.get(code, f"Error NetSDK código {code}.")
        raise ConnectionError(f"Dahua NetSDK [{code}]: {msg}")

    def build_rtsp_url(self, channel: int, sub_stream: bool = False) -> str:
        st = 1 if sub_stream else 0
        return (
            f"rtsp://{self.username}:{self.password}"
            f"@{self.host}:554/cam/realmonitor?channel={channel}&subtype={st}"
        )
