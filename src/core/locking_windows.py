import win32gui
import win32con
import pyautogui




class WindowLocker:
    """
    Clase para controlar el estado 'siempre encima' y bloqueo de ventanas
    """
    def __init__(self):
        self.locked_windows = {}  # {hwnd: {'always_on_top': bool, 'locked': bool}}
    
    def control_window(self, hwnd, always_on_top=True, lock_position=True):
        """
        Control completo de una ventana: siempre encima y bloqueada
        """
        try:
            # Verificar que la ventana existe
            if not win32gui.IsWindow(hwnd):
                print(f"Ventana {hwnd} no existe")
                return False
            
            # 1. Activar siempre encima
            if always_on_top:
                set_window_always_on_top(hwnd, True)
            
            # 2. Bloquear posición
            if lock_position:
                lock_window_position(hwnd, True)
            
            # 3. Traer al frente
            win32gui.SetForegroundWindow(hwnd)
            
            # Guardar estado
            self.locked_windows[hwnd] = {
                'always_on_top': always_on_top,
                'locked': lock_position
            }
            
            print(f"Ventana controlada: {win32gui.GetWindowText(hwnd)}")
            return True
            
        except Exception as e:
            print(f"Error controlando ventana: {e}")
            return False
    
    def release_window(self, hwnd):
        """
        Liberar una ventana (quitar siempre encima y desbloquear)
        """
        try:
            if hwnd in self.locked_windows:
                # Quitar siempre encima
                set_window_always_on_top(hwnd, False)
                
                # Desbloquear posición
                lock_window_position(hwnd, False)
                
                # Remover de la lista
                del self.locked_windows[hwnd]
                
                print(f"Ventana {hwnd} liberada")
                return True
            else:
                print(f"Ventana {hwnd} no estaba controlada")
                return False
                
        except Exception as e:
            print(f"Error liberando ventana: {e}")
            return False
    
    def release_all_windows(self):
        """Liberar todas las ventanas controladas"""
        windows_to_release = list(self.locked_windows.keys())
        
        for hwnd in windows_to_release:
            self.release_window(hwnd)
        
        print(f"Todas las ventanas liberadas ({len(windows_to_release)} ventanas)")