"""Final render of every universe's art (007 waits for the gun-barrel video)."""
import os, sys, subprocess
os.makedirs("refs/um", exist_ok=True)
ids = ["spiderman", "middleearth", "wizarding", "starwars", "johnwick", "mcu", "dc", "batman", "xmen", "dune",
       "startrek", "mi", "jurassic", "transformers", "matrix", "terminator", "conjuring", "fast", "madmax", "indiana",
       "alienpredator", "godzillakong", "apes"]
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/um", *ids], capture_output=True, text=True)
open("refs/um/log.txt", "w").write(r.stdout + "\n" + r.stderr[-6000:])
