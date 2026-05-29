from PySide6.QtCore import Signal, QThread

import win32gui
import win32con
import pythoncom
import ctypes
from ctypes import wintypes
import time
import psutil


# Definir la estructura de la función de callback para SetWinEventHook
WINEVENTPROC = ctypes.WINFUNCTYPE(
    None, 
    wintypes.HANDLE, 
    wintypes.DWORD, 
    wintypes.HWND, 
    wintypes.LONG, 
    wintypes.LONG, 
    wintypes.DWORD, 
    wintypes.DWORD
)





class WindowScannerThread(QThread):

    """Hilo que escanea periódicamente las ventanas abiertas."""
    window_opened = Signal(int, str)  # hwnd, title
    window_closed = Signal(int)       # hwnd



    def __init__(self, ignore_hwnds=None, parent=None):
        super().__init__(parent)
        self.running = True
        self.current_windows = {}  # hwnd -> title
        self.ignore_hwnds = ignore_hwnds or []  # Lista de HWNDs a ignorar



    def run(self):
        while self.running:
            self._check_window_changes()
            time.sleep(0.3)  # Escanear cada 300ms



    def _check_window_changes(self):
        new_windows = {}
        
        def enum_windows(hwnd, _):
            # Si este HWND está en la lista de ignorados, saltarlo
            if hwnd in self.ignore_hwnds:
                return True
                
            if (win32gui.IsWindowVisible(hwnd) and 
                win32gui.GetParent(hwnd) == 0 and
                win32gui.GetWindowText(hwnd) != ""):
                
                title = win32gui.GetWindowText(hwnd)
                new_windows[hwnd] = title
            return True
        
        win32gui.EnumWindows(enum_windows, None)
        
        # Detectar nuevas ventanas
        for hwnd, title in new_windows.items():
            if hwnd not in self.current_windows:
                self.window_opened.emit(hwnd, title)
        
        # Detectar ventanas cerradas
        for hwnd in list(self.current_windows.keys()):
            if hwnd not in new_windows:
                self.window_closed.emit(hwnd)
        
        self.current_windows = new_windows






    def stop(self):
        self.running = False
        self.quit()
