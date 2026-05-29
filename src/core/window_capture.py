import win32gui
import win32ui
import win32con
from PIL import Image
from typing import Optional
import time



class WindowCapture:
    """
    Servicio especializado en captura de contenido de ventanas
    """

    
    def __init__(self):
        self.capture_interval = 0.1  # 10 FPS por defecto
        self.is_capturing = False
    


    def capture_window_by_hwnd(self, hwnd: int) -> Optional[Image.Image]:
        """
        Captura el contenido de una ventana específica por su HWND
        """
        if not win32gui.IsWindow(hwnd):
            return None

        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                return None

            hwndDC = win32gui.GetWindowDC(hwnd)
            if not hwndDC:
                return None

            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

            if not result:
                return None

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            return Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )

        except Exception as e:
            print(f"Error capturando ventana {hwnd}: {e}")
            return None
        finally:
            try:
                if saveBitMap is not None:
                    win32gui.DeleteObject(saveBitMap.GetHandle())
            except Exception:
                pass
            try:
                if saveDC is not None:
                    saveDC.DeleteDC()
            except Exception:
                pass
            try:
                if mfcDC is not None:
                    mfcDC.DeleteDC()
            except Exception:
                pass
            try:
                if hwndDC is not None:
                    win32gui.ReleaseDC(hwnd, hwndDC)
            except Exception:
                pass
        
        
    
    def start_realtime_capture(self, hwnd: int, callback: callable, fps: int = 5):
        """
        Iniciar captura en tiempo real de una ventana
        """
        self.is_capturing = True
        interval = 1.0 / fps
        
        while self.is_capturing:
            start_time = time.time()
            
            # Capturar frame
            frame = self.capture_window_by_hwnd(hwnd)
            if frame and callback:
                callback(frame)
            
            # Control de FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)
    

    def stop_realtime_capture(self):
        """Detener captura en tiempo real"""
        self.is_capturing = False