"""International Cinema A2 with the docked title block: South Korea, Italy, Nordic Noir."""
import os, sys, subprocess
os.makedirs("refs/intl", exist_ok=True)
env = dict(os.environ, INTL_LOOK="A2")
r = subprocess.run([sys.executable, "art_tools/intl_art.py", "refs/intl", "South Korea", "Italy", "Nordic Noir"], capture_output=True, text=True, env=env)
open("refs/intl/log.txt", "w").write(r.stdout + r.stderr[-3000:])
