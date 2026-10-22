"""Networks row focus animations (art_tools/network_art.py)."""
import os, sys, subprocess
os.makedirs("refs/net", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/network_art.py", "builder/out/delivered/baseline.json", "refs/net", "HBO"],
                   capture_output=True, text=True)
open("refs/net/log.txt", "w").write(r.stdout + "\n" + r.stderr[-6000:])
