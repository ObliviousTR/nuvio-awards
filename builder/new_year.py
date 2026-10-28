"""Roll the calendar rails of the delivered collection (run by .github/workflows/new-year.yml), in two steps:
  --part recent    (1 January)  the "right now" windows that start a year back (YEAR-2-01-01, no end: the Trending
                                genre rails) move on, so they keep covering last year and this year
  --part showcase  (1 March)    the "this year" rails move on only once the new year has films to show (Ozzy, 28 Oct
                                2026: empty lists in January are no good): Top of the Year, Best of <year> and its art,
                                Best Documentaries of <year>; the decade folder keeps its Most Popular of the Year
                                <old> rail and gets one for the new year after it
Both the collection file and the Library's genre-true rail definitions (library/genre_rails.json, served by the
daily Genre rails run) are rolled. Folder and catalog ids stay the same, so Ozzy's own settings stay with them.
usage: python3 new_year.py in.json out.json YEAR --part recent|showcase [--rails ../library/genre_rails.json]"""
import argparse, copy, hashlib, json, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("year", type=int)
ap.add_argument("--part", choices=("recent", "showcase"), required=True)
ap.add_argument("--rails")
a = ap.parse_args()
year, old, older = a.year, a.year - 1, a.year - 2
moved, titles = 0, 0


def shift(d):
    return f"{int(d[:4]) + 1}{d[4:]}"


def roll(fl):
    """Move a rail's window if this part covers it; True when it moved."""
    gte, lte = fl.get("releaseDateGte") or "", fl.get("releaseDateLte") or ""
    if a.part == "recent":
        hit = gte == f"{older}-01-01" and not lte
    else:
        hit = gte.startswith(f"{old}-") and lte.startswith(f"{old}-")
    if hit:
        fl["releaseDateGte"] = shift(gte)
        if lte:
            fl["releaseDateLte"] = shift(lte)
        if fl.get("year") == old:
            fl["year"] = year
    return hit


def rename(s, key):
    global titles
    if a.part == "showcase" and str(old) in (s.get(key) or ""):
        s[key] = s[key].replace(str(old), str(year)); titles += 1


data = json.load(open(a.src))
for row in data:
    for f in row.get("folders", []):
        hit = False
        per_year = f"Most Popular of the Year {old}"
        if a.part == "showcase":
            for s in list(f.get("sources", [])):
                if s.get("title") == per_year and not any(x.get("title") == f"Most Popular of the Year {year}" for x in f["sources"]):
                    new = copy.deepcopy(s)
                    new["title"] = f"Most Popular of the Year {year}"
                    new["filters"]["releaseDateGte"] = shift(new["filters"]["releaseDateGte"])
                    new["filters"]["releaseDateLte"] = shift(new["filters"]["releaseDateLte"])
                    f["sources"].insert(f["sources"].index(s) + 1, new)
                    moved += 1
        for s in f.get("sources", []):
            if (s.get("title") or "").startswith("Most Popular of the Year "):
                continue
            if s.get("filters") and roll(s["filters"]):
                rename(s, "title"); moved += 1; hit = True
            elif a.part == "showcase" and s.get("provider") == "addon" and s.get("catalogId", "").startswith("gen-") \
                    and str(old) in (s.get("title") or ""):
                rename(s, "title"); hit = True                    # a Library rail: its window rolls in genre_rails.json
        if hit and a.part == "showcase" and str(old) in f["title"]:
            rename(f, "title")
            for k in ("coverImageUrl", "focusGifUrl", "heroBackdropUrl"):
                u = f.get(k) or ""
                if f"best-of-{old}" in u:
                    base = u.split("?")[0].replace(f"best-of-{old}", f"best-of-{year}")
                    try:
                        f[k] = f"{base}?v={hashlib.md5(urllib.request.urlopen(base, timeout=60).read()).hexdigest()[:8]}"
                    except Exception as e:
                        print(f"keeping {k} of {f['title']}: {e}")
json.dump(data, open(a.dst, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"collection, {a.part} {old} -> {year}: {moved} rails moved, {titles} titles renamed")

if a.rails:
    rails, n = json.load(open(a.rails, encoding="utf-8")), 0
    for r in rails:
        if r.get("filters") and roll(r["filters"]):
            rename(r, "name"); n += 1
    json.dump(rails, open(a.rails, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"genre_rails.json: {n} rails moved")
