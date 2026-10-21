"""Sitcom rails (agreed 2026-10-21), added into existing folders.

TMDB keyword "sitcom" (193171, ~2000 series), animation always out (Simpsons, Family Guy stay in animation rails).
Workplace comedy (210605) and mockumentary (11800) are their own rails in Genres › Comedy.
Placement: Genres › Comedy, the sitcom networks (NBC, CBS, ABC, FOX, Comedy Central, BBC, Channel 4),
Moods & Vibes › Cozy & Comforting, By Decade 1970s–2020s. Each rail goes right after the folder's series rails.
usage: python3 build_sitcoms.py in.json out.json
"""
import sys
from common import src, span, load, save, row, NOISE

SITCOM, WORKPLACE, MOCKUMENTARY = "193171", "210605", "11800"
VOTES = "vote_count.desc"  # "the" sitcoms first: Friends, Seinfeld, The Office


def sit(title, sort=VOTES, kw=SITCOM, **f):
    return src(title, "TV", sort, withKeywords=kw, withoutGenres="16|" + NOISE, **f)


def insert_after(folder, after, rails):
    folder["sources"] = [s for s in folder["sources"] if s["title"] not in {r["title"] for r in rails}]
    titles = [s["title"] for s in folder["sources"]]
    at = titles.index(after) + 1 if after in titles else len(titles)
    folder["sources"][at:at] = rails


data = load(sys.argv[1])
fold = lambda r, t: next(f for f in row(data, r)["folders"] if f["title"] == t)
added = 0

insert_after(fold("Genres", "Comedy"), "Top of the Year Series", rails := [
    sit("Classic Sitcoms", withOriginalLanguage="en", releaseDateLte="2009-12-31", voteCountGte=100),
    sit("Modern Sitcoms", withOriginalLanguage="en", releaseDateGte="2010-01-01", voteCountGte=50),
    sit("British Sitcoms", withOriginCountry="GB", voteCountGte=20),
    sit("Workplace Comedies", kw=WORKPLACE, withOriginalLanguage="en", voteCountGte=30),
    sit("Mockumentary Series", kw=MOCKUMENTARY, withOriginalLanguage="en", voteCountGte=20),
])
added += len(rails)

for net, nets, title, kw in (("NBC", "6", "Sitcoms", SITCOM), ("CBS", "16", "Sitcoms", SITCOM),
                             ("ABC", "2", "Sitcoms", SITCOM), ("FOX", "19", "Sitcoms", SITCOM),
                             ("Comedy Central", "47", "Sitcoms", SITCOM),
                             # British comedy: mockumentaries (Cunk, W1A, This Country) belong with the sitcoms
                             ("BBC", "4|332|3|100", "Sitcoms & Mockumentaries", SITCOM + "|" + MOCKUMENTARY),
                             ("Channel 4", "26", "Sitcoms & Mockumentaries", SITCOM + "|" + MOCKUMENTARY)):
    f = fold("Networks", net)
    have = [s["title"] for s in f["sources"]]
    after = next((t for t in ("Comedy", "Sci-Fi & Mystery") if t in have), have[-1])
    insert_after(f, after, [sit(title, kw=kw, withNetworks=nets, voteCountGte=5)])
    added += 1

insert_after(fold("Moods & Vibes", "Cozy & Comforting"), "Heartwarming TV Comedies & Dramas",
             [sit("Comfort Sitcoms", withOriginalLanguage="en", voteCountGte=500)])
added += 1

for decade in (1970, 1980, 1990, 2000, 2010, 2020):
    f = fold("By Decade", f"{decade}s")
    insert_after(f, f"Top Rated {decade}s TV Shows",
                 [sit(f"{decade}s Sitcoms", withOriginalLanguage="en", voteCountGte=10, **span(decade, decade + 9))])
    added += 1

save(data, sys.argv[2])
print(f"ok: {added} sitcom rails -> {sys.argv[2]}")
