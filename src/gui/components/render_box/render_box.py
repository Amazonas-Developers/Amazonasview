"""
src/gui/components/render_box/render_box.py
RenderBox original + soporte de drag & drop DVR (RTSP) con detección automática de Hik-Connect e IP.

Cambios vs original:
  • dragEnterEvent / dropEvent aceptan también CAMERA_MIME
  • start_dvr_stream() lanza RTSPWorker con detección automática de tipo (Hik-Connect/IP)
  • _stop_dvr_stream() detiene el RTSPWorker
  • Botón "⏹ DVR" en la barra flotante cuando hay stream activo
  • Compatible con datos cifrados de Hik-Connect y URLs de IP
"""
import os, json, base64, sys
import re
import time
import uuid
import msgpack

from PySide6.QtWidgets import (
    QFrame, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QGridLayout, QSizePolicy, QMenu, QWidgetAction, QCheckBox,
    QLineEdit,
)
from PySide6.QtCore  import Qt, Slot, QProcess, QUrl, Signal, QEvent, QBuffer, QIODevice
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtGui   import QPixmap, QCursor, QImage

from ..custon_label.interactive_imageLabel import Interactive_imageLabel
from ..custon_btn.btn_footer import BtnIco

from core.state_global.hwnd import hwndState
from core.capture_exaple import capture_window_by_hwnd, pil_image_to_png_bytes, window_exists, get_title
from core.window_controller import set_window_always_on_top
from core.dvr.hikconnect_channel_encoder import ChannelTypeDetector

# DVR
from workers.rtsp_worker import RTSPWorker
_DVR_MIME = "application/x-dvr-channel"


class Render_box(QFrame):

    double_clicked_signal = Signal(int, bool)
    roi_change_signal     = Signal(list)
    alert_received        = Signal(dict)

    def __init__(self,
                 frames_per_milliseconds=100,
                 index=0,
                 hwnd=None,
                 inferece_play=False,
                 roi=[[100,100],[900,100],[900,900],[100,900]],
                 roi_boolean=False,
                 order_zone=None,
                 order_zone_boolean=False,
                 delivery_zone=None,
                 delivery_zone_boolean=False,
                 vlm_enabled_boolean=False,
                 callback_save_data=None,
                 socket_services=None,
                 api_jarvis=None,
                 **_legacy_kwargs,
                 ):
        super().__init__()

        self.setAcceptDrops(True)
        self.hwnd        = hwnd
        self.smart_mode  = inferece_play
        self.index       = index
        self.api_jarvis  = api_jarvis
        self.socket      = socket_services
        self.socket.connected_signal.connect(self.reconnect_socket)
        self.socket.disconnected_signal.connect(self.diconect_socket)

        self.roi                     = roi
        self.roi_boolean             = roi_boolean
        # ROI azul de Toma de orden
        self.order_zone              = order_zone if order_zone else [[200,400],[500,400],[500,700],[200,700]]
        self.order_zone_boolean      = bool(order_zone_boolean)
        # ROI rojo de Entrega de plato
        self.delivery_zone           = delivery_zone if delivery_zone else [[550,400],[850,400],[850,700],[550,700]]
        self.delivery_zone_boolean   = bool(delivery_zone_boolean)
        # ETAPA 2 — toggle VLM
        self.vlm_enabled_boolean     = bool(vlm_enabled_boolean)
        self.callback_save_data      = callback_save_data

        self.process              = None
        self.stop                 = False
        self.frames_per_milliseconds = frames_per_milliseconds
        self.frame_count          = 0
        self.last_fps_time        = time.time()
        self.current_fps          = 0
        self.is_maximized         = False
        self.image_w              = 0
        self.image_h              = 0
        self.current_pixmap       = None
        self.component_key        = str(uuid.uuid4())
        self.can_send_next_frame  = True
        # Ángulo de cámara para demografía (Personal de Amazonas):
        # "auto" => el servidor lo detecta solo (frontal/lateral/cenital) por
        # la forma de las personas. También admite "frontal"|"lateral"|"cenital"
        # si se quiere fijar manualmente.
        self.camera_angle         = "auto"

        # DVR
        self._rtsp_worker: RTSPWorker | None = None
        self._dvr_mode:    bool = False

        # ── Clases para tracking (COCO) ──
        # Mapa: nombre_display → class_id (int).
        self._available_classes = {
            "Persona":    0,
            "Auto":       2,
            "Moto":       3,
            "Bus":        5,
            "Camion":     7,
            "Perro":     16,
        }
        # Por defecto: solo Persona (sistema personas + demografia).
        self._selected_classes = [0]

        self.setup_ui()

        if self.hwnd is not None and window_exists(self.hwnd):
            self.get_hwnd_and_print(self.hwnd)
            self.title      = get_title(self.hwnd)
            self.id_windows = int(hwnd)
            if self.socket.is_connected() and self.smart_mode:
                self.init_loop()

        hwndState.change_hwnd.connect(self.get_hwnd_and_print)
        if self.socket is not None:
            self.socket.signal_inference.connect(self.on_text_message_received)


    def setup_ui(self):
        self.setObjectName("box-content")
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setContentsMargins(0, 0, 0, 0)

        self.stack = QVBoxLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)

        # Barra info
        self.bar_info = QWidget(self)
        self.bar_info.setAttribute(Qt.WA_StyledBackground, True)
        self.bar_info.setMaximumHeight(30)
        self.bar_info.setObjectName("bar_options")
        bar_info_layout = QHBoxLayout(self.bar_info)

        self.text_fps  = QLabel(f"FPS: {self.current_fps}")
        self.text_fps.setObjectName("text-fps")
        self.text_size = QLabel("0x0")
        self.text_size.setObjectName("text-fps")
        self._dvr_label = QLabel("")
        self._dvr_label.setObjectName("text-fps")
        self._dvr_label.setVisible(False)

        bar_info_layout.addWidget(self.text_fps)
        bar_info_layout.addWidget(self.text_size)
        bar_info_layout.addStretch()
        bar_info_layout.addWidget(self._dvr_label)

        # Imagen
        self.imagen_label = Interactive_imageLabel(
            "viewing window",
            roi=self.roi,
            roi_active=self.roi_boolean,
            order_zone=self.order_zone,
            order_zone_active=self.order_zone_boolean,
            delivery_zone=self.delivery_zone,
            delivery_zone_active=self.delivery_zone_boolean,
        )
        self.imagen_label.point_change.connect(self.save_point)
        self.imagen_label.setAlignment(Qt.AlignCenter)
        self.imagen_label.installEventFilter(self)
        self.stack.addWidget(self.imagen_label)

        # Barra botones
        self.bar_options = QWidget(self)
        self.bar_options.setAttribute(Qt.WA_StyledBackground, True)
        self.bar_options.setMaximumHeight(30)
        self.bar_options.setObjectName("bar_options")
        bar_opt_layout = QHBoxLayout(self.bar_options)
        bar_opt_layout.setContentsMargins(10, 0, 10, 0)
        bar_opt_layout.setSpacing(5)

        # ── Grupo IA ──
        self.btn_smart = BtnIco(ico_path="resource/mode_ai.png",
                                title="Monitoreo inteligente", h=30, w=30)
        self.btn_smart.setObjectName("btn-bar")
        self.btn_smart.clicked.connect(self.activate_modesmart)
        self.btn_smart.setCheckable(True)
        self.btn_smart.setDisabled(True)

        # ── Grupo ROI ──
        self.btn_perimeterroi = BtnIco(ico_path="resource/perimeter.png",
                                       title="Activar/Desactivar ROI", h=30, w=30)
        self.btn_perimeterroi.setCheckable(True)
        self.btn_perimeterroi.setObjectName("btn-bar")
        self.btn_perimeterroi.clicked.connect(self._hideandclear_roy)

        # Botón para ocultar/mostrar puntos del ROI (sin desactivarlo)
        self.btn_hide_points = BtnIco(ico_path="resource/layout.png",
                                      title="Ocultar/Mostrar puntos ROI", h=30, w=30)
        self.btn_hide_points.setCheckable(True)
        self.btn_hide_points.setObjectName("btn-bar")
        self.btn_hide_points.clicked.connect(self._toggle_points_visibility)

        # ── Toggle ROI Toma de orden (azul) ──
        self.btn_order_zone = BtnIco(ico_path="resource/perimeter.png",
                                     title="ROI Toma de orden (azul)", h=30, w=30)
        self.btn_order_zone.setCheckable(True)
        self.btn_order_zone.setChecked(self.order_zone_boolean)
        self.btn_order_zone.setObjectName("btn-bar")
        self.btn_order_zone.setStyleSheet(
            "QPushButton { border: 2px solid rgba(40,120,255,220); border-radius: 4px; }"
            "QPushButton:checked { background-color: rgba(40,120,255,160); }"
        )
        self.btn_order_zone.clicked.connect(self._toggle_order_zone)

        # ── Toggle ROI Entrega de plato (rojo) ──
        self.btn_delivery_zone = BtnIco(ico_path="resource/perimeter.png",
                                        title="ROI Entrega de plato (rojo)", h=30, w=30)
        self.btn_delivery_zone.setCheckable(True)
        self.btn_delivery_zone.setChecked(self.delivery_zone_boolean)
        self.btn_delivery_zone.setObjectName("btn-bar")
        self.btn_delivery_zone.setStyleSheet(
            "QPushButton { border: 2px solid rgba(255,60,60,220); border-radius: 4px; }"
            "QPushButton:checked { background-color: rgba(255,60,60,160); }"
        )
        self.btn_delivery_zone.clicked.connect(self._toggle_delivery_zone)

        # ── Toggle VLM (Etapa 2 — verificador Qwen2.5-VL) ──
        self.btn_vlm = BtnIco(ico_path="resource/mode_ai.png",
                              title="VLM (Etapa 2): verificador SI/NO de eventos", h=30, w=30)
        self.btn_vlm.setCheckable(True)
        self.btn_vlm.setChecked(self.vlm_enabled_boolean)
        self.btn_vlm.setObjectName("btn-bar")
        self.btn_vlm.setStyleSheet(
            "QPushButton { border: 2px solid rgba(170,80,255,220); border-radius: 4px; }"
            "QPushButton:checked { background-color: rgba(170,80,255,180); }"
        )
        self.btn_vlm.clicked.connect(self._toggle_vlm)

        # ── Grupo Clases (selector de qué trackear) ──
        self._btn_classes = BtnIco(ico_path="resource/camera_box.png",
                                   title="Seleccionar clases a detectar", h=30, w=30)
        self._btn_classes.setObjectName("btn-bar")
        self._btn_classes.clicked.connect(self._show_class_menu)

        # ── Grupo Controles de captura ──
        self.btn_cap = BtnIco(ico_path="resource/camera_box.png", title="Captura", h=30, w=30)
        self.btn_cap.setObjectName("btn-bar")

        btn_play  = BtnIco(ico_path="resource/play_box.png",  title="Iniciar", h=30, w=30)
        btn_pause = BtnIco(ico_path="resource/pause_box.png", title="Pausar",  h=30, w=30)
        btn_stop  = BtnIco(ico_path="resource/stop_box.png",  title="Parar",   h=30, w=30)
        for b in (btn_play, btn_pause, btn_stop):
            b.setObjectName("btn-bar")

        btn_play.clicked.connect(self.init_loop)
        btn_pause.clicked.connect(self.pause_loop)
        btn_stop.clicked.connect(self.detroy_loop)

        # Botón detener DVR
        self._btn_stop_dvr = BtnIco(ico_path="resource/stop_box.png",
                                    title="Detener DVR", h=30, w=30)
        self._btn_stop_dvr.setObjectName("btn-bar")
        self._btn_stop_dvr.setToolTip("Detener stream DVR")
        self._btn_stop_dvr.clicked.connect(self._stop_dvr_stream)
        self._btn_stop_dvr.setVisible(False)

        # ── Separador visual (línea vertical) ──
        def _sep():
            s = QFrame()
            s.setFrameShape(QFrame.VLine)
            s.setStyleSheet("color: #666;")
            s.setFixedWidth(2)
            s.setFixedHeight(20)
            return s

        # Layout: [IA | ROIs | Classes] --- [Capture Play Pause Stop DVR]
        bar_opt_layout.addWidget(self.btn_smart)
        bar_opt_layout.addWidget(_sep())
        bar_opt_layout.addWidget(self.btn_perimeterroi)
        bar_opt_layout.addWidget(self.btn_hide_points)
        bar_opt_layout.addWidget(self.btn_order_zone)
        bar_opt_layout.addWidget(self.btn_delivery_zone)
        bar_opt_layout.addWidget(self.btn_vlm)
        bar_opt_layout.addWidget(_sep())
        bar_opt_layout.addWidget(self._btn_classes)
        bar_opt_layout.addStretch(1)
        bar_opt_layout.addWidget(self.btn_cap)
        bar_opt_layout.addWidget(btn_play)
        bar_opt_layout.addWidget(btn_pause)
        bar_opt_layout.addWidget(btn_stop)
        bar_opt_layout.addWidget(self._btn_stop_dvr)

        self.bar_info.hide()
        self.bar_options.hide()


    # ── DVR: stream RTSP ─────────────────────────────────────

    def start_dvr_stream(self, channel_data: dict):
        """
        Recibe datos del canal (drop) e inicia el RTSPWorker.
        Detecta automáticamente si es Hik-Connect o IP.
        Si es Hik-Connect sin URL válida o con encriptación, pide clave.
        """
        self._stop_dvr_stream()

        # Detener captura HWND sin resetear estado de IA
        if self.process is not None:
            self.process.terminate()
            if not self.process.waitForFinished(1000):
                self.process.kill()
            self.process = None
        self.hwnd = None

        # Detectar tipo de canal (Hik-Connect o IP)
        channel_type = ChannelTypeDetector.get_channel_type(channel_data)
        rtsp_url = channel_data.get("rtsp_main", "")

        # ── Hik-Connect: detección a prueba de balas de encriptación ──
        # Cualquiera de estas condiciones dispara el diálogo de clave:
        url_invalid = (not rtsp_url) or ("ErrCode" in rtsp_url) or ("9053" in rtsp_url)
        flag_set    = channel_data.get("stream_encrypt_enable", False)
        needs_code  = (channel_type == "hikconnect") and (flag_set or url_invalid)

        print(f"[DVR] start_dvr_stream: type={channel_type} url_invalid={url_invalid} "
              f"flag={flag_set} needs_code={needs_code} url={(rtsp_url or '')[:80]}")

        if needs_code:
            from PySide6.QtWidgets import QInputDialog
            code, ok = QInputDialog.getText(
                self, "Código de verificación del stream",
                "Este canal tiene encriptación de stream habilitada.\n\n"
                "Ingresa el Código de Verificación del dispositivo.\n"
                "Puedes encontrarlo en:\n"
                "  • Interfaz web local del DVR → Configuración → Red → Plataforma\n"
                "  • O en la etiqueta física del dispositivo (6 dígitos)",
                QLineEdit.Password,
            )
            if not ok or not code.strip():
                self.text_fps.setText("⚠ Clave de encriptación requerida")
                return

            # Obtener nueva URL con la clave
            resource_id   = channel_data.get("resource_id") or channel_data.get("channel_id", "")
            device_serial = channel_data.get("device_serial", "")

            self.text_fps.setText("⏳ Obteniendo stream con clave…")
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            from core.dvr.hikconnect import HikConnectStrategy
            from models.dvr_storage import DVRRepository
            repo = DVRRepository()
            access_token = ""
            area_domain  = ""
            app_key      = ""
            app_secret   = ""

            # Buscar la cuenta Hik-Connect en el repo
            for dev in repo.all():
                if dev.brand == "Hik-Connect":
                    app_key    = dev.username
                    app_secret = dev.password
                    # Si no tenemos device_serial, sacarlo de los canales guardados
                    if not device_serial:
                        for ch in dev.channels:
                            ch_d = ch if isinstance(ch, dict) else {}
                            if (ch_d.get("resource_id") == resource_id or
                                ch_d.get("id") == resource_id):
                                device_serial = ch_d.get("device_serial", "")
                                break
                    break

            if not app_key or not app_secret:
                self.text_fps.setText("⚠ No hay cuenta Hik-Connect guardada")
                return

            # Renovar token
            token_data = HikConnectStrategy.refresh_token(app_key, app_secret)
            if token_data:
                access_token = token_data["access_token"]
                area_domain  = token_data["area_domain"]
            else:
                self.text_fps.setText("⚠ No se pudo renovar token Hik-Connect")
                return

            print(f"[DVR] refresh_live_url: rid={resource_id} serial={device_serial} "
                  f"area={area_domain}")

            if not (resource_id and device_serial):
                self.text_fps.setText("⚠ Faltan datos del canal (rid/serial)")
                return

            new_url = HikConnectStrategy.refresh_live_url(
                area_domain=area_domain,
                access_token=access_token,
                resource_id=resource_id,
                device_serial=device_serial,
                quality=1,
                code=code.strip(),
            )
            if new_url:
                rtsp_url = new_url
                print(f"[DVR] URL nueva con clave: {new_url[:100]}")
            else:
                self.text_fps.setText("⚠ Stream encriptado no disponible vía nube")
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setWindowTitle("Stream encriptado - HiLook/EZVIZ")
                msg.setIcon(QMessageBox.Warning)
                msg.setText(
                    "<b>No se pudo obtener el stream encriptado.</b><br><br>"
                    "El DVR HiLook usa encriptación EZVIZ que la API de HikConnect "
                    "no puede desbloquear directamente.<br><br>"
                    "<b>Solución recomendada:</b><br>"
                    "Deshabilita la encriptación de stream en el DVR:<br>"
                    "1. Accede a la interfaz web local del DVR<br>"
                    "2. Ve a <i>Configuración → Red → Plataforma</i><br>"
                    "3. Deshabilita <i>Stream Encryption</i><br>"
                    "4. Guarda y vuelve a intentarlo<br><br>"
                    "<i>La cámara 1 funciona porque no tiene encriptación habilitada.</i>"
                )
                msg.exec()
                return

        if not rtsp_url:
            self.text_fps.setText("⚠ Sin URL de stream disponible")
            return

        alias   = channel_data.get("device_alias", "")
        ch_name = channel_data.get("channel_name", "")
        type_label = "🔐 HC" if channel_type == "hikconnect" else "📹"
        label   = f"{type_label} {alias} · {ch_name}" if alias else f"{type_label} {ch_name}"

        self._dvr_label.setText(label)
        self._dvr_label.setVisible(True)
        self._btn_stop_dvr.setVisible(True)
        self._dvr_mode = True
        self.stop = False
        self.can_send_next_frame = True

        # Habilitar boton IA si el socket esta conectado
        if self.socket and self.socket.is_connected():
            self.btn_smart.setEnabled(True)

        self._rtsp_worker = RTSPWorker(
            rtsp_url,
            channel_id=channel_data.get("channel_id", ""),
        )
        self._rtsp_worker.frame_ready.connect(self._on_dvr_frame)
        self._rtsp_worker.connected.connect(
            lambda: self.text_fps.setText("🟢 DVR en vivo")
        )
        self._rtsp_worker.error.connect(
            lambda msg: self.text_fps.setText(f"⚠ {msg.split(chr(10))[0]}")
        )
        self._rtsp_worker.disconnected.connect(
            lambda: self.text_fps.setText("⚫ DVR desconectado")
        )
        self._rtsp_worker.start()
        self.text_fps.setText("⏳ Conectando al stream…")

    def _on_dvr_frame(self, img: QImage):
        if not self._dvr_mode:
            return

        pix = QPixmap.fromImage(img)
        self.current_pixmap = pix
        w, h = img.width(), img.height()
        self.image_w = w
        self.image_h = h

        # FPS tracking
        self.frame_count += 1
        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = now
            prefix = "AI" if self.smart_mode else "DVR"
            self.text_fps.setText(f"{prefix} FPS: {self.current_fps}")

        # Si IA activa, enviar frame al servidor (solo mostrar respuesta del servidor)
        if self.smart_mode and self.socket is not None and self.socket.is_connected():
            if self.can_send_next_frame:
                buf = QBuffer()
                buf.open(QIODevice.WriteOnly)
                img.save(buf, "JPEG", 80)
                jpeg_bytes = bytes(buf.data())
                buf.close()

                roi_c       = self.imagen_label.get_coordinates(w, h)
                order_c     = self.imagen_label.get_order_zone_coordinates(w, h)
                delivery_c  = self.imagen_label.get_delivery_zone_coordinates(w, h)

                data = {
                    "image": jpeg_bytes,
                    "roi_coordinates": roi_c,
                    "roi_activate": self.roi_boolean,
                    "order_zone_coordinates":    order_c,
                    "order_zone_activate":       self.order_zone_boolean,
                    "delivery_zone_coordinates": delivery_c,
                    "delivery_zone_activate":    self.delivery_zone_boolean,
                    "enable_vlm":                self.vlm_enabled_boolean,
                    "camera_id": self.component_key,
                    "camera_angle": self.camera_angle,
                    "track_classes": self._selected_classes,
                }
                self.socket.send_binary_frame(self.component_key, data)
                self.can_send_next_frame = False
            # No mostrar frame crudo — solo se muestra el frame del servidor
            # via on_text_message_received → update_streaming_frame
        else:
            # Sin IA: mostrar frame crudo directamente
            self.imagen_label.setPixmap(
                pix.scaled(self.imagen_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def _stop_dvr_stream(self):
        if self._rtsp_worker and self._rtsp_worker.isRunning():
            self._rtsp_worker.stop()
        self._rtsp_worker  = None
        self._dvr_mode     = False
        self._dvr_label.setVisible(False)
        self._btn_stop_dvr.setVisible(False)
        self.smart_mode    = False
        self.btn_smart.setChecked(False)
        self.btn_smart.setStyleSheet("background-color:#BFBFBF;")
        self.can_send_next_frame = True
        self.text_fps.setText("FPS: 0")


    # ── Drag & Drop (ventana Windows + canal DVR) ─────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-boxcap"):
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(_DVR_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        try:
            if event.mimeData().hasFormat(_DVR_MIME):
                raw  = bytes(event.mimeData().data(_DVR_MIME)).decode("utf-8")
                data = json.loads(raw)
                self.start_dvr_stream(data)
                event.acceptProposedAction()
                return

            if event.mimeData().hasFormat("application/x-boxcap"):
                raw = bytes(event.mimeData().data("application/x-boxcap")).decode("utf-8")
                other_hwnd, other_title = raw.split("|", 1)
                if int(other_hwnd) == getattr(self, "id_windows", None):
                    event.ignore()
                    return
                self._stop_dvr_stream()
                self.get_hwnd_and_print(int(other_hwnd))
                self.id_windows = int(other_hwnd)
                self.title      = other_title
                self.hwnd       = self.id_windows
                event.acceptProposedAction()
                if callable(self.callback_save_data):
                    self.callback_save_data(self.index, "hwnd", self.id_windows)
                return

            event.ignore()
        except Exception as e:
            print(f"dropEvent error: {e}")


    # ── Resto del código original (sin cambios) ───────────────

    def _hideandclear_roy(self):
        """Activa/desactiva el ROI de personas individualmente."""
        self.imagen_label.toggle_points()
        self.roi_boolean = not self.roi_boolean
        self.imagen_label.update()
        self._save_all("roi_boolean", self.roi_boolean)

    def _toggle_points_visibility(self):
        """Oculta/muestra los puntos del ROI sin desactivar el ROI."""
        self.imagen_label.toggle_points_visibility()

    def _toggle_order_zone(self):
        """Activa/desactiva el ROI azul de Toma de orden."""
        self.order_zone_boolean = self.btn_order_zone.isChecked()
        self.imagen_label.toggle_order_zone(self.order_zone_boolean)
        if self.order_zone_boolean:
            self.imagen_label.set_edit_target('order')
            # Garantiza que el overlay no esté globalmente oculto
            if self.imagen_label.points_hidden:
                self.imagen_label.points_hidden = False
                self.btn_hide_points.setChecked(False)
        self.imagen_label.update()
        self._save_all("order_zone_boolean", self.order_zone_boolean)

    def _toggle_delivery_zone(self):
        """Activa/desactiva el ROI rojo de Entrega de plato."""
        self.delivery_zone_boolean = self.btn_delivery_zone.isChecked()
        self.imagen_label.toggle_delivery_zone(self.delivery_zone_boolean)
        if self.delivery_zone_boolean:
            self.imagen_label.set_edit_target('delivery')
            if self.imagen_label.points_hidden:
                self.imagen_label.points_hidden = False
                self.btn_hide_points.setChecked(False)
        self.imagen_label.update()
        self._save_all("delivery_zone_boolean", self.delivery_zone_boolean)

    def _toggle_vlm(self):
        """Activa/desactiva el verificador VLM (Etapa 2) en el servidor.
        El estado viaja en el payload websocket; el servidor hace lazy-load
        del modelo Qwen2.5-VL la primera vez que se enciende."""
        self.vlm_enabled_boolean = self.btn_vlm.isChecked()
        self._save_all("vlm_enabled_boolean", self.vlm_enabled_boolean)

    def _show_class_menu(self):
        """Muestra un menú popup con checkboxes para seleccionar qué clases detectar."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #2b2b2b; border: 1px solid #555; padding: 4px; }
            QCheckBox { color: white; padding: 4px 8px; font-size: 12px; }
            QCheckBox::indicator { width: 14px; height: 14px; }
            QCheckBox::indicator:checked { background: #4CAF50; border: 1px solid #666; border-radius: 2px; }
            QCheckBox::indicator:unchecked { background: #555; border: 1px solid #666; border-radius: 2px; }
        """)

        for name, class_id in self._available_classes.items():
            cb = QCheckBox(name)
            cb.setChecked(class_id in self._selected_classes)
            cb.toggled.connect(
                lambda checked, cid=class_id: self._on_class_toggled(cid, checked)
            )
            action = QWidgetAction(menu)
            action.setDefaultWidget(cb)
            menu.addAction(action)

        # Mostrar debajo del botón
        btn_pos = self._btn_classes.mapToGlobal(self._btn_classes.rect().bottomLeft())
        menu.exec(btn_pos)

    def _on_class_toggled(self, class_id: int, checked: bool):
        """Actualiza las clases seleccionadas para tracking."""
        if checked and class_id not in self._selected_classes:
            self._selected_classes.append(class_id)
        elif not checked and class_id in self._selected_classes:
            self._selected_classes.remove(class_id)
        # Guardar en configuración persistente
        self._save_all("track_classes", self._selected_classes[:])

    def init_loop(self):
        try:
            if self.hwnd is None:
                return
            if self.process is None:
                self.process = QProcess(self)
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.loop_show_result)
                worker_script = "src/workers/capture_woker.py"
                if not os.path.exists(worker_script):
                    return
                self.process.start(sys.executable, [worker_script, str(self.hwnd)])
                if not self.process.waitForStarted(5000):
                    return
            else:
                self.process.readyReadStandardOutput.connect(self.loop_show_result)
        except Exception as e:
            print(f"init_loop error: {e}")

    def pause_loop(self):
        if self.process:
            self.text_fps.setText("FPS: 0")

    def activate_modesmart(self):
        self.smart_mode = not self.smart_mode
        self._save_all("inference_play", self.smart_mode)
        if self.smart_mode:
            self.btn_smart.setStyleSheet("background-color:#FF0000;")
            self.stop = False
            self.can_send_next_frame = True
        else:
            self.btn_smart.setStyleSheet("background-color:#BFBFBF;")
            self.can_send_next_frame = True

    def detroy_loop(self):
        self.btn_smart.setChecked(False)
        self.stop = True; self.smart_mode = False
        if self.process is not None:
            self.process.terminate()
            if not self.process.waitForFinished(1000):
                self.process.kill()
            self.process = None
        self.title = None; self.hwnd = None
        self.imagen_label.setPixmap(QPixmap())
        self.imagen_label.clear()
        self.imagen_label.setText("viewing window")
        self.can_send_next_frame = True
        if callable(self.callback_save_data):
            self.callback_save_data(self.index, "hwnd", None)

    @Slot(int)
    def get_hwnd_and_print(self, hwnd=None):
        try:
            if hwnd is not None:
                self.hwnd = hwnd
            set_window_always_on_top(self.hwnd)
            buffer = capture_window_by_hwnd(self.hwnd)
            if buffer is None: return
            image = pil_image_to_png_bytes(buffer)
            if image is None: return
            self.update_streaming_frame(image, type_image="bytes", tets=False)
            self.bar_options.raise_()
        except Exception as e:
            print(f"get_hwnd error: {e}")

    def loop_show_result(self):
        if not self.process: return
        raw_data = self.process.readAllStandardOutput().data()
        if not raw_data: return
        try:
            unpacker = msgpack.Unpacker(raw=False, strict_map_key=False)
            unpacker.feed(raw_data)
            message = next(iter(unpacker), None)
            if message is None: return
            header      = message.get("header")
            image_bytes = message.get("image_bytes")
            if not header or not image_bytes: return

            self.frame_count += 1
            now = time.time()
            if now - self.last_fps_time >= 1.0:
                self.current_fps   = self.frame_count
                self.frame_count   = 0
                self.last_fps_time = now
                self.text_fps.setText(f"FPS: {self.current_fps}")

            if self.socket is not None:
                if self.image_w == 0 or self.image_h == 0:
                    tmp = QPixmap()
                    tmp.loadFromData(image_bytes, "JPEG")
                    if not tmp.isNull():
                        self.image_w = tmp.width()
                        self.image_h = tmp.height()

                roi_c       = self.imagen_label.get_coordinates(self.image_w, self.image_h)
                order_c     = self.imagen_label.get_order_zone_coordinates(self.image_w, self.image_h)
                delivery_c  = self.imagen_label.get_delivery_zone_coordinates(self.image_w, self.image_h)

                data = {
                    "header": header, "image": image_bytes,
                    "roi_coordinates": roi_c,   "roi_activate": self.roi_boolean,
                    "order_zone_coordinates":    order_c,
                    "order_zone_activate":       self.order_zone_boolean,
                    "delivery_zone_coordinates": delivery_c,
                    "delivery_zone_activate":    self.delivery_zone_boolean,
                    "enable_vlm":                self.vlm_enabled_boolean,
                    "camera_id": self.component_key,
                    "camera_angle": self.camera_angle,
                    "track_classes": self._selected_classes,
                }
                if self.smart_mode and self.can_send_next_frame:
                    self.socket.send_binary_frame(self.component_key, data)
                    self.can_send_next_frame = False

                if self.smart_mode:
                    self.loop_show_result()
                else:
                    self.update_streaming_frame(image_bytes, type_image="jpeg_bytes", tets=True)
        except Exception as e:
            print(f"loop_show_result error: {e}")

    def update_streaming_frame(self, frame, type_image="base64", tets=False):
        try:
            if tets: self.open = True
            pixmap = QPixmap()
            if type_image == "base64":
                frame_bytes = base64.b64decode(re.sub(r"^data:image/\w+;base64,", "", frame))
                pixmap.loadFromData(frame_bytes, "JPEG")
            elif type_image == "jpeg_bytes":
                pixmap.loadFromData(frame, "JPEG")
            else:
                pixmap.loadFromData(frame, "PNG")

            if not pixmap.isNull():
                self.current_pixmap = pixmap
                self.image_w = pixmap.width()
                self.image_h = pixmap.height()
                self.text_size.setText(f"{self.image_w}x{self.image_h}")
                self.imagen_label.setPixmap(
                    pixmap.scaled(self.imagen_label.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                )
        except Exception as e:
            print(f"update_frame error: {e}")
        finally:
            if not self.stop and tets:
                self.loop_show_result()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if hasattr(self, "bar_info"):
            self.bar_info.setGeometry(0, 0, w, 30)
        if hasattr(self, "bar_options"):
            hb = self.bar_options.height()
            self.bar_options.setGeometry(0, h - hb, w, hb)
        if self.current_pixmap:
            self.imagen_label.setPixmap(
                self.current_pixmap.scaled(self.imagen_label.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            )

    def enterEvent(self, event):
        self.bar_info.show(); self.bar_options.show()
        self.bar_info.raise_(); self.bar_options.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        try:
            from PySide6.QtWidgets import QApplication
            if QApplication.activePopupWidget() is not None:
                return
        except Exception:
            pass
        self.bar_info.hide(); self.bar_options.hide()
        super().leaveEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
            self.is_maximized = not self.is_maximized
            self.double_clicked_signal.emit(self.index, self.is_maximized)
        return super().eventFilter(watched, event)

    @Slot(dict)
    def on_text_message_received(self, message):
        try:
            msg_key = message.get("component_key") or message.get("camera_id") or ""
            if msg_key and msg_key != self.component_key: return
            metadata  = message.get("data", {}).get("metadata", {})
            if metadata:
                list_alert = metadata.get("alerts", []) or []
                for iteration in list_alert:
                    event_type = iteration.get("event_type", "Alerta")
                    img_b64 = (
                        iteration.get("image_base64", "")
                        or iteration.get("crop_image", "")
                        or ""
                    )
                    print(f'[ALERT-EMIT] event={event_type!r} img_len={len(img_b64)}', flush=True)
                    self.alert_received.emit({
                        "event_type":      event_type,
                        "class_name":      iteration.get("class_name", event_type),
                        "description":     iteration.get("description", ""),
                        "timestamp":       iteration.get("timestamp", ""),
                        "image_base64":    img_b64,
                        "crop_image":      img_b64,
                        "camera_id":       message.get("component_key", ""),
                        "screenshot_path": iteration.get("screenshot_path", ""),
                    })
            data = message["data"]
            if data["status"] == "success" and data["camera_id"] == self.component_key:
                self.update_streaming_frame(data["processed_image"], type_image="base64", tets=False)
            if data["status"] == "error":
                raise Exception(data.get("message", "Error del servidor"))
        except Exception as e:
            print(f"on_text_message_received error: {e}")
        finally:
            self.can_send_next_frame = True

    def reconnect_socket(self, data):
        self.can_send_next_frame = True
        self.btn_smart.setEnabled(True)
        self.loop_show_result()

    def diconect_socket(self, data):
        self.btn_smart.setEnabled(False)

    def _save_all(self, key, value):
        if self.callback_save_data:
            self.callback_save_data(self.index, key, value)

    def save_point(self, roi, roi_boolean,
                   order_zone=None, order_zone_boolean=False,
                   delivery_zone=None, delivery_zone_boolean=False):
        # Sincroniza estado interno con lo que el label acaba de emitir
        if order_zone is not None:
            self.order_zone = order_zone
            self.order_zone_boolean = bool(order_zone_boolean)
        if delivery_zone is not None:
            self.delivery_zone = delivery_zone
            self.delivery_zone_boolean = bool(delivery_zone_boolean)
        if self.callback_save_data:
            self.callback_save_data(self.index, "roi",         roi)
            self.callback_save_data(self.index, "roi_boolean", roi_boolean)
            if order_zone is not None:
                self.callback_save_data(self.index, "order_zone",         order_zone)
                self.callback_save_data(self.index, "order_zone_boolean", order_zone_boolean)
            if delivery_zone is not None:
                self.callback_save_data(self.index, "delivery_zone",         delivery_zone)
                self.callback_save_data(self.index, "delivery_zone_boolean", delivery_zone_boolean)
