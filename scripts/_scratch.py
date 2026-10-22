"""Studios samples: Paramount (pilot) and Disney & Pixar (our own ident)."""
import os, sys, subprocess
os.makedirs("refs/studio", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/studio_art.py", "refs/studio"], capture_output=True, text=True)
open("refs/studio/log.txt", "w").write(r.stdout + r.stderr[-3000:])
