"""Reality TV 'on air' samples: Cooking (kitchen countdown) and Makeover (before / after slider)."""
import os, sys, subprocess
os.makedirs("refs/rt", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/reality_art.py", "refs/rt"], capture_output=True, text=True)
open("refs/rt/log.txt", "w").write(r.stdout + r.stderr[-3000:])
