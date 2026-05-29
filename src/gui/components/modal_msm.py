from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTextEdit, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import os



class ModalDialog(QDialog):
    def __init__(self, titulo="Error", descripcion="Ha ocurrido un error", tipo_error="general", parent=None):
        super().__init__(parent)
        self.titulo = titulo
        self.descripcion = descripcion
        self.tipo_error = tipo_error.lower()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(self.titulo)
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        # Hacer la ventana siempre encima
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Contenido principal
        content_layout = QHBoxLayout()
        
        # Sección de imagen (izquierda)
        image_section = self.create_image_section()
        content_layout.addWidget(image_section)
        
        # Sección de texto (derecha)
        text_section = self.create_text_section()
        content_layout.addWidget(text_section)
        
        layout.addLayout(content_layout)
        
        # Botones
        button_layout = self.create_buttons()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Aplicar estilos
        self.apply_styles()
    
    def create_image_section(self):
        """Crear la sección de imagen basada en el tipo de error"""
        image_widget = QWidget()
        image_layout = QVBoxLayout()
        image_layout.setAlignment(Qt.AlignCenter)
        
        # Etiqueta para la imagen
        self.image_label = QLabel()
        self.image_label.setFixedSize(128, 128)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        # Cargar imagen según el tipo de error
        self.load_error_image()
        
        image_layout.addWidget(self.image_label)
        image_widget.setLayout(image_layout)
        return image_widget
    
    def load_error_image(self):
        """Cargar la imagen correspondiente al tipo de error"""
        # Mapeo de tipos de error a imágenes/emoji
        error_images = {
            "admin": "🔒",  # Icono de candado
            "permisos": "🚫",  # Icono de prohibido
            "conexion": "📡",  # Icono de conexión
            "archivo": "📁",  # Icono de archivo
            "captura": "📷",  # Icono de cámara
            "ventana": "🪟",  # Icono de ventana
            "general": "❌",  # Icono de error general
            "advertencia": "⚠️",  # Icono de advertencia
            "info": "ℹ️",   # Icono de información
            "exito": "✅"   # Icono de éxito
        }
        
        # Obtener emoji o usar uno por defecto
        emoji = error_images.get(self.tipo_error, "❓")
        
        # Crear un pixmap simple con el emoji (en una app real, cargarías imágenes reales)
        self.image_label.setText(emoji)
        self.image_label.setStyleSheet("""
            font-size: 80px;
            background-color: #34495e;
            border-radius: 15px;
            padding: 20px;
        """)
        
        # Alternativa: Cargar imagen desde archivo si existe
        image_path = f"resources/{self.tipo_error}.png"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.image_label.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def create_text_section(self):
        """Crear la sección de texto"""
        text_widget = QWidget()
        text_layout = QVBoxLayout()
        
        # Título
        title_label = QLabel(self.titulo)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Descripción
        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setPlainText(self.descripcion)
        desc_text.setFixedHeight(150)
        
        # Tipo de error
        type_label = QLabel(f"Tipo: {self.tipo_error.upper()}")
        type_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_text)
        text_layout.addWidget(type_label)
        text_widget.setLayout(text_layout)
        
        return text_widget
    
    def create_buttons(self):
        """Crear los botones de acción"""
        button_layout = QHBoxLayout()
        
        # Botón de cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.setFixedHeight(35)
        close_btn.clicked.connect(self.accept)
        
        # Botón de detalles (opcional)
        details_btn = QPushButton("Ver Detalles")
        details_btn.setFixedHeight(35)
        details_btn.clicked.connect(self.show_details)
        
        button_layout.addWidget(details_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        return button_layout
    
    def apply_styles(self):
        """Aplicar estilos a la ventana"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 2px solid #34495e;
                border-radius: 10px;
            }
            QTextEdit {
                background-color: #34495e;
                border: 1px solid #5a6c7d;
                border-radius: 5px;
                color: #ecf0f1;
                padding: 8px;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
    
    def show_details(self):
        """Mostrar detalles adicionales del error"""
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle("Detalles del Error")
        details_dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        details_text = QTextEdit()
        details_text.setPlainText(
            f"Título: {self.titulo}\n"
            f"Tipo: {self.tipo_error}\n"
            f"Descripción: {self.descripcion}\n\n"
            f"Información técnica:\n"
            f"- Timestamp: ...\n"
            f"- Contexto: ...\n"
            f"- Solución sugerida: ..."
        )
        details_text.setReadOnly(True)
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(details_dialog.accept)
        
        layout.addWidget(details_text)
        layout.addWidget(close_btn)
        
        details_dialog.setLayout(layout)
        details_dialog.exec()

