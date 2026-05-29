"""
src/gui/components/sidebar/dvr_tree.py
Árbol sidebar con DVRs y canales arrastrables.
"""
from __future__ import annotations
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QToolButton, QHBoxLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, QMimeData, QByteArray
from PySide6.QtGui  import QDrag, QPixmap, QPainter, QColor, QFont

from models.dvr_storage import DVRDevice

CAMERA_MIME = "application/x-dvr-channel"


class ChannelItem(QFrame):
    def __init__(self, device: DVRDevice, channel: dict, parent=None):
        super().__init__(parent)
        self._device  = device
        self._channel = channel
        self.setObjectName("ChannelItem")
        self.setCursor(Qt.OpenHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 4, 8, 4)

        dot = QLabel("▶")
        dot.setObjectName("ChDot")
        dot.setFixedWidth(14)

        ch_name = channel.get("name") or f"Canal {channel['id']}"
        lbl = QLabel(f"  {ch_name}")
        lbl.setObjectName("ChName")

        layout.addWidget(dot)
        layout.addWidget(lbl, stretch=1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return

        drag    = QDrag(self)
        mime    = QMimeData()
        payload = json.dumps({
            "device_id":    self._device.id,
            "device_alias": self._device.alias,
            "channel_id":   self._channel["id"],
            "channel_name": self._channel.get("name", ""),
            "rtsp_main":    self._channel.get("rtsp_main", ""),
            "rtsp_sub":     self._channel.get("rtsp_sub", ""),
        }).encode()

        mime.setData(CAMERA_MIME, QByteArray(payload))
        drag.setMimeData(mime)
        drag.setPixmap(self._drag_pixmap())
        drag.setHotSpot(self._drag_pixmap().rect().center())

        self.setCursor(Qt.ClosedHandCursor)
        drag.exec(Qt.CopyAction)
        self.setCursor(Qt.OpenHandCursor)

    def _drag_pixmap(self) -> QPixmap:
        name = self._channel.get("name", "Canal")
        pix  = QPixmap(180, 28)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#1f6feb"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 180, 28, 6, 6)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(pix.rect(), Qt.AlignCenter, f"▶  {name}")
        p.end()
        return pix


class DVRGroupItem(QWidget):
    def __init__(self, device: DVRDevice, parent=None):
        super().__init__(parent)
        self._device   = device
        self._expanded = True
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 4)
        root.setSpacing(0)

        hdr = QFrame()
        hdr.setObjectName("DVRGroupHeader")
        hdr.setCursor(Qt.PointingHandCursor)
        hdr.mouseReleaseEvent = lambda e: self._toggle()

        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(10, 6, 8, 6)

        self._btn_toggle = QToolButton()
        self._btn_toggle.setObjectName("BtnToggle")
        self._btn_toggle.setArrowType(Qt.DownArrow)
        self._btn_toggle.setFixedSize(16, 16)
        self._btn_toggle.clicked.connect(self._toggle)

        lbl_name  = QLabel(self._device.alias or self._device.host)
        lbl_name.setObjectName("DVRGroupName")
        lbl_count = QLabel(f"{self._device.num_channels} ch")
        lbl_count.setObjectName("DVRGroupCount")

        hdr_layout.addWidget(self._btn_toggle)
        hdr_layout.addWidget(lbl_name, stretch=1)
        hdr_layout.addWidget(lbl_count)
        root.addWidget(hdr)

        self._ch_widget = QWidget()
        self._ch_widget.setObjectName("ChannelsContainer")
        ch_layout = QVBoxLayout(self._ch_widget)
        ch_layout.setContentsMargins(0, 0, 0, 0)
        ch_layout.setSpacing(1)

        for ch in self._device.channels:
            ch_layout.addWidget(ChannelItem(self._device, ch))

        if not self._device.channels:
            no_ch = QLabel("  Sin canales registrados")
            no_ch.setObjectName("ChName")
            ch_layout.addWidget(no_ch)

        root.addWidget(self._ch_widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self._ch_widget.setVisible(self._expanded)
        self._btn_toggle.setArrowType(
            Qt.DownArrow if self._expanded else Qt.RightArrow
        )


class DVRTree(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: dict[str, DVRGroupItem] = {}
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QLabel("CÁMARAS DVR")
        hdr.setObjectName("SidebarSectionTitle")
        root.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 4, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.addStretch()

        scroll.setWidget(self._content)
        root.addWidget(scroll, stretch=1)

        self._empty = QLabel("Agrega un DVR en la\npestaña Dispositivos")
        self._empty.setObjectName("SidebarEmpty")
        self._empty.setAlignment(Qt.AlignCenter)
        root.addWidget(self._empty)

    def refresh(self, devices: list[DVRDevice]):
        for g in self._groups.values():
            self._content_layout.removeWidget(g)
            g.deleteLater()
        self._groups.clear()

        for dev in devices:
            if dev.channels:
                group = DVRGroupItem(dev)
                idx   = self._content_layout.count() - 1
                self._content_layout.insertWidget(idx, group)
                self._groups[dev.id] = group

        self._empty.setVisible(len(self._groups) == 0)

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { background:transparent; }
            #SidebarSectionTitle { font-size:10px; font-weight:700; color:#6e7681;
                letter-spacing:1px; padding:8px 12px 4px 12px; }
            #SidebarEmpty { color:#6e7681; font-size:12px; padding:20px; }
            #DVRGroupHeader { background:#161b22; border-radius:6px;
                border:1px solid #21262d; }
            #DVRGroupHeader:hover { background:#1c2128; }
            #DVRGroupName  { font-size:12px; font-weight:600; color:#c9d1d9; }
            #DVRGroupCount { font-size:10px; color:#6e7681; }
            #BtnToggle { border:none; background:transparent; color:#6e7681; }
            #ChannelItem { background:transparent; border-radius:4px; border:none; }
            #ChannelItem:hover { background:#1c2128; }
            #ChDot  { color:#3fb950; font-size:10px; }
            #ChName { font-size:12px; color:#8b949e; }
            #ChannelsContainer { background:transparent; }
            QScrollArea { border:none; background:transparent; }
            QScrollBar:vertical { background:transparent; width:4px; }
            QScrollBar::handle:vertical { background:#30363d; border-radius:2px; }
        """)
