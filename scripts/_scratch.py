import os, sys, subprocess
os.makedirs("refs/um", exist_ok=True)
ids = ["xmen", "indiana", "alienpredator", "apes"]
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/um", *ids], capture_output=True, text=True)
open("refs/um/log.txt", "w").write(r.stdout + "\n" + r.stderr[-6000:])
