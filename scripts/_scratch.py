"""Iconic Actors reel samples on the new low-key portraits."""
import os, sys, subprocess
os.makedirs("refs/act", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless"], capture_output=True, text=True).stderr[-500:]
os.environ["ART_REF"] = "4f43d77c464234577ae11b23514937b5c590324b"
r = subprocess.run([sys.executable, "art_tools/actor_art.py", "refs/act", "Al Pacino", "Frances McDormand", "Tom Holland"], capture_output=True, text=True)
log += r.stdout + r.stderr[-3000:]
open("refs/act/log.txt", "w").write(log)
