"""Copy only reviewable project artifacts to a separately cloned repository."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
target=root/'tmp/publish'
if not (target/'.git').is_dir():
    raise SystemExit('Clone the destination repository into tmp/publish first.')
folders=['src','tests','configs','sql','docs','notebooks','scripts','.github','outputs']
files=['README.md','.gitignore','.dockerignore','pyproject.toml','requirements.lock','Dockerfile','compose.yaml']
for name in folders:
    for p in (root/name).rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ['__pycache__','private','.ipynb_checkpoints']) and not any(x.endswith('.egg-info') for x in p.parts):
            dst=target/p.relative_to(root)
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,dst)
for name in files:
    shutil.copy2(root/name,target/name)
print('Copied source and shareable outputs; excluded raw data, warehouse and private records.')
