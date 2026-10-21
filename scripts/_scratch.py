"""Render the remaining folder covers (art_tools/folder_art.py)."""
import os, sys, subprocess
os.makedirs("refs/fa", exist_ok=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rembg[cpu]", "onnxruntime"], capture_output=True)
r = subprocess.run([sys.executable, "art_tools/folder_art.py", "refs/fa"], capture_output=True, text=True)
open("refs/fa/log.txt", "w").write(r.stdout + "\n" + r.stderr[-8000:])
