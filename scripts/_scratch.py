"""Legendary Directors viewfinder samples."""
import os, sys, subprocess
os.makedirs("refs/dir", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless"], capture_output=True, text=True).stderr[-300:]
os.environ["ART_REF"] = "a2f4b1d571ae4ee68d5ae44babbe20829c79d87e"
r = subprocess.run([sys.executable, "art_tools/director_art.py", "refs/dir", "Stanley Kubrick", "Sofia Coppola"], capture_output=True, text=True)
log += r.stdout + r.stderr[-3000:]
open("refs/dir/log.txt", "w").write(log)
