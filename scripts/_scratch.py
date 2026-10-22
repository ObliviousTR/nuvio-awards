"""Universes: re-render every universe with its films' key art behind the mark (4 at a time)."""
import os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor
os.makedirs("refs/um", exist_ok=True)
ids = ["matrix", "jurassic", "dc", "batman", "spiderman", "middleearth", "wizarding", "starwars", "johnwick", "mcu",
       "dune", "startrek", "mi", "transformers", "terminator", "conjuring", "fast", "madmax", "indiana",
       "alienpredator", "godzillakong", "apes", "xmen"]


def run(u):
    r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/um", u], capture_output=True, text=True)
    return r.stdout + r.stderr[-1500:]


with ThreadPoolExecutor(4) as ex:
    logs = list(ex.map(run, ids))
open("refs/um/log.txt", "w").write("\n".join(logs))
