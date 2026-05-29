import win32gui
import win32ui
import win32con
from PIL import Image
import ctypes
from ctypes import wintypes
import io



# Configurar PrintWindow
PrintWindow = ctypes.windll.user32.PrintWindow
PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
PrintWindow.restype = wintypes.BOOL


def capture_window_by_hwnd(hwnd):
    """
    Captura el contenido de una ventana específica por su HWND usando PrintWindow.
    Devuelve un objeto PIL Image o None si falla.
    """
    if not win32gui.IsWindow(hwnd):
        return None

    hwndDC = None
    mfcDC = None
    saveDC = None
    saveBitMap = None
    try:
        # Obtener dimensiones de la ventana
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            return None

        # Obtener el contexto del dispositivo de la ventana
        hwndDC = win32gui.GetWindowDC(hwnd)
        if not hwndDC:
            return None

        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # Crear bitmap compatible
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)

        # Intentar capturar con PrintWindow (PW_RENDERFULLCONTENT = 0x00000002)
        result = PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

        if not result:
            # Fallback a BitBlt
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

        if not result:
            return None

        # Convertir a formato PIL Image
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        return im.resize((800, 600), Image.Resampling.BILINEAR)

    except Exception as e:
        print(f"💥 Error capturando ventana: {e}")
        return None
    finally:
        # Siempre liberar recursos GDI, sin importar si hubo excepcion
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
    
    
    
    
def window_exists(hwnd):
    try:
        if hwnd is None:
            return False
        return bool(win32gui.IsWindow(hwnd))
    except Exception:
        return False
    


def get_title(hwnd = None):
    if hwnd is None: return '' 
    return win32gui.GetWindowText(hwnd)


def pil_image_to_png_bytes(imagen_pil, format="PNG", quality=None):
    if imagen_pil is None:
        return None
    try:
        buffer = io.BytesIO()

        # 3. Guardar la imagen PIL en el buffer de memoria en formato PNG
        #    Esto codifica la imagen como bytes PNG.
        is_quality = quality if quality else None
        imagen_pil.save(buffer, format=format, quality=is_quality)
        
        # 4. Obtener los bytes codificados
        png_bytes = buffer.getvalue()
        buffer.close()
        
        # 5. Cargar los bytes PNG en QPixmap
        return png_bytes

    except Exception as e:
        print(f"💥 Error al convertir la imagen a QPixmap: {e}")
        return None