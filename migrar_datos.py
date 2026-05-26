import sqlite3
import json
import os

def migrar_datos():
    data_file = "data.json"
    
    if not os.path.exists(data_file):
        print(f"No se encontró {data_file}. No hay datos que migrar.")
        return

    # Leer datos del archivo JSON
    with open(data_file, "r", encoding="utf-8") as f:
        try:
            datos_json = json.load(f)
            registros = datos_json.get("canibalizaciones", [])
        except json.JSONDecodeError:
            print("El archivo data.json está vacío o no tiene formato JSON válido.")
            return

    if not registros:
        print("No hay registros en data.json para migrar.")
        return

    # Conectarse a la base de datos
    conexion = sqlite3.connect("canibalizacion.db")
    cursor = conexion.cursor()
    
    registros_migrados = 0
    
    # Preparar el comando SQL de inserción
    sql_insertar = """
    INSERT OR REPLACE INTO registros (
        id, fecha, fecha_registro, maquina_donante, maquina_receptora, 
        repuesto_codigo, repuesto_nombre, repuesto_descripcion, cantidad, razon, 
        orden_trabajo, retirado_por, cargo_tecnico, correo_tecnico, plan_accion, 
        tiempo_reposicion, responsable_reposicion, cargo_responsable, correo_responsable, 
        personal_bodega, comentarios, codigo_bodega, usuario_registro, normalizado
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    """
    
    for r in registros:
        # Extraer valores manejando campos faltantes o nulos
        valores = (
            str(r.get("id")),
            r.get("fecha", ""),
            r.get("fecha_registro", ""),
            r.get("maquina_donante", ""),
            r.get("maquina_receptora", ""),
            r.get("repuesto_codigo", ""),
            r.get("repuesto_nombre", ""),
            r.get("repuesto_descripcion", ""),
            int(r.get("cantidad", 0)),
            r.get("razon", ""),
            r.get("orden_trabajo", ""),
            r.get("retirado_por", ""),
            r.get("cargo_tecnico", ""),
            r.get("correo_tecnico", ""),
            r.get("plan_accion", ""),
            r.get("tiempo_reposicion", ""),
            r.get("responsable_reposicion", ""),
            r.get("cargo_responsable", ""),
            r.get("correo_responsable", ""),
            r.get("personal_bodega", ""),
            r.get("comentarios", ""),
            r.get("codigo_bodega", ""),
            r.get("usuario_registro", ""),
            1 if r.get("normalizado", False) else 0  # SQLite no tiene tipo boolean, usamos 0 o 1
        )
        
        try:
            cursor.execute(sql_insertar, valores)
            registros_migrados += 1
        except Exception as e:
            print(f"Error al insertar el registro {r.get('id')}: {e}")

    # Guardar cambios y cerrar conexión
    conexion.commit()
    conexion.close()
    
    print(f"Se migraron exitosamente {registros_migrados} registros de {data_file} a canibalizacion.db.")

if __name__ == "__main__":
    migrar_datos()
