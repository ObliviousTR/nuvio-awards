"""Film Collections: re-render Crime, Drama, Thriller after the re-shuffle."""
import os, sys, subprocess
os.makedirs("refs/fc", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/collection_art.py", "refs/fc", "Crime Collections", "Drama Collections",
                    "Thriller Collections"], capture_output=True, text=True)
open("refs/fc/log.txt", "w").write(r.stdout + r.stderr[-3000:])
