from fastapi import FastAPI, Body, HTTPException, status, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
import uvicorn
import os
import requests
from bs4 import BeautifulSoup
import hashlib
import uuid
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ldap_utils import load_env, get_emails_for_role

# Cargar variables de entorno al iniciar
load_env()

SESSION_TIMEOUT_SECONDS = 900  # 15 minutos
ACTIVE_SESSIONS = {}  # token -> {"usuario": str, "rol": str, "nombre": str, "last_activity": float}

app = FastAPI(title="Canibalización API")

def enviar_correo(subject: str, html_body: str, to_emails: list):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.office365.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "system_metrics@goodyear.com")
    smtp_pass = os.environ.get("SMTP_PASS", "medicioncontrolanalisis015")
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    smtp_use_ssl = os.environ.get("SMTP_USE_SSL", "False").lower() in ("true", "1", "yes")

    to_emails = [email.strip() for email in to_emails if email and "@" in email]
    if not to_emails:
        print("WARNING: No hay destinatarios válidos para el correo.")
        return False
        
    print(f"Enviando correo '{subject}' a {to_emails}...")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_emails)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    try:
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            
        if smtp_use_tls:
            server.starttls()
            
        if smtp_pass:
            server.login(smtp_user, smtp_pass)
            
        server.sendmail(smtp_user, to_emails, msg.as_string())
        server.quit()
        print("¡Correo enviado con éxito!")
        return True
    except Exception as e:
        print(f"ERROR: No se pudo enviar el correo por SMTP: {e}")
        return False

def enviar_correo_aviso(registro: dict):
    # Si la petición incluye una lista explícita de destinatarios seleccionados, la usamos directamente
    if registro.get("destinatarios_notificacion") and isinstance(registro["destinatarios_notificacion"], list):
        destinatarios = registro["destinatarios_notificacion"]
    else:
        # Fallback de resolución automática si no viene la lista
        destinatarios = []
        
        # a. Planner
        if registro.get("correo_responsable"):
            destinatarios.append(registro["correo_responsable"])
            
        # b. Ing Mtto
        if registro.get("correo_tecnico"):
            destinatarios.append(registro["correo_tecnico"])
            
        # c. ETL
        etl_emails = get_emails_for_role('etl')
        destinatarios.extend(etl_emails)
        
        # d. Planificador de bodega (solo si existe código de bodega)
        codigo_bodega = registro.get("codigo_bodega") or ""
        if codigo_bodega.strip():
            bodega_emails = get_emails_for_role('bodega')
            destinatarios.extend(bodega_emails)
        
    destinatarios = list(set([d.strip() for d in destinatarios if d and "@" in d]))
    if not destinatarios:
        print("WARNING: No se encontraron destinatarios de correo válidos para el aviso.")
        return
        
    subject = f"[AVISO] Nueva Canibalización Registrada - Planta L504"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; color: #1f2937; margin: 0; padding: 0; }}
            .container {{ max-width: 650px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-top: 6px solid #FFDE00; }}
            .header {{ background-color: #111827; color: #ffffff; padding: 20px; text-align: center; }}
            .header h2 {{ margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }}
            .content {{ padding: 25px; }}
            .section-title {{ font-size: 16px; font-weight: 600; color: #111827; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 5px; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .info-table td {{ padding: 10px 8px; border-bottom: 1px solid #f3f4f6; font-size: 14px; vertical-align: top; }}
            .info-table td.label {{ font-weight: 600; color: #4b5563; width: 35%; }}
            .info-table td.value {{ color: #111827; }}
            .footer {{ background-color: #f9fafb; text-align: center; padding: 15px; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
            .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; background-color: #fef3c7; color: #d97706; }}
            .badge-bodega {{ background-color: #dbeafe; color: #1e40af; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Control de Canibalizaciones — Planta L504</h2>
            </div>
            <div class="content">
                <p style="font-size: 15px; margin-top: 0; color: #374151;">Se ha registrado una nueva canibalización en el sistema. A continuación se detallan los datos del aviso:</p>
                
                <div class="section-title">Detalles del Repuesto</div>
                <table class="info-table">
                    <tr>
                        <td class="label">Repuesto:</td>
                        <td class="value"><strong>{registro.get('repuesto_nombre', 'N/A')}</strong></td>
                    </tr>
                    <tr>
                        <td class="label">Código SAP:</td>
                        <td class="value">{registro.get('repuesto_codigo') or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td class="label">Código Bodega:</td>
                        <td class="value">
                            {f'<span class="badge badge-bodega">{codigo_bodega}</span>' if codigo_bodega else '<em>No registrado</em>'}
                        </td>
                    </tr>
                    <tr>
                        <td class="label">Cantidad:</td>
                        <td class="value">{registro.get('cantidad', 1)} unidades</td>
                    </tr>
                    <tr>
                        <td class="label">Descripción:</td>
                        <td class="value">{registro.get('repuesto_descripcion', 'N/A')}</td>
                    </tr>
                </table>
                
                <div class="section-title">Ubicaciones y OT</div>
                <table class="info-table">
                    <tr>
                        <td class="label">Máquina Donante:</td>
                        <td class="value" style="color: #b91c1c;">{registro.get('maquina_donante', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">Máquina Receptora:</td>
                        <td class="value" style="color: #15803d;">{registro.get('maquina_receptora', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">Orden de Trabajo:</td>
                        <td class="value"><span class="badge">{registro.get('orden_trabajo', 'N/A')}</span></td>
                    </tr>
                    <tr>
                        <td class="label">Razón / Motivo:</td>
                        <td class="value">{registro.get('razon', 'N/A')}</td>
                    </tr>
                </table>
                
                <div class="section-title">Responsabilidades y Trazabilidad</div>
                <table class="info-table">
                    <tr>
                        <td class="label">Retirado por (Ing/Tec):</td>
                        <td class="value">{registro.get('retirado_por', 'N/A')} ({registro.get('correo_tecnico', 'N/A')})</td>
                    </tr>
                    <tr>
                        <td class="label">Planner Responsable:</td>
                        <td class="value">{registro.get('responsable_reposicion', 'N/A')} ({registro.get('correo_responsable', 'N/A')})</td>
                    </tr>
                    <tr>
                        <td class="label">Fecha Compromiso:</td>
                        <td class="value" style="font-weight: bold; color: #b91c1c;">{registro.get('tiempo_reposicion', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">Plan de Acción:</td>
                        <td class="value">{registro.get('plan_accion', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            <div class="footer">
                <strong>Gestión de Repuestos</strong><br>
                Planta Goodyear – Chile
            </div>
        </div>
    </body>
    </html>
    """
    
    enviar_correo(subject, html_body, destinatarios)


# Modelo de datos para validación
class LoginRequest(BaseModel):
    usuario: str
    contrasena: str

class EditDateRequest(BaseModel):
    registro_id: str
    nueva_fecha: str
    token: str

class NormalizarRequest(BaseModel):
    token: str

class Registro(BaseModel):
    id: Optional[str] = None
    fecha: str
    fecha_registro: str
    maquina_donante: str
    maquina_receptora: str
    repuesto_codigo: Optional[str] = None
    repuesto_nombre: str
    repuesto_descripcion: str
    cantidad: int
    razon: str
    orden_trabajo: str
    retirado_por: str
    cargo_tecnico: Optional[str] = None
    correo_tecnico: Optional[str] = None
    plan_accion: str
    tiempo_reposicion: str
    responsable_reposicion: str
    cargo_responsable: Optional[str] = None
    correo_responsable: Optional[str] = None
    personal_bodega: Optional[str] = None
    comentarios: Optional[str] = None
    codigo_bodega: Optional[str] = None
    usuario_registro: Optional[str] = None
    normalizado: bool = False
    destinatarios_notificacion: Optional[list] = None

DB_FILE = "canibalizacion.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
async def startup_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Crear tabla de usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario TEXT PRIMARY KEY,
        contrasena_hash TEXT,
        nombre TEXT,
        rol TEXT
    )
    """)
    # Crear tabla de historial de cambios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_cambios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registro_id TEXT,
        usuario TEXT,
        fecha_cambio TEXT,
        campo_modificado TEXT,
        valor_anterior TEXT,
        valor_nuevo TEXT
    )
    """)
    
    # Pre-poblar usuarios si no existen
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        def get_pwd_hash(password: str) -> str:
            return hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO usuarios (usuario, contrasena_hash, nombre, rol) VALUES (?, ?, ?, ?)",
                       ("planificador", get_pwd_hash("goodyear123"), "Planificador L504", "planificador"))
        cursor.execute("INSERT INTO usuarios (usuario, contrasena_hash, nombre, rol) VALUES (?, ?, ?, ?)",
                       ("confiabilidad", get_pwd_hash("goodyear123"), "Ing. Confiabilidad L504", "ingeniero_confiabilidad"))
        cursor.execute("INSERT INTO usuarios (usuario, contrasena_hash, nombre, rol) VALUES (?, ?, ?, ?)",
                       ("admin", get_pwd_hash("admin123"), "Administrador de Ingeniería", "admin"))
    conn.commit()
    conn.close()

@app.get("/api/equipos")
async def obtener_equipos():
    try:
        if not os.path.exists("arbol_equipos.json"):
            return {"error": "Archivo arbol_equipos.json no encontrado"}
        
        with open("arbol_equipos.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"DEBUG: Árbol de equipos servido con éxito ({len(data.get('divisiones', []))} divisiones)")
            return data
    except Exception as e:
        print(f"ERROR: No se pudo cargar el árbol: {str(e)}")
        return {"error": f"No se pudo cargar el árbol: {str(e)}"}

@app.get("/api/registros")
async def obtener_registros():
    if not os.path.exists(DB_FILE):
        return {"canibalizaciones": []}
    try:
        conn = get_db_connection()
        registros = conn.execute('SELECT * FROM registros').fetchall()
        conn.close()
        
        lista_registros = []
        for r in registros:
            d = dict(r)
            d["normalizado"] = bool(d["normalizado"])
            lista_registros.append(d)
            
        return {"canibalizaciones": lista_registros}
    except Exception as e:
        print(f"Error al obtener registros: {e}")
        return {"canibalizaciones": []}

@app.get("/api/registros/{registro_id}")
async def obtener_registro_detalle(registro_id: str):
    if not os.path.exists(DB_FILE):
        return {"error": "No hay datos"}
    try:
        conn = get_db_connection()
        registro = conn.execute('SELECT * FROM registros WHERE id = ?', (registro_id,)).fetchone()
        conn.close()
        
        if registro is None:
            return {"error": "Registro no encontrado"}
            
        d = dict(registro)
        d["normalizado"] = bool(d["normalizado"])
        return d
    except Exception as e:
        return {"error": f"Error al leer datos: {str(e)}"}

@app.post("/guardar")
async def guardar(registro: Registro, background_tasks: BackgroundTasks):
    import time
    nuevo_registro = registro.dict()
    
    # Asignar ID si no tiene (para nuevos registros)
    if not nuevo_registro.get("id"):
        nuevo_registro["id"] = str(int(time.time() * 1000))

    try:
        conn = get_db_connection()
        
        # Insertar nuevo registro
        conn.execute('''
            INSERT INTO registros (
                id, fecha, fecha_registro, maquina_donante, maquina_receptora, 
                repuesto_codigo, repuesto_nombre, repuesto_descripcion, cantidad, razon, 
                orden_trabajo, retirado_por, cargo_tecnico, correo_tecnico, plan_accion, 
                tiempo_reposicion, responsable_reposicion, cargo_responsable, correo_responsable, 
                personal_bodega, comentarios, codigo_bodega, usuario_registro, normalizado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nuevo_registro["id"], nuevo_registro.get("fecha", ""), nuevo_registro.get("fecha_registro", ""),
            nuevo_registro.get("maquina_donante", ""), nuevo_registro.get("maquina_receptora", ""),
            nuevo_registro.get("repuesto_codigo", ""), nuevo_registro.get("repuesto_nombre", ""),
            nuevo_registro.get("repuesto_descripcion", ""), int(nuevo_registro.get("cantidad", 0)),
            nuevo_registro.get("razon", ""), nuevo_registro.get("orden_trabajo", ""),
            nuevo_registro.get("retirado_por", ""), nuevo_registro.get("cargo_tecnico", ""),
            nuevo_registro.get("correo_tecnico", ""), nuevo_registro.get("plan_accion", ""),
            nuevo_registro.get("tiempo_reposicion", ""), nuevo_registro.get("responsable_reposicion", ""),
            nuevo_registro.get("cargo_responsable", ""), nuevo_registro.get("correo_responsable", ""),
            nuevo_registro.get("personal_bodega", ""), nuevo_registro.get("comentarios", ""),
            nuevo_registro.get("codigo_bodega", ""), nuevo_registro.get("usuario_registro", ""),
            1 if nuevo_registro.get("normalizado", False) else 0
        ))
        
        conn.commit()
        conn.close()
        
        # Disparar envío de correo en segundo plano
        background_tasks.add_task(enviar_correo_aviso, nuevo_registro)
        
        return {"mensaje": "Registro guardado correctamente", "id": nuevo_registro["id"]}
    except Exception as e:
        print(f"Error al guardar registro: {e}")
        return {"error": f"Error interno: {str(e)}"}

@app.post("/api/normalizar/{registro_id}")
async def normalizar(registro_id: str, req: NormalizarRequest):
    if not os.path.exists(DB_FILE):
        return {"error": "No hay datos"}
    
    # 1. Validar token
    if req.token not in ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada"
        )
        
    session = ACTIVE_SESSIONS[req.token]
    
    # Validar inactividad (15 min)
    if time.time() - session.get("last_activity", 0) > SESSION_TIMEOUT_SECONDS:
        del ACTIVE_SESSIONS[req.token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión ha expirado por inactividad"
        )
        
    # Actualizar actividad
    session["last_activity"] = time.time()
    
    usuario = session["usuario"]
    rol = session["rol"]
    
    # 2. Validar rol (solo planificador, ingeniero_confiabilidad o admin)
    if rol not in ["planificador", "ingeniero_confiabilidad", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para cambiar el estado"
        )
        
    try:
        conn = get_db_connection()
        registro = conn.execute('SELECT normalizado FROM registros WHERE id = ?', (registro_id,)).fetchone()
        
        if registro is None:
            conn.close()
            return {"error": "Registro no encontrado"}
            
        nuevo_estado = 0 if registro["normalizado"] else 1
        
        conn.execute('UPDATE registros SET normalizado = ? WHERE id = ?', (nuevo_estado, registro_id))
        
        # 3. Registrar en historial de cambios
        fecha_cambio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        valor_anterior = "Normalizado" if registro["normalizado"] else "Pendiente"
        valor_nuevo = "Pendiente" if registro["normalizado"] else "Normalizado"
        
        conn.execute("""
            INSERT INTO historial_cambios (registro_id, usuario, fecha_cambio, campo_modificado, valor_anterior, valor_nuevo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (registro_id, session["nombre"], fecha_cambio, "normalizado", valor_anterior, valor_nuevo))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "mensaje": f"Estado actualizado a {valor_nuevo}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar estado: {str(e)}"
        )

@app.delete("/api/registros/{registro_id}")
async def eliminar_registro(registro_id: str):
    if not os.path.exists(DB_FILE):
        return {"error": "No hay datos"}
    
    try:
        conn = get_db_connection()
        cursor = conn.execute('DELETE FROM registros WHERE id = ?', (registro_id,))
        eliminados = cursor.rowcount
        conn.commit()
        conn.close()
        
        if eliminados > 0:
            return {"mensaje": "Registro eliminado temporalmente"}
        
        return {"error": "Registro no encontrado"}
    except Exception as e:
        return {"error": f"Error al eliminar: {str(e)}"}

@app.get("/api/stock/repuesto/{query}")
async def verificar_stock(query: str, tipo: str = "codigo"):
    url = "http://10.107.194.72/ingenieria/spare_parts/asset/php/get_spare.php"
    
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # Mapeo según el comando curl del usuario
    is_cod = "true" if tipo == "codigo" else "false"
    is_des = "true" if tipo == "descripcion" else "false"
    
    payload = {
        "bus": query,
        "cod": is_cod,
        "des": is_des
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=5, verify=False)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Formatear todos los resultados encontrados
                    resultados = []
                    for item in data:
                        resultados.append({
                            "stock_nuevo": item.get("NewBatchStock", "0"),
                            "stock_reparado": item.get("refurbished", "0"),
                            "stock_total": item.get("unrestricted_stock", "0"),
                            "precio_nuevo": f"{item.get('price', '0')} {item.get('currency', 'USD')}",
                            "precio_reparado": f"{item.get('refur_price', '0')} {item.get('currency', 'USD')}",
                            "descripcion": item.get("description", "Sin descripción"),
                            "descripcion_extensa": item.get("po_text", ""),
                            "codigo": item.get("mat_number", ""),
                            "mensaje": f"Ubicación: {item.get('storageBin', 'N/A')}"
                        })
                    
                    return {
                        "existe": True,
                        "multiple": len(resultados) > 1,
                        "resultados": resultados,
                        # Mantener compatibilidad con el código anterior devolviendo el primero como principal
                        **resultados[0] 
                    }
            except:
                if len(response.text.strip()) > 10:
                    return {
                        "existe": True,
                        "stock": "Ver en Web", 
                        "descripcion": "Encontrado (HTML)",
                        "codigo": query,
                        "mensaje": "Respuesta recibida en formato tabla/HTML"
                    }
            
            return {"existe": False, "stock": 0, "descripcion": "", "mensaje": "No se encontró el repuesto"}
        else:
            return {"existe": False, "stock": 0, "descripcion": "", "mensaje": f"Error del servidor: {response.status_code}"}
            
    except requests.RequestException as e:
        return {"existe": False, "stock": 0, "descripcion": "", "mensaje": f"Error de conexión: Red interna no alcanzable"}

@app.get("/api/personal")
async def buscar_personal(q: str, division: Optional[str] = None):
    # Usamos solo el término q para la búsqueda inicial para no ser restrictivos
    # El filtrado por división se hará en el frontend si es necesario,
    # ya que el motor de búsqueda interno podría no manejar bien múltiples términos.
    search_url = f"http://10.107.194.70/conn/temp/ldap.php?search={q}"
    try:
        search_res = requests.get(search_url, timeout=3, verify=False)
        users_found = []
        if search_res.status_code == 200:
            users_found = search_res.json()
        
        # Si no hay resultados de búsqueda, intentar como ID directo
        if not users_found:
            users_found = [{"user": q, "name": q}]

        # Para cada usuario, obtener su perfil completo (título y correo)
        final_results = []
        for u in users_found[:5]: # Limitar a 5 para rapidez
            user_id = u.get("user")
            profile_url = f"http://10.107.194.70/conn/temp/ldap.php?user={user_id}"
            
            try:
                p_res = requests.get(profile_url, timeout=2, verify=False)
                if p_res.status_code == 200:
                    soup = BeautifulSoup(p_res.text, 'html.parser')
                    
                    # Extraer datos (usando la lógica refinada)
                    name_elem = soup.find('h4')
                    nombre = name_elem.get_text(strip=True) if name_elem else u.get("name")
                    
                    email_tag = soup.find(id="txtMail")
                    email = email_tag.get_text(strip=True) if email_tag else None
                    
                    boss_link = soup.find('a', href=lambda h: h and '?user=' in h)
                    boss_id = None
                    boss_name = None
                    if boss_link:
                        boss_full = boss_link.get_text(strip=True)
                        boss_name = boss_full
                        import re
                        m = re.search(r'\((.*?)\)', boss_full)
                        if m: boss_id = m.group(1)
                    
                    title_tag = soup.find('span', class_='text-muted')
                    title = title_tag.get_text(strip=True) if title_tag else "Personal"
                    
                    if nombre and len(nombre) > 3:
                        final_results.append({
                            "user": user_id,
                            "displayName": nombre,
                            "title": title,
                            "email": email,
                            "boss_name": boss_name,
                            "boss_id": boss_id
                        })
            except:
                continue

        return final_results
            
    except Exception as e:
        print(f"Error en búsqueda inteligente: {str(e)}")
        return []

@app.post("/api/login")
async def login(req: LoginRequest):
    pwd_hash = hashlib.sha256(req.contrasena.encode()).hexdigest()
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM usuarios WHERE usuario = ? AND contrasena_hash = ?", 
                        (req.usuario, pwd_hash)).fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
        
    token = str(uuid.uuid4())
    user_dict = dict(user)
    ACTIVE_SESSIONS[token] = {
        "usuario": user_dict["usuario"],
        "rol": user_dict["rol"],
        "nombre": user_dict["nombre"],
        "last_activity": time.time()
    }
    return {
        "success": True,
        "token": token,
        "usuario": user_dict["usuario"],
        "rol": user_dict["rol"],
        "nombre": user_dict["nombre"]
    }

@app.post("/api/registros/editar_fecha")
async def editar_fecha(req: EditDateRequest):
    # 1. Validar token
    if req.token not in ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada"
        )
        
    session = ACTIVE_SESSIONS[req.token]
    
    # Validar inactividad (15 min)
    if time.time() - session.get("last_activity", 0) > SESSION_TIMEOUT_SECONDS:
        del ACTIVE_SESSIONS[req.token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión ha expirado por inactividad"
        )
        
    # Actualizar actividad
    session["last_activity"] = time.time()
    
    usuario = session["usuario"]
    rol = session["rol"]
    
    # 2. Validar rol (solo planificador, ingeniero_confiabilidad o admin)
    if rol not in ["planificador", "ingeniero_confiabilidad", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para editar la fecha de reposición"
        )
        
    conn = get_db_connection()
    # 3. Obtener valor anterior
    registro = conn.execute("SELECT tiempo_reposicion FROM registros WHERE id = ?", (req.registro_id,)).fetchone()
    if registro is None:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro no encontrado"
        )
        
    valor_anterior = registro["tiempo_reposicion"]
    
    # 4. Actualizar fecha
    conn.execute("UPDATE registros SET tiempo_reposicion = ? WHERE id = ?", (req.nueva_fecha, req.registro_id))
    
    # 5. Insertar en historial_cambios
    fecha_cambio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO historial_cambios (registro_id, usuario, fecha_cambio, campo_modificado, valor_anterior, valor_nuevo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (req.registro_id, session["nombre"], fecha_cambio, "tiempo_reposicion", valor_anterior, req.nueva_fecha))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "mensaje": "Fecha estimada de reposición actualizada con éxito"}

@app.post("/api/logout")
async def logout(body: dict = Body(...)):
    token = body.get("token")
    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    return {"success": True, "mensaje": "Sesión cerrada correctamente"}

@app.get("/api/registros/{registro_id}/historial")
async def obtener_historial(registro_id: str):
    conn = get_db_connection()
    cambios = conn.execute("""
        SELECT usuario, fecha_cambio, campo_modificado, valor_anterior, valor_nuevo 
        FROM historial_cambios 
        WHERE registro_id = ? 
        ORDER BY id DESC
    """, (registro_id,)).fetchall()
    conn.close()
    
    lista_cambios = [dict(c) for c in cambios]
    return {"historial": lista_cambios}

# Servir archivos estáticos (index.html, styles.css)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

@app.get("/api/destinatarios_disponibles")
async def obtener_destinatarios_disponibles():
    from ldap_utils import get_members_for_role
    try:
        etl_members = get_members_for_role('etl')
        bodega_members = get_members_for_role('bodega')
        return {
            "etl": etl_members,
            "bodega": bodega_members
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener destinatarios de LDAP: {str(e)}"
        )

@app.get("/api/admin/enviar_resumen_semanal")
async def trigger_enviar_resumen_semanal(background_tasks: BackgroundTasks):
    try:
        import subprocess
        def run_script():
            env_py = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python3")
            script_path = os.path.join(os.path.dirname(__file__), "enviar_resumen_semanal.py")
            if not os.path.exists(env_py):
                env_py = "python3"
            subprocess.run([env_py, script_path], check=True)
            
        background_tasks.add_task(run_script)
        return {"success": True, "mensaje": "Ejecución del reporte semanal iniciada en segundo plano."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
