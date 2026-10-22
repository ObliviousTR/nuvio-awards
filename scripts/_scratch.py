"""Genres sample + hero/logo samples."""
import os, sys, subprocess
os.makedirs("refs/gen", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/genre_art.py", "refs/gen", "Action & Adventure"], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, "art_tools/hero_logo.py", "builder/out/delivered/baseline.json", "refs/gen/hl",
                     "Anime/Seinen, Dark & Psychological=wall", "Anime/Seinen, Dark & Psychological=row:SEINEN|DARK & PSYCHOLOGICAL",
                     "Awards & Festivals/The Emmy Awards=wall", "Iconic Actors/Frances McDormand=script:Frances McDormand"],
                    capture_output=True, text=True)
open("refs/gen/log.txt", "w").write(r.stdout + r2.stdout + "\n" + r.stderr[-3000:] + r2.stderr[-3000:])
