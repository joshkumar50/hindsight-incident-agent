import os
import ast
from pathlib import Path

def get_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except Exception:
            return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                imports.add(node.module.split('.')[0])
    return imports

std_libs = set(['os', 'sys', 'time', 'math', 'json', 'random', 'asyncio', 'logging', 'typing', 're', 'datetime', 'pathlib'])

for base in ['platform', 'apps']:
    base_dir = Path(base)
    if not base_dir.exists():
        continue
    for svc in base_dir.iterdir():
        if not svc.is_dir():
            continue
        req_path = svc / 'requirements.txt'
        main_path = svc / 'main.py'
        
        req_exists = req_path.exists()
        req_empty = True
        req_deps = set()
        if req_exists:
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    req_empty = False
                    for line in content.splitlines():
                        if line and not line.startswith('#'):
                            dep = line.split('=')[0].split('>')[0].split('<')[0].strip()
                            req_deps.add(dep.lower())
                            
        imported = set()
        if main_path.exists():
            imported = get_imports(main_path)
            
        third_party = set(i for i in imported if i not in std_libs and i not in ['pkg', 'shared'])
        
        print(f"Service: {svc}")
        print(f"  Requirements exists: {req_exists}")
        print(f"  Requirements empty: {req_empty}")
        print(f"  Actual third-party imports: {third_party}")
        print(f"  Listed in requirements: {req_deps}")
        print()
