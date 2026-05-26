import json
import os

def count_nodes(nodes):
    total = len(nodes)
    for node in nodes:
        if 'hijos' in node:
            total += count_nodes(node['hijos'])
    return total

path = 'arbol_equipos.json'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        total = count_nodes(data['divisiones'])
        print(f"Total nodes: {total}")
        
        # Check for depth
        def max_depth(nodes):
            if not nodes: return 0
            return 1 + max(max_depth(node.get('hijos', [])) for node in nodes)
        print(f"Max depth: {max_depth(data['divisiones'])}")
else:
    print("File not found")
