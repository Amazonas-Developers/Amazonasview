from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath, QFontMetrics, QMouseEvent,  QDrag
from PySide6.QtCore import Qt, QTimer, Slot, QRect, QMimeData,QByteArray

from core.capture_exaple import capture_window_by_hwnd, pil_image_to_png_bytes
from core.window_controller import set_window_always_on_top
from core.state_global.hwnd import hwndState



class Box_cap(QWidget):


    def __init__(self, window):
        super().__init__()
        self.id_windows = window['hwnd']
        self.title = window['title']
        self.set_ui()



    def set_ui(self):
        self.setObjectName('box-hwnd-self.id_windows}')
        print(f'initializing in window window: {self.id_windows}\ntitle: {self.title}')

        layaut_content = QHBoxLayout(self)
        layaut_content.setContentsMargins(0,0,0,0)
        self.image_label = QLabel()
        layaut_content.addWidget(self.image_label)
        self.update_frame()




    def cap_img(self):
        if(self.activateWindow): set_window_always_on_top(self.id_windows)
        image_buffer = capture_window_by_hwnd(self.id_windows)
        return  pil_image_to_png_bytes( image_buffer)





    def update_frame(self):

        image = QPixmap()
        image.loadFromData(self.cap_img(), 'png')
        image = image.scaled(180, 140, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        painter_text = QPainter(image)
        painter_text.setRenderHint(QPainter.Antialiasing)
        painter_text.setRenderHint(QPainter.TextAntialiasing)

        font = QFont('Arial', 10)
        painter_text.setFont(font)
        fm = QFontMetrics(font)

        text_path = QPainterPath()

        lineas = f"{self.title}\n{self.id_windows}".split("\n")
        x, y = 5, 20
        line_height = fm.height()

        for i, linea in enumerate(lineas):
            text_path.addText(x, y + i * line_height, font, linea)

        # Borde negro
        painter_text.setPen(QColor('black'))
        painter_text.setBrush(Qt.NoBrush)
        painter_text.strokePath(text_path, painter_text.pen())

        # Relleno amarillo
        painter_text.setPen(Qt.NoPen)
        painter_text.setBrush(QColor("#4eff2b"))
        painter_text.fillPath(text_path, painter_text.brush())
        painter_text.end()

        self.image_label.setPixmap(image)





    def mousePressEvent(self, event):
         if event.button() == Qt.LeftButton:
            # 1. Crear el objeto QDrag
            drag = QDrag(self)

            # 2. Crear y asignar datos MIME
            mime = self.build_mime()

            drag.setMimeData(mime)

            # 3. Pixmap para feedback visual
            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())

            # 4. Ejecutar el arrastre
            drag.exec(Qt.CopyAction)



    def build_mime(self):
        mime = QMimeData()
        payload = f'{self.id_windows}|{self.title}'
        mime.setData("application/x-boxcap", QByteArray(payload.encode("utf-8")))
        return mime
