"""Create a reviewable source archive, excluding runtime data, dependencies and secrets."""
import os
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
target = root.parent / 'outputs' / 'VibeSync-source.zip'
target.parent.mkdir(exist_ok=True)
excluded = {'.git', '.deps', '.venv', 'node_modules', '.next', '__pycache__', '.pytest_cache', '.terraform'}
count = 0
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for folder, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in excluded)
        for name in sorted(files):
            path = Path(folder) / name
            if name.startswith('.env') and name != '.env.example':
                continue
            if any(marker in name for marker in ('.db', '.sqlite', '.tfstate', '.tfplan')) or name.endswith(('.pyc', '.tsbuildinfo', '.log', '.tfvars')):
                continue
            archive.write(path, path.relative_to(root))
            count += 1
print(f'Packaged {count} reviewed source files: {target}')
