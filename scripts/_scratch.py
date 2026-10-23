"""International Cinema samples: South Korea and Türkiye."""
import os, sys, subprocess
os.makedirs("refs/intl", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/intl_art.py", "refs/intl", "South Korea", "Türkiye"], capture_output=True, text=True)
open("refs/intl/log.txt", "w").write(r.stdout + r.stderr[-4000:])
