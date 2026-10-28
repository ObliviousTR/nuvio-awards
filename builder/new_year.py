"""Roll the delivered collection into a new year (run by .github/workflows/new-year.yml on 1 January).
Nuvio's TMDB rails keep their dates in the file, so every rail tied to the calendar is moved one year on:
  - "this year" windows (YEAR-1-01-01 .. YEAR-1-12-31: Top of the Year, Best of <year>, Best Documentaries of <year>)
  - "right now" windows that start a year back (YEAR-2-01-01, no end: the Trending genre rails)
  - the decade folder keeps its "Most Popular of the Year <old>" rail and gets one for the new year after it
  - the year in their folder and rail titles, and the "Best of <year>" art (art_tools/decade_art.py renders the new one
    on the 1st of the month, before this runs)
Folder ids stay the same, so Ozzy's own settings in Nuvio stay with them.
usage: python3 new_year.py in.json out.json YEAR"""
import copy, hashlib, json, re, sys, urllib.request

src, dst, year = sys.argv[1], sys.argv[2], int(sys.argv[3])
old, older = year - 1, year - 2
data = json.load(open(src))
moved, titles = 0, 0


def shift(d):
    return f"{int(d[:4]) + 1}{d[4:]}"


for row in data:
    for f in row.get("folders", []):
        hit = False
        per_year = f"Most Popular of the Year {old}"
        for i, s in enumerate(list(f.get("sources", []))):
            if s.get("title") == per_year and not any(x.get("title") == per_year.replace(str(old), str(year)) for x in f["sources"]):
                new = copy.deepcopy(s)
                new["title"] = per_year.replace(str(old), str(year))
                new["filters"]["releaseDateGte"] = shift(new["filters"]["releaseDateGte"])
                new["filters"]["releaseDateLte"] = shift(new["filters"]["releaseDateLte"])
                f["sources"].insert(f["sources"].index(s) + 1, new)
                moved += 1
                continue
        for s in f.get("sources", []):
            if (s.get("title") or "").startswith("Most Popular of the Year "):
                continue
            fl = s.get("filters") or {}
            gte, lte = fl.get("releaseDateGte") or "", fl.get("releaseDateLte") or ""
            this_year = gte.startswith(f"{old}-") and (not lte or lte.startswith(f"{old}-"))
            right_now = gte == f"{older}-01-01" and not lte
            if this_year or right_now:
                fl["releaseDateGte"] = shift(gte)
                if lte:
                    fl["releaseDateLte"] = shift(lte)
                if fl.get("year") == old:
                    fl["year"] = year
                if str(old) in (s.get("title") or ""):
                    s["title"] = s["title"].replace(str(old), str(year)); titles += 1
                moved += 1
                hit = True
        if hit and str(old) in f["title"]:
            f["title"] = f["title"].replace(str(old), str(year)); titles += 1
            for k in ("coverImageUrl", "focusGifUrl", "heroBackdropUrl"):
                u = f.get(k) or ""
                if f"best-of-{old}" in u:
                    base = u.split("?")[0].replace(f"best-of-{old}", f"best-of-{year}")
                    try:
                        v = hashlib.md5(urllib.request.urlopen(base, timeout=60).read()).hexdigest()[:8]
                        f[k] = f"{base}?v={v}"
                    except Exception as e:
                        print(f"keeping {k} of {f['title']}: {e}")
json.dump(data, open(dst, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"{old} -> {year}: {moved} rails moved, {titles} titles renamed")
