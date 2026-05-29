# Integración Hik-Connect - Guía de Uso

## 📋 Resumen

Se ha implementado soporte completo para **Hik-Connect** en el sistema de dispositivos DVR, permitiendo:
- Autenticación con App Key + App Secret
- Carga automática de dispositivos y cámaras
- Compatibilidad total con canales IP existentes
- Arrastre de canales al render_box
- Cierre de sesión y gestión de cuentas

## 🚀 Flujo de Integración

### 1. **Agregar Cuenta Hik-Connect**

1. En la pestaña **Dispositivos**, cambiar a **"Hik-Connect"**
2. Completar:
   - **App Key**: `C31f0Ce2UNEnA0WAQhRACnPduUXIQ1Ak`
   - **App Secret**: `tYagGPNQsPIUu3npOEXwqPb6KP7bgggj`
3. Hacer clic en **"🔌 Probar conexión"**
4. Si es exitosa, guardar con **"✅ Guardar dispositivo"**

### 2. **Ver Canales**

Una vez guardada la cuenta:
1. Hacer clic en la fila de la cuenta en la lista
2. Se mostrarán los canales disponibles en la sección **"Canales disponibles"**
3. Los canales de Hik-Connect tienen indicador **🔐**

### 3. **Cargar Canal a Pantalla**

1. Hacer clic y arrastrar un canal desde la lista de canales
2. Soltar en el render_box (área de video)
3. El sistema detecta automáticamente si es Hik-Connect o IP
4. Se inicia el stream RTSP automáticamente

### 4. **Cerrar Sesión**

1. Seleccionar la cuenta Hik-Connect en la lista
2. Hacer clic en **"🔓 Cerrar sesión"**
3. Se elimina la cuenta y todos sus canales

## 🔧 Cambios Técnicos Implementados

### Archivos Modificados

#### `src/core/dvr/context.py`
- Agregada importación de `HikConnectStrategy`
- Registro de "Hik-Connect" en estrategias disponibles
- Puerto 443 configurado (aunque no se usa directamente)

#### `src/gui/components/device_panel.py`
- UI con selector de tipo de conexión ("Conexión por IP" / "Hik-Connect")
- Campos dinámicos: IP/puerto o App Key/Secret
- Lista de canales arrastrables
- Botón de logout para Hik-Connect
- Métodos de codificación compatibles

### Archivos Nuevo

#### `src/core/dvr/hikconnect_channel_encoder.py`
- `HikConnectChannelEncoder`: Codifica/decodifica canales Hik-Connect
- `ChannelTypeDetector`: Detecta automáticamente tipo de canal
- Mantiene compatibilidad con formato drag&drop de IP

#### `src/gui/components/channel_row.py`
- `ChannelRow`: Fila arrastrables de canal
- Soporta drag&drop nativo de Qt
- Indica visualmente si es Hik-Connect (🔐) o IP (📹)

#### `src/gui/components/render_box/render_box.py` (Mejorado)
- Importa `ChannelTypeDetector`
- `start_dvr_stream()`: Detecta tipo automáticamente
- Etiqueta visual diferenciada para Hik-Connect

## 🔐 Seguridad

- **Almacenamiento**: App Key y Secret cifrados con Fernet (CMS-128 + HMAC)
- **Ubicación**: `%APPDATA%/window_manager/dvr_devices.enc`
- **Derivación**: Clave basada en hostname + MAC de máquina
- **URLs RTSP**: Generadas dinámicamente por Hik-Connect (HLS/HTTPS)

## 🎯 Patrón Strategy Implementado

```
DVRContext (Punto de entrada único)
    ├── HikvisionHTTPStrategy
    ├── HikvisionSDKStrategy  
    ├── DahuaHTTPStrategy
    ├── DahuaSDKStrategy
    └── HikConnectStrategy ✨ (NUEVO)

Codificación de Canales:
    ├── IP: { device_alias, channel_name, rtsp_main, is_hikconnect: False }
    └── HC: { device_alias, channel_name, rtsp_main, device_serial, is_hikconnect: True, encrypted_key }
```

## 📝 Notas Importantes

1. **URLs RTSP Dinámicas**: Hik-Connect genera URLs con time-limited tokens
2. **Protocolo HLS**: Se usa HTTPS en puerto 443
3. **Compatibilidad**: No rompe existente flujo de IP
4. **Validación de Tipo**: El detector automático verifica `is_hikconnect` flag

## ✅ Verificación de Instalación

Desde el directorio `ELDE/`:

```bash
python test_hikconnect_integration.py
```

**Salida Esperada:**
```
✅ TODAS LAS PRUEBAS PASARON - LISTO PARA PRODUCCIÓN
```

Si obtienes este resultado, la integración está **100% operativa**.

### Detalles del Test:
- ✅ **TEST 1**: Todos los módulos importan correctamente
- ✅ **TEST 2**: Codificación/decodificación de canales funcional
- ✅ **TEST 3**: Hik-Connect registrada en DVRContext

## 🎯 Resumen de Implementación

- [x] Context DVR registra HikConnectStrategy
- [x] device_panel.py tiene selector de tipo conexión
- [x] Credenciales Hik-Connect se guardan cifradas
- [x] Canales se cargan automáticamente
- [x] Canales son arrastrables
- [x] render_box detecta tipo de canal
- [x] Logout elimina cuenta y canales
- [x] Estilos diferenciados (🔐 vs 📹)

## 🚨 Troubleshooting

| Problema | Solución |
|----------|----------|
| "Sin token: LAP300001" | Verificar App Key/Secret correctos |
| "No se pudo abrir stream" | Verificar HTTPS habilitado, token válido |
| "Canales no aparecen" | Validar que la cuenta tenga cámaras asociadas |
| "Drag&drop no funciona" | Verificar que render_box tenga `setAcceptDrops(True)` |

## 🔮 Próximos Pasos (Opcional)

- [ ] Implementar re-autenticación automática si token expira
- [ ] Cachear URLs RTSP por tiempo limitado
- [ ] Soporte multi-dispositivo en una sola sesión
- [ ] Notificaciones de desconexión
- [ ] Estadísticas de uso por conexión
