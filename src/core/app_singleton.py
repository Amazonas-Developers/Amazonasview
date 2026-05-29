import os
import sys
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject


load_dotenv()


class AppSingleton(QObject):
    """
    Singleton para gestionar la QApplication global
    """
    _instance = None
    _app = None
    _initialized = False
    


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppSingleton, cls).__new__(cls)
        return cls._instance
    


    @classmethod
    def initialize(cls, sys_argv=None):
       
        if cls._app is None:
            if sys_argv is None:
                sys_argv = sys.argv
            cls._app = QApplication(sys_argv)
            
            # Configuración básica de la aplicación
            cls._app.setApplicationName(os.getenv('name_project'))
            cls._app.setApplicationVersion(os.getenv('version'))
            cls._app.setOrganizationName(os.getenv('name_company'))
            cls._app.setQuitOnLastWindowClosed(True)
            
            cls._initialized = True
        return cls._app
    
    
    
    @classmethod
    def get_app(cls):
        """
        Obtener la instancia de QApplication
        """
        if cls._app is None:
            # Intentar obtener instancia existente
            existing_app = QApplication.instance()
            if existing_app:
                cls._app = existing_app
                cls._initialized = True
                print("⚠️  Usando QApplication existente")
            else:
                raise RuntimeError(
                    "QApplication no inicializada. "
                    "Llama a AppSingleton.initialize() primero desde main.py"
                )
        
        return cls._app
    



    @classmethod
    def get_main_window(cls):
        """
        Obtener la ventana principal activa
        """
        app = cls.get_app()
        return app.activeWindow()
    



    @classmethod
    def is_initialized(cls):
        """Verificar si la aplicación está inicializada"""
        return cls._initialized
    


    @classmethod
    def exec(cls):
        """Ejecutar el bucle de la aplicación"""
        if cls._app:
            return cls._app.exec()
        else:
            raise RuntimeError("QApplication no inicializada")