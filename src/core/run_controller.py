import sys
import ctypes



def check_admin_privileges(callback):
    """Verificar y manejar permisos de administrador"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            callback()
            sys.exit(1)
        return True
    except:
        callback()
        sys.exit(1)