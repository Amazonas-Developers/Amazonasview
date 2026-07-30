from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout, QComboBox
from PySide6.QtCore import Slot, Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices

from .custon_btn.btn_footer import BtnIco
from .custon_btn.btn_footer import BtnIco

# Misma direccion base que windows_main.py usa para el WebSocket
# (ws://127.0.0.1:9000/ws) -- el dashboard se sirve por HTTP en el
# mismo host/puerto, ver SERVER-IA Amazonas README.md.
DASHBOARD_URL = "http://127.0.0.1:9000/"


class CustomStatusBar(QStatusBar):
    
    
    inference_type_selected = Signal(str)
    
    
    def __init__(self, 
                list_establishment=[],
                type_inference_default=None,
                selected_establishment_default=None
        ):
        
        super().__init__(parent=None)
        print(list_establishment)
        self.list_establishment =  list_establishment
        self.selected_establishment_default=selected_establishment_default
        self.type_inference_default=type_inference_default
        self.setup_ui()
        
        
    def setup_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(35)
        self.setObjectName('FooterBar')
        self.setStyleSheet('''
            QStatusBar { background-color: #424242; color: white; }
        ''')
        
        container = QWidget()
        self.container_layout = QHBoxLayout(container)
        self.container_layout.setSpacing(20)
        self.container_layout.setContentsMargins(0,0,0,0)
        "inserción______⤵️_______"
        self.addPermanentWidget(container)
        
        
        
        """______Lista de clientes_______"""
        if len(self.list_establishment) > 0:
            new_list = []
            
            for iteration in self.list_establishment:
                new_list.append(iteration['name'])

            list_label = QLabel('Selecione el cliente: ')
            self.selector_establishment = QComboBox()
            self.selector_establishment.addItem('Seleccione...')
            self.selector_establishment.addItems(new_list)
            self.container_layout.addWidget(list_label)
            self.container_layout.addWidget(self.selector_establishment)
            self.container_layout.addStretch()
            
            if self.selected_establishment_default is not None:
                
                index_establishment = self.selector_establishment.findText(self.selected_establishment_default)
                if index_establishment != -1: self.selector_establishment.setCurrentIndex(index_establishment)
            '''
            type_inference_default=None,
            selected_establishment_default=None
            '''
        
        
        """____Indicador del server___"""
        self.msg_label = QLabel('Selecione el tipo de inferencia --->')
        self .indicator = QLabel('●')
        self.indicator.setStyleSheet('color: gray;')
        "inserción______⤵️_______"
        self.container_layout.addWidget(self.indicator)
        self.container_layout.addWidget(self.msg_label)
        self.container_layout.addStretch()
        
        self.layout_selector = QComboBox()
        self.layout_selector.addItems(['Seleccione...', 'Hummus', 'HummusVLM', 'Autolavado', 'Perimetrales', 'PerimetralesMultiCam', 'Personal de Amazonas', 'Misters'])
        
        if self.type_inference_default is not None:
            index_inference = self.layout_selector.findText(self.type_inference_default)
            self.layout_selector.setCurrentIndex(index_inference)
            self.layout_selector.setDisabled(True)
            
            
        self.layout_selector.currentTextChanged.connect(self._on_selector_changed)
        "inserción______⤵️_______"
        self.container_layout.addWidget(QLabel("Tipos de inferencias:")) # Etiqueta opcional
        self.container_layout.addWidget(self.layout_selector)
        
        self.btn_stopconection = BtnIco(ico_path='resource/finish_connection.png', title='Cerrar conexión con el servidor', h=25, w=25)
        "inserción______⤵️_______"
        self.container_layout.addWidget(self.btn_stopconection)
        
        """____Boton para selección de render_BOX___"""
        self.btn_layout = BtnIco(ico_path='resource/layout.png', title='Divisiones de ventanas: (3x3, 2x2, etc.)')
        "inserción______⤵️_______"
        self.container_layout.addWidget(self.btn_layout)

        """____Boton para abrir el dashboard de analitica___"""
        self.btn_dashboard = BtnIco(
            ico_path='resource/mode_ai.png',
            title='Abrir dashboard de analítica (detecciones, demografía, reportes)',
            h=25, w=25,
        )
        self.btn_dashboard.clicked.connect(self._open_dashboard)
        self.container_layout.addWidget(self.btn_dashboard)

    def _open_dashboard(self):
        QDesktopServices.openUrl(QUrl(DASHBOARD_URL))
    
    
    
    def _on_selector_changed(self, text):
        if text != 'Seleccione...':
            self.inference_type_selected.emit(text)
            self.layout_selector.setDisabled(True)
        
    
    
    
    @Slot(bool, str)
    def update_ui(self, is_connected, message):
        if is_connected:
            self.showMessage('Conexión establecida con el servidor', 3000)
            self.indicator.setStyleSheet('color: #4eff2b; font-weight: bold;')
            self.msg_label.setStyleSheet('color: #4eff2b; font-weight: bold;')
            self.layout_selector.setEnabled(False)
        else:
            self.showMessage('Conexión perdida con el servidor', 3000)
            self.indicator.setStyleSheet('color: #8B0000; font-weight: bold;')
            self.msg_label.setStyleSheet('color: white; font-weight: bold;')
            self.layout_selector.setEnabled(True)
        self.msg_label.setText(message)
       
    
    @Slot(str)
    def receive_message(self, mesagge):
        self.showMessage(mesagge, 3000)