"""Reality TV row: the 6 agreed folders (reality_spec.py), Kaptain's folder art, native TMDB rails.

Keyword names were resolved to TMDB ids by the resolver run (reality_keywords.json). Default rail: Reality genre,
English, from the US / UK / Australia, no animation, no wrestling (TMDB files WWE under Reality). Korean rails are
the agreed exception. This row is not touched by apply_language_policy / apply_no_animation.
"""
import json, os, sys
from common import src, load, save, row, placeholder_folder, POP, TOP, NEW
from reality_spec import FOLDERS, ANGLO, EXCLUDE

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
KW = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "reality_keywords.json")))
SORT = {"pop": POP, "top": TOP, "new": NEW["TV"], "votes": "vote_count.desc"}
NO_KW = "|".join(i for n in EXCLUDE for i in KW[n].split("|") if i)


def rail(title, r):
    genres = r.get("genres", "10764")
    keep = set((genres or "").split("|"))
    without = "|".join(g for g in ("16", "10763", "10766", "10767") if g not in keep)
    f = dict(withGenres=genres, withoutGenres=without, withoutKeywords=NO_KW,
             withOriginCountry=r.get("country", ANGLO), withOriginalLanguage=r.get("lang", "en"),
             voteCountGte=r.get("vc") or None)
    if r.get("kw"):
        ids = [i for n in r["kw"] for i in KW[n].split("|") if i]
        assert ids, f"no keyword ids for {title}"
        f["withKeywords"] = "|".join(dict.fromkeys(ids))
    if r.get("net"):
        f["withNetworks"] = r["net"]
    if r.get("since"):
        f["releaseDateGte"] = f"{r['since']}-01-01"
    if r.get("until"):
        f["releaseDateLte"] = f"{r['until']}-12-31"
    return src(title, "TV", SORT[r["sort"]], **f)


data = load(SRC)
reality = row(data, "Reality TV")
kaptain = {f["title"]: f for f in reality["folders"]}
folders, report = [], []
for title, art, rails in FOLDERS:
    if art in kaptain:
        f = {k: v for k, v in kaptain[art].items() if k not in ("sources", "catalogSources")}
        f["title"] = title
    else:
        f = placeholder_folder(title, "📺")
    f["sources"], f["catalogSources"] = [rail(t, r) for t, r in rails], []
    folders.append(f)
    report.append(f"## {title} ({len(rails)} rails)")
    report += [f"   {i+1:2}. {t}" for i, (t, _) in enumerate(rails)]
reality["folders"] = folders
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} folders -> {OUT}")
