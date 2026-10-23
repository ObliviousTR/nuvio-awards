"""International Cinema: flag-map cards with the fly-through hover (Korea, Italy, Türkiye, Nordic)."""
import os, sys, subprocess
os.makedirs("refs/intl", exist_ok=True)
log = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "cairosvg"], capture_output=True, text=True).stderr[-300:]
r = subprocess.run([sys.executable, "art_tools/intl_hover.py", "refs/intl", "South Korea", "Italy", "Türkiye", "Nordic Noir"], capture_output=True, text=True)
open("refs/intl/log.txt", "w").write(log + r.stdout + r.stderr[-3000:])
