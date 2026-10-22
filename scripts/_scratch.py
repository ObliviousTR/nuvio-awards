"""Genres sample: popular films' landscape key art, genre-led picks."""
import os, subprocess, sys
os.makedirs("refs/gen", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/genre_art.py", "refs/gen", "Comedy", "Animation", "Action & Adventure"],
                   capture_output=True, text=True)
open("refs/gen/log.txt", "w").write(r.stdout + "\n" + r.stderr[-4000:])
