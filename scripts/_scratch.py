"""Iconic Actors samples (Al Pacino, Frances McDormand) + Tom Holland's portrait card."""
import os, sys, subprocess
os.makedirs("refs/act", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless"], capture_output=True, text=True).stderr[-500:]
r = None

r = subprocess.run([sys.executable, "art_tools/actor_art.py", "refs/act", "Al Pacino", "Frances McDormand"], capture_output=True, text=True)
log += r.stdout + r.stderr[-3000:]
open("refs/act/log.txt", "w").write(log)
