"""
src/core/dvr/hikvision_sdk.py
Estrategia Hikvision via HCNetSDK nativo (ctypes).
Puerto por defecto: 8000.

Requiere DLL en: src/sdk/hikvision/HCNetSDK.dll
"""
import ctypes
import ctypes.util
import os
import platform
import sys
from pathlib import Path

from .base import DVRStrategy, DeviceInfo, ChannelInfo

# ── Constantes ───────────────────────────────────────────────
SERIALNO_LEN        = 48
NET_DVR_MAX_NAMELEN = 16
DEV_TYPE_NAME_LEN   = 24
GET_DEVICECFG_V40   = 1062


# ── Estructuras ctypes ───────────────────────────────────────

class NET_DVR_DEVICEINFO_V30(ctypes.Structure):
    _pack_   = 1
    _fields_ = [
        ("sSerialNumber",      ctypes.c_byte  * SERIALNO_LEN),
        ("byAlarmInPortNum",   ctypes.c_byte),
        ("byAlarmOutPortNum",  ctypes.c_byte),
        ("byDiskNum",          ctypes.c_byte),
        ("byDVRType",          ctypes.c_byte),
        ("byChanNum",          ctypes.c_byte),
        ("byStartChan",        ctypes.c_byte),
        ("byAudioChanNum",     ctypes.c_byte),
        ("byIPChanNum",        ctypes.c_byte),
        ("byZeroChanNum",      ctypes.c_byte),
        ("byMainProto",        ctypes.c_byte),
        ("bySubProto",         ctypes.c_byte),
        ("bySupport",          ctypes.c_byte),
        ("bySupport1",         ctypes.c_byte),
        ("bySupport2",         ctypes.c_byte),
        ("wDevType",           ctypes.c_uint16),
        ("bySupport3",         ctypes.c_byte),
        ("byMultiStreamProto", ctypes.c_byte),
        ("byStartDChan",       ctypes.c_byte),
        ("byStartDTalkChan",   ctypes.c_byte),
        ("byHighDChanNum",     ctypes.c_byte),
        ("bySupport4",         ctypes.c_byte),
        ("byLanguageType",     ctypes.c_byte),
        ("byVoiceInChanNum",   ctypes.c_byte),
        ("byStartVoiceInChanNo", ctypes.c_byte),
        ("byRes3",             ctypes.c_byte * 2),
        ("byMirrorChanNum",    ctypes.c_byte),
        ("wStartMirrorChanNo", ctypes.c_uint16),
        ("byRes2",             ctypes.c_byte * 2),
    ]


class NET_DVR_USER_LOGIN_INFO(ctypes.Structure):
    _pack_   = 1
    _fields_ = [
        ("sDeviceAddress", ctypes.c_char  * 129),
        ("byUseTransport", ctypes.c_byte),
        ("wPort",          ctypes.c_uint16),
        ("sUserName",      ctypes.c_char  * 64),
        ("sPassword",      ctypes.c_char  * 64),
        ("cbLoginResult",  ctypes.c_void_p),
        ("pUser",          ctypes.c_void_p),
        ("bUseAsynLogin",  ctypes.c_bool),
        ("byProxyType",    ctypes.c_byte),
        ("byUseUTCTime",   ctypes.c_byte),
        ("byLoginMode",    ctypes.c_byte),
        ("byHttps",        ctypes.c_byte),
        ("byProxyID",      ctypes.c_int32),
        ("byVerifyMode",   ctypes.c_byte),
        ("byRes3",         ctypes.c_byte * 119),
    ]


class NET_DVR_DEVICECFG_V40(ctypes.Structure):
    _pack_   = 1
    _fields_ = [
        ("dwSize",               ctypes.c_uint32),
        ("sDVRName",             ctypes.c_char  * NET_DVR_MAX_NAMELEN),
        ("dwDVRID",              ctypes.c_uint32),
        ("dwRecycleRecord",      ctypes.c_uint32),
        ("sSerialNumber",        ctypes.c_char  * SERIALNO_LEN),
        ("dwSoftwareVersion",    ctypes.c_uint32),
        ("dwSoftwareBuildDate",  ctypes.c_uint32),
        ("dwDSPSoftwareVersion", ctypes.c_uint32),
        ("dwDSPSoftwareBuildDate", ctypes.c_uint32),
        ("dwPanelVersion",       ctypes.c_uint32),
        ("dwPanelBuildDate",     ctypes.c_uint32),
        ("byIPChanNum",          ctypes.c_byte),
        ("byStartDChan",         ctypes.c_byte),
        ("byStartAudioDChan",    ctypes.c_byte),
        ("byIPChanNumHigh",      ctypes.c_byte),
        ("byLaneNum",            ctypes.c_byte),
        ("byRes1",               ctypes.c_byte * 3),
        ("dwHardwareVersion",    ctypes.c_uint32),
        ("dwHardwareBuildDate",  ctypes.c_uint32),
        ("sDVRType",             ctypes.c_char  * DEV_TYPE_NAME_LEN),
        ("dwCompatibleVersion",  ctypes.c_uint32),
        ("byBootVersion",        ctypes.c_uint32),
        ("byBootBuildDate",      ctypes.c_uint32),
        ("sRes",                 ctypes.c_char  * 64),
    ]


# ── Estrategia ───────────────────────────────────────────────

class HikvisionSDKStrategy(DVRStrategy):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sdk     = None
        self._user_id = -1

    # ── Carga DLL ────────────────────────────────────────────

    def _load_sdk(self):
        sdk_path = Path(self.sdk_path) if self.sdk_path else None

        if not sdk_path or not sdk_path.is_file():
            # Buscar en src/sdk/hikvision/ relativo al script
            base = Path(sys.argv[0]).parent
            for candidate in [
                base / "sdk" / "hikvision" / "HCNetSDK.dll",
                base.parent / "sdk" / "hikvision" / "HCNetSDK.dll",
                Path("src/sdk/hikvision/HCNetSDK.dll"),
            ]:
                if candidate.exists():
                    sdk_path = candidate
                    break
            else:
                raise FileNotFoundError(
                    "No se encontró HCNetSDK.dll.\n\n"
                    "Copia todas las DLLs de:\n"
                    "  EN-HCNetSDKV6.1.9.4_build20220412_win64\\lib\\\n"
                    "a la carpeta:\n"
                    "  src/sdk/hikvision/\n\n"
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
                f"No se pudo cargar HCNetSDK.dll:\n{e}\n\n"
                "Verifica que TODAS las DLLs de /lib estén en src/sdk/hikvision/"
            )

    # ── Init / Login / Logout ────────────────────────────────

    def _init_sdk(self):
        self._sdk.NET_DVR_Init.restype        = ctypes.c_bool
        self._sdk.NET_DVR_GetLastError.restype = ctypes.c_uint32
        self._sdk.NET_DVR_Login_V40.restype   = ctypes.c_long
        if not self._sdk.NET_DVR_Init():
            raise ConnectionError("NET_DVR_Init() falló.")
        self._sdk.NET_DVR_SetConnectTime(5000, 3)
        self._sdk.NET_DVR_SetReconnect(10000, True)

    def _login(self):
        login_info = NET_DVR_USER_LOGIN_INFO()
        dev_info   = NET_DVR_DEVICEINFO_V30()
        login_info.sDeviceAddress = self.host.encode("ascii")
        login_info.wPort          = self.port
        login_info.sUserName      = self.username.encode("ascii")
        login_info.sPassword      = self.password.encode("ascii")
        login_info.bUseAsynLogin  = False
        login_info.byLoginMode    = 0

        user_id = self._sdk.NET_DVR_Login_V40(
            ctypes.byref(login_info),
            ctypes.byref(dev_info),
        )
        if user_id < 0:
            self._raise_error(self._sdk.NET_DVR_GetLastError())
        return user_id, dev_info

    def _logout(self):
        if self._sdk and self._user_id >= 0:
            self._sdk.NET_DVR_Logout(ctypes.c_long(self._user_id))
            self._user_id = -1

    def _cleanup(self):
        self._logout()
        if self._sdk:
            try:
                self._sdk.NET_DVR_Cleanup()
            except Exception:
                pass

    # ── get_device_info ──────────────────────────────────────

    def get_device_info(self) -> DeviceInfo:
        self._sdk = self._load_sdk()
        self._init_sdk()
        try:
            user_id, dv  = self._login()
            self._user_id = user_id
            return self._build_info(user_id, dv)
        finally:
            self._cleanup()

    def _build_info(self, user_id: int, dv: NET_DVR_DEVICEINFO_V30) -> DeviceInfo:
        info = DeviceInfo(brand="Hikvision SDK", ip_address=self.host)

        info.serial_number      = bytes(dv.sSerialNumber).rstrip(b"\x00").decode(errors="replace")
        info.num_audio_channels = int(dv.byAudioChanNum)

        analog   = int(dv.byChanNum)
        ip_ch    = int(dv.byIPChanNum) + (int(dv.byHighDChanNum) << 8)
        total    = analog + ip_ch
        start    = int(dv.byStartChan)
        info.num_video_channels = total
        info.extra = {"analog": analog, "ip_channels": ip_ch}

        # Configuración extendida
        cfg        = NET_DVR_DEVICECFG_V40()
        cfg.dwSize = ctypes.sizeof(NET_DVR_DEVICECFG_V40)
        returned   = ctypes.c_uint32(0)

        ret = self._sdk.NET_DVR_GetDeviceConfig(
            ctypes.c_long(user_id),
            ctypes.c_uint32(GET_DEVICECFG_V40),
            ctypes.c_uint32(0),
            ctypes.byref(cfg),
            ctypes.c_uint32(ctypes.sizeof(cfg)),
            None,
            ctypes.byref(returned),
        )
        if ret:
            info.device_name    = cfg.sDVRName.decode(errors="replace").rstrip("\x00")
            info.model          = cfg.sDVRType.decode(errors="replace").rstrip("\x00")
            serial_cfg          = cfg.sSerialNumber.decode(errors="replace").rstrip("\x00")
            if serial_cfg:
                info.serial_number = serial_cfg
            v = cfg.dwSoftwareVersion
            info.firmware_version = (
                f"V{(v>>24)&0xFF}.{(v>>16)&0xFF}.{(v>>8)&0xFF}"
                f" build{cfg.dwSoftwareBuildDate}"
            )
        else:
            info.model = f"Hikvision DVR (tipo {int(dv.byDVRType)})"

        for i in range(total):
            ch_num = start + i
            info.channels.append(ChannelInfo(
                id        = str(ch_num),
                name      = f"Canal {ch_num}",
                rtsp_main = self.build_rtsp_url(ch_num, False),
                rtsp_sub  = self.build_rtsp_url(ch_num, True),
            ))
        return info

    def _raise_error(self, code: int):
        errors = {
            1:  "Parámetro inválido. Verifica IP y puerto 8000.",
            4:  "Límite de conexiones simultáneas alcanzado.",
            5:  "Contraseña incorrecta.",
            6:  "Usuario no existe.",
            17: "IP bloqueada por intentos fallidos.",
            23: "Función no soportada.",
            47: "Timeout. Verifica que el puerto 8000 esté abierto.",
            91: "Versión de SDK incompatible con el firmware.",
        }
        msg = errors.get(code, f"Error código {code}.")
        raise ConnectionError(f"HCNetSDK [{code}]: {msg}")

    def build_rtsp_url(self, channel: int, sub_stream: bool = False) -> str:
        s = 2 if sub_stream else 1
        return (
            f"rtsp://{self.username}:{self.password}"
            f"@{self.host}:554/Streaming/Channels/{channel:d}0{s}"
        )
