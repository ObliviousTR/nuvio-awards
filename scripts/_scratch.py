import os, sys, subprocess
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/um"], capture_output=True, text=True)
os.makedirs("refs/um", exist_ok=True)
open("refs/um/log.txt", "w").write(r.stdout + "\n" + r.stderr[-4000:])
