"""Samples: Universes with the parting pictures (Star Wars, Matrix), Film Collections deal (Action)."""
import os, sys, subprocess
os.makedirs("refs/s", exist_ok=True)
log = ""
for u in ("starwars", "matrix"):
    r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/s", u], capture_output=True, text=True)
    log += r.stdout + r.stderr[-1500:]
r = subprocess.run([sys.executable, "art_tools/collection_art.py", "refs/s", "Action Collections"], capture_output=True, text=True)
log += r.stdout + r.stderr[-3000:]
open("refs/s/log.txt", "w").write(log)
