"""
src/gui/components/device_panel.py
Panel completo DVR para la pestaña "Dispositivos".

Izquierda: formulario agregar/editar
Derecha:   lista de dispositivos guardados

Señales:
    devices_updated → emitida al guardar o eliminar (actualiza sidebar)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QGroupBox, QScrollArea, QFrame, QFileDialog,
    QProgressBar, QTextEdit, QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui  import QFont

from models.dvr_storage                       import DVRRepository, DVRDevice
from workers.dvr_connect_worker               import DVRConnectWorker
from core.dvr                                 import DVRContext, DeviceInfo
from core.dvr.hikconnect_channel_encoder     import HikConnectChannelEncoder, ChannelTypeDetector
from .channel_row                            import ChannelRow


# ── Fila de un dispositivo en la lista ───────────────────────

class _DeviceRow(QFrame):
    sig_edit   = Signal(str)
    sig_delete = Signal(str)

    def __init__(self, device: DVRDevice, parent=None):
        super().__init__(parent)
        self._id = device.id
        self.setObjectName("DeviceRow")
        self.setFixedHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)

        dot = QLabel("●")
        dot.setObjectName("RowDot")
        dot.setFixedWidth(14)

        col = QVBoxLayout()
        col.setSpacing(1)
        self.lbl_name = QLabel(device.alias or device.host)
        self.lbl_name.setObjectName("RowName")
        self.lbl_sub = QLabel(
            f"{device.brand}  ·  {device.host}:{device.port}"
            f"  ·  {device.num_channels} canal(es)"
        )
        self.lbl_sub.setObjectName("RowSub")
        col.addWidget(self.lbl_name)
        col.addWidget(self.lbl_sub)

        btn_e = QPushButton("✏")
        btn_e.setObjectName("BtnRowIcon")
        btn_e.setFixedSize(26, 26)
        btn_e.setToolTip("Editar")
        btn_e.clicked.connect(lambda: self.sig_edit.emit(self._id))

        btn_d = QPushButton("🗑")
        btn_d.setObjectName("BtnRowDel")
        btn_d.setFixedSize(26, 26)
        btn_d.setToolTip("Eliminar")
        btn_d.clicked.connect(lambda: self.sig_delete.emit(self._id))

        layout.addWidget(dot)
        layout.addLayout(col, stretch=1)
        layout.addWidget(btn_e)
        layout.addWidget(btn_d)

    def refresh(self, device: DVRDevice):
        self._id = device.id
        self.lbl_name.setText(device.alias or device.host)
        if device.brand == "Hik-Connect":
            brand_display = "Hik-Connect"
        else:
            brand_display = device.brand
        self.lbl_sub.setText(
            f"{brand_display}  ·  {device.host or 'cloud'}:{device.port}"
            f"  ·  {device.num_channels} canal(es)"
        )


# ── Panel principal ───────────────────────────────────────────

class DevicePanel(QWidget):
    devices_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo        = DVRRepository()
        self._rows: dict[str, _DeviceRow] = {}
        self._editing_id: str | None = None
        self._worker:     DVRConnectWorker | None = None
        self._last_info:  DeviceInfo | None = None

        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()
        self._apply_styles()
        self._load_devices()

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._build_form())
        splitter.addWidget(self._build_list())
        splitter.setSizes([420, 560])
        root.addWidget(splitter)

    def _build_form(self) -> QWidget:
        w = QWidget()
        w.setObjectName("FormPanel")
        w.setAttribute(Qt.WA_StyledBackground, True)
        root = QVBoxLayout(w)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        self._form_title = QLabel("Agregar dispositivo DVR")
        self._form_title.setObjectName("FormTitle")
        root.addWidget(self._form_title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("FormSep"); root.addWidget(sep)

        # Tipo de conexión
        grp_type = QGroupBox("Tipo de conexión")
        f_type   = QFormLayout(grp_type)
        f_type.setSpacing(8); f_type.setContentsMargins(12, 12, 12, 12)
        self.cb_connection_type = QComboBox()
        self.cb_connection_type.addItems(["Conexión por IP", "Hik-Connect"])
        self.cb_connection_type.currentTextChanged.connect(self._on_connection_type_changed)
        f_type.addRow("Tipo:", self.cb_connection_type)
        root.addWidget(grp_type)

        # Nombre
        grp_id = QGroupBox("Identificación")
        f_id   = QFormLayout(grp_id)
        f_id.setSpacing(8); f_id.setContentsMargins(12, 12, 12, 12)
        self.txt_alias = QLineEdit()
        self.txt_alias.setPlaceholderText("Ej: Oficina Principal, Sucursal Norte…")
        f_id.addRow("Nombre del dispositivo:", self.txt_alias)
        root.addWidget(grp_id)

        # Conexión
        self.grp_conn = QGroupBox("Conexión")
        f_conn   = QFormLayout(self.grp_conn)
        f_conn.setSpacing(8); f_conn.setContentsMargins(12, 12, 12, 12)

        self.cb_brand = QComboBox()
        self.cb_brand.addItems(DVRContext.brands())
        self.cb_brand.currentTextChanged.connect(self._on_brand_changed)

        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("192.168.1.64")

        self.txt_port = QLineEdit("80")
        self.txt_port.setFixedWidth(70)

        host_row = QHBoxLayout()
        host_row.addWidget(self.txt_host)
        host_row.addWidget(QLabel(":"))
        host_row.addWidget(self.txt_port)

        port_row = QHBoxLayout(); port_row.setSpacing(4)
        for p in ["80", "8080", "8000", "37777"]:
            b = QPushButton(p)
            b.setObjectName("BtnQuick"); b.setFixedHeight(22)
            b.clicked.connect(lambda _, port=p: self.txt_port.setText(port))
            port_row.addWidget(b)

        f_conn.addRow("Tipo / Marca:", self.cb_brand)
        f_conn.addRow("IP / Host:", host_row)
        f_conn.addRow("Puerto rápido:", port_row)
        root.addWidget(self.grp_conn)

        # Credenciales
        self.grp_cred = QGroupBox("Credenciales")
        f_cred   = QFormLayout(self.grp_cred)
        f_cred.setSpacing(8); f_cred.setContentsMargins(12, 12, 12, 12)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("admin")
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_pass.setPlaceholderText("••••••••")
        self.txt_pass.returnPressed.connect(self._test_connection)

        # Para Hik-Connect
        self.lbl_appkey = QLabel("App Key:")
        self.txt_appkey = QLineEdit()
        self.txt_appkey.setPlaceholderText("Tu App Key de Hik-Connect")
        self.lbl_appsecret = QLabel("App Secret:")
        self.txt_appsecret = QLineEdit()
        self.txt_appsecret.setEchoMode(QLineEdit.Password)
        self.txt_appsecret.setPlaceholderText("••••••••")
        self.txt_appsecret.returnPressed.connect(self._test_connection)

        f_cred.addRow("Usuario:", self.txt_user)
        f_cred.addRow("Contraseña:", self.txt_pass)
        f_cred.addRow(self.lbl_appkey, self.txt_appkey)
        f_cred.addRow(self.lbl_appsecret, self.txt_appsecret)
        root.addWidget(self.grp_cred)

        # SDK (solo visible para estrategias nativas)
        self.grp_sdk = QGroupBox("SDK nativo")
        f_sdk = QVBoxLayout(self.grp_sdk)
        f_sdk.setContentsMargins(12, 10, 12, 10); f_sdk.setSpacing(6)
        self.txt_sdk = QLineEdit()
        self.txt_sdk.setPlaceholderText("src/sdk/hikvision/HCNetSDK.dll")
        btn_browse = QPushButton("📂  Buscar DLL…")
        btn_browse.setObjectName("BtnQuick"); btn_browse.setFixedHeight(26)
        btn_browse.clicked.connect(self._browse_sdk)
        f_sdk.addWidget(self.txt_sdk)
        f_sdk.addWidget(btn_browse)
        self.grp_sdk.setVisible(False)
        root.addWidget(self.grp_sdk)

        # Probar conexión
        self.btn_test = QPushButton("🔌  Probar conexión")
        self.btn_test.setObjectName("BtnTest")
        self.btn_test.setMinimumHeight(36)
        self.btn_test.clicked.connect(self._test_connection)
        root.addWidget(self.btn_test)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setObjectName("LogBox")
        self.log_box.setMaximumHeight(90)
        self.log_box.setVisible(False)
        root.addWidget(self.log_box)

        root.addStretch()

        btn_row = QHBoxLayout()
        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.setObjectName("BtnSecondary")
        self.btn_clear.clicked.connect(self._clear_form)

        # Botón logout (solo visible para Hik-Connect)
        self.btn_logout = QPushButton("🔓  Cerrar sesión")
        self.btn_logout.setObjectName("BtnSecondary")
        self.btn_logout.setVisible(False)
        self.btn_logout.clicked.connect(self._logout_account)

        self.btn_save = QPushButton("✅  Guardar dispositivo")
        self.btn_save.setObjectName("BtnSave")
        self.btn_save.setMinimumHeight(36)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_device)

        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_logout)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)
        # Inicializar visibilidad
        self._on_connection_type_changed(self.cb_connection_type.currentText())
        return w

    def _build_list(self) -> QWidget:
        w = QWidget()
        w.setObjectName("ListPanel")
        w.setAttribute(Qt.WA_StyledBackground, True)
        root = QVBoxLayout(w)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        title = QLabel("Dispositivos registrados")
        title.setObjectName("ListTitle")
        root.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("FormSep"); root.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_inner  = QWidget()
        self._list_layout = QVBoxLayout(self._list_inner)
        self._list_layout.setSpacing(6)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_inner)
        root.addWidget(scroll)

        # Área de canales (inicialmente oculta)
        self._channels_group = QGroupBox("Canales disponibles")
        self._channels_group.setVisible(False)
        channels_layout = QVBoxLayout(self._channels_group)
        channels_layout.setContentsMargins(0, 0, 0, 0)
        channels_layout.setSpacing(2)
        
        self._channels_scroll = QScrollArea()
        self._channels_scroll.setWidgetResizable(True)
        self._channels_scroll.setFrameShape(QFrame.NoFrame)
        self._channels_scroll.setMaximumHeight(150)
        
        self._channels_inner = QWidget()
        self._channels_list_layout = QVBoxLayout(self._channels_inner)
        self._channels_list_layout.setContentsMargins(0, 0, 0, 0)
        self._channels_list_layout.setSpacing(4)
        self._channels_list_layout.addStretch()
        
        self._channels_scroll.setWidget(self._channels_inner)
        channels_layout.addWidget(self._channels_scroll)
        root.addWidget(self._channels_group)

        self._lbl_empty = QLabel(
            "Aún no hay dispositivos.\n"
            "Completa el formulario, prueba la conexión\n"
            "y guarda el dispositivo."
        )
        self._lbl_empty.setObjectName("EmptyLabel")
        self._lbl_empty.setAlignment(Qt.AlignCenter)
        root.addWidget(self._lbl_empty)
        return w

    # ── Carga inicial ─────────────────────────────────────────

    def _load_devices(self):
        for dev in self._repo.all():
            self._add_row(dev)
        self._update_empty()

    def _add_row(self, dev: DVRDevice):
        row = _DeviceRow(dev)
        row.sig_edit.connect(self._load_for_edit)
        row.sig_delete.connect(self._delete_device)
        idx = self._list_layout.count() - 1
        self._list_layout.insertWidget(idx, row)
        self._rows[dev.id] = row

    # ── Eventos formulario ────────────────────────────────────

    def _on_connection_type_changed(self, conn_type: str):
        is_hikconnect = conn_type == "Hik-Connect"
        # Mostrar/ocultar grupos
        self.grp_conn.setVisible(not is_hikconnect)
        self.grp_sdk.setVisible(not is_hikconnect)
        # Para credenciales, mostrar campos apropiados
        self.txt_user.setVisible(not is_hikconnect)
        self.lbl_appkey.setVisible(is_hikconnect)
        self.txt_appkey.setVisible(is_hikconnect)
        self.lbl_appsecret.setVisible(is_hikconnect)
        self.txt_appsecret.setVisible(is_hikconnect)
        # Cambiar título
        self._form_title.setText("Iniciar sesión desde Hik-Connect" if is_hikconnect else "Agregar dispositivo DVR")

    def _on_brand_changed(self, brand: str):
        self.txt_port.setText(str(DVRContext.default_port(brand)))
        self.grp_sdk.setVisible(DVRContext.needs_sdk(brand))

    def _browse_sdk(self):
        brand = self.cb_brand.currentText()
        f = "HCNetSDK (HCNetSDK.dll)" if "Hikvision" in brand else "NetSDK (dhnetsdk.dll)"
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar DLL", "", f";;Todos (*)")
        if path:
            self.txt_sdk.setText(path)

    # ── Prueba de conexión ────────────────────────────────────

    def _test_connection(self):
        conn_type = self.cb_connection_type.currentText()
        if conn_type == "Hik-Connect":
            appkey = self.txt_appkey.text().strip()
            appsecret = self.txt_appsecret.text().strip()
            if not appkey or not appsecret:
                self._log("⚠ Ingresa App Key y App Secret.", error=True)
                return
            brand = "Hik-Connect"
            host = ""
            port = 443
            username = appkey
            password = appsecret
            sdk_path = ""
        else:
            host = self.txt_host.text().strip()
            port = self.txt_port.text().strip()
            if not host or not port:
                self._log("⚠ Ingresa IP y puerto.", error=True)
                return
            brand = self.cb_brand.currentText()
            username = self.txt_user.text().strip()
            password = self.txt_pass.text()
            sdk_path = self.txt_sdk.text().strip()

        self._set_loading(True)
        self.log_box.setVisible(True)
        self.log_box.clear()
        self._log(f"Conectando a {brand}…")

        if self._worker and self._worker.isRunning():
            self._worker.quit()

        self._worker = DVRConnectWorker(
            brand    = brand,
            host     = host,
            port     = port,
            username = username,
            password = password,
            sdk_path = sdk_path,
        )
        self._worker.success.connect(self._on_connect_ok)
        self._worker.error.connect(self._on_connect_err)
        self._worker.start()

    def _on_connect_ok(self, info: DeviceInfo):
        self._last_info = info
        self._set_loading(False)
        self._log(f"✅ {info.brand} {info.model}  ·  Serie: {info.serial_number}")
        self._log(f"   Firmware: {info.firmware_version}  ·  {info.num_video_channels} canales")
        for ch in info.channels:
            self._log(f"   ▶ Canal {ch.id}: {ch.name}  —  {ch.rtsp_main}")
        self.btn_save.setEnabled(True)

    def _on_connect_err(self, msg: str):
        self._last_info = None
        self._set_loading(False)
        self._log(msg, error=True)
        self.btn_save.setEnabled(False)

    def _set_loading(self, loading: bool):
        self.progress.setVisible(loading)
        self.btn_test.setEnabled(not loading)
        self.btn_test.setText("⏳ Probando…" if loading else "🔌  Probar conexión")

    def _log(self, msg: str, error: bool = False):
        color = "#ff6b6b" if error else "#58a6ff"
        self.log_box.append(f'<span style="color:{color}">{msg}</span>')

    # ── Guardar ───────────────────────────────────────────────

    def _save_device(self):
        conn_type = self.cb_connection_type.currentText()
        alias = self.txt_alias.text().strip()
        if not alias:
            if conn_type == "Hik-Connect":
                alias = "Cuenta Hik-Connect"
            else:
                alias = f"{self.txt_host.text().strip()}:{self.txt_port.text().strip()}"

        dev = self._repo.get(self._editing_id) if self._editing_id else DVRDevice()
        if dev is None:
            dev = DVRDevice(id=self._editing_id)

        if conn_type == "Hik-Connect":
            dev.brand    = "Hik-Connect"
            dev.host     = ""
            dev.port     = 443
            dev.username = self.txt_appkey.text().strip()
            dev.password = self.txt_appsecret.text()
            dev.sdk_path = ""
        else:
            dev.brand    = self.cb_brand.currentText()
            dev.host     = self.txt_host.text().strip()
            dev.port     = int(self.txt_port.text().strip() or "80")
            dev.username = self.txt_user.text().strip()
            dev.password = self.txt_pass.text()
            dev.sdk_path = self.txt_sdk.text().strip()

        dev.alias = alias

        if self._last_info:
            dev.num_channels = self._last_info.num_video_channels
            dev.channels     = [ch.to_dict() for ch in self._last_info.channels]

        if self._editing_id:
            self._repo.update(dev)
            row = self._rows.get(dev.id)
            if row:
                row.refresh(dev)
        else:
            self._repo.add(dev)
            self._add_row(dev)

        self._update_empty()
        self._clear_form()
        self.devices_updated.emit()

    # ── Editar / eliminar ─────────────────────────────────────

    def _load_for_edit(self, device_id: str):
        dev = self._repo.get(device_id)
        if not dev:
            return
        self._editing_id = device_id
        self._last_info  = None
        self.txt_alias.setText(dev.alias)
        
        # Mostrar/cargar canales
        self._show_device_channels(dev)
        
        if dev.brand == "Hik-Connect":
            self.cb_connection_type.setCurrentText("Hik-Connect")
            self.txt_appkey.setText(dev.username)
            self.txt_appsecret.setText(dev.password)
            self.btn_logout.setVisible(True)
            self._form_title.setText("Sesión Hik-Connect")
        else:
            self.cb_connection_type.setCurrentText("Conexión por IP")
            idx = self.cb_brand.findText(dev.brand)
            if idx >= 0:
                self.cb_brand.setCurrentIndex(idx)
            self.txt_host.setText(dev.host)
            self.txt_port.setText(str(dev.port))
            self.txt_user.setText(dev.username)
            self.txt_pass.setText(dev.password)
            self.txt_sdk.setText(dev.sdk_path)
            self.btn_logout.setVisible(False)
            self._form_title.setText("Editar dispositivo")
        self.btn_save.setEnabled(True)
        self.log_box.setVisible(False)

    def _show_device_channels(self, dev: DVRDevice):
        """Muestra los canales del dispositivo en la lista."""
        # Limpiar canales anteriores
        while self._channels_list_layout.count() > 1:  # > 1 porque el último es stretch
            item = self._channels_list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not dev.channels:
            self._channels_group.setVisible(False)
            return

        self._channels_group.setVisible(True)
        
        for ch in dev.channels:
            ch_dict = ch if isinstance(ch, dict) else (ch.to_dict() if hasattr(ch, 'to_dict') else {})
            if not ch_dict:
                continue
            
            # Preparar datos del canal para drag&drop
            if dev.brand == "Hik-Connect":
                channel_data = HikConnectChannelEncoder.encode_channel(
                    device_alias   = dev.alias or "Cuenta HC",
                    channel_name   = ch_dict.get("name", ""),
                    rtsp_main      = ch_dict.get("rtsp_main", ""),
                    rtsp_sub       = ch_dict.get("rtsp_sub", ""),
                    channel_id     = ch_dict.get("id", ""),
                    device_serial  = dev.username,
                )
            else:
                channel_data = {
                    "device_alias":   dev.alias or dev.host,
                    "channel_name":   ch_dict.get("name", ""),
                    "rtsp_main":      ch_dict.get("rtsp_main", ""),
                    "rtsp_sub":       ch_dict.get("rtsp_sub", ""),
                    "is_hikconnect":  False,
                }
            
            row = ChannelRow(dev.id, channel_data)
            self._channels_list_layout.insertWidget(
                self._channels_list_layout.count() - 1, row  # Antes del stretch
            )

    def _delete_device(self, device_id: str):
        dev = self._repo.get(device_id)
        if not dev:
            return
        reply = QMessageBox.question(
            self, "Eliminar dispositivo",
            f"¿Eliminar '{dev.display_label()}'?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._repo.remove(device_id)
        row = self._rows.pop(device_id, None)
        if row:
            self._list_layout.removeWidget(row)
            row.deleteLater()
        self._update_empty()
        self.devices_updated.emit()

    def _logout_account(self):
        """Cierra sesión de una cuenta Hik-Connect."""
        if not self._editing_id:
            return
        dev = self._repo.get(self._editing_id)
        if not dev or dev.brand != "Hik-Connect":
            return
        
        reply = QMessageBox.question(
            self, "Cerrar sesión Hik-Connect",
            f"¿Desconectar '{dev.display_label()}'?\n"
            "Se eliminarán todos los canales asociados.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        
        # Eliminar la cuenta
        self._delete_device(self._editing_id)
        self._clear_form()
        self._log("✅ Sesión cerrada correctamente", error=False)

    def _clear_form(self):
        self._editing_id = None
        self._last_info  = None
        self.cb_connection_type.setCurrentText("Conexión por IP")
        self.txt_alias.clear()
        self.txt_host.clear()
        self.txt_port.setText("80")
        self.txt_user.setText("admin")
        self.txt_pass.clear()
        self.txt_appkey.clear()
        self.txt_appsecret.clear()
        self.txt_sdk.clear()
        self.cb_brand.setCurrentIndex(0)
        self.btn_save.setEnabled(False)
        self.btn_logout.setVisible(False)
        self._channels_group.setVisible(False)
        self.log_box.setVisible(False)
        self.log_box.clear()
        self._form_title.setText("Agregar dispositivo DVR")

    def _update_empty(self):
        self._lbl_empty.setVisible(len(self._rows) == 0)

    def get_repo(self) -> DVRRepository:
        return self._repo

    # ── Métodos públicos para los canales ──────────────────────

    def get_device_channels(self, device_id: str) -> list[dict]:
        """
        Retorna lista de canales del dispositivo en formato drag&drop.
        Para Hik-Connect, codifica con metadatos de encriptación.
        """
        dev = self._repo.get(device_id)
        if not dev:
            return []
        
        channels = []
        for ch in dev.channels:
            if isinstance(ch, dict):
                ch_dict = ch
            else:
                ch_dict = ch.to_dict() if hasattr(ch, 'to_dict') else {}
            
            # Si es Hik-Connect, codificar apropiadamente
            if dev.brand == "Hik-Connect":
                encoded = HikConnectChannelEncoder.encode_channel(
                    device_alias   = dev.alias or "Cuenta HC",
                    channel_name   = ch_dict.get("name", f"Canal {len(channels)+1}"),
                    rtsp_main      = ch_dict.get("rtsp_main", ""),
                    rtsp_sub       = ch_dict.get("rtsp_sub", ""),
                    channel_id     = ch_dict.get("id", ""),
                    device_serial  = dev.username,  # App Key en serial temporal
                )
                channels.append(encoded)
            else:
                # Para IP, usar directamente
                channels.append({
                    "device_alias":   dev.alias or dev.host,
                    "channel_name":   ch_dict.get("name", ""),
                    "rtsp_main":      ch_dict.get("rtsp_main", ""),
                    "rtsp_sub":       ch_dict.get("rtsp_sub", ""),
                    "is_hikconnect":  False,
                })
        return channels

    def logout_hikconnect(self, device_id: str) -> bool:
        """
        Elimina una cuenta Hik-Connect y todos sus canales asociados.
        """
        dev = self._repo.get(device_id)
        if dev and dev.brand == "Hik-Connect":
            self._delete_device(device_id)
            return True
        return False

    # ── Estilos ───────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background:#0d1117; color:#c9d1d9;
                font-family:'Segoe UI',sans-serif; font-size:13px; }
            #FormPanel  { background:#0d1117; border-right:1px solid #21262d; }
            #ListPanel  { background:#0d1117; }
            #FormTitle, #ListTitle { font-size:15px; font-weight:700; color:#e6edf3; }
            #FormSep    { color:#21262d; }
            QGroupBox   { border:1px solid #30363d; border-radius:6px; margin-top:8px;
                color:#8b949e; font-size:11px; font-weight:600; }
            QGroupBox::title { subcontrol-origin:margin; left:10px;
                background:#0d1117; padding:0 4px; }
            QLineEdit, QComboBox { background:#161b22; border:1px solid #30363d;
                border-radius:5px; padding:6px 8px; color:#e6edf3; }
            QLineEdit:focus, QComboBox:focus { border-color:#58a6ff; }
            QComboBox QAbstractItemView { background:#161b22; color:#c9d1d9;
                selection-background-color:#21262d; }
            QLabel { color:#8b949e; font-size:12px; }
            #BtnTest { background:#1f2d3d; color:#58a6ff; border:1px solid #1f6feb;
                border-radius:6px; font-size:13px; font-weight:600; }
            #BtnTest:hover { background:#1f6feb; color:#fff; }
            #BtnTest:disabled { background:#161b22; color:#6e7681; border-color:#30363d; }
            #BtnSave { background:#238636; color:#fff; border:none;
                border-radius:6px; font-size:13px; font-weight:600; }
            #BtnSave:hover { background:#2ea043; }
            #BtnSave:disabled { background:#161b22; color:#6e7681; }
            #BtnSecondary { background:#21262d; color:#8b949e; border:1px solid #30363d;
                border-radius:6px; padding:6px 14px; }
            #BtnQuick { background:#161b22; color:#6e7681; border:1px solid #30363d;
                border-radius:4px; font-size:11px; }
            #BtnQuick:hover { background:#21262d; color:#c9d1d9; }
            #LogBox { background:#0a0e13; border:1px solid #21262d; border-radius:5px;
                color:#c9d1d9; font-family:'Courier New',monospace; font-size:11px; }
            QProgressBar { border:none; background:#21262d; border-radius:2px; }
            QProgressBar::chunk { background:#1f6feb; border-radius:2px; }
            #DeviceRow { background:#161b22; border:1px solid #21262d; border-radius:7px; }
            #DeviceRow:hover { border-color:#30363d; }
            #RowDot  { color:#3fb950; font-size:13px; }
            #RowName { font-size:13px; font-weight:600; color:#e6edf3; }
            #RowSub  { font-size:11px; color:#6e7681; }
            #BtnRowIcon { background:#21262d; border:1px solid #30363d;
                border-radius:4px; font-size:12px; color:#8b949e; }
            #BtnRowIcon:hover { background:#30363d; color:#c9d1d9; }
            #BtnRowDel { background:#21262d; border:1px solid #30363d;
                border-radius:4px; font-size:12px; color:#8b949e; }
            #BtnRowDel:hover { background:#2d1212; color:#ff6b6b; border-color:#5a1a1a; }
            #EmptyLabel { color:#6e7681; font-size:13px; padding:30px; }
            QScrollArea { border:none; background:transparent; }
            QScrollBar:vertical { background:#0d1117; width:6px; border-radius:3px; }
            QScrollBar::handle:vertical { background:#30363d; border-radius:3px; }
            QSplitter::handle { background:#21262d; }
        """)
