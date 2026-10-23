"""Based On drafts: all five cards, real pictures."""
import os, sys, subprocess
os.makedirs("refs/bo", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless"], capture_output=True, text=True).stderr[-300:]
r = subprocess.run([sys.executable, "art_tools/basedon_art.py", "refs/bo"], capture_output=True, text=True)
log += r.stdout + r.stderr[-4000:]
open("refs/bo/log.txt", "w").write(log)
