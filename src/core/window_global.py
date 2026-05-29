import win32gui
import win32process


from PySide6.QtCore import QObject, Signal, QThread, Property
from core.windows_detector import WindowScannerThread





class Windows_monitor(QObject):

    _instance = None
    # Señales para notificar cambios: ahora son eventos específicos
    window_opened = Signal(int, str)  # hwnd, title
    window_closed = Signal(int)      # hwnd
    
    # Señal antigua (para notificar que la lista completa ha cambiado)
    windows_event_detected = Signal(list) 

    # Señal antigua (para notificar que la lista completa ha cambiado)
    windows_event_detected = Signal(list) 


    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Windows_monitor, cls).__new__(cls)
        return cls._instance



    def __init__(self, parent=None, main_window=None):
        if not hasattr(self, '_initialized'):
            super().__init__(parent)
            self._initialized = True
            
            # Obtener el HWND de la ventana principal para ignorarla
            self._ignore_hwnds = self._get_own_window_hwnds(main_window)
            
            # Inicializamos el rastreo con un diccionario {hwnd: {'hwnd', 'title', 'class'}}
            self._current_windows = self._gather_list_windows_dict(self._ignore_hwnds) 
            self._list_windows = list(self._current_windows.values())
            
            # Inicializar el thread de escaneo periódico con la lista de HWNDs a ignorar
            self._scanner_thread = WindowScannerThread(ignore_hwnds=self._ignore_hwnds)
            
            # Conectar las señales del thread a los slots del monitor
            self._scanner_thread.window_opened.connect(self._handle_window_opened)
            self._scanner_thread.window_closed.connect(self._handle_window_closed)
            
            # Iniciar el hilo
            self._scanner_thread.start()
            
            # Asegurar que el hilo se detenga al salir de la aplicación
            self.destroyed.connect(self._scanner_thread.stop)

    def _get_own_window_hwnds(self, main_window=None):
        """Obtiene los HWNDs de todas las ventanas de la aplicación actual."""
        ignore_hwnds = []
        
        # Método 1: Si se proporciona la ventana principal directamente
        if main_window and hasattr(main_window, 'winId'):
            try:
                hwnd = main_window.winId()
                if hwnd:
                    ignore_hwnds.append(int(hwnd))
                    print(f"Ventana principal a ignorar: HWND={hwnd}")
            except Exception as e:
                print(f"Error obteniendo HWND de ventana principal: {e}")
        
        # Método 2: Buscar por nombre de clase o título de la aplicación
        # Obtener el nombre del proceso actual
        try:
            import psutil
            import os
            current_pid = os.getpid()
            
            def enum_windows_proc(hwnd, param):
                if win32gui.IsWindowVisible(hwnd):
                    _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if found_pid == current_pid:
                        ignore_hwnds.append(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        print(f"Ventana de la app a ignorar: HWND={hwnd}, Título='{title}'")
                return True
            
            win32gui.EnumWindows(enum_windows_proc, None)
        except ImportError:
            print("Instala psutil para mejor detección: pip install psutil")
        except Exception as e:
            print(f"Error buscando ventanas del proceso: {e}")
        
        return ignore_hwnds

    @Property(list, notify=windows_event_detected)
    def show_windows(self):
        return self._list_windows

    # --- SLOTS DE MANEJO DE EVENTOS ---



    def _handle_window_opened(self, hwnd: int, title: str):
        # Doble verificación por si acaso
        if hwnd in self._ignore_hwnds:
            return
            
        print(f'Ventana abierta: {hwnd} - {title} ')
        """Slot llamado cuando una ventana se abre (desde el thread)."""
        if hwnd not in self._current_windows:
            window_data = {
                'hwnd': hwnd, 
                'title': title, 
                'class': win32gui.GetClassName(hwnd) if win32gui.IsWindow(hwnd) else 'N/A'
            }
            self._current_windows[hwnd] = window_data
            self._update_list_and_notify()
            self.window_opened.emit(hwnd, title) # Emitir el evento específico




    def _handle_window_closed(self, hwnd: int):
        # Doble verificación por si acaso
        if hwnd in self._ignore_hwnds:
            return
            
        """Slot llamado cuando una ventana se cierra (desde el thread)."""
        if hwnd in self._current_windows:
            print(f'Ventana cerrada: {hwnd} - {self._current_windows[hwnd]["title"]}')
            del self._current_windows[hwnd]
            self._update_list_and_notify()
            self.window_closed.emit(hwnd) # Emitir el evento específico




    # --- MÉTODOS INTERNOS ---
    def _update_list_and_notify(self):
        """Actualiza la lista y emite la señal de lista completa para la propiedad."""
        self._list_windows = list(self._current_windows.values())
        self.windows_event_detected.emit(self._list_windows) # Notifica a la Property




    @staticmethod
    def _gather_list_windows_dict(ignore_hwnds=None): 
        """Método estático para recopilar la lista inicial como un diccionario {hwnd: data}."""
        if ignore_hwnds is None:
            ignore_hwnds = []
            
        windows = {}
        def enum_windows_proc(hwnd, param):
            # Ignorar ventanas en la lista de exclusiones
            if hwnd in ignore_hwnds:
                return True
                
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows[hwnd] = {
                    'hwnd': hwnd,
                    'title': win32gui.GetWindowText(hwnd),
                    'class': win32gui.GetClassName(hwnd)
                }
            return True
        
        win32gui.EnumWindows(enum_windows_proc, None)
        return windows
    



    def add_window_to_ignore(self, hwnd):
        """Añade un HWND a la lista de ventanas a ignorar."""
        if hwnd not in self._ignore_hwnds:
            self._ignore_hwnds.append(hwnd)
            # También actualizar el thread de escaneo
            self._scanner_thread.ignore_hwnds = self._ignore_hwnds



    def get_ignore_list(self):
        """Devuelve la lista de HWNDs que se están ignorando."""
        return self._ignore_hwnds.copy()



windows_monitor = Windows_monitor()