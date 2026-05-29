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
    QComboBox, QApplication,
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
                 roi_door=[],
                 roi_dor_boolean=False,
                 roi_dor_direction=[],
                 roi_dor_direction_boolean=False,
                 roi_entrega=None,
                 roi_entrega_boolean=False,
                 cosmetics_enabled=True,
                 callback_save_data=None,
                 socket_services=None,
                 api_jarvis=None,
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
        self.roi_door                = roi_door
        self.roi_dor_boolean         = roi_dor_boolean
        self.roi_dor_direction       = roi_dor_direction
        self.roi_dor_direction_boolean = roi_dor_direction_boolean
        self.roi_entrega             = roi_entrega if roi_entrega else [[300,600],[700,600],[700,900],[300,900]]
        self.roi_entrega_boolean     = True  # siempre activo (igual que door ROI)
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

        # DVR
        self._rtsp_worker: RTSPWorker | None = None
        self._dvr_mode:    bool = False

        # ── Clases para tracking ──
        # Mapa: nombre_display → class_id (int para COCO) o list[int] (grupo).
        # Cosmeticos reemplaza a Bicicleta y agrupa los 16 SKUs del modelo
        # cosmeticos (Personal de Amazonas). El server ignora ids que no
        # correspondan a su modelo activo, asi que es seguro mantenerlo
        # visible en todos los modos.
        self._available_classes = {
            "Persona":    0,
            "Cosmeticos": list(range(16)),  # 16 SKUs del modelo cosmeticos
            "Auto":       2,
            "Moto":       3,
            "Bus":        5,
            "Camion":     7,
            "Perro":     16,
        }
        self._cosmetic_classes = {}  # Ya no se usa (fusionado arriba)
        # Por defecto solo persona activa
        self._selected_classes = [0]

        # Toggle independiente del modelo de cosméticos. No afecta a Persona
        # (clase 0 del modelo COCO) ni a la inferencia de género/edad: solo
        # indica al servidor si debe correr o no el modelo de cosméticos.
        self.cosmetics_enabled = bool(cosmetics_enabled)

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
            roi=self.roi,           roi_active=self.roi_boolean,
            roi_door=self.roi_door, roi_door_active=self.roi_dor_boolean,
            dor_direction=self.roi_dor_direction,
            dor_direction_active=self.roi_dor_direction_boolean,
            roi_entrega=self.roi_entrega,
            roi_entrega_active=self.roi_entrega_boolean,
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

        # Selector de ROIs habilitados (perimetro / puerta / direccion / entrega)
        self.btn_roi_select = BtnIco(ico_path="resource/perimeter.png",
                                     title="Seleccionar ROIs habilitados", h=30, w=30)
        self.btn_roi_select.setObjectName("btn-bar")
        self.btn_roi_select.clicked.connect(self._show_roi_select_menu)

        # Resetear posicion de los ROIs
        self.btn_roi_reset = BtnIco(ico_path="resource/close.png",
                                    title="Reiniciar posicion de ROIs", h=30, w=30)
        self.btn_roi_reset.setObjectName("btn-bar")
        self.btn_roi_reset.clicked.connect(self._reset_roi_positions)

        # ── Grupo Clases (selector de qué trackear) ──
        self._btn_classes = BtnIco(ico_path="resource/camera_box.png",
                                   title="Seleccionar clases a detectar", h=30, w=30)
        self._btn_classes.setObjectName("btn-bar")
        self._btn_classes.clicked.connect(self._show_class_menu)

        # ── Toggle Cosméticos (independiente de Persona/género/edad) ──
        from PySide6.QtWidgets import QPushButton
        self.btn_cosmetics = QPushButton("Cosméticos: ON")
        self.btn_cosmetics.setCheckable(True)
        self.btn_cosmetics.setChecked(self.cosmetics_enabled)
        self.btn_cosmetics.setCursor(Qt.PointingHandCursor)
        self.btn_cosmetics.setToolTip(
            "Activar/Desactivar tracking de cosméticos.\n"
            "No afecta la detección de personas, género ni edad."
        )
        self.btn_cosmetics.setFixedHeight(26)
        self.btn_cosmetics.clicked.connect(self._toggle_cosmetics)
        self._refresh_cosmetics_btn_style()

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

        # Layout: [IA | ROI HidePoints | Classes] --- [Capture Play Pause Stop DVR]
        bar_opt_layout.addWidget(self.btn_smart)
        bar_opt_layout.addWidget(_sep())
        bar_opt_layout.addWidget(self.btn_perimeterroi)
        bar_opt_layout.addWidget(self.btn_hide_points)
        bar_opt_layout.addWidget(self.btn_roi_select)
        bar_opt_layout.addWidget(self.btn_roi_reset)
        bar_opt_layout.addWidget(_sep())
        bar_opt_layout.addWidget(self._btn_classes)
        bar_opt_layout.addWidget(self.btn_cosmetics)
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
        
        if not rtsp_url:
            self._log_dvr(f"⚠ Sin URL RTSP disponible", error=True)
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

                roi_c  = self.imagen_label.get_coordinates(w, h)
                door_c = self.imagen_label.get_door_coordinates(w, h)
                dir_c  = self.imagen_label.get_door_direction_coordinates(w, h)

                data = {
                    "image": jpeg_bytes,
                    "roi_coordinates": roi_c,
                    "roi_activate": self.roi_boolean,
                    "door_roi_coordinates": door_c,
                    "door_roi_activate": True,
                    "door_direction": dir_c,
                    "door_direction_activate": True,
                    "camera_id": self.component_key,
                    "track_classes": self._selected_classes,
                    "cosmetics_enabled": self.cosmetics_enabled,
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
        self.imagen_label.toggle_points()
        self.roi_boolean = not self.roi_boolean
        # Activar/desactivar TODOS los ROIs juntos
        self.imagen_label.door_active = self.roi_boolean
        self.imagen_label.entrega_active = self.roi_boolean
        self.imagen_label.update()

    def _toggle_points_visibility(self):
        """Oculta/muestra los puntos del ROI sin desactivar el ROI."""
        self.imagen_label.toggle_points_visibility()

    def _show_roi_select_menu(self):
        """Popup con checkboxes para activar/desactivar cada ROI individualmente."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #2b2b2b; border: 1px solid #555; padding: 4px; }
            QCheckBox { color: white; padding: 4px 8px; font-size: 12px; }
            QCheckBox::indicator { width: 14px; height: 14px; }
            QCheckBox::indicator:checked { background: #4CAF50; border: 1px solid #666; border-radius: 2px; }
            QCheckBox::indicator:unchecked { background: #555; border: 1px solid #666; border-radius: 2px; }
        """)

        def add_check(label, getter, setter):
            cb = QCheckBox(label)
            cb.setChecked(bool(getter()))
            cb.toggled.connect(lambda checked: (setter(checked), self.imagen_label.update()))
            action = QWidgetAction(menu)
            action.setDefaultWidget(cb)
            menu.addAction(action)

        def _ensure_visible(v):
            # Si activa un ROI, asegurar que el dibujo no este globalmente oculto
            if bool(v):
                self.imagen_label.points_hidden = False
                if hasattr(self, 'btn_hide_points'):
                    self.btn_hide_points.setChecked(False)

        def set_perimeter(v):
            _ensure_visible(v)
            self.roi_boolean = bool(v)
            self.imagen_label.show_points = bool(v)
            self._save_all("roi_boolean", bool(v))

        def set_door(v):
            _ensure_visible(v)
            self.imagen_label.door_active = bool(v)

        def set_direction(v):
            _ensure_visible(v)
            self.imagen_label.door_direction_active = bool(v)

        def set_entrega(v):
            _ensure_visible(v)
            self.roi_entrega_boolean = bool(v)
            self.imagen_label.entrega_active = bool(v)
            self._save_all("roi_entrega_boolean", bool(v))

        add_check("Perimetro",      lambda: self.roi_boolean,                       set_perimeter)
        add_check("Puerta",         lambda: self.imagen_label.door_active,          set_door)
        add_check("Direccion",      lambda: self.imagen_label.door_direction_active, set_direction)
        add_check("Entrega",        lambda: self.imagen_label.entrega_active,       set_entrega)

        btn_pos = self.btn_roi_select.mapToGlobal(self.btn_roi_select.rect().bottomLeft())
        menu.exec(btn_pos)

    def _reset_roi_positions(self):
        """Reinicia las posiciones de TODOS los ROIs a defaults visibles y persiste."""
        self.imagen_label.reset_points()
        # Sincronizar flags del render_box con las del label
        self.roi_boolean = True
        self.roi_entrega_boolean = True
        defaults = self.imagen_label.get_reset_lists()
        for key, value in defaults.items():
            self._save_all(key, value)
        self._save_all("roi_boolean", True)
        self._save_all("roi_entrega_boolean", True)

    def _current_class_dict(self) -> dict:
        """Devuelve el dict de clases a mostrar en el menu."""
        return self._available_classes

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

        class_dict = self._current_class_dict()
        # Aplanar valores (int o list[int]) para calcular ids validos
        valid_ids = set()
        for v in class_dict.values():
            if isinstance(v, (list, tuple)):
                valid_ids.update(v)
            else:
                valid_ids.add(v)
        # Si cambiamos a un dict cuyos ids no tienen nada que ver con los
        # previamente seleccionados (p.ej. pasar de COCO a cosmeticos),
        # resetear la seleccion a TODAS las clases del dict actual.
        if not any(cid in valid_ids for cid in self._selected_classes):
            self._selected_classes = list(valid_ids)
            self._save_all("track_classes", self._selected_classes[:])

        for name, class_id in class_dict.items():
            cb = QCheckBox(name)
            if isinstance(class_id, (list, tuple)):
                # Grupo: checked si TODOS sus ids estan seleccionados
                ids = list(class_id)
                cb.setChecked(all(i in self._selected_classes for i in ids))
                cb.toggled.connect(
                    lambda checked, gids=ids: self._on_class_group_toggled(gids, checked)
                )
            else:
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

    def _toggle_cosmetics(self):
        """Activa/Desactiva el modelo de cosméticos sin tocar Persona/género/edad."""
        self.cosmetics_enabled = self.btn_cosmetics.isChecked()
        self._refresh_cosmetics_btn_style()
        self._save_all("cosmetics_enabled", self.cosmetics_enabled)

    def _refresh_cosmetics_btn_style(self):
        on = self.cosmetics_enabled
        self.btn_cosmetics.setText(f"Cosméticos: {'ON' if on else 'OFF'}")
        if on:
            self.btn_cosmetics.setStyleSheet(
                "QPushButton { background:#2E7D32; color:white; border:1px solid #1B5E20;"
                " border-radius:4px; padding:2px 10px; font-size:11px; font-weight:bold; }"
                "QPushButton:hover { background:#388E3C; }"
            )
        else:
            self.btn_cosmetics.setStyleSheet(
                "QPushButton { background:#555; color:#ddd; border:1px solid #333;"
                " border-radius:4px; padding:2px 10px; font-size:11px; font-weight:bold; }"
                "QPushButton:hover { background:#666; }"
            )

    def _on_class_group_toggled(self, class_ids: list, checked: bool):
        """Activa/desactiva en bloque un grupo de class_ids (ej: Cosmeticos=0..15)."""
        if checked:
            for cid in class_ids:
                if cid not in self._selected_classes:
                    self._selected_classes.append(cid)
        else:
            self._selected_classes = [
                cid for cid in self._selected_classes if cid not in class_ids
            ]
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
            self.roi_boolean = True
            self.imagen_label.show_points = True
            self.imagen_label.points_hidden = False
            self.imagen_label.door_active = True
            self.imagen_label.entrega_active = True
            if hasattr(self, 'btn_hide_points'):
                self.btn_hide_points.setChecked(False)
            self.imagen_label.update()
            self._save_all("roi_boolean", True)
        else:
            self.btn_smart.setStyleSheet("background-color:#BFBFBF;")
            self.can_send_next_frame = True
            self.roi_boolean = False
            self.imagen_label.show_points = False
            self.imagen_label.door_active = False
            self.imagen_label.entrega_active = False
            self.imagen_label.update()
            self._save_all("roi_boolean", False)

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

                roi_c     = self.imagen_label.get_coordinates(self.image_w, self.image_h)
                door_c    = self.imagen_label.get_door_coordinates(self.image_w, self.image_h)
                dir_c     = self.imagen_label.get_door_direction_coordinates(self.image_w, self.image_h)
                entrega_c = self.imagen_label.get_entrega_coordinates(self.image_w, self.image_h)

                data = {
                    "header": header, "image": image_bytes,
                    "roi_coordinates": roi_c,   "roi_activate": self.roi_boolean,
                    "door_roi_coordinates": door_c, "door_roi_activate": True,
                    "door_direction": dir_c,    "door_direction_activate": True,
                    "entrega_roi_coordinates": entrega_c, "entrega_roi_activate": self.roi_entrega_boolean,
                    "camera_id": self.component_key,
                    "track_classes": self._selected_classes,
                    "cosmetics_enabled": self.cosmetics_enabled,
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
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e):
                self.stop = True
                return
            import traceback
            print(f"on_text_message_received RuntimeError: {e}")
            traceback.print_exc()
        except Exception as e:
            import traceback
            print(f"on_text_message_received error: {e}")
            traceback.print_exc()
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

    def save_point(self, roi, roi_boolean, roi_door, roi_dor_boolean,
                   roi_dor_direction, roi_dor_direction_boolean,
                   roi_entrega=None, roi_entrega_boolean=False):
        if self.callback_save_data:
            self.callback_save_data(self.index, "roi",                     roi)
            self.callback_save_data(self.index, "roi_boolean",             roi_boolean)
            self.callback_save_data(self.index, "roi_door",                roi_door)
            self.callback_save_data(self.index, "roi_dor_boolean",         roi_dor_boolean)
            self.callback_save_data(self.index, "roi_dor_direction",       roi_dor_direction)
            self.callback_save_data(self.index, "roi_dor_direction_boolean", roi_dor_direction_boolean)
            if roi_entrega is not None:
                self.callback_save_data(self.index, "roi_entrega",         roi_entrega)
                self.callback_save_data(self.index, "roi_entrega_boolean", roi_entrega_boolean)
