"""Moods sample: Spooky & Creepy, Mind-Bending; our cover next to Kaptain's for comparison."""
import io, os, subprocess, sys, urllib.request
sys.path.insert(0, "art_tools"); sys.path.insert(0, "scripts")
from PIL import Image
os.makedirs("refs/moods", exist_ok=True)
r = subprocess.run([sys.executable, "art_tools/mood_art.py", "refs/moods", "Spooky & Creepy", "Mind-Bending", "Feel-Good"],
                   capture_output=True, text=True)
open("refs/moods/log.txt", "w").write(r.stdout + "\n" + r.stderr[-4000:])
import mood_art as m, genre_art as g
for t in ("Spooky & Creepy", "Mind-Bending", "Feel-Good"):
    try:
        k = m.get(m.KAPTAIN + m.MOODS[t][3]).resize((640, 360))
        o = Image.open(f"refs/moods/{g.slug_of(t)}/cover.jpg").convert("RGB").resize((640, 360))
        c = Image.new("RGB", (1280, 360)); c.paste(k, (0, 0)); c.paste(o, (640, 0))
        c.save(f"refs/moods/cmp_{g.slug_of(t)}.jpg", quality=85)
    except Exception as e:
        print(e)
