import sys, os, json, base64, time
import time
from datetime import datetime
import win32gui
import win32ui
import win32con
from PIL import Image
import ctypes
from ctypes import wintypes
import io

# 🔥 SUPRIMIR LOGS NO DESEADOS AL INICIO
import warnings
warnings.filterwarnings('ignore')

# Configurar variables de entorno para Qt ANTES de cualquier import
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.*=false'
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''

# Configurar PrintWindow
PrintWindow = ctypes.windll.user32.PrintWindow
PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
PrintWindow.restype = wintypes.BOOL




def capture_window_by_hwnd(hwnd):
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

        # Intentar capturar con PrintWindow
        result = PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

        if not result:
            # Fallback a BitBlt
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

        if result:
            # Convertir a formato PIL Image
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )



            # Limpiar recursos
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            return im
        else:
            # Limpiar recursos en caso de error
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            return None

    except Exception:
        return None


def pil_image_to_png_bytes(imagen_pil, format="PNG", quality=None):
    try:
        buffer = io.BytesIO()
        is_quality = quality if quality else None
        imagen_pil.save(buffer, format=format, quality=is_quality)
        png_bytes = buffer.getvalue()
        buffer.close()
        return png_bytes
    except Exception:
        return None


import msgpack  # Agrega esta línea para serialización binaria

# ... (código existente antes del main)

# 🔥 MANEJO SEGURO DE ARGUMENTOS
if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            sys.exit(1)

        hwnd = int(sys.argv[1])

        while True:
            buffer = capture_window_by_hwnd(hwnd)

            if buffer:
                image_bytes = pil_image_to_png_bytes(buffer, 'JPEG', 75)
                if image_bytes:
                    header = {
                        "timestamp": datetime.now().isoformat(),
                        "size": len(image_bytes),
                        "format": "JPEG"
                    }

                    # Serializar mensaje binario con MessagePack
                    message = {
                        'header': header,
                        'image_bytes': image_bytes
                    }
                    binary_message = msgpack.packb(message)

                    # Enviar bytes directamente a stdout
                    sys.stdout.buffer.write(binary_message)
                    sys.stdout.flush()

            time.sleep(1 / 90)

    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception:
        # 🔥 SILENCIAR CUALQUIER EXCEPCIÓN EN PRODUCCIÓN
        pass
