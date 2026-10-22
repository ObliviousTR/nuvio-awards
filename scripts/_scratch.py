"""Legendary Directors: all viewfinder reels, 4 at a time."""
import os, sys, subprocess, json
from concurrent.futures import ThreadPoolExecutor
os.makedirs("refs/dir", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless"], capture_output=True, text=True).stderr[-300:]
os.environ["ART_REF"] = "a2f4b1d571ae4ee68d5ae44babbe20829c79d87e"
d = json.load(open("builder/out/delivered/baseline.json"))
names = [f["title"] for c in d if c["title"] == "Legendary Directors" for f in c["folders"]]
def run(n):
    r = subprocess.run([sys.executable, "art_tools/director_art.py", "refs/dir", n], capture_output=True, text=True)
    return r.stdout + (r.stderr[-1500:] if r.returncode else "")
with ThreadPoolExecutor(4) as ex:
    for out in ex.map(run, names):
        log += out
open("refs/dir/log.txt", "w").write(log)
