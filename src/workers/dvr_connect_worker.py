"""
src/workers/dvr_connect_worker.py
QThread que ejecuta DVRContext.connect() sin bloquear la UI.
"""
from PySide6.QtCore import QThread, Signal
from core.dvr       import DVRContext, DeviceInfo


class DVRConnectWorker(QThread):
    success = Signal(object)   # DeviceInfo
    error   = Signal(str)

    def __init__(
        self,
        brand:    str,
        host:     str,
        port:     str | int,
        username: str,
        password: str,
        sdk_path: str = "",
    ):
        super().__init__()
        self.brand    = brand
        self.host     = host
        self.port     = int(port)
        self.username = username
        self.password = password
        self.sdk_path = sdk_path

    def run(self):
        try:
            info = DVRContext.connect(
                brand    = self.brand,
                host     = self.host,
                port     = self.port,
                username = self.username,
                password = self.password,
                sdk_path = self.sdk_path,
            )
            self.success.emit(info)

        except PermissionError as e:
            self.error.emit(f"🔐 Credenciales incorrectas:\n{e}")
        except TimeoutError as e:
            self.error.emit(f"⏱ Timeout:\n{e}")
        except FileNotFoundError as e:
            self.error.emit(f"📁 SDK no encontrado:\n{e}")
        except ConnectionError as e:
            self.error.emit(f"🔌 Error de conexión:\n{e}")
        except ValueError as e:
            self.error.emit(f"⚙ Configuración incorrecta:\n{e}")
        except Exception as e:
            msg = str(e)
            if "10054" in msg or "ConnectionReset" in msg or "Connection aborted" in msg:
                self.error.emit(
                    "🔌 El DVR cerró la conexión (WinError 10054)\n\n"
                    "• Verifica el puerto (prueba 80, 8080, 8000)\n"
                    "• Verifica que el DVR esté encendido\n"
                    "• Revisa el firewall"
                )
            else:
                self.error.emit(f"⚠ {type(e).__name__}: {e}")
