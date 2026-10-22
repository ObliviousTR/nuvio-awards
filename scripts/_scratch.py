"""Studios: render all ten cards."""
import os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "art_tools"); sys.path.insert(0, "scripts")
os.makedirs("refs/studio", exist_ok=True)
names = ["A24", "Blumhouse Productions", "NEON", "Studio Ghibli", "Disney & Pixar Animation", "Searchlight Pictures",
         "Warner Bros. Pictures", "Universal Pictures", "Paramount Pictures", "20th Century Studios"]


def run(n):
    r = subprocess.run([sys.executable, "art_tools/studio_art.py", "refs/studio", n], capture_output=True, text=True)
    return r.stdout + r.stderr[-1500:]


with ThreadPoolExecutor(4) as ex:
    logs = list(ex.map(run, names))
open("refs/studio/log.txt", "w").write("\n".join(logs))
