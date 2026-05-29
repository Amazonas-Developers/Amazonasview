"""
src/gui/windows_main.py
Ventana principal — integra la pestaña Dispositivos DVR.
"""
from typing import Any
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QWidget, QVBoxLayout,
    QLabel, QPushButton, QSizePolicy, QGridLayout, QDialog, QTabWidget,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui  import QCursor, QIcon

from gui.components.title_bar.window_bar import CustomTitleBar
from gui.components.custon_btn.btn_footer import BtnIco
from gui.components.render_box.render_box import Render_box
from gui.components.custom_status_bar import CustomStatusBar

# ── DVR ──────────────────────────────────────────────────────
from gui.components.device_panel import DevicePanel


class MainWindow(QMainWindow):

    MARGIN = 16

    def __init__(self, socket_service, jarvis_api=None, data_model_gui=None,
                 amount_renderbox=2, data_box=None):
        super().__init__()

        self.jarvis_api     = jarvis_api
        self._resizing      = False
        self._resize_direction = None
        self._start_pos     = None
        self._start_geom    = None
        self.list_box       = []
        self.amount_renderbox = data_model_gui.get("amount_renderbox")
        self.data_model_gui   = data_model_gui
        self.socket           = socket_service

        self.setup_ui()

        self.socket.connected_signal.connect(self.footer_bar.update_ui)
        self.socket.disconnected_signal.connect(self.footer_bar.update_ui)
        self.socket.re_connect_signal.connect(self.footer_bar.receive_message)

        self.setMouseTracking(True)
        for child in self.findChildren(QWidget):
            child.setMouseTracking(True)

        self.create_list_box()
        self.prerender_renderbox(self.amount_renderbox, add=True)

        index_principal_box = self.data_model_gui.get("principal_box", -1)
        if index_principal_box > -1:
            self.render_maxized_box(index_principal_box, True)


    def setup_ui(self):
        self.setObjectName("MainWindowStyle")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlag(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setContentsMargins(0, 0, 0, 0)
        self.resize(1024, 768)
        self.center_windows()

        main_content = QWidget()
        main_content.setContentsMargins(0, 0, 0, 0)
        self.layout_main = QVBoxLayout(main_content)
        self.layout_main.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(main_content)

        title_bar = CustomTitleBar(self)
        self.layout_main.addWidget(title_bar)

        self.window_child = QMainWindow()
        self.window_child.setAttribute(Qt.WA_StyledBackground, True)
        self.window_child.setWindowFlag(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.layout_main.addWidget(self.window_child)

        # ── Pestañas ─────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(0, 0, 0, 0)
        self.tabs.setAttribute(Qt.WA_StyledBackground, True)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background:#292929; border-top-left-radius:4px;
                border-top-right-radius:4px;
                border:1px solid #000; padding:8px 12px;
                color:#ffffff; font-size:10pt;
            }
            QTabBar::tab:selected { border-bottom:2px solid #00A8E8; }
            QTabBar::tab:hover    { background:#363535; }
            QTabWidget            { background:#000; border:0; padding:0; }
        """)
        self.window_child.setCentralWidget(self.tabs)

        # ── Pestaña: Smart Streaming ──────────────────────────
        content_box = QWidget()
        content_box.setObjectName("TabContent")
        content_box.setAttribute(Qt.WA_StyledBackground, True)
        self.content_box_layout = QGridLayout(content_box)
        self.content_box_layout.setSpacing(0)
        self.content_box_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(content_box, "Smart Streaming")

        # ── Pestaña: Dispositivos DVR ─────────────────────────
        self.device_panel = DevicePanel()
        self.device_panel.devices_updated.connect(self._on_devices_updated)
        self.tabs.addTab(self.device_panel, "Dispositivos")

        # ── Footer ────────────────────────────────────────────
        last_inference         = self.data_model_gui.get("last_inference", None)
        selected_establishment = self.data_model_gui.get("selected_establishment", None)

        self.footer_bar = CustomStatusBar(
            list_establishment             = self.jarvis_api.list_of_establishments,
            type_inference_default         = last_inference,
            selected_establishment_default = selected_establishment,
        )
        self.footer_bar.btn_layout.clicked.connect(self.open_dialog)
        self.footer_bar.inference_type_selected.connect(self.socket_init)
        self.footer_bar.btn_stopconection.clicked.connect(self.socket_close)
        self.footer_bar.setStyleSheet("QStatusBar { background-color:#424242; color:white; }")

        if selected_establishment is not None:
            self.jarvis_api.selection_establishment(selected_establishment)

        # selector_establishment solo existe si hay establecimientos
        if hasattr(self.footer_bar, "selector_establishment"):
            self.footer_bar.selector_establishment.currentTextChanged.connect(
                self.clicked_selection_establishment
            )

        self.window_child.setStatusBar(self.footer_bar)

        if last_inference is not None:
            self.socket_init(last_inference)


    # ── DVR: actualizar sidebar cuando cambia la lista ────────

    def _on_devices_updated(self):
        """
        Llamado cuando el usuario guarda o elimina un DVR.
        Busca el Sidebar_Dock y le pide refrescar el DVRTree.
        """
        try:
            from gui.components.sidebar.sidebar_dock import Sidebar_Dock
            from PySide6.QtWidgets import QDockWidget
            repo    = self.device_panel.get_repo()
            devices = repo.all()
            for dock in self.window_child.findChildren(QDockWidget):
                sidebar = dock.widget()
                if isinstance(sidebar, Sidebar_Dock):
                    sidebar.refresh_dvr_tree(devices)
                    break
        except Exception as e:
            print(f"[DVR] _on_devices_updated error: {e}")


    # ── Socket ────────────────────────────────────────────────

    def socket_init(self, parameter):
        self.socket.url            = "ws://72.68.60.171:9000/ws"
        self.socket.type_inference = parameter
        self.socket.conect_server()
        self.data_model_gui.set("last_inference", parameter)

    def clicked_selection_establishment(self, text):
        self.jarvis_api.selection_establishment(text)
        self.data_model_gui.set("selected_establishment", text)

    def socket_close(self):
        self.socket.disconnect_server()
        self.data_model_gui.set("last_inference", None)


    # ── RenderBox ─────────────────────────────────────────────

    def prerender_renderbox(self, amount: int = 2, add=False, callback=None, data=None):
        try:
            amount_box = 0; row = 0
            if not add:
                self._clear_layout_only()
            while row < amount:
                col = 0
                while col < amount:
                    box = self.list_box[amount_box]
                    self.content_box_layout.addWidget(box, row, col)
                    box.show()
                    amount_box += 1; col += 1
                row += 1
                if callable(callback):
                    callback()
        except Exception as e:
            print(e)
        finally:
            if self.data_model_gui and hasattr(self.data_model_gui, "set"):
                self.data_model_gui.set("amount_renderbox", amount)

    def render_maxized_box(self, index_box, maximized):
        for i in range(self.content_box_layout.count()):
            if maximized:
                if index_box != i:
                    self.list_box[i].hide()
            else:
                self.list_box[i].show()

    def create_list_box(self):
        for i in range(16):
            cfg = self.data_model_gui.get_box_config(i)
            box = Render_box(
                index                      = len(self.list_box),
                socket_services            = self.socket,
                hwnd                       = cfg["hwnd"],
                inferece_play              = cfg["inference_play"],
                roi                        = cfg["roi"],
                roi_boolean                = cfg["roi_boolean"],
                roi_door                   = cfg["roi_door"],
                roi_dor_boolean            = cfg["roi_dor_boolean"],
                roi_dor_direction          = cfg["roi_dor_direction"],
                roi_dor_direction_boolean  = cfg["roi_dor_direction_boolean"],
                roi_entrega                = cfg.get("roi_entrega", [[300,600],[700,600],[700,900],[300,900]]),
                roi_entrega_boolean        = cfg.get("roi_entrega_boolean", False),
                cosmetics_enabled          = cfg.get("cosmetics_enabled", True),
                callback_save_data         = self._save_data_render_box,
                api_jarvis                 = self.jarvis_api,
            )
            box.double_clicked_signal.connect(
                lambda idx, isMx: self.handdler_dlouble_click(idx, isMx)
            )
            self.list_box.append(box)

    def handdler_dlouble_click(self, index, isMaximised):
        self.data_model_gui.set("principal_box", index if isMaximised else -1)
        self.render_maxized_box(index, isMaximised)

    def _save_data_render_box(self, index: int = -1, key: str = "", value: Any = None):
        if self.data_model_gui and hasattr(self.data_model_gui, "update_box_config"):
            self.data_model_gui.update_box_config(index, key, value)

    def _clear_layout_only(self):
        while self.content_box_layout.count():
            item   = self.content_box_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)


    # ── Diálogo layout ────────────────────────────────────────

    def open_dialog(self):
        dlg = QDialog(parent=self)
        dlg.setFixedSize(260, 180)
        dlg.setStyleSheet("QDialog { background-color:#424242; color:white; }")
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        def close_dlg(): dlg.close()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Divisiones de las ventanas", alignment=Qt.AlignCenter))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        for amount, path, label in [
            (1, "resource/1-.png",   "1x1"),
            (2, "resource/2x2-.png", "2x2"),
            (3, "resource/3x3-.png", "3x3"),
            (4, "resource/4x4-.png", "4x4"),
        ]:
            b = BtnIco(ico_path=path, title=label, h=40, w=40)
            b.clicked.connect(
                lambda _, a=amount: self.prerender_renderbox(amount=a, add=False, callback=close_dlg)
            )
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row, stretch=1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton { background:transparent; border:none;"
            " text-decoration:underline; color:#fff }"
        )
        btn_cancel.clicked.connect(close_dlg)
        layout.addWidget(btn_cancel, alignment=Qt.AlignCenter)
        dlg.setLayout(layout)
        dlg.exec()


    # ── Utilidades ────────────────────────────────────────────

    def center_windows(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )


    # ── Redimensionamiento ────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos        = event.globalPosition().toPoint()
            self._start_geom       = self.geometry()
            self._resize_direction = self._get_resize_direction(event.pos())
            if self._resize_direction:
                self._resizing = True

    def mouseMoveEvent(self, event):
        if not self._resizing:
            self._update_cursor(event.pos())
        else:
            self._resize_window(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._resize_direction = None

    def _get_resize_direction(self, pos):
        x, y   = pos.x(), pos.y()
        w, h   = self.width(), self.height()
        m      = self.MARGIN
        if   x < m and y < m:         return "top_left"
        elif x > w-m and y < m:       return "top_right"
        elif x < m and y > h-m:       return "bottom_left"
        elif x > w-m and y > h-m:     return "bottom_right"
        elif x < m:                    return "left"
        elif x > w-m:                  return "right"
        elif y < m:                    return "top"
        elif y > h-m:                  return "bottom"
        return None

    def _update_cursor(self, pos):
        cursors = {
            "top_left":    Qt.SizeFDiagCursor, "bottom_right": Qt.SizeFDiagCursor,
            "top_right":   Qt.SizeBDiagCursor, "bottom_left":  Qt.SizeBDiagCursor,
            "left":        Qt.SizeHorCursor,   "right":        Qt.SizeHorCursor,
            "top":         Qt.SizeVerCursor,   "bottom":       Qt.SizeVerCursor,
        }
        self.setCursor(cursors.get(self._get_resize_direction(pos), Qt.ArrowCursor))

    def _resize_window(self, global_pos):
        delta = global_pos - self._start_pos
        geom  = QRect(self._start_geom)
        d     = self._resize_direction
        if "left"   in d: geom.setLeft(geom.left()     + delta.x())
        if "right"  in d: geom.setRight(geom.right()   + delta.x())
        if "top"    in d: geom.setTop(geom.top()       + delta.y())
        if "bottom" in d: geom.setBottom(geom.bottom() + delta.y())
        if geom.width() >= self.minimumWidth() and geom.height() >= self.minimumHeight():
            self.setGeometry(geom)
