import json
import os
from pathlib import Path
from appdirs import user_config_dir
from cryptography.fernet import Fernet



class SettingsModel:
    
    def __init__(self, app_name='amazonas_view', filename='config.json', keyfile='cfghwrpoñm,.}ht4780sSDCWAG.key'):

        config_dir = user_config_dir(app_name)
      
        self.key_path = os.path.join(config_dir, keyfile)
        
        os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
        
        if os.path.exists(self.key_path): 
            with open(self.key_path, 'rb') as f: 
                self.key = f.read() 
        else: 
            self.key = Fernet.generate_key() 
            with open(self.key_path, 'wb') as f: f.write(self.key)
        
        self.f = Fernet(self.key)
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(project_root, ".."))
        
        
        os.makedirs(config_dir, exist_ok=True)
        
        self.file_path = os.path.join(config_dir, filename)

        self.data = {}
        self.load_config()
        
        
        
    def load_config(self): 

        if os.path.exists(self.file_path): 
            print(self.file_path)
            try:
                with open(self.file_path, 'r', encoding='utf-8') as file: 
                    token = file.read()
                    decryted = self.f.decrypt(token)
                    self.data = json.loads(decryted.decode('utf-8'))
                    print('Archivo de configuración creado 📄')
            except json.JSONDecodeError: # Si el archivo está vacío o corrupto, regenerar 
                self.data = self.default_config() 
                self.save_config()
                print('Archivo de configuración cargado ✅')
        else: 
            self.data = self.default_config()
            self.save_config()
                
                
                
                
    def save_config(self):
        json_str = json.dumps(self.data, indent=4)
        token = self.f.encrypt(json_str.encode('utf-8'))
        with open(self.file_path, 'wb') as file: 
            file.write(token)
            
                
                
    def default_config(self): 
        return { 
            'principal_box': -1,
            'last_inference': None, 
            'selected_establishment':  None,
            'boxs_config': [
                    {
                        'hwnd': None,
                        'index': i, 
                        'play': False, # POR APLICAR
                        'inference_play': False, # POR DEPURAR
                        # ROI PRINCIPAL
                        'roi': [[100,200],[900,100],[900,900],[100,900]], 
                        'roi_boolean': True,
                        # ROI DE PUERTA
                        'roi_door': [[220,140],[420,140],[420,320],[220,320]],
                        'roi_dor_boolean': True,
                        # ROI DE DIRECCIÓN DE PUERTA
                        'roi_dor_direction': [[50,100],[100,900]],
                        'roi_dor_direction_boolean': True, # Discarded
                        # Tracking de cosméticos (independiente de persona/género/edad)
                        'cosmetics_enabled': True,

                    } for i in range(16)
            ],
            'amount_renderbox': 2,
            'devices': []
        }
    
    
    
    def set(self, key, value): 
        self.data[key] = value 
        self.save_config() 
        
        
        
    def get(self, key, default=None): 
        return self.data.get(key, default)
    
    
    
    def update_box_config(self, index, key, value):
        """ Actualiza o añade una propiedad dentro de un diccionario de boxs_config. """ 
        for box in self.data['boxs_config']: 
     
            if box['index'] == index:
                box[key] = value 
                self.save_config() 
                
                return # Si no existe el índice, opcionalmente lo creamos 
        new_box = {'index': index, key: value} 
        self.data['boxs_config'].append(new_box) 
        self.save_config()
        
        
        
    def get_box_config(self, index):
        for box in self.data['boxs_config']:
            if box['index'] == index:
               return box


    def add_device(self, name, ip, http_port, rtsp_port, user, password):
        device = {
            'name': name,
            'ip': ip,
            'http_port': http_port,
            'rtsp_port': rtsp_port,
            'user': user,
            'password': password,
            'connected': False
        }
        self.data['devices'].append(device)
        self.save_config()


    def get_devices(self):
        return self.data.get('devices', [])


    def update_device_connection(self, index, connected):
        if 0 <= index < len(self.data['devices']):
            self.data['devices'][index]['connected'] = connected
            self.save_config()

    def remove_device(self, index):
        if 0 <= index < len(self.data['devices']):
            self.data['devices'].pop(index)
            self.save_config()

        