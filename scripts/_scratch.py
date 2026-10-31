import os, json, urllib.request, urllib.parse
# Networks heroes: each network's best-known series (poster paths) and its TMDB logos.
OUT = "refs/hero"; os.makedirs(OUT, exist_ok=True)
K = os.environ["TMDB_API_KEY"]
IDS = {"HBO": [49], "FX": [88], "AMC": [174], "Showtime": [67], "Sky Atlantic": [1063], "BBC": [4, 332, 3, 100], "ITV": [9], "Channel 4": [26], "U&Dave": [388], "NBC": [6], "ABC": [2], "CBS": [16], "FOX": [19], "USA Network": [30], "Syfy": [77], "Comedy Central": [47], "Adult Swim": [80], "Cartoon Network": [56], "TV Tokyo": [98], "Fuji TV / MBS": [1, 94], "Discovery Channel": [64], "National Geographic": [43], "History Channel": [65], "Food Network": [143]}


def get(p, **q):
    q["api_key"] = K
    try:
        return json.loads(urllib.request.urlopen(f"https://api.themoviedb.org/3{p}?{urllib.parse.urlencode(q)}",
                                                 timeout=60).read())
    except Exception as e:
        print("ERR", p, e)
        return {}


res = {}
for name, nets in IDS.items():
    items, seen = [], set()
    for n in nets:
        for page in (1, 2):
            for r in get("/discover/tv", with_networks=n, sort_by="vote_count.desc", page=page,
                         without_genres="10763|10767|10766").get("results", []):
                if r.get("poster_path") and r["id"] not in seen:
                    seen.add(r["id"])
                    items.append({"id": r["id"], "title": r["name"], "poster": r["poster_path"],
                                  "votes": r.get("vote_count", 0), "net": n})
    items.sort(key=lambda x: -x["votes"])
    logos = {n: [(l["file_path"], l["width"], l["height"]) for l in get(f"/network/{n}/images").get("logos", [])]
             for n in nets[:1]}
    res[name] = {"items": items, "logos": logos}
    print(name, len(items), [i["title"] for i in items[:10]], logos)
json.dump(res, open(f"{OUT}/networks.json", "w"), indent=1, ensure_ascii=False)
