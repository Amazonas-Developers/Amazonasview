"""
src/core/dvr/dahua_http.py
Estrategia Dahua via CGI / RPC2 (HTTP + Digest Auth).
Puerto por defecto: 80.
Intenta CGI clásico primero; si falla usa RPC2 (firmware moderno).
"""
import requests
from requests.auth import HTTPDigestAuth
from .base import DVRStrategy, DeviceInfo, ChannelInfo

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WM-DVR/1.0)",
    "Connection": "close",
}


def _kv(text: str) -> str:
    return text.split("=", 1)[1].strip() if "=" in text else text.strip()


class DahuaHTTPStrategy(DVRStrategy):

    def _auth(self):
        return HTTPDigestAuth(self.username, self.password)

    def _cgi(self, action: str) -> str:
        r = requests.get(
            f"{self.base_http_url}/cgi-bin/magicBox.cgi?action={action}",
            auth=self._auth(), headers=_HEADERS, timeout=self.timeout,
        )
        self._check_http_status(r)
        return _kv(r.text.strip())

    def get_device_info(self) -> DeviceInfo:
        info = DeviceInfo(brand="Dahua", ip_address=self.host)
        try:
            info.model            = self._cgi("getDeviceType")
            info.serial_number    = self._cgi("getSerialNo")
            info.firmware_version = self._cgi("getSoftwareVersion")
            self._fill_channels_cgi(info)
        except Exception:
            self._fill_channels_rpc2(info)
        return info

    def _fill_channels_cgi(self, info: DeviceInfo):
        r = requests.get(
            f"{self.base_http_url}/cgi-bin/configManager.cgi"
            f"?action=getConfig&name=ChannelTitle",
            auth=self._auth(), headers=_HEADERS, timeout=self.timeout,
        )
        lines = [l for l in r.text.splitlines() if "ChannelTitle" in l and "Name" in l]
        if not lines:
            raise ConnectionError("Sin canales via CGI.")
        for i, line in enumerate(lines, 1):
            info.channels.append(ChannelInfo(
                id        = str(i),
                name      = _kv(line) or f"Canal {i}",
                rtsp_main = self.build_rtsp_url(i, False),
                rtsp_sub  = self.build_rtsp_url(i, True),
            ))
        info.num_video_channels = len(info.channels)

    def _fill_channels_rpc2(self, info: DeviceInfo):
        payload = {
            "method": "configManager.getConfig",
            "params": {"name": "ChannelTitle"},
            "id": 1,
        }
        r      = requests.post(
            f"{self.base_http_url}/RPC2",
            json=payload, auth=self._auth(), timeout=self.timeout,
        )
        titles = r.json().get("params", {}).get("table", {}).get("ChannelTitle", [])
        for i, ch in enumerate(titles, 1):
            name = ch.get("Name", f"Canal {i}") if isinstance(ch, dict) else f"Canal {i}"
            info.channels.append(ChannelInfo(
                id        = str(i),
                name      = name,
                rtsp_main = self.build_rtsp_url(i, False),
                rtsp_sub  = self.build_rtsp_url(i, True),
            ))
        info.num_video_channels = len(info.channels)

    def build_rtsp_url(self, channel: int, sub_stream: bool = False) -> str:
        st = 1 if sub_stream else 0
        return (
            f"rtsp://{self.username}:{self.password}"
            f"@{self.host}:554/cam/realmonitor?channel={channel}&subtype={st}"
        )
