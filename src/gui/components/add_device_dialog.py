from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt



class AddDeviceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Dispositivo DVR")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedWidth(350)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
            }
            QLabel {
                color: white;
                min-width: 80px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                min-width: 200px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: 1px solid #666;
                padding: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """)
        self.setup_ui()



    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # Espacio entre widgets

        # Título
        title_label = QLabel("Agrega Dispositivo")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title_label)

        layout.addSpacing(20)  # Espacio después del título

        # Nombre
        name_layout = QHBoxLayout()
        name_label = QLabel("Nombre:")
        self.name_edit = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # IP
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP:")
        self.ip_edit = QLineEdit()
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_edit)
        layout.addLayout(ip_layout)

        # Puerto HTTP
        http_port_layout = QHBoxLayout()
        http_port_label = QLabel("Puerto HTTP:")
        self.http_port_edit = QLineEdit()
        http_port_layout.addWidget(http_port_label)
        http_port_layout.addWidget(self.http_port_edit)
        layout.addLayout(http_port_layout)

        # Puerto RTSP
        rtsp_port_layout = QHBoxLayout()
        rtsp_port_label = QLabel("Puerto RTSP:")
        self.rtsp_port_edit = QLineEdit()
        rtsp_port_layout.addWidget(rtsp_port_label)
        rtsp_port_layout.addWidget(self.rtsp_port_edit)
        layout.addLayout(rtsp_port_layout)

        # Usuario
        user_layout = QHBoxLayout()
        user_label = QLabel("Usuario:")
        self.user_edit = QLineEdit()
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_edit)
        layout.addLayout(user_layout)

        # Clave
        password_layout = QHBoxLayout()
        password_label = QLabel("Clave:")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_edit)
        layout.addLayout(password_layout)

        layout.addSpacing(20)  # Espacio antes de los botones

        # Botones
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Agregar")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)
        layout.addLayout(buttons_layout)



    def get_device_data(self):
        return {
            'name': self.name_edit.text(),
            'ip': self.ip_edit.text(),
            'http_port': self.http_port_edit.text(),
            'rtsp_port': self.rtsp_port_edit.text(),
            'user': self.user_edit.text(),
            'password': self.password_edit.text()
        }