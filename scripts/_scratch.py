"""International Cinema: second take on A (A2) and the flight (B)."""
import os, sys, subprocess
os.makedirs("refs/intl", exist_ok=True)
log = ""
env = dict(os.environ, INTL_LOOK="A2")
r = subprocess.run([sys.executable, "art_tools/intl_art.py", "refs/intl", "South Korea", "Italy"], capture_output=True, text=True, env=env)
log += r.stdout + r.stderr[-3000:]
r = subprocess.run([sys.executable, "art_tools/intl_flight.py", "refs/intl", "South Korea", "Italy"], capture_output=True, text=True)
log += r.stdout + r.stderr[-3000:]
open("refs/intl/log.txt", "w").write(log)
