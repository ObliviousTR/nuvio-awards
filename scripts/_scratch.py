"""Documentaries samples: True Crime (evidence board) and History (archive colourised)."""
import os, sys, subprocess
os.makedirs("refs/docs", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/docs_art.py", "refs/docs"], capture_output=True, text=True)
open("refs/docs/log.txt", "w").write(r.stdout + r.stderr[-3000:])
