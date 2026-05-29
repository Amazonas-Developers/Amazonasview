import os
from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap ,QPainter, QColor



class SplashScreen(QSplashScreen):

    def __init__(self, image_path='src/resources/logo.ico', message='Iniciando...'):
        # ✅ TAMAÑO EXACTO: 600x400 con fondo gris
        pixmap = QPixmap(600, 400)
        pixmap.fill(QColor("#222222"))  # Fondo gris exacto


        if image_path and os.path.exists(image_path):
            logo = QPixmap(image_path)
            logo_scaled = logo.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter = QPainter(pixmap)
                    
                    # ✅ CENTRAR EXACTO: (600-200)/2 = 200, (400-200)/2 = 100
            x = (600 - 200) // 2  # 200px desde la izquierda
            y = (400 - 200) // 2  # 100px desde arriba
                    
            painter.drawPixmap(x, y, logo_scaled)
            painter.end()

          
            
        super().__init__(pixmap)
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        self.showMessage(
            message,
            alignment=Qt.AlignBottom | Qt.AlignCenter,
            color=Qt.white
        )


    def mousePressEvent(self, arg__1):
        pass