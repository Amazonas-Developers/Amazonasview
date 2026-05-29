import win32gui
import win32con
import win32ui
import pyautogui
import time
from PIL import Image
import ctypes
from ctypes import wintypes




# Configurar PrintWindow
PrintWindow = ctypes.windll.user32.PrintWindow
PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
PrintWindow.restype = wintypes.BOOL





def list_windows():
    windows = []
    def enum_windows_proc(hwnd, param):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            windows.append({
                'hwnd': hwnd,
                'title': win32gui.GetWindowText(hwnd),
                'class': win32gui.GetClassName(hwnd)
            })
        return True
    win32gui.EnumWindows(enum_windows_proc, None)
    return windows




def activate_window(hwnd):
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print(f"Error activating window: {e}")
        return False




def close_window(hwnd):
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception as e:
        print(f"Error closing window: {e}")
        return False




def minimize_window(hwnd):
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return True
    except Exception as e:
        print(f"Error minimizing window: {e}")
        return False




def maximize_window(hwnd):
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return True
    except Exception as e:
        print(f"Error maximizing window: {e}")
        return False



def send_text_to_window(hwnd, text):
    if activate_window(hwnd):
        time.sleep(0.5)  # Wait for the window to activate
        pyautogui.write(text)
        return True
    return False



def send_enter_to_window(hwnd):
    if activate_window(hwnd):
        time.sleep(0.5)
        pyautogui.press('enter')
        return True
    return False



# Combinación: enviar texto y luego enter
def send_text_and_enter(hwnd, text):
    if send_text_to_window(hwnd, text):
        time.sleep(0.2)
        send_enter_to_window(hwnd)
        return True
    return False






def set_window_always_on_top(hwnd):
    """
    Activa una ventana de forma segura sin usar métodos bloqueados
    """
    try:
        # Verificar si la ventana existe
        if not win32gui.IsWindow(hwnd):
            print(f"❌ Ventana con ID {hwnd} no existe")
            return False

        print(f"🎯 Intentando activar ventana: {hwnd}")

        # 1. Primero restaurar si está minimizada (esto casi siempre funciona)
        if win32gui.IsIconic(hwnd):
            print("  📱 Restaurando ventana minimizada...")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

        # 2. Verificar si la ventana está visible y habilitada
        if not win32gui.IsWindowVisible(hwnd):
            print("  👀 Ventana no visible")
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            time.sleep(0.1)

        if not win32gui.IsWindowEnabled(hwnd):
            print("  ⚠️  Ventana deshabilitada")

        # 3. MÉTODO SEGURO: Usar SetWindowPos para traer al frente SIN activar
        print("  🪟 Usando SetWindowPos...")
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,  # Traer al frente pero no "siempre encima"
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        )

        # 4. MÉTODO ALTERNATIVO: BringWindowToTop (menos invasivo)
        print("  🔼 Usando BringWindowToTop...")
        win32gui.BringWindowToTop(hwnd)

        # 5. MÉTODO ALTERNATIVO: FlashWindow para llamar atención sin forzar
        print("  💡 Haciendo flash de ventana...")
        win32gui.FlashWindow(hwnd, True)

        # Pequeña pausa para que los cambios tomen efecto
        time.sleep(0.2)

        # 6. Verificar resultado SIN usar SetFocus
        ventana_activa = win32gui.GetForegroundWindow()
        
        if ventana_activa == hwnd:
            print(f"✅ Ventana {hwnd} activada correctamente")
            return True
        else:
            # Aunque no sea la ventana activa, verificar si al menos es visible
            if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                print(f"⚠️  Ventana {hwnd} visible pero no tiene foco (puede ser normal)")
                return True  # Consideramos éxito si está visible
            else:
                print(f"❌ No se pudo activar ventana {hwnd}. Ventana activa actual: {ventana_activa}")
                return False

    except Exception as e:
        print(f"💥 Error activando ventana: {e}")
        return False





def lock_window_position(hwnd, lock=True):
    """
    Bloquear/desbloquear la posición y tamaño de una ventana
    """
    try:
        # Obtener estilo actual de la ventana
        current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        
        if lock:
            # Quitar bordes redimensionables y barra de título
            new_style = current_style & ~(
                win32con.WS_THICKFRAME |  # Quitar borde redimensionable
                win32con.WS_MAXIMIZEBOX | # Quitar botón maximizar
                win32con.WS_MINIMIZEBOX   # Quitar botón minimizar
            )
            print(f"Ventana {hwnd} bloqueada")
        else:
            # Restaurar bordes redimensionables
            new_style = current_style | (
                win32con.WS_THICKFRAME |  # Restaurar borde redimensionable
                win32con.WS_MAXIMIZEBOX | # Restaurar botón maximizar
                win32con.WS_MINIMIZEBOX   # Restaurar botón minimizar
            )
            print(f"Ventana {hwnd} desbloqueada")
        
        # Aplicar nuevo estilo
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
        
        # Forzar redibujado
        win32gui.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | 
            win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
        )
        
        return True
    except Exception as e:
        print(f"Error bloqueando ventana: {e}")
        return False