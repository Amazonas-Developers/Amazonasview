import sys
import os
import numpy as np
from PIL import Image
from dotenv import load_dotenv

### MODELS AND DATA
from model.windows.list_windows import open_windows_windows
from core.window_global import windows_monitor


###    CONTROLLER AND LOGIC
from core.app_singleton import  AppSingleton


### COMPONENTS AND UI
##from gui.components.modal_msm import ModalDialog
##from gui.windows_main import MainWindow


from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget, QDockWidget, QTextEdit
from PySide6.QtCore import Qt

from gui.windows_main import MainWindow 
from gui.components.SplashScreen import SplashScreen
from gui.components.render_box.render_box import Render_box
from gui.components.sidebar.sidebar_dock import Sidebar_Dock
from gui.components.sidebar.alerts_sidebar import AlertsSidebar
from model.settings_model import SettingsModel

## rest ann straming
from core.network.jarvis_api import Jarvis_api
from core.network.socket_client import Socket_services

        

def load_stylesheet():
    qss_path = os.path.join(os.path.dirname(__file__), 'gui', 'styles', 'global.qss')

    if os.path.exists(qss_path):
        print('Loading stylesheet from:', qss_path)
        with open(qss_path, 'r') as f:
            return f.read()
    else: print('Stylesheet file not found:', qss_path)





def main():
    try:
        load_dotenv()
        
        email_jarvis = os.getenv('jarvis_email')
        password_jarvis = os.getenv('jarvis_password')
        url_api_jarvis = os.getenv('jarvis_url')
        
        settingsModel = SettingsModel()
        list_windows = open_windows_windows()
        
        app = AppSingleton.initialize(sys.argv)
        app.setStyleSheet(load_stylesheet())
        
        jarvis_api = Jarvis_api(emailuser=email_jarvis, password=password_jarvis, url_api=url_api_jarvis)
        
        socket_client = Socket_services()
        
        splashScreen = SplashScreen()
        splashScreen.show()
        window_containter = MainWindow(
            socket_service=socket_client,
            jarvis_api=jarvis_api,
            data_model_gui = settingsModel
        )
        
        windowsPrincipal = window_containter.window_child 
    
        asidebar = Sidebar_Dock(parent=None, title='Visión', src_ico='src/resources/ico.png')
        asidebar.print_list(list_windows)
        
        
        windows_monitor.window_opened.connect(asidebar.add_new_window)
        windows_monitor.window_closed.connect(asidebar.remove_closed_windows)
        
        
        dock = QDockWidget(None)
        dock.setWidget(asidebar)
        dock.setStyleSheet("""
            QDockWidget::title {
                padding: 0px;       /* elimina espacio interno */
                margin: 0px;        /* elimina espacio externo */
                spacing: 0px;       /* elimina separación entre ícono y texto */
                text-align: center; /* centra el texto */
            }
            QDockWidget::close-button, QDockWidget::float-button {
                width: 0px;
                height: 0px;
            }
        """)
        
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget())
        windowsPrincipal.addDockWidget(Qt.LeftDockWidgetArea, dock)  # lo acoplas a la izquierda


        # ── Sidebar de Alertas IA (lado derecho) ──
        alerts_sidebar = AlertsSidebar(parent=None, title='Alertas IA')
        
        dock_alerts = QDockWidget(None)
        dock_alerts.setWidget(alerts_sidebar)
        dock_alerts.setStyleSheet("""
            QDockWidget::title {
                padding: 0px;
                margin: 0px;
                spacing: 0px;
                text-align: center;
            }
            QDockWidget::close-button, QDockWidget::float-button {
                width: 0px;
                height: 0px;
            }
        """)
        dock_alerts.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock_alerts.setTitleBarWidget(QWidget())
        windowsPrincipal.addDockWidget(Qt.RightDockWidgetArea, dock_alerts)

        # Conectar alertas de cada render_box al sidebar
        for box in window_containter.list_box:
            box.alert_received.connect(alerts_sidebar.add_alert)
    
        window_containter.show()
    
        splashScreen.finish(windowsPrincipal)
        return app.exec()
        


    except Exception as e:
        print(f'Fatal crash: {e}')
        import traceback
        traceback.print_exc()
        return 1






if __name__ == '__main__':  # FUNCTION MAIN

    sys.exit(main())