# Registro de Avances y Desarrollo del Sistema - Planta L504

Este documento contiene el registro completo de todas las funcionalidades, configuraciones, accesos y base de datos implementadas en el **Sistema de Canibalizaciones** de la Planta L504. También incluye una guía práctica para que tú mismo puedas generar y actualizar archivos de documentación.

---

## 📋 Resumen de Avances y Características

### 1. Búsqueda y Despliegue en el Árbol de Equipos (`dashboard.html`)
- **Funcionamiento**: Permite buscar un componente o máquina de manera textual. Al ingresar la búsqueda, el árbol de equipos se expande de manera automática y resalta el elemento coincidente.
- **Beneficio**: Permite acceder y visualizar la ubicación jerárquica de la máquina incluso si el operador no recuerda la zona, división o área exacta.
- **Datos de Origen**: Se utiliza el archivo `arbol_equipos.json` (que posee la estructura completa de activos de la planta).

### 2. Autenticación y Auditoría (`detail.html` / `app.py`)
- **Acceso Restringido**: Tanto la edición de la fecha estimada de reposición como el cambio de estado (pasar a *Normalizado* o *Pendiente*) en el detalle del registro ahora requieren que el usuario inicie sesión mediante credenciales autorizadas.
- **Usuarios de Prueba (Base de Datos)**:
  - **Planificador**: Usuario `planificador` / Contraseña `goodyear123` (Rol: `planificador`)
  - **Ingeniero de Confiabilidad**: Usuario `confiabilidad` / Contraseña `goodyear123` (Rol: `ingeniero_confiabilidad`)
  - **Administrador**: Usuario `admin` / Contraseña `admin123` (Rol: `admin`)
- **Historial de Cambios**: Cada edición de fecha y cada cambio de estado (normalización/pendiente) se registra de forma obligatoria en la tabla `historial_cambios` de la base de datos, almacenando el nombre del responsable, la fecha/hora del cambio, el campo modificado (`tiempo_reposicion` o `normalizado`), el valor anterior y el valor nuevo. Estos se muestran en la sección de historial correspondiente en el detalle.

### 3. Expiración de Sesión por Inactividad (Auto-Logout)
Para proteger la integridad de los datos, el sistema cierra la sesión del usuario si no se detecta actividad (movimientos de mouse, clics o teclado):
- **Cliente (Navegador)**: Cierre automático tras **10 minutos** de inactividad.
- **Servidor (API)**: Expiración de token a los **15 minutos** de inactividad.
- **¿Cómo modificar estos tiempos?**
  - **En el Servidor**: Abre el archivo `app.py` y edita la constante de la línea 16: `SESSION_TIMEOUT_SECONDS = 900` (tiempo en segundos).
  - **En el Navegador**: Abre `detail.html` y edita el valor en la línea 424 (aproximadamente): `}, 600000);` (tiempo en milisegundos, donde `600000` ms = 10 minutos).

### 4. Visualización Completa de Máquinas en el Dashboard (`history.html`)
- **Mejora**: En la columna **Máquinas (Origen ➔ Destino)** del Dashboard, además de la máquina se muestra la **División** y el **Área** correspondiente debajo de cada nombre en formato compacto.
- **Funcionamiento**: Extrae y formatea de manera dinámica las partes del path jerárquico guardado en la base de datos (separado por ` > `).

### 5. Filtros Interactivos y Diseño Compacto en el Dashboard (`history.html`)
- **Estructura por Filas con Títulos**: El panel superior se reorganizó en dos filas bien definidas con títulos a la izquierda y un borde decorativo amarillo:
  1. **"Filtro Registro canibalizaciones"**: Contiene las tarjetas de *Total Canibalizaciones*, *Pendientes de Normalizar* y *Normalizados* (los cuales ahora actúan como botones para filtrar de forma instantánea) y la tarjeta *Usuario Activo* (que extrae dinámicamente el usuario logueado en la sesión).
  2. **"Filtro por división"**: Contiene los botones de filtro rápido para *División A*, *División B*, *Facilities* y *Utilities*.
- **Filtrado Combinado**: Puedes hacer clic en una División (ej. "División B") y en un Estado (ej. "Pendientes de Normalizar") simultáneamente, además de buscar por texto. El Dashboard combinará las tres condiciones y mostrará un mensaje de estado indicando los filtros aplicados.
- **Diseño Compacto**: Se disminuyó el tamaño de fuente, márgenes y relleno (`padding`) de los recuadros para que la tabla del historial de movimientos gane mayor protagonismo vertical.
