"""
src/core/dvr/hikconnect.py — Hik-Connect for Teams OpenAPI V2.14.0
"""
from __future__ import annotations
import requests
from .base import DVRStrategy, DeviceInfo, ChannelInfo

_REGION_HOSTS = [
    "https://isa.hikcentralconnect.com",
    "https://ius.hikcentralconnect.com",
    "https://ieu.hikcentralconnect.com",
    "https://isgp.hikcentralconnect.com",
]

_TOKEN_PATH   = "/api/hccgw/platform/v1/token/get"
_DEVICES_PATH = "/api/hccgw/resource/v1/devices/get"
_CAMERAS_PATH = "/api/hccgw/resource/v1/areas/cameras/get"
_LIVE_PATH    = "/api/hccgw/video/v1/live/address/get"


def _safe_json(resp) -> dict:
    try:
        t = resp.text.strip()
        if not t or t.startswith("<"):
            return {}
        return resp.json()
    except Exception:
        return {}


class HikConnectStrategy(DVRStrategy):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token: str | None = None
        self._area_domain: str | None = None
        self._debug_log: list[str] = []

    @property
    def _app_key(self): return self.username.strip()
    @property
    def _app_secret(self): return self.password.strip()

    @property
    def _base(self) -> str:
        return (self._area_domain or _REGION_HOSTS[0]).rstrip("/")

    def _h(self, token=False) -> dict:
        h = {"Content-Type": "application/json"}
        if token and self._token:
            h["Token"] = self._token
        return h

    def _log(self, msg): self._debug_log.append(msg)

    # ── Token ─────────────────────────────────────────────────

    def _get_token(self) -> str:
        hosts = list(_REGION_HOSTS)
        user = self.host.strip() if self.host else ""
        if user and "hik-connect.com" not in user and user not in ("open.hikvision.com", ""):
            b = user if user.startswith("http") else f"https://{user}"
            if b not in hosts:
                hosts.insert(0, b)

        errors = []
        for base in hosts:
            try:
                r = requests.post(f"{base}{_TOKEN_PATH}",
                    json={"appKey": self._app_key, "secretKey": self._app_secret},
                    headers=self._h(), timeout=self.timeout)
                if "text/html" in r.headers.get("Content-Type", ""):
                    errors.append(f"{base} → HTML"); continue
                if r.status_code not in (200, 201):
                    errors.append(f"{base} → HTTP {r.status_code}"); continue
                d = _safe_json(r)
                if not d:
                    errors.append(f"{base} → vacío"); continue
                code = str(d.get("errorCode", "-1"))
                if code == "0":
                    inner = d.get("data") or {}
                    tok = inner.get("accessToken", "")
                    if not tok:
                        errors.append(f"{base} → token vacío"); continue
                    area = inner.get("areaDomain", "")
                    self._area_domain = area.rstrip("/") if area else base
                    self._log(f"✅ Token desde: {base}")
                    self._log(f"   areaDomain: {self._area_domain}")
                    return tok
                if code == "LAP300001":
                    errors.append(f"{base} → LAP300001"); continue
                raise PermissionError({
                    "OPEN300001": "AK/SK inválido.",
                    "OPEN300002": "API Secret incorrecto.",
                }.get(code, f"[{code}] {d.get('message', code)}"))
            except PermissionError: raise
            except Exception as e:
                errors.append(f"{base} → {e}"); continue
        raise ConnectionError("Sin token:\n" + "\n".join(f"  • {e}" for e in errors))

    # ── Dispositivos ─────────────────────────────────────────

    def _get_devices(self) -> list[dict]:
        try:
            r = requests.post(f"{self._base}{_DEVICES_PATH}",
                json={"pageIndex": 1, "pageSize": 100},
                headers=self._h(token=True), timeout=self.timeout)
            d = _safe_json(r)
            total = (d.get("data") or {}).get("totalCount", "?")
            devs  = (d.get("data") or {}).get("device", [])
            self._log(f"📦 Devices: HTTP {r.status_code} | code={d.get('errorCode')} "
                      f"| total={total} | devs={len(devs)}")
            return devs
        except Exception as e:
            self._log(f"📦 Devices error: {e}")
            return []

    # ── Cámaras por serial ────────────────────────────────────

    def _get_cameras_by_serial(self, serial: str) -> list[dict]:
        """Busca cámaras pasando deviceSerialNo — evita el bug de areaID."""
        try:
            payload = {
                "pageIndex": 1,
                "pageSize":  200,
                "filter": {"deviceSerialNo": serial},
            }
            r = requests.post(f"{self._base}{_CAMERAS_PATH}",
                json=payload, headers=self._h(token=True), timeout=self.timeout)
            d    = _safe_json(r)
            code = str(d.get("errorCode", "-1"))
            cams = (d.get("data") or {}).get("camera", [])
            total = (d.get("data") or {}).get("totalCount", "?")
            self._log(f"   📷 serial={serial}: HTTP {r.status_code} "
                      f"| code={code} | total={total} | cams={len(cams)}")
            return cams if code == "0" else []
        except Exception as e:
            self._log(f"   📷 serial={serial} error: {e}")
            return []

    def _get_cameras_no_filter(self) -> list[dict]:
        """Intenta sin ningún filtro — algunos servidores lo aceptan."""
        try:
            payload = {"pageIndex": 1, "pageSize": 200, "filter": {}}
            r = requests.post(f"{self._base}{_CAMERAS_PATH}",
                json=payload, headers=self._h(token=True), timeout=self.timeout)
            d    = _safe_json(r)
            code = str(d.get("errorCode", "-1"))
            cams = (d.get("data") or {}).get("camera", [])
            total = (d.get("data") or {}).get("totalCount", "?")
            self._log(f"   📷 sin filtro: HTTP {r.status_code} "
                      f"| code={code} | total={total} | cams={len(cams)}")
            return cams if code == "0" else []
        except Exception as e:
            self._log(f"   📷 sin filtro error: {e}")
            return []

    # ── Live URL ──────────────────────────────────────────────

    def _get_live_url(self, resource_id: str, serial: str, quality: int = 1) -> str:
        try:
            r = requests.post(f"{self._base}{_LIVE_PATH}",
                json={"deviceSerial": serial, "resourceId": resource_id,
                      "type": "1", "protocol": 2, "quality": quality,   # 2=HLS (port 443), 3=RTMP (port 1935 bloqueado)
                      "expireTime": 3600},
                headers=self._h(token=True), timeout=self.timeout)
            d    = _safe_json(r)
            code = str(d.get("errorCode", "-1"))
            if code == "0":
                url = (d.get("data") or {}).get("url", "")
                return url
            else:
                # Log error codes para diagnóstico
                msg = d.get("message", code)
                self._log(f"   ⚠ live URL error [{code}] rid={resource_id[:8]} "
                          f"serial={serial} q={quality}: {msg}")
        except Exception as e:
            self._log(f"   ⚠ live URL excepción: {e}")
        return ""

    # ── get_device_info ───────────────────────────────────────

    def get_device_info(self) -> DeviceInfo:
        self._debug_log = []
        self._token = self._get_token()

        # 1. Obtener dispositivos (con serial de cada uno)
        devices = self._get_devices()

        # 2. Buscar cámaras por serial de cada dispositivo
        cameras: list[dict] = []
        serials = [d.get("serialNo", "") for d in devices if d.get("serialNo")]

        self._log(f"🔎 Buscando cámaras por serial para: {serials}")
        for serial in serials:
            cams = self._get_cameras_by_serial(serial)
            cameras.extend(cams)

        # 3. Si no encontró por serial, intentar sin filtro
        if not cameras:
            self._log("🔎 Intentando sin filtro...")
            cameras = self._get_cameras_no_filter()

        # 4. DeviceInfo
        info = DeviceInfo(brand="Hik-Connect", ip_address=self._base)
        if devices:
            d = devices[0]
            info.model            = d.get("type", "DVR/NVR")
            info.serial_number    = d.get("serialNo", "")
            info.device_name      = d.get("name", "")
            info.firmware_version = d.get("version", "")
            info.extra["total_devices"] = len(devices)
            info.extra["devices"] = [
                f"{dv.get('name','')} ({dv.get('serialNo','')}) "
                f"online={dv.get('onlineStatus','?')}"
                for dv in devices
            ]
        info.extra["debug"] = self._debug_log
        info.num_video_channels = len(cameras)

        for i, cam in enumerate(cameras, 1):
            rid       = cam.get("id", "")
            ch_name   = cam.get("name", f"Canal {i}")
            online    = str(cam.get("online", "1"))
            dev_inf   = cam.get("device", {}).get("devInfo", {})
            dev_ser   = dev_inf.get("serialNo", "")
            ch_info   = cam.get("device", {}).get("channelInfo", {})
            ch_no     = str(ch_info.get("id", i))

            # Solo obtener URL para canales online (ahorra tiempo)
            if online == "1":
                rtsp_main = self._get_live_url(rid, dev_ser, quality=1)
                rtsp_sub  = self._get_live_url(rid, dev_ser, quality=2)
                if rtsp_main:
                    self._log(f"   🎬 {ch_name}: {rtsp_main[:90]}...")
                else:
                    self._log(f"   ❌ {ch_name}: SIN URL")
            else:
                rtsp_main = ""
                rtsp_sub  = ""

            info.channels.append(ChannelInfo(
                id=rid or str(i), name=ch_name,
                status="active" if online == "1" else "inactive",
                rtsp_main=rtsp_main, rtsp_sub=rtsp_sub,
            ))

        return info

    def build_rtsp_url(self, channel: int, sub_stream: bool = False) -> str:
        return f"[Hik-Connect URL dinámica — canal {channel}]"
