"""Universes ident trial: MCU, DC, Wizarding World, Middle-earth samples -> refs/uident."""
import os, subprocess, sys
os.makedirs("refs/uident", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_ident.py", "refs/uident"], capture_output=True, text=True)
open("refs/uident/log.txt", "w").write(r.stdout + "\n" + r.stderr[-6000:])
print(r.stdout, r.stderr[-3000:])
