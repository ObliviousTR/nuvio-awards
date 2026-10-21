import os, sys, subprocess
os.makedirs("refs/um", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/um", "middleearth", "wizarding", "starwars"], capture_output=True, text=True)
open("refs/um/log.txt", "w").write(r.stdout + "\n" + r.stderr[-4000:])
