"""Kids & Family sample: Saturday Morning."""
import os, sys, subprocess
os.makedirs("refs/kids", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/kids_art.py", "refs/kids", "Saturday Morning & Classic Cartoons"], capture_output=True, text=True)
open("refs/kids/log.txt", "w").write(r.stdout + r.stderr[-3000:])
