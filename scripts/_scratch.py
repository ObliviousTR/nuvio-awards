"""Universes loop (mi, starwars, middleearth) and Studios without the lap, with film labels (A24, Studio Ghibli)."""
import os, subprocess, sys
os.makedirs("refs/uni", exist_ok=True)
os.makedirs("refs/stu", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/uni", "mi", "starwars", "middleearth"],
                   capture_output=True, text=True)
open("refs/uni/log.txt", "w").write(r.stdout[-3000:] + r.stderr[-4000:])
r = subprocess.run([sys.executable, "art_tools/studio_art.py", "refs/stu", "A24", "Studio Ghibli"], capture_output=True, text=True)
open("refs/stu/log.txt", "w").write(r.stdout[-3000:] + r.stderr[-4000:])
