window_manager/
├── main.py                     # Punto de entrada y inicialización de la app.
|
├── core/                       # Lógica de negocio (Controladores, lógica de captura).
│   ├── network/
│   │   
|   │_init__.py
│   │   │  
│   │   ├── socket_client.py    # Maneja la conexión continua (WebSockets/Socket.io)
│   │   └── api_client.py
│   │   
│   └── window_controller.py
|
├── native/                     # Funciones C++ y Pybind11 para tareas nativas.
│   ├── ...
│   └── bindings.cpp
|
├── gui/                        # Capa de presentación (Widgets, Ventana principal).
│   ├── main_window.py
│   ├── components/
│   │   ├── ...
│   │   └── window_preview.py   # Contiene la clase interactive_imageLabel
│   └── styles/
│       └── theme.py
|
├── models/                     # Modelos de datos y la CLASE que maneja la persistencia.
│   ├── __init__.py
│   ├── window_data.py
│   └── settings_model.py       # NUEVO: Clase central para cargar/guardar la configuración del usuario.
|
├── config/                     # Configuración estática y por defecto.
│   ├── __init__.py
│   └── default_settings.json   # NUEVO: Valores iniciales de los puntos, tema, etc.
|
└── data_user/                  # Ubicación LÓGICA donde se guardan los archivos de usuario.
    └── user_settings.json      # ARCHIVO REAL: Se guarda en una ruta específica del SO (ej. %APPDATA%).ssss
---

## Instalación en otra computadora

> **Importante:** El SDK nativo de Hikvision (los archivos `.dll`, `.exe` y `.lib`)
> **NO** está incluido en este repositorio porque pesa ~69 MB y es software de
> terceros. Hay que descargarlo aparte y colocarlo manualmente (ver paso 4).

### 1. Clonar el repositorio
```bash
git clone <URL-del-repo>
cd "Amazonas View"
```

### 2. Crear y activar un entorno virtual
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Colocar el SDK de Hikvision (necesario para el modo SDK nativo)
1. Descarga el **HCNetSDK** desde el portal de desarrolladores de Hikvision
   (versión usada por la app: `EN-HCNetSDKV6.1.9.4_build20220412_win64`).
2. Copia **todas** las DLLs de la carpeta `\lib\` del SDK dentro de:
   ```
   src/sdk/hikvision/
   ```
   El archivo principal debe quedar en `src/sdk/hikvision/HCNetSDK.dll`,
   junto con las subcarpetas `HCNetSDKCom/` y demás DLLs.
3. (Opcional, Dahua) Copia `dhnetsdk.dll`, `dhconfigsdk.dll` y `dhplay.dll`
   en `src/sdk/dahua/`.

> En cada carpeta hay un archivo `COLOCA_DLLS_AQUI.txt` como recordatorio.
> Alternativamente, dentro de la app puedes indicar la ruta del DLL en el
> campo **"Ruta SDK"** en lugar de copiarlo aquí.

### 5. Ejecutar
```bash
python src/main.py
```

### ¿Y si no quiero usar el SDK nativo?
La aplicación también soporta conexión por **HTTP/ISAPI** (Hikvision y Dahua)
y por **Hik-Connect**, que **no requieren** los DLLs. En ese caso puedes
omitir el paso 4 y elegir ese modo de conexión al añadir el dispositivo.

## Dashboard de analítica

La barra de estado inferior tiene un botón (ícono de IA) para **abrir el
dashboard de analítica** del backend SERVER-IA (detecciones, demografía,
reportes por fecha) en el navegador por defecto —
[src/gui/components/custom_status_bar.py](src/gui/components/custom_status_bar.py).
Asume que el servidor corre en `http://127.0.0.1:9000/` (mismo host/puerto
que el WebSocket de inferencia); si el servidor esta en otra maquina, cambia
`DASHBOARD_URL` en ese archivo o abre la URL manualmente.

Cuando el modo IA está activo, el cliente también envía `frame_width` y
`frame_height` en el payload del WebSocket (ver
[src/gui/components/render_box/render_box.py](src/gui/components/render_box/render_box.py)),
para que el servidor pueda registrar la resolución real de cada cámara junto
con cada visita detectada.
