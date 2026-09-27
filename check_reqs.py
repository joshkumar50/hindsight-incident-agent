import os
import glob

dirs_to_check = glob.glob('platform/*') + glob.glob('apps/*')
for d in dirs_to_check:
    if os.path.isdir(d):
        req_file = os.path.join(d, 'requirements.txt')
        if not os.path.exists(req_file) or os.path.getsize(req_file) == 0:
            print(f"Empty or missing: {req_file}")
            
            # read main.py to figure out what it needs
            main_py = os.path.join(d, 'main.py')
            imports = set()
            if os.path.exists(main_py):
                with open(main_py, 'r') as f:
                    for line in f:
                        if line.startswith('import '):
                            imports.add(line.split()[1].split('.')[0])
                        elif line.startswith('from '):
                            imports.add(line.split()[1].split('.')[0])
            
            # map standard stdlib away
            stdlib = {'os', 'sys', 'time', 'json', 'logging', 'asyncio', 'typing', 'datetime'}
            third_party = imports - stdlib - {'pkg'}
            
            if not third_party:
                third_party = {'fastapi', 'uvicorn'}
            
            # fallback minimums
            if 'fastapi' not in third_party:
                third_party.add('fastapi')
            if 'uvicorn' not in third_party:
                third_party.add('uvicorn')
                
            with open(req_file, 'w') as f:
                for req in sorted(list(third_party)):
                    f.write(req + '\n')
            print(f"  -> Added {third_party}")
