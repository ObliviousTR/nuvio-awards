"""Universes: the loop that starts and ends on the cover, with film labels (samples: mi, starwars, middleearth)."""
import os, subprocess, sys
os.makedirs("refs/uni", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/uni", "mi", "starwars", "middleearth"],
                   capture_output=True, text=True)
open("refs/uni/log.txt", "w").write(r.stdout[-3000:] + r.stderr[-4000:])
