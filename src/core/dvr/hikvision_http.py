"""
src/core/dvr/hikvision_http.py
Estrategia Hikvision via ISAPI (HTTP + Digest Auth + XML).
Puerto por defecto: 80 u 8080.
"""
import xml.etree.ElementTree as ET
import requests
from requests.auth import HTTPDigestAuth
from .base import DVRStrategy, DeviceInfo, ChannelInfo

_NS  = "http://www.hikvision.com/ver20/XMLSchema"
_MAP = {"h": _NS}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WM-DVR/1.0)",
    "Accept":     "application/xml, */*",
    "Connection": "close",
}


def _find(el, tag: str) -> str:
    node = el.find(f"h:{tag}", _MAP) or el.find(tag)
    return node.text.strip() if (node is not None and node.text) else ""


class HikvisionHTTPStrategy(DVRStrategy):

    def _session(self):
        s = requests.Session()
        s.auth = HTTPDigestAuth(self.username, self.password)
        s.headers.update(_HEADERS)
        return s

    def _get(self, session, path: str):
        """GET con reintento automático de puerto (80 ↔ 8080)."""
        alt_port = 8080 if self.port == 80 else 80
        for port in [self.port, alt_port]:
            try:
                r = session.get(
                    f"http://{self.host}:{port}{path}",
                    timeout=self.timeout,
                )
                self._check_http_status(r)
                self.port = port
                return r
            except (requests.exceptions.ConnectionError, ConnectionResetError):
                continue
        raise ConnectionError(
            f"No se pudo conectar a {self.host}.\n"
            f"Verifica IP, puerto ({self.port}) y que el DVR esté encendido."
        )

    def get_device_info(self) -> DeviceInfo:
        s    = self._session()
        info = DeviceInfo(brand="Hikvision", ip_address=self.host)

        r    = self._get(s, "/ISAPI/System/deviceInfo")
        root = ET.fromstring(r.text)

        info.model            = _find(root, "model")
        info.device_name      = _find(root, "deviceName")
        info.serial_number    = _find(root, "serialNumber")
        info.firmware_version = _find(root, "firmwareVersion")
        info.mac_address      = _find(root, "macAddress")

        r2    = self._get(s, "/ISAPI/System/Video/inputs/channels")
        root2 = ET.fromstring(r2.text)
        chs   = (
            root2.findall("h:VideoInputChannel", _MAP)
            or root2.findall(".//VideoInputChannel")
        )

        for ch in chs:
            cid = _find(ch, "id")
            rx  = _find(ch, "resolutionWidth")
            ry  = _find(ch, "resolutionHeight")
            info.channels.append(ChannelInfo(
                id         = cid,
                name       = _find(ch, "name") or f"Canal {cid}",
                resolution = f"{rx}x{ry}" if rx and ry else "",
                rtsp_main  = self.build_rtsp_url(int(cid), False),
                rtsp_sub   = self.build_rtsp_url(int(cid), True),
            ))

        info.num_video_channels = len(info.channels)
        return info

    def build_rtsp_url(self, channel: int, sub_stream: bool = False) -> str:
        s = 2 if sub_stream else 1
        return (
            f"rtsp://{self.username}:{self.password}"
            f"@{self.host}:554/Streaming/Channels/{channel:d}0{s}"
        )
