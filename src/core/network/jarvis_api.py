from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QSslConfiguration , QNetworkCookieJar, QNetworkReply, QSslSocket, QHttpMultiPart, QHttpPart
from PySide6.QtCore import QObject , QUrl, QByteArray,Signal, QEventLoop
import json
import base64, re



class Jarvis_api(QObject):
    
    
    error_request = Signal(str)
    selected_establishmentSignal = Signal(dict)
    
    
    def __init__(self, emailuser=None, password=None, url_api=None):
        super().__init__()
        self.email_jarvis_request = emailuser
        self.password_jarvis_request = password
        self.url_api_base = url_api

        self.session_user = None
        self.error_User = None
        self.list_of_establishments = []
        self.selected_establishment = None
        
        self.manager_request = QNetworkAccessManager()
        cookie_jar = QNetworkCookieJar()
        self.manager_request.setCookieJar(cookie_jar)
        
        self.ssl_config = QSslConfiguration.defaultConfiguration()  # OBTIENE LA CONFIGURACIÓN SSL
        self.ssl_config.setPeerVerifyMode(QSslSocket.VerifyNone) # DESACTIVA ERROR DE CERTIFICADOS SSL INVALIDO
        
        self.create_session()
        self.fetching_establishment()
        
        
    
    def selection_establishment(self, name):
        for iteration in self.list_of_establishments:
            if iteration['name'] == name:
                self.selected_establishment = iteration
                print(f'{name} seleted by client')
                break
    
    
    
    
    def create_session(self):
        body_dic = { "email": self.email_jarvis_request, "password": self.password_jarvis_request } 
        response = self._request(resource='auth/login', body=body_dic, berb='post')
        response.finished.connect(lambda: self._handler_response_session(response))
        
        
        
    def fetching_establishment(self):
        response = self._request(resource='localligth')
        response.finished.connect(lambda: self._handler_response_establishment(response))
        
        
        
    def send_alert_to_api(self, url_image='https://amazona365.ddns.net/api_jarvis/v1/novelty/img=novelty_1769530415033.jpeg' , title='Alerta de perimetral', message='', params=None):
        try:
            return None  #  CÓDIGO COMENTADO PARA EL ENVIOS DE ALERTAS
            if self.session_user is None:
                self.error_request.emit('Error de sesión')
                return None
            if self.selected_establishment is None:
                self.error_request.emit('Seleciones un establecimiento o lugar')
                return None

            imageurl = url_image
            data = {
                'title': f'{title} ("Modo IA")',
                'userName': f"{self.session_user['name']} {self.session_user['surName']}",
                'userId': self.session_user['_id'],
                'localName': self.selected_establishment['name'],
                'localId': self.selected_establishment['_id'],
                'ruleBonus': {'worth': 0, 'acomulate': 0},
                'alertId': '6977974dfed1f0dcaffceefa',
                'description': 'Alerta generada con IA',
                'imageToShare': imageurl,
                'menu': f"*{self.selected_establishment['name']}*\n_{title}_\n{message}",
                'imageUrl': [
                    {'url': imageurl, 'caption': 'alert'}
                ]
            }
  
            response = self._request(resource='novelties', body=data, berb='post')
            response.finished.connect(lambda: self.__handler_response_alert(response))
        except Exception as e:
            print(e)        
        
        
        
    def _request(self, resource='', body=None, berb='get'):
        try:
            request = QNetworkRequest(QUrl(f'{self.url_api_base}/{resource}'))
            request.setSslConfiguration(self.ssl_config)
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
            
            # Agregar cabeceras personalizadas
            request.setRawHeader(QByteArray(b'Source-Application'), QByteArray(b'Jarvis_Vision'))
            request.setRawHeader(QByteArray(b'Version-App'), QByteArray(b'1.0'))
            
            if berb == 'post':
                body_byte = QByteArray(json.dumps(body).encode("utf-8"))
                return self.manager_request.post(request, body_byte)
            else:
                return self.manager_request.get(request)
                
        except Exception  as e:
            print(e)
            
            
    
    
    def _handler_response_session(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError: 
            data = reply.readAll().data().decode() 
            try: 
                json_data = json.loads(data) 
                print('User autenticated')
                self.session_user = json_data
       
            except Exception:
                print("Respuesta texto:", data)
             
        else: 
            print("Error en la respuesta:", reply.errorString())
            self.error_request.emit('Error en la autenticación en el servicio de Jarvis365')
            
            
            
            
    def _handler_response_establishment(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError: 
            data = reply.readAll().data().decode() 
            try: 
                json_data = json.loads(data) 
          
                self.list_of_establishments = json_data
         
            except Exception:
                print("Respuesta texto:", data)
        else:
        
            print("Error en la respuesta:", reply.errorString())
            self.error_request.emit('Error al obtener la lista de clientes')
            
            
    
    def __handler_response_alert(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data().decode()
            try:
                json_data = json.loads(data)
       
            except Exception:
                print("Respuesta texto:", data)
        else:
            # Leer cuerpo de la respuesta para obtener detalles del error
            data = reply.readAll().data().decode()
            try:
                json_data = json.loads(data)
                print("Error response JSON:", json_data)
                if isinstance(json_data, dict) and 'response' in json_data:
                    print("Propiedad 'response' del servidor:", json_data['response'])
            except Exception:
                print("Error response text:", data)
            print("Error en la respuesta:", reply.errorString())
            self.error_request.emit('Error al enviar la alerta')



    def send_base64_image(self, base64_image: str, field_name: str = 'img', filename: str = 'image.jpg', timeout: int = 15000):
        """Envía una imagen en base64 al endpoint /multimedia y devuelve la respuesta del servidor.

        Devuelve (success: bool, result: dict|str).
        Atención: este método espera de forma bloqueante hasta que la petición termine o se alcance `timeout`.
        """
        try:
            # Normalizar y decodificar base64 (soporta data URLs)
            b64 = re.sub(r'^data:image/\w+;base64,', '', base64_image)
            raw = base64.b64decode(b64)

            multipart = QHttpMultiPart(QHttpMultiPart.FormDataType)

            part = QHttpPart()
            part.setHeader(QNetworkRequest.ContentDispositionHeader, f'form-data; name="{field_name}"; filename="{filename}"')
            content_type = 'image/jpeg'
            if filename.lower().endswith('.png'):
                content_type = 'image/png'
            part.setHeader(QNetworkRequest.ContentTypeHeader, content_type)
            part.setBody(QByteArray(raw))
            multipart.append(part)

            request = QNetworkRequest(QUrl(f'{self.url_api_base}/multimedia'))
            request.setSslConfiguration(self.ssl_config)
            # agregar cabeceras personalizadas
            request.setRawHeader(QByteArray(b'Source-Application'), QByteArray(b'Jarvis_Vision'))
            request.setRawHeader(QByteArray(b'Version-App'), QByteArray(b'1.0'))

            reply = self.manager_request.post(request, multipart)
            multipart.setParent(reply)

            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec()

            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = reply.readAll().data().decode()
                try:
                    return True, json.loads(data)
                except Exception:
                    return True, data
            else:
                data = reply.readAll().data().decode()
                try:
                    json_data = json.loads(data)
                    if isinstance(json_data, dict) and 'response' in json_data:
                        return False, json_data['response']
                    return False, json_data
                except Exception:
                    return False, data or reply.errorString()

        except Exception as e:
            return False, str(e)
            
            
            
            