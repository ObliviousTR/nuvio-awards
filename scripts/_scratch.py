"""All Universes in the Studios rhythm (for nuvio-art art/universes)."""
import os, subprocess, sys
os.makedirs("refs/uniall", exist_ok=True)
r = subprocess.run([sys.executable, "scripts/universe_motion.py", "refs/uniall"], capture_output=True, text=True)
open("refs/uniall/log.txt", "w").write(r.stdout[-6000:] + r.stderr[-6000:])
