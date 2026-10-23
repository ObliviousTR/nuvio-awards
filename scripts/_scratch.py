"""By Decade samples: the 1980s (VHS) and the 1950s (black and white)."""
import os, sys, subprocess
os.makedirs("refs/dec", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/decade_art.py", "refs/dec", "1980s", "1950s & Golden Age"], capture_output=True, text=True)
open("refs/dec/log.txt", "w").write(r.stdout + r.stderr[-4000:])
