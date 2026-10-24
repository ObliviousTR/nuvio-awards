"""Universes cover-first trial, round 2: Wizarding World and Star Wars -> refs/uident2."""
import os, subprocess, sys
os.makedirs("refs/uident2", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_ident3.py", "refs/uident2", "starwars"], capture_output=True, text=True)
open("refs/uident2/log.txt", "w").write(r.stdout + "\n" + r.stderr[-6000:])
print(r.stdout, r.stderr[-3000:])
