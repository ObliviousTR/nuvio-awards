"""Kids & Family: the 6 agreed folders, native TMDB rails, Kaptain's rail ideas.

Agreed folders: Discover Family, Family Movie Night, Disney & Pixar Magic, DreamWorks & Illumination,
Studio Spotlight (Laika, Aardman, Cartoon Saloon), Saturday Morning & Classic Cartoons.
Kaptain's Preschool folder is dropped; his Disney Channel & Family TV rails move into Discover Family.
User rule: family rails must show at least as much live action as animation, so "Family" rails are
live-action and animated family titles get their own clearly named rails. English-language only (no anime).
IDs checked against the TMDB API (companies, networks, keywords).
"""
import sys
from common import src, span, load, save, row, placeholder_folder, NOISE, POP, TOP, NEW

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
EN = {"withOriginalLanguage": "en"}
LA_M = dict(withoutGenres="16", **EN)            # live-action movies
LA_T = dict(withoutGenres="16|10764|" + NOISE, **EN)   # live-action scripted series (no reality / game shows)
ANIMALS = "15162|2673|267848|18165"              # dog, horse, talking animal, animals
STOP_MOTION, SUPERHERO, ADULT_TOON = "10121", "9715", "161919"


def company(title, cid, media="MOVIE", sort=POP, vc=20, **f):
    return src(title, media, sort, withCompanies=str(cid), voteCountGte=vc, **f)


FOLDERS = [
    ("Discover Family", "Discover Family", [
        src("Popular Family Movies", "MOVIE", POP, withGenres="10751", voteCountGte=100, **LA_M),
        src("Popular Family Series", "TV", POP, withGenres="10751", voteCountGte=30, **LA_T),
        src("New Family Movies", "MOVIE", NEW["MOVIE"], withGenres="10751", voteCountGte=10, **LA_M),
        src("New Family Series", "TV", NEW["TV"], withGenres="10751", voteCountGte=5, **LA_T),
        src("Top Rated Family Movies", "MOVIE", TOP, withGenres="10751", voteCountGte=1000, **LA_M),
        src("Top Rated Family Series", "TV", TOP, withGenres="10751", voteCountGte=200, **LA_T),
        src("Popular Animated Family Movies", "MOVIE", POP, withGenres="16,10751", voteCountGte=100, **EN),
        src("Popular Kids Shows", "TV", POP, withGenres="16,10762", voteCountGte=20, **EN),
        src("Top Rated Animated Family Movies", "MOVIE", TOP, withGenres="16,10751", voteCountGte=1000, **EN),
        src("Top Rated Kids Series", "TV", TOP, withGenres="16,10762", voteCountGte=100, **EN),
        src("Disney Channel Originals", "TV", POP, stype="NETWORK", tmdb_id=54, voteCountGte=20, **LA_T),
        src("Nickelodeon Teen Comedies", "TV", POP, stype="NETWORK", tmdb_id=13, voteCountGte=20, **LA_T),
        src("Wholesome Family Sitcoms", "TV", POP, withGenres="10751,35", voteCountGte=30, **LA_T),
        src("Teen Fantasy & Mystery", "TV", POP, withGenres="10751,10765", voteCountGte=20, **LA_T),
    ]),
    ("Family Movie Night", "Family Movie Night", [  # all live-action: the animated studios have their own folders
        src("Iconic Family Classics", "MOVIE", POP, withGenres="10751", voteCountGte=3000,
            releaseDateLte="2005-12-31", **LA_M),
        src("Magical Fantasy Adventures", "MOVIE", POP, withGenres="10751,14", voteCountGte=300, **LA_M),
        src("Family Comedies", "MOVIE", POP, withGenres="10751,35", voteCountGte=300, **LA_M),
        src("Animal & Creature Adventures", "MOVIE", POP, withGenres="10751", withKeywords=ANIMALS,
            voteCountGte=100, **LA_M),
        src("Top Rated Family Adventures", "MOVIE", TOP, withGenres="10751,12", voteCountGte=1000, **LA_M),
        src("New Family Movie Releases", "MOVIE", NEW["MOVIE"], withGenres="10751", voteCountGte=10, **LA_M),
    ]),
    ("Disney & Pixar Magic", "✨", [
        company("Pixar Favorites", 3, vc=500),
        company("Walt Disney Animation Studios", 6125, vc=500),
        company("Disney Live-Action Favorites", 2, vc=500, withGenres="10751", withoutGenres="16"),  # Family tag keeps PG-13 tentpoles (Pirates, Cruella) out
        company("Disney Animated Classics", 6125, vc=300, releaseDateLte="1999-12-31"),
        company("Disney Live-Action Classics", 2, vc=200, withGenres="10751", withoutGenres="16", releaseDateLte="1999-12-31"),
        company("Top Rated Pixar", 3, sort=TOP, vc=1000),
        company("Disney Animated Series", 3475, media="TV", vc=50),
    ]),
    ("DreamWorks & Illumination", "🐉", [
        company("DreamWorks Animation Favorites", 521, vc=500),
        company("Illumination Blockbusters", 6704, vc=500),
        company("Top Rated DreamWorks Animation", 521, sort=TOP, vc=1000),
        company("DreamWorks Animated Series", 42141, media="TV", vc=20),
        company("Sony Pictures Animation Hits", 2251, vc=300),
        company("Blue Sky Studios", 9383, vc=300),
    ]),
    ("Studio Spotlight", "Animated Studio Spotlight", [
        company("LAIKA", 11537, vc=50),
        company("Aardman", 297, vc=50),
        company("Cartoon Saloon", 23948, vc=20),
        src("Stop-Motion Treasures", "MOVIE", POP, withGenres="16", withKeywords=STOP_MOTION, voteCountGte=100),
    ]),
    ("Saturday Morning & Classic Cartoons", "Saturday Morning & Nostalgic Cartoons", [
        src("Iconic 80s Cartoons", "TV", POP, withGenres="16", withoutKeywords=ADULT_TOON, voteCountGte=20, **span(1980, 1989), **EN),
        src("Iconic 90s Cartoons", "TV", POP, withGenres="16", withoutKeywords=ADULT_TOON, voteCountGte=30, **span(1990, 1999), **EN),
        src("2000s Animated Hits", "TV", POP, withGenres="16", withoutKeywords=ADULT_TOON, voteCountGte=50, **span(2000, 2009), **EN),
        src("Cartoon Network Classics", "TV", POP, stype="NETWORK", tmdb_id=56, withGenres="16", withoutKeywords=ADULT_TOON,
            voteCountGte=30, releaseDateLte="2012-12-31"),
        src("Nicktoons", "TV", POP, stype="NETWORK", tmdb_id=13, withGenres="16", withoutKeywords=ADULT_TOON, voteCountGte=30),
        src("Superhero Animated Series", "TV", POP, withGenres="16", withoutKeywords=ADULT_TOON, withKeywords=SUPERHERO, voteCountGte=30, **EN),
        src("Classic Cartoons of the Golden Age", "TV", POP, withGenres="16", withoutKeywords=ADULT_TOON, voteCountGte=10,
            releaseDateLte="1979-12-31", **EN),
    ]),
]

data = load(SRC)
kids = row(data, "Kids and Family")
kids["title"] = "Kids & Family"
kaptain = {f["title"]: f for f in kids["folders"]}
folders, report = [], []
for title, art, rails in FOLDERS:
    if art in kaptain:
        f = {k: v for k, v in kaptain[art].items() if k not in ("sources", "catalogSources")}
        f["title"] = title
    else:
        f = placeholder_folder(title, art)
    f["sources"], f["catalogSources"] = rails, []
    folders.append(f)
    report.append(f"## {title} ({len(rails)} rails)")
    report += [f"   {i+1:2}. {s['title']}" for i, s in enumerate(rails)]
kids["folders"] = folders
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} folders -> {OUT}")
