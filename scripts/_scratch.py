"""International Cinema audit: how much notable content each folder / rail really has (TMDB discover)."""
import json, os, sys
sys.path.insert(0, "scripts")
from spotlight import tmdb
os.makedirs("refs/intl", exist_ok=True)
d = json.load(open("builder/out/delivered/baseline.json"))
row = [c for c in d if c["title"] == "International Cinema"][0]
MAP = {"withOriginalLanguage": "with_original_language", "withOriginCountry": "with_origin_country", "withoutGenres": "without_genres",
       "withGenres": "with_genres"}
def count(src, vc, va):
    f = src.get("filters") or {}
    kind = "tv" if src.get("mediaType") == "TV" else "movie"
    q = {MAP[k]: v for k, v in f.items() if k in MAP and v}
    q.update({"vote_count.gte": vc, "vote_average.gte": va, "sort_by": "vote_count.desc"})
    r = tmdb(f"/discover/{kind}", **q) or {}
    return r.get("total_results", 0), [(x.get("title") or x.get("name"), (x.get("release_date") or x.get("first_air_date") or "")[:4], x.get("vote_average"), x.get("vote_count")) for x in r.get("results", [])[:12]]
out = []
for fo in row["folders"]:
    seen = set()
    for s in fo.get("sources") or []:
        f = s.get("filters") or {}
        key = (s.get("mediaType"), f.get("withOriginalLanguage"), f.get("withOriginCountry"), f.get("withGenres"))
        if key in seen:
            continue
        seen.add(key)
        n1, top = count(s, 300, 6.8)
        n2, _ = count(s, 100, 6.5)
        out.append({"folder": fo["title"], "rail": s["title"], "media": s.get("mediaType"), "notable": n1, "decent": n2, "top": top})
# the regions asked about, alone
extra = {"Russian & Soviet": {"withOriginalLanguage": "ru"}, "Arab": {"withOriginalLanguage": "ar"}, "Iranian": {"withOriginalLanguage": "fa"},
         "Israeli": {"withOriginalLanguage": "he"}, "Ukrainian": {"withOriginalLanguage": "uk"}, "African (sw|yo|ha|zu|am|af)": {"withOriginalLanguage": "sw|yo|ha|zu|am|af"}}
for name, f in extra.items():
    for media in ("MOVIE", "TV"):
        s = {"filters": dict(f, withoutGenres="16|99"), "mediaType": media}
        n1, top = count(s, 300, 6.8)
        n2, _ = count(s, 100, 6.5)
        out.append({"folder": "(region) " + name, "rail": name, "media": media, "notable": n1, "decent": n2, "top": top})
json.dump(out, open("refs/intl/audit.json", "w"), ensure_ascii=False, indent=1)
