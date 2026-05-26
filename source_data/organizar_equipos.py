import json
import os

def parse_tree_file(filepath):
    equipos = []
    stack = [] # Almacenará tuplas (nodo, profundidad_tabs)
    
    if not os.path.exists(filepath):
        print(f"Error: No se encuentra {filepath}")
        return []

    try:
        with open(filepath, 'r', encoding='utf-16') as f:
            for line in f:
                # Contar tabulaciones iniciales para determinar profundidad
                depth = len(line) - len(line.lstrip('\t'))
                clean_line = line.strip()
                
                # Ignorar líneas irrelevantes
                if not clean_line or clean_line.startswith("Ubicación") or clean_line.startswith("Denominación") or clean_line.startswith("Válido"):
                    continue
                
                # 1. Filtro de Redundancia: Ignorar el nodo intermedio de ASRS
                if "Automated Storage and Retrieval System" in clean_line:
                    continue

                # Separar ID de Nombre
                parts = [p.strip() for p in clean_line.split('\t') if p.strip()]
                if len(parts) < 2:
                    continue
                
                node_id = parts[0]
                node_name = " ".join(parts[1:])
                
                node = {
                    "id": node_id,
                    "nombre": node_name,
                    "hijos": []
                }
                
                # 2. Lógica de Jerarquía Robusta:
                # Si el nuevo nodo tiene una profundidad menor o igual a los anteriores, 
                # sacamos elementos del stack hasta encontrar a su padre real.
                while stack and stack[-1][1] >= depth:
                    stack.pop()
                
                if not stack:
                    equipos.append(node)
                else:
                    # El padre es el que queda en el tope del stack
                    stack[-1][0]["hijos"].append(node)
                
                # Agregamos el nodo actual al stack para que sea padre de los siguientes
                stack.append((node, depth))
                
    except Exception as e:
        print(f"Error procesando {filepath}: {e}")
        
    return equipos

def main():
    print("Iniciando procesamiento de árboles de equipos...")
    
    diva = parse_tree_file("ÁrbolEquipos_DIVA.XLS")
    divb = parse_tree_file("ArbolDeEquipoDIVB.xls")
    divc = parse_tree_file("ArbolEquipos_Facility.XLS")
    divu = parse_tree_file("ArbolEquipos_Utilities.XLS")
    
    # Combinar ambos en una raíz única
    arbol_completo = {
        "nombre": "Planta L504",
        "divisiones": diva + divb + divc + divu
    }
    
    # El archivo JSON principal debe quedar en la raíz para que la App lo lea
    output_file = "../arbol_equipos.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(arbol_completo, f, indent=4, ensure_ascii=False)
        
    print(f"¡Éxito! Árbol principal actualizado en: {output_file}")
    
    # También generamos una versión plana (CSV) en la misma carpeta source_data por si se necesita
    with open("arbol_equipos_plano.csv", "w", encoding="utf-8") as f:
        f.write("Nivel;ID;Denominacion\n")
        def escribir_plano(nodos, nivel):
            for n in nodos:
                f.write(f"{nivel};{n['id']};{n['nombre']}\n")
                escribir_plano(n['hijos'], nivel + 1)
        
        escribir_plano(diva + divb + divc + divu, 0)
    print("Versión plana (CSV) generada en esta carpeta para referencia.")

if __name__ == "__main__":
    main()
