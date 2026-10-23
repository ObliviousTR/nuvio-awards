"""Genres without the lap: styles A / B / C on one card (Action & Adventure), with film labels."""
import os, subprocess, sys
log = []
for st in "ABC":
    os.makedirs(f"refs/loop/{st}", exist_ok=True)
    r = subprocess.run([sys.executable, "art_tools/genre_art.py", f"refs/loop/{st}", "Action & Adventure"],
                       capture_output=True, text=True, env=dict(os.environ, GENRE_STYLE=st))
    log.append(f"== {st}\n" + r.stdout[-1500:] + r.stderr[-3000:])
open("refs/loop/log.txt", "w").write("\n".join(log))
