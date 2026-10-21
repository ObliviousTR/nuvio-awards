"""Anime row: the 7 agreed folders, Kaptain's rail ideas, native TMDB + MAL/Simkl via AIOMetadata.

Agreed folders (+ Kaptain's Studio Spotlight, added at the user's request): Seasonal & Currently Airing, All-Time Top Rated Anime, Anime Movies & Feature Films,
Shonen & High-Octane Action, Seinen Dark & Psychological, Isekai Magic & Fantasy Worlds,
Romance Comedy & Slice of Life. Kaptain's Sports rails go into Shonen; his Ghibli rail into Movies.
TMDB has no "currently airing" filter, so the seasonal folder leans on AIOMetadata's MAL / Simkl
catalogs (already in the user's config, type "anime"). Every TMDB rail is Japanese animation.
Keyword IDs checked against the TMDB API.
"""
import sys
from common import src, addon_src, span, load, save, row, placeholder_folder, POP, TOP, NEW

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
A = {"withGenres": "16", "withOriginalLanguage": "ja"}
KW = dict(shonen="207826", seinen="195668", slice="9914", sports="6075", isekai="237451",
          mecha_cyber="10046|12190", dark="177895|6152", psych="272553|12565|295702",
          martial="779|1462", magic="2343", game="282", romance="9840", school="6270|190116",
          iyashikei="291483", coming_of_age="10683",
          horror="315058|9853|162846|3358|295907")


def M(title, sort=POP, vc=50, genres=None, **f):
    return src(title, "MOVIE", sort, voteCountGte=vc, **{**A, **({"withGenres": f"16,{genres}"} if genres else {})}, **f)


def S(title, sort=POP, vc=30, genres=None, **f):
    return src(title, "TV", sort, voteCountGte=vc, **{**A, **({"withGenres": f"16,{genres}"} if genres else {})}, **f)


def studio(title, ids, media="TV", vc=30, sort=POP):
    return src(title, media, sort, withCompanies=ids, voteCountGte=vc, **A)


def aio(title, cid, genre="None"):
    """MAL / Simkl catalogs (type "anime"). IDs checked against AIOMetadata's source: Gemini's
    mal.top / mal.popular / simkl.trending / simkl.best / simkl.airing don't exist and returned nothing."""
    s = addon_src(title, "TV", cid)
    s["type"], s["genre"] = "anime", genre
    return s


FOLDERS = [
    ("Seasonal & Currently Airing", "Discover Anime", [
        aio("Currently Airing · MAL", "mal.airing"),
        aio("Top Rated This Week · MAL", "mal.season_top"),
        aio("Trending This Week · Simkl", "simkl.trending.anime", genre="week"),
        S("New Anime Premieres", NEW["TV"], vc=5),
        aio("Upcoming Season · MAL", "mal.upcoming"),
        S("Popular Anime Series", vc=50),
        M("New Anime Movies", NEW["MOVIE"], vc=5),
    ]),
    ("All-Time Top Rated Anime", "🏆", [
        M("Top Rated Anime Movies", TOP, vc=500),
        S("Top Rated Anime Series", TOP, vc=300),
        aio("MAL Top Anime", "mal.top_anime"),
        aio("MAL Most Favorited", "mal.most_favorites"),
        M("Modern Classics of the 2010s · Movies", TOP, vc=300, **span(2010, 2019)),
        S("Modern Classics of the 2010s · Series", TOP, vc=200, **span(2010, 2019)),
        M("Timeless Classics · Movies", TOP, vc=200, releaseDateLte="1999-12-31"),
        S("Timeless Classics · Series", TOP, vc=100, releaseDateLte="1999-12-31"),
        aio("MAL Most Popular", "mal.most_popular"),
    ]),
    ("Anime Movies & Feature Films", "🎬", [
        M("Popular Anime Movies", vc=100),
        M("Top Rated Anime Movies", TOP, vc=500),
        M("New Anime Movies", NEW["MOVIE"], vc=5),
        M("Action & Sci-Fi Anime Movies", vc=100, genres="28|878"),
        M("Coming of Age & Tearjerkers", vc=50, withKeywords=KW["coming_of_age"]),
        M("Fantasy & Adventure Anime Movies", vc=100, genres="14|12"),
    ]),
    ("Shonen & High-Octane Action", "Shonen & Action Anime", [
        S("Popular Shonen Series", vc=50, withKeywords=KW["shonen"]),
        M("Popular Shonen Movies", vc=50, withKeywords=KW["shonen"]),
        S("Top Rated Battle Anime", TOP, vc=200, genres="10759"),
        M("Top Rated Action Anime Movies", TOP, vc=200, genres="28"),
        S("Martial Arts & Swordplay", vc=20, withKeywords=KW["martial"]),
        S("Mecha & Cyberpunk Series", vc=20, withKeywords=KW["mecha_cyber"]),
        M("Mecha & Cyberpunk Movies", vc=50, withKeywords=KW["mecha_cyber"]),
        S("Popular Sports Anime", vc=20, withKeywords=KW["sports"]),
        S("Top Rated Sports Anime", TOP, vc=50, withKeywords=KW["sports"]),
        S("New Action Anime", NEW["TV"], vc=5, genres="10759"),
    ]),
    ("Seinen, Dark & Psychological", "🌑", [
        S("Popular Seinen Series", vc=50, withKeywords=KW["seinen"]),
        M("Seinen Movies", vc=50, withKeywords=KW["seinen"]),
        S("Top Rated Seinen", TOP, vc=150, withKeywords=KW["seinen"]),
        S("Psychological & Mind Games · Series", vc=20, withKeywords=KW["psych"]),
        M("Psychological & Mind Games · Movies", vc=50, withKeywords=KW["psych"]),
        S("Dark Fantasy & Supernatural", vc=30, withKeywords=KW["dark"]),
        S("Crime & Thriller Anime · Series", vc=30, genres="80|9648"),
        M("Crime & Thriller Anime · Movies", vc=50, genres="80|53"),
        S("Horror Anime · Series", vc=20, withKeywords=KW["horror"]),
        M("Horror Anime · Movies", vc=30, genres="27"),
    ]),
    ("Isekai, Magic & Fantasy Worlds", "Isekai & Fantasy Sagas", [
        S("Popular Isekai Adventures", vc=30, withKeywords=KW["isekai"]),
        S("Top Rated Isekai", TOP, vc=100, withKeywords=KW["isekai"]),
        S("Trapped in a Game World", vc=20, withKeywords=KW["game"]),
        S("Epic Magic & Fantasy Sagas", vc=30, genres="10765", withKeywords=KW["magic"]),
        S("Acclaimed Fantasy Worlds", TOP, vc=300, genres="10765"),
        M("Fantasy Anime Movies", vc=100, genres="14"),
        S("New Isekai Releases", NEW["TV"], vc=3, withKeywords=KW["isekai"]),
    ]),
    ("Romance, Comedy & Slice of Life", "Slice of Life & Romance", [
        S("Popular Slice of Life", vc=30, withKeywords=KW["slice"]),
        S("Top Rated Romance Anime", TOP, vc=100, withKeywords=KW["romance"]),
        M("Romance Anime Movies", vc=50, genres="10749"),
        S("Comedy Anime Series", vc=50, genres="35"),
        S("High School Stories", vc=30, withKeywords=KW["school"]),
        S("Cozy & Relaxing Favorites", vc=10, withKeywords=KW["iyashikei"]),
        M("Coming of Age Tearjerkers", vc=50, withKeywords=KW["coming_of_age"]),
        S("New Romance Anime", NEW["TV"], vc=3, withKeywords=KW["romance"]),
    ]),
    ("Studio Spotlight", "Studio Spotlight", [  # Kaptain's studio rails; company IDs checked on TMDB
        studio("Studio Ghibli Masterpieces", "10342", media="MOVIE", vc=100),
        studio("Kyoto Animation Visual Gems", "5438"),
        studio("MAPPA Modern Powerhouse", "21444"),
        studio("Ufotable Cinematic Spectacles", "5887"),
        studio("Madhouse & Production I.G", "3464|529"),
        studio("Bones, WIT & Trigger", "2849|31058|50908"),
        studio("CloverWorks & Science SARU", "121589|99494"),
        studio("Anime Studio Films · MAPPA, ufotable, KyoAni & more",
               "21444|5887|5438|3464|529|2849|31058|50908|121589|99494", media="MOVIE", vc=100),
    ]),
]

data = load(SRC)
anime = row(data, "Anime")
kaptain = {f["title"]: f for f in anime["folders"]}
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
anime["folders"] = folders
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} folders -> {OUT}")
