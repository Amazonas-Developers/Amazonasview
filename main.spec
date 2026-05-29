# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import shutil
from PySide6 import QtCore

block_cipher = None

# Obtener rutas
pyside_dir = os.path.dirname(QtCore.__file__)
current_dir = os.getcwd()

print(f"📁 Directorio actual: {current_dir}")
print(f"📁 Directorio PySide6: {pyside_dir}")

# Verificar que los archivos existen
def verify_files():
    files_to_check = [
        'src/workers/capture_woker.py',
        'src/resources/ico.png'
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(current_dir, file_path)
        if os.path.exists(full_path):
            print(f"✅ ARCHIVO ENCONTRADO: {file_path}")
        else:
            print(f"❌ ARCHIVO NO ENCONTRADO: {file_path}")

verify_files()

a = Analysis(
    ['src/main.py'],
    pathex=[current_dir, os.path.join(current_dir, 'src')],
    binaries=[],
    datas=[
        # Plugins esenciales de Qt
        (os.path.join(pyside_dir, 'plugins', 'platforms'), 'PySide6/plugins/platforms'),
        (os.path.join(pyside_dir, 'plugins', 'styles'), 'PySide6/plugins/styles'),
        (os.path.join(pyside_dir, 'plugins', 'iconengines'), 'PySide6/plugins/iconengines'),
        
        # Recursos (estos irán a _internal)
        (os.path.join(current_dir, 'src', 'resources', 'ico.png'), 'src/resources'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'PySide6.QtProcess',
        'PySide6.QtNetwork',
        'PySide6.QtWebSockets',
        'numpy',
        'PIL',
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageGrab',
        'win32gui',
        'win32ui',
        'win32con',
        'win32api',
        'pywintypes',
        'core.capture_exaple',
        'core.run_controller',
        'core.window_controller',
        'core.app_singleton',
        'core.state_global.hwnd',
        'model.windows.list_windows',
        'gui.windows_main',
        'gui.components.SplashScreen',
        'gui.components.render_box.render_box',
        'gui.components.sidebar.sidebar_dock',
        'traceback',
        'json',
        'base64',
        'io',
        'ctypes',
        'ctypes.wintypes',
        'warnings',
    ] ,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)

# 🔥 PASO CRÍTICO: Copiar el worker a la ubicación deseada DESPUÉS del build
def copy_worker_to_correct_location():
    print("\n" + "="*50)
    print("📦 MOVIENDO WORKER A LA UBICACIÓN CORRECTA")
    print("="*50)
    
    dist_main_dir = os.path.join(current_dir, 'dist', 'main')
    worker_source = os.path.join(current_dir, 'src', 'workers', 'capture_woker.py')
    worker_target_dir = os.path.join(dist_main_dir, 'src', 'workers')
    worker_target = os.path.join(worker_target_dir, 'capture_woker.py')
    
    # Verificar que el worker fuente existe
    if not os.path.exists(worker_source):
        print(f"❌ ERROR: No existe el worker fuente: {worker_source}")
        return False
    
    # Crear directorio de destino si no existe
    os.makedirs(worker_target_dir, exist_ok=True)
    
    # Copiar el worker
    try:
        shutil.copy2(worker_source, worker_target)
        print(f"✅ Worker copiado exitosamente:")
        print(f"   DE: {worker_source}")
        print(f"   A:  {worker_target}")
        
        # Verificar que se copió correctamente
        if os.path.exists(worker_target):
            file_size = os.path.getsize(worker_target)
            print(f"   TAMAÑO: {file_size} bytes")
            return True
        else:
            print(f"❌ ERROR: No se pudo verificar la copia")
            return False
            
    except Exception as e:
        print(f"❌ ERROR copiando worker: {e}")
        return False

# También copiar el archivo de recursos
def copy_resources_to_correct_location():
    print("\n" + "="*50)
    print("📦 MOVIENDO RECURSOS A LA UBICACIÓN CORRECTA")
    print("="*50)
    
    dist_main_dir = os.path.join(current_dir, 'dist', 'main')
    resource_source = os.path.join(current_dir, 'src', 'resources', 'ico.png')
    resource_target_dir = os.path.join(dist_main_dir, 'src', 'resources')
    resource_target = os.path.join(resource_target_dir, 'ico.png')
    
    if not os.path.exists(resource_source):
        print(f"⚠️ ADVERTENCIA: No existe el recurso: {resource_source}")
        return False
    
    # Crear directorio de destino si no existe
    os.makedirs(resource_target_dir, exist_ok=True)
    
    # Copiar el recurso
    try:
        shutil.copy2(resource_source, resource_target)
        print(f"✅ Recurso copiado exitosamente:")
        print(f"   DE: {resource_source}")
        print(f"   A:  {resource_target}")
        return True
    except Exception as e:
        print(f"❌ ERROR copiando recurso: {e}")
        return False

# Ejecutar las copias después del build
copy_worker_to_correct_location()
copy_resources_to_correct_location()

# Verificación final
def final_verification():
    print("\n" + "="*50)
    print("🔍 VERIFICACIÓN FINAL")
    print("="*50)
    
    dist_main_dir = os.path.join(current_dir, 'dist', 'main')
    worker_target = os.path.join(dist_main_dir, 'src', 'workers', 'capture_woker.py')
    resource_target = os.path.join(dist_main_dir, 'src', 'resources', 'ico.png')
    
    checks_passed = 0
    total_checks = 2
    
    # Verificar worker
    if os.path.exists(worker_target):
        print(f"✅ WORKER ENCONTRADO: {worker_target}")
        checks_passed += 1
    else:
        print(f"❌ WORKER NO ENCONTRADO: {worker_target}")
    
    # Verificar recurso
    if os.path.exists(resource_target):
        print(f"✅ RECURSO ENCONTRADO: {resource_target}")
        checks_passed += 1
    else:
        print(f"❌ RECURSO NO ENCONTRADO: {resource_target}")
    
    print(f"\n📊 RESULTADO: {checks_passed}/{total_checks} verificaciones exitosas")
    
    if checks_passed == total_checks:
        print("🎉 ¡Build completado exitosamente!")
    else:
        print("⚠️  Build completado con advertencias")

final_verification()