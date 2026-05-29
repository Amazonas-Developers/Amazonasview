"""
AlertsSidebar (Amazonas View) – Panel lateral con una sola columna
'Alerta en vivo' que muestra las fotos tomadas por el sistema.
"""

import base64
import os
import subprocess
import time
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QFrame, QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal, Slot, QByteArray, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QFont, QIcon


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────
MAX_ALERTS = 200           # Máximo de alertas en el historial antes de descartar las más antiguas
AUTO_CLEAR_EVERY = 80      # Cada N fotos, el banner se vacía automáticamente
CROP_THUMB_WIDTH = 380     # Ancho de la imagen de la alerta en px (layout vertical)
CROP_THUMB_HEIGHT = 240    # Alto maximo de la imagen en px


# Colores por tipo de evento
EVENT_COLORS = {
    "Entrada":        "#2ecc71",   # verde
    "Salida":         "#e74c3c",   # rojo
    "Entrada Puerta": "#3498db",   # azul
    "Salida Puerta":  "#e67e22",   # naranja
    "Permanencia":    "#f1c40f",   # amarillo
    "Alerta":         "#e74c3c",   # rojo
}

EVENT_ICONS = {
    "Entrada":        "▶",
    "Salida":         "◀",
    "Entrada Puerta": "🚪▶",
    "Salida Puerta":  "🚪◀",
    "Permanencia":    "⏱",
    "Alerta":         "⚠",
}

DEFAULT_COLOR = "#95a5a6"


# ─────────────────────────────────────────────────────────────────────────────
# Widget individual de alerta
# ─────────────────────────────────────────────────────────────────────────────

class AlertItemWidget(QFrame):
    """Representa una sola alerta en la lista."""

    def __init__(self, alert_data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("AlertItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Guardar ruta del screenshot para abrir al hacer click
        self._screenshot_path = alert_data.get("screenshot_path", "")

        event_type = alert_data.get("event_type", "Alerta")
        # Renombrar "toma de orden" -> "Alerta en vivo" en Amazonas View
        if str(event_type).strip().lower() in ("toma de orden", "toma_de_orden", "order"):
            event_type = "Alerta en vivo"
        class_name = alert_data.get("class_name", "Desconocido")
        description = alert_data.get("description", "")
        timestamp = alert_data.get("timestamp", time.time())
        crop_b64 = alert_data.get("crop_image", "") or alert_data.get("image_base64", "")
        camera_id = alert_data.get("camera_id", "")

        color = EVENT_COLORS.get(event_type, DEFAULT_COLOR)
        icon_text = EVENT_ICONS.get(event_type, "●")

        # ── Formatear hora ──
        try:
            if isinstance(timestamp, str):
                raw_timestamp = timestamp.strip()
                if raw_timestamp:
                    if raw_timestamp.endswith("Z"):
                        raw_timestamp = raw_timestamp[:-1] + "+00:00"
                    dt = datetime.fromisoformat(raw_timestamp)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone().replace(tzinfo=None)
                else:
                    dt = datetime.fromtimestamp(time.time())
            else:
                dt = datetime.fromtimestamp(float(timestamp))
            time_str = dt.strftime("%H:%M:%S")
        except (ValueError, TypeError, OSError):
            time_str = "--:--:--"

        # ── Estilo del frame ──
        self.setStyleSheet(f"""
            #AlertItem {{
                background-color: #1e1e1e;
                border-left: 3px solid {color};
                border-radius: 4px;
                margin: 2px 4px;
                padding: 6px;
            }}
            #AlertItem:hover {{
                background-color: #2a2a2a;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # ── Imagen grande del crop ──
        if crop_b64:
            thumb_label = QLabel()
            thumb_label.setMinimumWidth(CROP_THUMB_WIDTH)
            thumb_label.setMaximumHeight(CROP_THUMB_HEIGHT)
            thumb_label.setStyleSheet("border-radius: 4px; background-color: #111;")
            try:
                pixmap = QPixmap()
                raw = base64.b64decode(crop_b64)
                pixmap.loadFromData(QByteArray(raw))
                if not pixmap.isNull():
                    thumb_label.setPixmap(
                        pixmap.scaled(
                            CROP_THUMB_WIDTH, CROP_THUMB_HEIGHT,
                            Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    thumb_label.setAlignment(Qt.AlignCenter)
            except Exception:
                thumb_label.setText("?")
                thumb_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(thumb_label)

        # ── Texto ──
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # Línea superior: icono + tipo + clase
        header_label = QLabel(f"{icon_text}  {event_type} — {class_name}")
        header_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        header_label.setWordWrap(True)
        text_layout.addWidget(header_label)

        # Descripción
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #b0b0b0; font-size: 11px; background: transparent; border: none;")
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        # Pie: hora + cámara
        footer_parts = [f"🕐 {time_str}"]
        if camera_id:
            footer_parts.append(f"📷 Cam {camera_id}")
        footer_label = QLabel("  ".join(footer_parts))
        footer_label.setStyleSheet("color: #666; font-size: 10px; background: transparent; border: none;")
        text_layout.addWidget(footer_label)

        layout.addLayout(text_layout)

    def mouseReleaseEvent(self, event):
        """Al hacer click en la alerta, abre la carpeta que contiene el screenshot."""
        if event.button() == Qt.LeftButton and self._screenshot_path:
            path = self._screenshot_path
            if os.path.isfile(path):
                # Abre Explorer con el archivo seleccionado
                subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
            elif os.path.isdir(os.path.dirname(path)):
                # Si el archivo no existe pero la carpeta sí, abre la carpeta
                subprocess.Popen(['explorer', os.path.normpath(os.path.dirname(path))])
        super().mouseReleaseEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# Columna individual de alertas (usada internamente por AlertsSidebar)
# ─────────────────────────────────────────────────────────────────────────────

class _AlertColumn(QWidget):
    """Una columna con header, scroll de alertas y contador propio."""

    def __init__(self, title: str, icon: str, color: str, max_alerts: int = MAX_ALERTS, parent=None):
        super().__init__(parent)
        self.max_alerts = max_alerts
        self.alert_count = 0
        self._color = color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header de columna ──
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #333333, stop:1 #292929
            );
            border-bottom: 1px solid #444;
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(6, 0, 6, 0)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        header_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        header_layout.addWidget(title_label, stretch=1)

        self.badge_label = QLabel("0")
        self.badge_label.setFixedSize(24, 16)
        self.badge_label.setAlignment(Qt.AlignCenter)
        self._update_badge_style()
        header_layout.addWidget(self.badge_label)

        layout.addWidget(header)

        # ── Scroll area ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.alerts_container = QWidget()
        self.alerts_container.setStyleSheet("background: transparent;")
        self.alerts_layout = QVBoxLayout(self.alerts_container)
        self.alerts_layout.setContentsMargins(2, 2, 2, 2)
        self.alerts_layout.setSpacing(3)
        self.alerts_layout.setAlignment(Qt.AlignTop)

        self.empty_label = QLabel("Sin alertas")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #555; font-size: 10px; padding: 20px; background: transparent; border: none;")
        self.alerts_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.alerts_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # ── Footer ──
        self.count_label = QLabel("0")
        self.count_label.setFixedHeight(20)
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setStyleSheet("color: #666; font-size: 9px; background-color: #222; border-top: 1px solid #333;")
        layout.addWidget(self.count_label)

    def add_alert(self, alert_data: dict):
        if self.empty_label.isVisible():
            self.empty_label.hide()

        item = AlertItemWidget(alert_data)
        self.alerts_layout.insertWidget(0, item)
        self.alert_count += 1
        self._update_counters()

        while self.alerts_layout.count() > self.max_alerts + 1:
            idx = self.alerts_layout.count() - 1
            layout_item = self.alerts_layout.itemAt(idx)
            if layout_item and layout_item.widget() and layout_item.widget() != self.empty_label:
                w = layout_item.widget()
                self.alerts_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
                self.alert_count = max(0, self.alert_count - 1)

        self.scroll_area.verticalScrollBar().setValue(0)

    def clear(self):
        while self.alerts_layout.count():
            item = self.alerts_layout.takeAt(0)
            widget = item.widget()
            if widget and widget != self.empty_label:
                widget.setParent(None)
                widget.deleteLater()
        self.alert_count = 0
        self._update_counters()
        self.empty_label.show()
        self.alerts_layout.addWidget(self.empty_label)

    def _update_counters(self):
        self.count_label.setText(f"{self.alert_count}")
        self._update_badge_style()

    def _update_badge_style(self):
        self.badge_label.setText(str(min(self.alert_count, 999)))
        if self.alert_count == 0:
            bg = "#555"
        elif self.alert_count < 10:
            bg = "#e67e22"
        else:
            bg = "#e74c3c"
        self.badge_label.setStyleSheet(f"""
            background-color: {bg}; color: white; font-size: 9px;
            font-weight: bold; border-radius: 8px; border: none;
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Panel lateral de alertas (1 columna - Amazonas View)
# ─────────────────────────────────────────────────────────────────────────────


class AlertsSidebar(QWidget):
    """
    Sidebar con una sola columna ancha 'Alerta en vivo'
    que muestra todas las fotos tomadas.
    """

    new_alert = Signal(dict)

    def __init__(self, parent=None, title="Alertas IA", max_alerts=MAX_ALERTS,
                 auto_clear_every=AUTO_CLEAR_EVERY):
        super().__init__(parent)
        self.max_alerts = max_alerts
        self.auto_clear_every = auto_clear_every
        self._photos_since_clear = 0
        self._title = title
        self._setup_ui()
        self.new_alert.connect(self.add_alert)

    def _setup_ui(self):
        self.setObjectName("AlertsSidebar")
        self.setFixedWidth(420)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            #AlertsSidebar {
                background-color: #1a1a1a;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header global ──
        header = QWidget()
        header.setObjectName("AlertsSidebarHeader")
        header.setFixedHeight(38)
        header.setStyleSheet("""
            #AlertsSidebarHeader {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #333333, stop:1 #292929
                );
                border-bottom: 1px solid #444;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)

        icon_label = QLabel("🔔")
        icon_label.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        header_layout.addWidget(icon_label)

        title_label = QLabel(self._title)
        title_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        header_layout.addWidget(title_label, stretch=1)

        self.badge_label = QLabel("0")
        self.badge_label.setFixedSize(28, 18)
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.setStyleSheet("""
            background-color: #555; color: white; font-size: 9px;
            font-weight: bold; border-radius: 9px; border: none;
        """)
        header_layout.addWidget(self.badge_label)

        btn_clear = QPushButton("Limpiar")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setFixedHeight(22)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888; font-size: 9px;
                border: 1px solid #555; border-radius: 3px;
                padding: 2px 6px;
            }
            QPushButton:hover { color: #fff; border-color: #888; }
        """)
        btn_clear.clicked.connect(self.clear_alerts)
        header_layout.addWidget(btn_clear)

        root_layout.addWidget(header)

        # ── Una sola columna ancha ──
        columns_widget = QWidget()
        columns_widget.setStyleSheet("background: transparent;")
        columns_layout = QHBoxLayout(columns_widget)
        columns_layout.setContentsMargins(2, 2, 2, 2)
        columns_layout.setSpacing(0)

        self.col_alerts = _AlertColumn(
            title="Alerta en vivo",
            icon="📸",
            color="#00c8ff",
            max_alerts=self.max_alerts,
        )

        columns_layout.addWidget(self.col_alerts, stretch=1)

        root_layout.addWidget(columns_widget, stretch=1)

    # ─────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────

    @Slot(dict)
    def add_alert(self, alert_data: dict):
        """Agrega la alerta a la columna unificada.

        Cada `auto_clear_every` fotos, el banner se vacía automáticamente
        antes de insertar la nueva foto, para que la última siempre quede visible.
        """
        if self.auto_clear_every > 0 and self._photos_since_clear >= self.auto_clear_every:
            self.col_alerts.clear()
            self._photos_since_clear = 0

        self.col_alerts.add_alert(alert_data)
        self._photos_since_clear += 1
        self._update_global_badge()

    @Slot()
    def clear_alerts(self):
        """Limpia la columna."""
        self.col_alerts.clear()
        self._photos_since_clear = 0
        self._update_global_badge()

    def _update_global_badge(self):
        total = self.col_alerts.alert_count
        self.badge_label.setText(str(min(total, 999)))
        if total == 0:
            bg = "#555"
        elif total < 10:
            bg = "#e67e22"
        else:
            bg = "#e74c3c"
        self.badge_label.setStyleSheet(f"""
            background-color: {bg}; color: white; font-size: 9px;
            font-weight: bold; border-radius: 9px; border: none;
        """)
