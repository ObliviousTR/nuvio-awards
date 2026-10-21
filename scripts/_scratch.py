"""Re-render a few folder covers."""
import os, sys, subprocess
os.makedirs("refs/fa", exist_ok=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rembg[cpu]", "onnxruntime"], capture_output=True)
ids = ["anime-film-collections", "fuji-tv-mbs", "frances-mcdormand", "edward-norton", "philip-seymour-hoffman",
       "bryan-cranston", "tilda-swinton", "toni-collette", "ethan-hawke", "sam-rockwell", "simon-pegg",
       "robert-pattinson", "sofia-coppola"]
r = subprocess.run([sys.executable, "art_tools/folder_art.py", "refs/fa", *ids], capture_output=True, text=True)
open("refs/fa/log.txt", "w").write(r.stdout + "\n" + r.stderr[-3000:])
