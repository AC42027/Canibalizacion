from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
import uvicorn
import os
import requests
from bs4 import BeautifulSoup

app = FastAPI(title="Canibalización API")

# Modelo de datos para validación
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

DB_FILE = "canibalizacion.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
async def guardar(registro: Registro):
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
        return {"mensaje": "Registro guardado correctamente", "id": nuevo_registro["id"]}
    except Exception as e:
        print(f"Error al guardar registro: {e}")
        return {"error": f"Error interno: {str(e)}"}

@app.post("/api/normalizar/{registro_id}")
async def normalizar(registro_id: str):
    if not os.path.exists(DB_FILE):
        return {"error": "No hay datos"}
    
    try:
        conn = get_db_connection()
        registro = conn.execute('SELECT normalizado FROM registros WHERE id = ?', (registro_id,)).fetchone()
        
        if registro is None:
            conn.close()
            return {"error": "Registro no encontrado"}
            
        nuevo_estado = 0 if registro["normalizado"] else 1
        
        conn.execute('UPDATE registros SET normalizado = ? WHERE id = ?', (nuevo_estado, registro_id))
        conn.commit()
        conn.close()
        
        return {"mensaje": "Estado actualizado"}
    except Exception as e:
        return {"error": f"Error al actualizar estado: {str(e)}"}

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

# Servir archivos estáticos (index.html, styles.css)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
