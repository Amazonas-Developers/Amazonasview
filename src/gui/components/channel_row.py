"""
src/gui/components/channel_row.py
Fila de canal con soporte drag & drop.

Permite arrastrar canales Hik-Connect e IP al render_box.
"""
from __future__ import annotations
import json
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray
from PySide6.QtGui import QDrag, QMouseEvent

_DVR_MIME = "application/x-dvr-channel"


class ChannelRow(QFrame):
    """Fila arrastrables de un canal DVR/Hik-Connect."""
    
    deleted = Signal(str)  # channel_id

    def __init__(self, device_id: str, channel_data: dict, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.channel_data = channel_data
        self.channel_id = channel_data.get("id") or channel_data.get("channel_id", "")
        
        self.setObjectName("ChannelRow")
        self.setFixedHeight(48)
        self.setCursor(Qt.OpenHandCursor)
        self.setAcceptDrops(False)  # Solo queremos arrastrar, no soltar aquí

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Indicador de tipo
        is_hik = channel_data.get("is_hikconnect", False)
        indicator = QLabel("🔐" if is_hik else "📹")
        indicator.setFixedWidth(20)

        # Info del canal
        col = QVBoxLayout()
        col.setSpacing(2)
        
        name = QLabel(channel_data.get("channel_name", "Canal desconocido"))
        name.setObjectName("ChannelName")
        name.setStyleSheet("font-weight: 600; color: #e6edf3;")
        
        device_name = QLabel(f"Dispositivo: {channel_data.get('device_alias', 'N/A')}")
        device_name.setObjectName("ChannelDevice")
        device_name.setStyleSheet("font-size: 11px; color: #8b949e;")
        
        col.addWidget(name)
        col.addWidget(device_name)

        layout.addWidget(indicator)
        layout.addLayout(col, stretch=1)

        # Botón de eliminación
        btn_del = QPushButton("✕")
        btn_del.setObjectName("ChannelDelBtn")
        btn_del.setFixedSize(24, 24)
        btn_del.setToolTip("Eliminar")
        btn_del.clicked.connect(lambda: self.deleted.emit(self.channel_id))
        layout.addWidget(btn_del)

    def mousePressEvent(self, event: QMouseEvent):
        """Inicia drag al presionar el mouse."""
        if event.button() == Qt.LeftButton:
            self._start_drag(event.pos())
        super().mousePressEvent(event)

    def _start_drag(self, pos):
        """Inicia operación de drag & drop."""
        drag = QDrag(self)
        
        # Crear MIME data
        mime = QMimeData()
        data_json = json.dumps(self.channel_data, ensure_ascii=False)
        mime.setData(_DVR_MIME, QByteArray(data_json.encode("utf-8")))
        
        # Establecer pixmap y ejecutar drag
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction | Qt.MoveAction)
