from PySide6.QtWebSockets import QWebSocket
from PySide6.QtCore import QObject, Signal, QUrl, QTimer, Slot
from PySide6.QtNetwork import QAbstractSocket
import json
import msgpack


class Socket_services(QObject):
    
  

    connected_signal = Signal(bool, str)
    disconnected_signal = Signal(bool, str)
    re_connect_signal = Signal(str)
    
    signal_inference = Signal(dict)
    
    
    
    def __init__(self, url=None, type_inference=None):
        # 2. Ahora super().__init__() funcionará correctamente
        super().__init__()
        self.url = url
        self._manual_stop = False
        self.type_inference = type_inference
        self.id_connection = None
        self.client = QWebSocket()
        self.client.connected.connect(self._on_connected)
        self.client.disconnected.connect(self._on_disconnected)
        self.client.textMessageReceived.connect(self.on_text_message_received)
        self.client.binaryMessageReceived.connect(self.on_binary_message_received)


        
      
    def conect_server(self, new_url=None, new_type=None):
        """Método para conectar o re-conectar"""
        # 1. Si enviamos nuevos parámetros, los actualizamos
        if new_url: self.url = new_url
        if new_type: self.type_inference = new_type
        
        # 2. Resetear la bandera de stop manual
        self._manual_stop = False
        
        # 3. Si ya está conectado, lo cerramos primero para limpiar
        if self.client.state() == QAbstractSocket.ConnectedState:
            self.client.close()
            
        print(f"🌐 Conectando a: {self.url}/{self.type_inference}")
        self.client.open(QUrl(f'{self.url}/{self.type_inference}'))
        
    
    
    
    def disconnect_server(self):
        """Método para desconexión intencional (limpia todo)"""
        print("🛑 Desconexión manual solicitada")
        self._manual_stop = True # Bloquea el bucle de reconexión
        
        # Detener timer si existe
        if hasattr(self, 'reconnect_timer') and self.reconnect_timer.isActive():
            self.reconnect_timer.stop()
            
        self.client.close()
        # Limpiamos datos sensibles o temporales
        self.id_connection = None
        
    
    
    
    def _on_disconnected(self):
        print('❌ WebSocket offline')
        self.disconnected_signal.emit(False, "Server Offline")
        
        # SOLO reconecta si NO fue una desconexión manual
        if not self._manual_stop:
            self._loop_conection()
        else:
            print("INFO: No se iniciará reconexión automática (Stop manual).")
            
            
            
        
    def _on_connected(self):
        print(f"Conneted to server")
        print('✅ WebSocket connected sucessfull')
        self.connected_signal.emit(True, 'Server connect') # Notifica a la UI
        
        if  hasattr(self, 'reconnect_timer'):
            self.reconnect_timer.stop()
            self.reconnect_timer.deleteLater()
        
        
        
        
    def _on_error(self, error):
        # El signal de error de Qt suele enviar información técnica
        error_msg = self.client.errorString()
        print(f"💥 Error socket: {error_msg}")
       
        self.disconnected_signal.emit(False, f"Error: {error_msg}")
        
        
        
        
    def _loop_conection(self):
        print('Bucle de reconexión al socket')
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(5000)  # Intentar cada 5 segundos
        self.reconnect_timer.timeout.connect(self._on_timeout)
        self.reconnect_timer.start()
        
        
        
    
    def _on_timeout(self): 
        self.conect_server() 
        self.re_connect_signal.emit("Reconectando...")
        
        
        
        
    def send_frame(self,component_key, frame_data):
        try:
            if component_key is None: raise ValueError('component_key o campos de frame_data son indefinidos')
            if self.id_connection is None: 
                print("⚠️ id_connection aún no asignado, esperando init del servidor...")
                return
            
            data_to_send = {
                'event': 'inference',
                'id_connection': self.id_connection,
                'type_inference': self.type_inference,
                'component_key': component_key,
                'data': frame_data
            }

            self.client.sendTextMessage(json.dumps(data_to_send))
        except Exception as e:
            print(e)
    
    
    
    def send_binary_frame(self, component_key, frame_data):
        try:
            if component_key is None: raise ValueError('component_key o campos de frame_data son indefinidos')
            if self.id_connection is None: 
                print("⚠️ id_connection aún no asignado, esperando init del servidor...")
                return
            
            data_to_send = {
                'event': 'inference',
                'id_connection': self.id_connection,
                'type_inference': self.type_inference,
                'component_key': component_key,
                'data': frame_data
            }
         
            binary_data = msgpack.packb(data_to_send)
            self.client.sendBinaryMessage(binary_data)
        except Exception as e:
            print(e)
    
    
    
    
    @Slot(str)
    def on_text_message_received(self, message):
        data = json.loads(message)   
     
        if data.get('event') is not None:
            if data['event'] == 'connection_init' or data['event'] == 'conection_init': 
                self.id_connection = data['id_connection']
                print(f"✅ ID de conexión recibido: {self.id_connection}")
            elif data['event'] == 'inference': 
                self.signal_inference.emit(data)



    @Slot(bytes)
    def on_binary_message_received(self, message):
        try:
            data = msgpack.unpackb(message, raw=False, strict_map_key=False)
      
            if data.get('event') is not None:
                if data['event'] == 'connection_init' or data['event'] == 'conection_init': 
                    self.id_connection = data['id_connection']
                    print(f"✅ ID de conexión recibido (binary): {self.id_connection}")
                elif data['event'] == 'inference': 
                    self.signal_inference.emit(data)
        except Exception as e:
            print(f"Error procesando mensaje binario: {e}")
            
            
    def is_connected(self):
        """
        Retorna True si el socket está físicamente conectado y listo para transmitir.
        Retorna False en cualquier otro caso (conectando, cerrando, desconectado).
        """
        if self.client is None:
            return False
            
        return self.client.state() == QAbstractSocket.ConnectedState