"""Studios row: the 10 agreed studios (master list order), Kaptain's rail line-up per studio.

Kaptain: Recent / Popular / Top Rated Movies, plus the same three for series where the studio makes TV.
Native TMDB discover by production company (a studio's old and new company ids together: Fox → 20th Century
Studios, Fox Searchlight → Searchlight). No animation except at Pixar and Studio Ghibli (animation studios by
definition). No language filter: a studio rail shows what the studio made.
usage: python3 build_studios.py in.json out.json report.txt  (importable: STUDIOS)
"""
import sys
from common import src, load, save, row, placeholder_folder, POP, TOP, NEW

# (folder title, Kaptain folder whose art we keep, company ids, animation studio?, series?, vote floor: popular, top)
STUDIOS = [
    ("A24", "A24", "41077", False, True, 50, 300),
    ("NEON", None, "90733", False, False, 20, 100),
    ("Blumhouse Productions", "Blumhouse Productions", "3172", False, True, 50, 300),
    ("Warner Bros. Pictures", "Warner Bros. Entertainment", "174", False, False, 200, 2000),
    ("Universal Pictures", "Universal Pictures", "33", False, False, 200, 2000),
    ("Paramount Pictures", "Paramount Pictures", "4", False, False, 200, 2000),
    ("20th Century Studios", "20th Century Studios", "127928|25", False, False, 200, 2000),
    ("Searchlight Pictures", "Searchlight Pictures", "127929|43", False, False, 50, 500),
    ("Pixar", "Pixar", "3", True, False, 50, 500),
    ("Studio Ghibli", "Studio Ghibli", "10342", True, False, 20, 300),
]
NOISE_TV = "10763|10764|10766|10767"


def rails(title, comp, toon, series, vc_pop, vc_top):
    m = dict(withCompanies=comp, withoutGenres=None if toon else "16")
    t = dict(withCompanies=comp, withoutGenres=NOISE_TV if toon else "16|" + NOISE_TV)
    out = [
        src("Recent Movies", "MOVIE", NEW["MOVIE"], voteCountGte=5, **m),
        src("Popular Movies", "MOVIE", POP, voteCountGte=vc_pop, **m),
        src("Top Rated Movies", "MOVIE", TOP, voteCountGte=vc_top, **m),
    ]
    if series:
        out += [
            src("Recent Series", "TV", NEW["TV"], voteCountGte=2, **t),
            src("Popular Series", "TV", POP, voteCountGte=10, **t),
            src("Top Rated Series", "TV", TOP, voteCountGte=50, **t),
        ]
    return out


if __name__ == "__main__":
    SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
    data = load(SRC)
    studios = row(data, "Studios")
    kaptain = {f["title"]: f for f in studios["folders"]}
    folders, report = [], []
    for title, art, comp, toon, series, vc_pop, vc_top in STUDIOS:
        if art in kaptain:
            f = {k: v for k, v in kaptain[art].items() if k not in ("sources", "catalogSources")}
            f["title"] = title
        else:
            f = placeholder_folder(title, "🎬")
        f["sources"], f["catalogSources"] = rails(title, comp, toon, series, vc_pop, vc_top), []
        folders.append(f)
        report.append(f"## {title} ({len(f['sources'])} rails) companies {comp}")
        report += [f"   {i+1:2}. {s['title']}" for i, s in enumerate(f["sources"])]
    studios["folders"] = folders
    save(data, OUT)
    open(REPORT, "w").write("\n".join(report) + "\n")
    print(f"ok: {len(folders)} folders -> {OUT}")
