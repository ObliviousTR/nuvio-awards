"""Spotlight row: rotating cards only (our own rotation, github.com/ObliviousTR/nuvio-awards → spotlight/).

The Headliner, The Visionary, The Powerhouse, The Saga, The Cultural Pulse — Kaptain's five, then his other three
(The Prestige Darling, The Living Legend, Retro Rewind) and our Yerli Yıldız (Turkish stars). The daily charts
moved to Discover and My Simkl to Favourites. Covers carry the subject's name, so folder titles stay hidden.
"""
import sys
from common import load, save, row, spot_src, art_folder, SPOT_ART

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]


def pair(slot, label, movies="Movies", series="Series"):
    return [spot_src(f"{label} · {movies}", "MOVIE", f"spotlight-{slot}-movies"),
            spot_src(f"{label} · {series}", "TV", f"spotlight-{slot}-series")]


CARDS = [  # (folder title, art slot, Kaptain folder whose id we keep)
    ("The Headliner", "headliner", "The Headliner"),
    ("The Visionary", "visionary", "The Visionary"),
    ("The Powerhouse", "powerhouse", "The Powerhouse"),
    ("The Saga", "saga", "The Saga"),
    ("The Cultural Pulse", "pulse", "The Cultural Pulse"),
    ("The Prestige Darling", "prestige", "The Prestige Darling"),
    ("The Living Legend", "legend", "The Living Legend"),
    ("Retro Rewind", "retro", "Retro Rewind"),
    ("Yerli Yıldız", "yerli", None),
]

data = load(SRC)
spotlight = row(data, "Spotlight")
kaptain = {f["title"]: f for f in spotlight["folders"]}
folders, report = [], []
for title, slot, keep in CARDS:
    fid = kaptain[keep]["id"] if keep in kaptain else f"folder-spotlight-{slot}"
    rails = pair(slot, title, "Filmler", "Diziler") if slot == "yerli" else pair(slot, title)
    folders.append(art_folder(fid, title, slot, rails))
    report.append(f"## {title} ({len(rails)} rails)")
    report += [f"   {i+1:2}. {s['title']}  [{s['catalogId']}]" for i, s in enumerate(rails)]
spotlight["folders"] = folders
spotlight["backdropImageUrl"] = f"{SPOT_ART}/headliner/backdrop.jpg"
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} folders -> {OUT}")
