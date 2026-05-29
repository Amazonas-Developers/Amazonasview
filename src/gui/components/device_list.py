from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from gui.components.add_device_dialog import AddDeviceDialog
from hikvisionapi import Client



class ConnectionCheckThread(QThread):
    
    ###  _STATUS DEVICE _INFO DEVICE _GET_FRAME

    result = Signal(int, bool)  # index, connected
    

    def __init__(self, devices):
        super().__init__()
        self.devices = devices
        

    def run(self):
        for i, device in enumerate(self.devices):
            try:
                cam = Client(f"http://{device['ip']}:{device.get('http_port', '80')}", device['user'], device['password'])
                # Try to get system info to check connection
                info = cam.System.deviceInfo()
                connected = True
            except:
                connected = False
            self.result.emit(i, connected)



class DeviceListWidget(QWidget):
    def __init__(self, settings_model, parent=None):
        super().__init__(parent)
        self.settings_model = settings_model
        self.devices = []
        self.setup_ui()
        self.load_devices()
        self.check_connections()
        
        

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Botones en la parte superior
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Agregar Dispositivo")
        add_button.clicked.connect(self.add_device)
        buttons_layout.addWidget(add_button)

        check_button = QPushButton("Verificar Conexiones")
        check_button.clicked.connect(self.check_connections)
        buttons_layout.addWidget(check_button)

        layout.addLayout(buttons_layout)

        # Lista de dispositivos abajo
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)

        # Estilos en modo oscuro
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: 1px solid #666;
                padding: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QListWidget {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
            }
            QListWidget::item {
                background-color: #3c3c3c;
                color: white;
            }
            QListWidget::item:selected {
                background-color: #5a5a5a;
            }
        """)

    def add_device(self):
        dialog = AddDeviceDialog(self)
        if dialog.exec() == dialog.Accepted:
            data = dialog.get_device_data()
            if data['name'] and data['ip'] and data['http_port'] and data['rtsp_port'] and data['user'] and data['password']:
                self.settings_model.add_device(data['name'], data['ip'], data['http_port'], data['rtsp_port'], data['user'], data['password'])
                self.load_devices()
                self.check_connections()
            else:
                # Mostrar mensaje de error
                pass
            

    def load_devices(self):
        self.devices = self.settings_model.get_devices()
        self.device_list.clear()
        for device in self.devices:
            item_text = f"{device['name']} - {device['ip']} (HTTP:{device.get('http_port', 'N/A')}, RTSP:{device.get('rtsp_port', 'N/A')}) ({'Conectado' if device['connected'] else 'Desconectado'})"
            item = QListWidgetItem(item_text)
            self.device_list.addItem(item)
            

    def check_connections(self):
        if self.devices:
            self.thread = ConnectionCheckThread(self.devices)
            self.thread.result.connect(self.update_connection_status)
            self.thread.start()
            

    def update_connection_status(self, index, connected):
        self.settings_model.update_device_connection(index, connected)
        self.load_devices()