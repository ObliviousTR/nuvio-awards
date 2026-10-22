"""Awards & Festivals samples: look A (winners) and C (trophy shelf)."""
import os, sys, subprocess
os.makedirs("refs/awd", exist_ok=True)
log = ""
for look in ("A", "C"):
    r = subprocess.run([sys.executable, "art_tools/awards_art.py", "refs/awd", look, "oscars", "festivals"], capture_output=True, text=True)
    log += r.stdout + r.stderr[-3000:]
open("refs/awd/log.txt", "w").write(log)
