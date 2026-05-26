import csv

input_file = 'arbol_equipos_plano.csv'
output_file = 'arbol_equipos_plano_fixed.csv'

to_remove = "Automated Storage and Retrieval System"
target_id = "L504-ASRS(M)"

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
adjusting = False
adjustment_level = 0

for line in lines:
    parts = line.strip().split(';')
    if len(parts) < 3:
        new_lines.append(line)
        continue
    
    level = int(parts[0])
    node_id = parts[1]
    name = parts[2]
    
    if name == to_remove or node_id == target_id:
        # Skip this line and start adjusting children
        adjusting = True
        adjustment_level = level
        continue
    
    if adjusting:
        # If we encounter a node with level <= adjustment_level, it's a sibling or parent of the removed node's parent section
        # So we stop adjusting.
        if level <= adjustment_level:
            adjusting = False
        else:
            # Shift level up
            parts[0] = str(level - 1)
            line = ";".join(parts) + "\n"
    
    new_lines.append(line)

with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Fixed CSV saved to {output_file}")
