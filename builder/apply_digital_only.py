"""Films still only in cinemas stay out of the collections (Ozzy, 28 Oct 2026: Clayface, The Odyssey).
Nuvio's TMDB source has no release-type filter, so every native film rail that can reach the last year gets a
watch-provider filter: available in the US to stream, rent or buy on any of the services below (Nuvio adds the
monetization types flatrate|free|ads|rent|buy). A film in cinemas only has none of them yet. Rows left alone: the
Streaming Services rails (already filtered by their own service) and International Cinema (foreign films that are
out at home but not offered in the US). The Library / Spotlight / Awards addons filter themselves (scripts/spotlight.py).
usage: python3 apply_digital_only.py in.json out.json"""
import sys
from common import load, save, CURRENT_YEAR

# US: the rent / buy stores (they carry almost every film once it is out at home) and the big services
PROVIDERS = "|".join(str(i) for i in (2, 3, 7, 10, 68, 192,                       # Apple TV store, Google Play, Fandango at Home, Amazon Video, Microsoft, YouTube
                                      8, 9, 15, 337, 1899, 531, 386, 350, 43, 526, 258, 11, 99, 283, 73, 191, 300, 538))
SKIP_ROWS = {"Streaming Services", "International Cinema"}
RECENT = f"{CURRENT_YEAR - 1}-01-01"


def apply(data):
    n = 0
    for row in data:
        if row["title"] in SKIP_ROWS:
            continue
        for f in row.get("folders", []):
            for s in f.get("sources", []):
                if s.get("provider") != "tmdb" or s.get("mediaType") != "MOVIE" or s.get("tmdbSourceType") != "DISCOVER":
                    continue
                fl = s.get("filters") or {}
                if fl.get("withWatchProviders") or (fl.get("releaseDateLte") and fl["releaseDateLte"] < RECENT):
                    continue
                s["filters"] = {**fl, "watchRegion": "US", "withWatchProviders": PROVIDERS}
                n += 1
    return n


if __name__ == "__main__":
    data = load(sys.argv[1])
    print(f"digital only: {apply(data)} film rails")
    save(data, sys.argv[2])
