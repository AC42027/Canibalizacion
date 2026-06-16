# 🛠️ Sistema de Control de Canibalizaciones — Planta L504

Este es el repositorio oficial del **Sistema de Control de Canibalizaciones** de Goodyear Planta L504. Este sistema web centraliza, registra, audita y gestiona el flujo de repuestos/componentes transferidos ("canibalizados") entre máquinas donantes y máquinas receptoras dentro de la planta, asegurando la trazabilidad y la normalización de los activos.

---

## 🚀 Inicio Rápido (Desarrollo en Windows)

El proyecto cuenta con un script automatizado para plataformas Windows que simplifica la inicialización del entorno y el servicio web:

1. **Ejecutar el Lanzador**: Haz doble clic en el archivo [INICIAR_SISTEMA.bat](./INICIAR_SISTEMA.bat).
2. **Qué hace el script automáticamente**:
   - Valida la instalación de Python en el sistema.
   - Crea un entorno virtual de Python (`venv`) si no existe.
   - Activa el entorno virtual e instala/actualiza silenciosamente las dependencias de [requirements.txt](./requirements.txt).
   - Abre tu navegador predeterminado en `http://localhost:8080/index.html`.
   - Inicia el servidor web backend mediante Uvicorn ejecutando [app.py](./app.py).

---

## 🔐 Gestión de Credenciales y Variables de Entorno

El sistema maneja credenciales sensibles para servicios externos (como servidores LDAP corporativos y servidores de correo SMTP de Office 365) mediante variables de entorno especificadas en el archivo [.env](./.env).

### 1. Variables Configuradas en `.env`

| Variable | Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| **LDAP_SERVER** | String | Host o dirección del servidor Active Directory / LDAP | `'ldapsCLSLA.la.ad.goodyear.com'` |
| **LDAP_PORT** | Integer | Puerto de conexión LDAP (3268 para Global Catalog) | `3268` |
| **LDAP_USER** | String | Usuario corporativo para enlazar (bind) | `'la\\LDA1425'` |
| **LDAP_PASS** | String | Contraseña del usuario LDAP | *[Definida en .env]* |
| **SMTP_SERVER** | String | Servidor de correo de salida (SMTP) | `smtp.office365.com` |
| **SMTP_PORT** | Integer | Puerto del servicio SMTP (habitualmente 587 para TLS) | `587` |
| **SMTP_USER** | String | Cuenta de correo emisora de notificaciones | `system_metrics@goodyear.com` |
| **SMTP_PASS** | String | Contraseña de la cuenta de correo | *[Definida en .env]* |
| **SMTP_USE_TLS**| Boolean| Indica si se debe emplear encriptación TLS | `True` |
| **SMTP_USE_SSL**| Boolean| Indica si se debe emplear encriptación SSL directa | `False` |

> [!WARNING]
> Nunca subas el archivo `.env` con credenciales reales a repositorios públicos o compartidos de Git. Asegúrate de que el archivo `.env` esté incluido en el archivo `.gitignore`.

### 2. Cómo se consumen estas credenciales en la Aplicación (Python)

Para que el backend en [app.py](./app.py) pueda leer y utilizar estas variables, se debe agregar el módulo `python-dotenv` al proyecto.

1. **Instalar Dependencia**:
   Agrega `python-dotenv` a [requirements.txt](./requirements.txt) o instálalo manualmente:
   ```bash
   pip install python-dotenv
   ```

2. **Carga en el Código (`app.py`)**:
   Inserta el siguiente código al inicio del archivo principal para cargar automáticamente las variables desde el archivo `.env` en `os.environ`:
   ```python
   import os
   from dotenv import load_dotenv

   # Cargar variables del archivo .env al entorno
   load_dotenv()

   # Ejemplo de lectura de variables LDAP
   LDAP_SERVER = os.getenv("LDAP_SERVER")
   LDAP_PORT = int(os.getenv("LDAP_PORT", 389))
   LDAP_USER = os.getenv("LDAP_USER")
   LDAP_PASS = os.getenv("LDAP_PASS")

   # Ejemplo de lectura de variables SMTP
   SMTP_SERVER = os.getenv("SMTP_SERVER")
   SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
   SMTP_USER = os.getenv("SMTP_USER")
   SMTP_PASS = os.getenv("SMTP_PASS")
   SMTP_USE_TLS = os.getenv("SMTP_USE_TLS") == "True"
   ```

---

## 🐧 Despliegue en Producción (RedHat Enterprise Linux)

Mientras que el desarrollo se realiza en entornos Windows, el servidor de producción definitivo correrá bajo **RedHat Enterprise Linux (RHEL)**. A continuación, se detalla la guía de configuración y despliegue para ese entorno.

### 1. Requisitos Previos en RedHat
Instala los paquetes necesarios del sistema usando el gestor de paquetes de RedHat (`dnf` o `yum`):
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-virtualenv sqlite nginx
```

### 2. Estructura y Permisos del Proyecto
Se recomienda ubicar la aplicación en `/opt/canibalizacion`. Es vital restringir los permisos para que los usuarios sin privilegios no puedan leer el archivo de configuración `.env`:

```bash
# Crear directorio de la aplicación
sudo mkdir -p /opt/canibalizacion
sudo chown -R $USER:$USER /opt/canibalizacion

# Clonar o transferir los archivos al directorio
# (Mover archivos aquí)

# Crear entorno virtual e instalar requerimientos
cd /opt/canibalizacion
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Asegurar las Credenciales en RedHat
Para proteger las contraseñas LDAP y SMTP del archivo `.env`, se deben ajustar los permisos del sistema de archivos linux:
```bash
# Cambiar propietario y permisos del .env
chmod 600 /opt/canibalizacion/.env
```
*Esto asegura que solo el usuario propietario de la ejecución de la app pueda leer el archivo con las credenciales.*

### 4. Configuración como Servicio del Sistema (Systemd)
Para garantizar que el servicio FastAPI se inicie automáticamente con el sistema, se recupere ante fallas y corra en segundo plano de manera segura, crearemos un servicio `systemd`:

1. Crea el archivo de servicio `/etc/systemd/system/canibalizacion.service`:
   ```ini
   [Unit]
   Description=Servicio de Control de Canibalizaciones (FastAPI)
   After=network.target

   [Service]
   User=goodyear_app
   Group=goodyear_app
   WorkingDirectory=/opt/canibalizacion
   EnvironmentFile=/opt/canibalizacion/.env
   ExecStart=/opt/canibalizacion/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8080
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
   *(Nota: Asegúrate de crear el usuario de sistema `goodyear_app` o usar el usuario configurado en tu servidor de RedHat).*

2. Habilitar y arrancar el servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable canibalizacion.service
   sudo systemctl start canibalizacion.service
   sudo systemctl status canibalizacion.service
   ```

### 5. Configuración del Firewall de RedHat
Por defecto, el firewall de RedHat bloqueará el tráfico entrante al puerto 8080. Ejecuta lo siguiente para permitirlo:
```bash
sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### 6. Configuración de Proxy Inverso Nginx (Opcional - Recomendado)
Para servir la aplicación sobre el puerto estándar HTTP (80) o HTTPS (443), configura Nginx como proxy inverso hacia Uvicorn:

1. Modifica `/etc/nginx/nginx.conf` o añade un archivo de configuración en `/etc/nginx/conf.d/canibalizacion.conf`:
   ```nginx
   server {
       listen 80;
       server_name canibalizaciones.goodyear.com; # o IP del servidor

       location / {
           proxy_pass http://127.0.0.1:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
2. Reinicia Nginx y habilítalo:
   ```bash
   sudo systemctl restart nginx
   sudo systemctl enable nginx
   ```

---

## 🔑 Credenciales de Acceso (Entorno de Prueba Local)

El sistema provee tres roles distintos con credenciales de prueba pre-pobladas en la base de datos SQLite:

| Usuario | Contraseña | Rol | Permisos |
| :--- | :--- | :--- | :--- |
| **planificador** | `goodyear123` | `planificador` | Edición de fechas y normalización |
| **confiabilidad** | `goodyear123` | `ingeniero_confiabilidad` | Edición de fechas y normalización |
| **admin** | `admin123` | `admin` | Acceso completo de administrador |

---

## 🛠️ Estructura del Código y Base de Datos

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
├── arbol_equipos.json         # Base de datos jerárquica de la planta
├── canibalizacion.db          # Base de datos relacional SQLite activa
├── .env                       # Credenciales de integración LDAP y SMTP (local)
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
El archivo [app.py](./app.py) integra llamadas a los servidores internos de la planta:
* **LDAP (Búsqueda de Personal)**: Consulta de manera dinámica los perfiles de los técnicos, jefes de departamento, puestos y correos.
* **SAP Stock (Spare Parts)**: Búsqueda y consulta de la disponibilidad física de repuestos (nuevo/reparado), ubicaciones en bodega y valorizaciones monetarias.

---
*Goodyear L504 - Área de Confiabilidad e Ingeniería de Mantenimiento*
