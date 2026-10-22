"""Iconic Actors: all reels (64 actors), 4 at a time."""
import os, sys, subprocess, json
from concurrent.futures import ThreadPoolExecutor
os.makedirs("refs/act", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless"], capture_output=True, text=True).stderr[-300:]
os.environ["ART_REF"] = "4f43d77c464234577ae11b23514937b5c590324b"
d = json.load(open("builder/out/delivered/baseline.json"))
names = ["Robert De Niro", "Jack Nicholson", "Anthony Hopkins", "Steve Carell"]
def run(n):
    r = subprocess.run([sys.executable, "art_tools/actor_art.py", "refs/act", n], capture_output=True, text=True)
    return r.stdout + (r.stderr[-1500:] if r.returncode else "")
with ThreadPoolExecutor(4) as ex:
    for out in ex.map(run, names):
        log += out
open("refs/act/log.txt", "w").write(log)
