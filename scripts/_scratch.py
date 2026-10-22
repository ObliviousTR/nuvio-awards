"""Genres row sample (art_tools/genre_art.py)."""
import os, sys, subprocess
os.makedirs("refs/gen", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/genre_art.py", "refs/gen", "Action & Adventure"], capture_output=True, text=True)
open("refs/gen/log.txt", "w").write(r.stdout + "\n" + r.stderr[-6000:])
