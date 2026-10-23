"""Universes in the Studios rhythm (mcu, starwars, mi) + the Bond films' key art for the 007 card."""
import os, subprocess, sys, urllib.request
sys.path.insert(0, "art_tools")
os.makedirs("refs/uni2", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/uni2", "mcu", "starwars", "mi"], capture_output=True, text=True)
open("refs/uni2/log.txt", "w").write(r.stdout[-3000:] + r.stderr[-5000:])
os.makedirs("refs/bondfilms", exist_ok=True)
import universe_keyart as U, genre_art as g
log = []
for i, (p, name, year) in enumerate(U.entries("bond")):
    im = g.load_img(p)
    im.save(f"refs/bondfilms/{i}.jpg", quality=92)
    log.append(f"{i}\t{name}\t{year}\t{p}")
open("refs/bondfilms/list.txt", "w").write("\n".join(log))
