#!/usr/bin/env python3
"""
Thin wrapper for scripts/estandarizar_imagenes_qa.py
"""
import sys
from pathlib import Path

root_script = Path(__file__).resolve().parents[2] / "scripts" / "estandarizar_imagenes_qa.py"
if root_script.is_file():
    sys.path.insert(0, str(root_script.parent))
    import subprocess
    sys.exit(subprocess.call([sys.executable, str(root_script)] + sys.argv[1:]))
else:
    print(f"Error: No se encontró {root_script}", file=sys.stderr)
    sys.exit(1)
