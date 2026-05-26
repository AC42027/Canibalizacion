import sqlite3

def crear_base_datos():
    # Conectarse a la base de datos (o crearla si no existe)
    conexion = sqlite3.connect("canibalizacion.db")
    
    # Un cursor nos permite ejecutar comandos SQL
    cursor = conexion.cursor()
    
    # Comando SQL para crear la tabla 'registros'
    # TEXT: para cadenas de texto
    # INTEGER: para números enteros y booleanos (0 = False, 1 = True)
    sql_crear_tabla = """
    CREATE TABLE IF NOT EXISTS registros (
        id TEXT PRIMARY KEY,
        fecha TEXT,
        fecha_registro TEXT,
        maquina_donante TEXT,
        maquina_receptora TEXT,
        repuesto_codigo TEXT,
        repuesto_nombre TEXT,
        repuesto_descripcion TEXT,
        cantidad INTEGER,
        razon TEXT,
        orden_trabajo TEXT,
        retirado_por TEXT,
        cargo_tecnico TEXT,
        correo_tecnico TEXT,
        plan_accion TEXT,
        tiempo_reposicion TEXT,
        responsable_reposicion TEXT,
        cargo_responsable TEXT,
        correo_responsable TEXT,
        personal_bodega TEXT,
        comentarios TEXT,
        codigo_bodega TEXT,
        usuario_registro TEXT,
        normalizado INTEGER DEFAULT 0
    )
    """
    
    # Ejecutamos el comando
    cursor.execute(sql_crear_tabla)
    
    # Guardamos los cambios
    conexion.commit()
    
    # Cerramos la conexión
    conexion.close()
    
    print("Base de datos 'canibalizacion.db' y tabla 'registros' creadas exitosamente.")

if __name__ == "__main__":
    crear_base_datos()
