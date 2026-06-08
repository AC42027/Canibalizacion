# 🛠️ Sistema de Control de Canibalizaciones — Planta L504

Este es el repositorio oficial del **Sistema de Control de Canibalizaciones** de Goodyear Planta L504. Este sistema web centraliza, registra, audita y gestiona el flujo de repuestos/componentes transferidos ("canibalizados") entre máquinas donantes y máquinas receptoras dentro de la planta, asegurando la trazabilidad y la normalización de los activos.

---

## 🚀 Inicio Rápido (Lanzador del Sistema)

El proyecto cuenta con un script automatizado para plataformas Windows que simplifica la inicialización del entorno y el servicio web:

1. **Ejecutar el Lanzador**: Haz doble clic en el archivo [INICIAR_SISTEMA.bat](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/INICIAR_SISTEMA.bat).
2. **Qué hace el script automáticamente**:
   - Valida la instalación de Python en el sistema.
   - Crea un entorno virtual de Python (`venv`) si no existe.
   - Activa el entorno virtual e instala/actualiza silenciosamente las dependencias de [requirements.txt](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/requirements.txt).
   - Abre tu navegador predeterminado en `http://localhost:8080/index.html`.
   - Inicia el servidor web backend mediante Uvicorn ejecutando [app.py](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/app.py).

---

## 📋 Resumen de Nuevas Funcionalidades y Cambios Recientes

El sistema ha sido mejorado con características avanzadas de búsqueda, seguridad, auditoría e interfaz interactiva:

### 1. Búsqueda y Expansión Dinámica del Árbol de Equipos
* **Archivo**: [dashboard.html](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/dashboard.html)
* **Funcionalidad**: Al ingresar un término de búsqueda para buscar una máquina o componente, el árbol de equipos completo (cargado de [arbol_equipos.json](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/arbol_equipos.json)) se expande de forma automática y resalta las coincidencias de inmediato.
* **Impacto**: Optimiza el tiempo del operador al ubicar jerárquicamente cualquier activo sin requerir memoria de su división o área exacta.

### 2. Autenticación y Auditoría Obligatoria
* **Archivos**: [detail.html](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/detail.html) y [app.py](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/app.py)
* **Restricción de Acceso**: La edición de la **Fecha estimada de reposición** y el cambio del estado de normalización (de *Pendiente* a *Normalizado* y viceversa) requieren un inicio de sesión con credenciales válidas.
* **Historial de Cambios (Logs de Auditoría)**: Cada acción de edición se registra en la base de datos dentro de la tabla `historial_cambios`. El detalle muestra un panel de historial detallado que contiene:
  - Nombre del responsable.
  - Fecha y hora exacta del cambio.
  - Campo modificado (`tiempo_reposicion` o `normalizado`).
  - Valor anterior y valor nuevo.

### 3. Expiración de Sesión por Inactividad (Auto-Logout)
Para mitigar riesgos de seguridad por pantallas abiertas sin supervisión en planta:
* **Cliente (Navegador)**: Cierra la sesión automáticamente después de **10 minutos** de inactividad física (sin movimientos del mouse, clics o teclado).
* **Servidor (FastAPI)**: Expira el token de sesión a los **15 minutos** de inactividad.
* **Configuración del Tiempo**:
  * *Servidor*: Modificar la constante `SESSION_TIMEOUT_SECONDS = 900` en [app.py](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/app.py#L16).
  * *Cliente*: Modificar el tiempo del timeout en la función de control de inactividad de [detail.html](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/detail.html) (ej. `600000` ms para 10 minutos).

### 4. Visualización Jerárquica Completa en Dashboard
* **Archivo**: [history.html](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/history.html)
* **Mejora**: En la columna **Máquinas (Origen ➔ Destino)** del listado de movimientos, se visualiza el nombre de la máquina y debajo la **División y Área** correspondiente en formato secundario y limpio. Esto proporciona contexto instantáneo de la procedencia y el destino del repuesto.

### 5. Panel de Filtros Interactivos Combinados
* **Archivo**: [history.html](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/history.html)
* **Reorganización**: El panel superior está estructurado en filas con títulos a la izquierda y un borde decorativo amarillo:
  1. *Filtro de Registro*: Tarjetas interactivas de *Total Canibalizaciones*, *Pendientes de Normalizar* y *Normalizados* (que operan como botones de filtrado instantáneo), y una tarjeta dinámica para visualizar el *Usuario Activo*.
  2. *Filtro por División*: Botones rápidos para filtrar movimientos de *División A*, *División B*, *Facilities* y *Utilities*.
* **Multifiltro**: Los filtros de estado, división y la barra de búsqueda por texto operan de manera conjunta y simultánea, mostrando la cantidad de resultados y las condiciones aplicadas en tiempo real.

---

## 🔑 Credenciales de Acceso (Entorno de Prueba)

El sistema provee tres roles distintos con credenciales de prueba pre-pobladas en la base de datos SQLite:

| Usuario | Contraseña | Rol | Permisos |
| :--- | :--- | :--- | :--- |
| **planificador** | `goodyear123` | `planificador` | Edición de fechas y normalización |
| **confiabilidad** | `goodyear123` | `ingeniero_confiabilidad` | Edición de fechas y normalización |
| **admin** | `admin123` | `admin` | Acceso completo de administrador |

---

## 🛠️ Arquitectura y Estructura del Código

El proyecto sigue una arquitectura ligera y autocontenida:

```bash
Canibalizacion/
│
├── app.py                     # Backend FastAPI (Servicios API, Auth, LDAP, SAP Stock)
├── crear_bd.py                # Script inicializador de tablas SQLite (canibalizacion.db)
├── migrar_datos.py            # Utilidad de migración de registros
├── ver_datos.py               # Script CLI para consultar registros en base de datos
│
├── index.html                 # Vista Principal: Formulario de creación de Canibalización
├── history.html               # Vista Dashboard: Buscador, filtros y tabla de historial
├── detail.html                # Vista Detalle: Formulario de consulta, auth y auditoría
├── dashboard.html             # Vista Árbol: Navegador de la estructura jerárquica de activos
├── styles.css                 # Hojas de estilo unificadas (Goodyear Theme: Dark & Yellow accents)
│
├── arbol_equipos.json         # Base de datos jerárquica de la planta (Divisiones/Áreas/Líneas/Máquinas)
├── canibalizacion.db          # Base de datos relacional SQLite activa
│
├── readmes/                   # Documentación adicional del proyecto
│   ├── AVANCES_Y_REGISTROS.md # Registro extendido de avances e instrucciones técnicas
│   └── README.md              # Enlace rápido de documentación
│
└── INICIAR_SISTEMA.bat        # Lanzador automatizado para Windows
```

### Base de Datos (`canibalizacion.db`)
El motor de datos emplea **SQLite** con la siguiente distribución relacional:
* **`registros`**: Almacena todos los campos del formulario de canibalización (ID, fecha, componentes, máquinas de origen y destino, orden de trabajo, responsables y estado de normalización).
* **`usuarios`**: Almacena los identificadores de usuarios, nombres, contraseñas encriptadas mediante SHA-256 y sus roles respectivos.
* **`historial_cambios`**: Registra los cambios de estado y fechas asociando el responsable de la acción.

### Integraciones Externas (APIs de Planta)
El archivo [app.py](file:///c:/Users/ac42028/Documents/canibalizacion/Canibalizacion/app.py) integra llamadas a los servidores internos de la planta:
* **LDAP (Búsqueda de Personal)**: Consulta de manera dinámica los perfiles de los técnicos, jefes de departamento, puestos y correos en `http://10.107.194.70/conn/temp/ldap.php`.
* **SAP Stock (Spare Parts)**: Búsqueda y consulta de la disponibilidad física de repuestos (nuevo/reparado), ubicaciones en bodega y valorizaciones monetarias a través del servicio en `http://10.107.194.72/ingenieria/spare_parts/asset/php/get_spare.php`.

---
*Goodyear L504 - Área de Confiabilidad e Ingeniería de Mantenimiento*
