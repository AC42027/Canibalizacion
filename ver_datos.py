import sqlite3

def ver_registros():
    # 1. Conectarnos a la base de datos
    conexion = sqlite3.connect("canibalizacion.db")
    
    # 2. Configurar para que los resultados se comporten como diccionarios
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    
    # 3. Ejecutar comando SQL para seleccionar todo (*) de la tabla registros
    print("Ejecutando consulta SQL: SELECT * FROM registros\n")
    cursor.execute("SELECT * FROM registros")
    
    # 4. Obtener todos los resultados
    registros = cursor.fetchall()
    
    # 5. Mostrar los resultados
    if not registros:
        print("La base de datos está vacía. No hay registros.")
    else:
        print(f"--- Se encontraron {len(registros)} registros ---\n")
        for r in registros:
            print(f"ID: {r['id']}")
            print(f"Fecha: {r['fecha']}")
            print(f"Máquina Donante: {r['maquina_donante']}")
            print(f"Repuesto: {r['repuesto_nombre']} ({r['repuesto_codigo']})")
            print(f"Responsable: {r['retirado_por']}")
            # Convertimos el 0/1 a texto legible para el estado
            estado = "Normalizado" if r['normalizado'] == 1 else "Pendiente"
            print(f"Estado: {estado}")
            print("-" * 40)
            
    # 6. Cerrar la conexión
    conexion.close()

if __name__ == "__main__":
    ver_registros()
