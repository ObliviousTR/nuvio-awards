"""Universes & Franchises, Film Collections, Iconic Actors, Legendary Directors (+ Anime Film Collections in the Anime row).

Content comes from our Nuvio Library addon (github.com/ObliviousTR/nuvio-awards → library/, rebuilt weekly from
TMDB with discovery of new titles). This script reads its index (library/index.json in the local clone) and lays
out the folders. Art: Kaptain's matching folder art where it exists, otherwise the TMDB poster / portrait with the
folder title shown (design pass later).
"""
import json, os, sys
from common import addon_src, load, save, row, placeholder_folder

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
LIB = "community.oblivioustr.nuvio-library"
INDEX = json.load(open(os.path.expanduser("/home/claude/nuvio-awards/library/index.json"), encoding="utf-8"))
IMG = "https://image.tmdb.org/t/p/w500"
# franchise id -> Kaptain's single-collection folder whose art fits
KAPTAIN_ART = {
    "batman": "The Dark Knight", "spiderman": "Spider-Man", "xmen": "X-Men", "mcu": "The Avengers Collection",
    "dc": "Man of Steel", "starwars": "Star Wars", "startrek": "Star Trek: Alternate Reality",
    "middleearth": "The Lord of the Rings", "godzillakong": "Godzilla", "alienpredator": "Alien",
    "wizarding": "Harry Potter", "bond": "James Bond", "dune": "Dune", "johnwick": "John Wick",
    "mi": "Mission: Impossible", "matrix": "The Matrix", "madmax": "Mad Max",
    "apes": "Planet of the Apes (Reboot) Collection", "conjuring": "The Conjuring", "fast": "The Fast and the Furious",
    "jurassic": "Jurassic Park", "terminator": "The Terminator", "transformers": "Transformers",
    "indiana": "Indiana Jones",
}
PERSON_ALIASES = {"Joel & Ethan Coen": "Joel Coen", "Bong Joon-ho": "Bong Joon Ho"}


def lib(title, c):
    s = addon_src(title, "MOVIE" if c["type"] == "movie" else "TV", c["id"], addon_id=LIB)
    s["genre"] = None  # static catalogs take no extras
    return s


def folder(fid, title, rails, kaptain=None, poster=None, shape="POSTER", emoji="🎬"):
    if kaptain:
        f = {k: v for k, v in kaptain.items() if k not in ("sources", "catalogSources")}
        f["title"] = title
        f["id"] = kaptain["id"] if fid is None else fid
    elif poster:
        f = {"id": fid, "title": title, "hideTitle": False, "tileShape": shape, "coverImageUrl": IMG + poster,
             "coverEmoji": None, "titleLogoUrl": None, "focusGifUrl": None, "focusGifEnabled": False,
             "heroBackdropUrl": None}
    else:
        f = placeholder_folder(title, emoji)
        f["id"], f["tileShape"] = fid, shape
    f["sources"], f["catalogSources"] = rails, []
    return f


data = load(SRC)
report = []

# ---- Universes & Franchises (new row, before Film Collections) / Film Collections (Kaptain's genre folders)
fc = row(data, "Film Collections")
k_fc = {f["title"]: f for f in fc["folders"]}
uni = {k: v for k, v in fc.items() if k != "folders"}
uni["id"], uni["title"] = "collection-lib-universes", "Universes & Franchises"
folders = []
for e in INDEX["franchises"]:
    rails = [lib(c["name"].split(" · ")[-1], c) for c in e["rails"]]
    k = k_fc.get(KAPTAIN_ART.get(e["id"], ""))
    f = folder(f"folder-lib-{e['id']}", e["title"], rails, kaptain=k, poster=e.get("poster"))
    folders.append(f)
    report.append(f"## {e['title']} [{e['kind']}] ({len(rails)} rails) art={'kaptain' if k else 'tmdb'}")
    report += [f"   - {r['title']}" for r in rails]
uni["folders"] = folders
genre = []
for g in INDEX["genre_folders"]:
    rails = [lib(c["name"], c) for c in g["rails"]]
    genre.append(folder(None, g["title"], rails, kaptain=k_fc.get(g["title"])))
    report.append(f"## Film Collections: {g['title']} ({len(rails)} rails)")
fc["folders"] = genre
data.insert(data.index(fc), uni)

# ---- Anime Film Collections (Anime row, after the films folder)
anime = row(data, "Anime")
for g in INDEX["anime_collections"]:
    rails = [lib(c["name"], c) for c in g["rails"]]
    f = folder("folder-lib-anime-collections", g["title"], rails, shape="LANDSCAPE", emoji="🎌")
    titles = [x["title"] for x in anime["folders"]]
    at = titles.index("Anime Movies & Feature Films") + 1 if "Anime Movies & Feature Films" in titles else len(titles)
    anime["folders"] = [x for x in anime["folders"] if x["title"] != g["title"]]
    anime["folders"].insert(at, f)
    report.append(f"## Anime: {g['title']} ({len(rails)} rails)")

# ---- Iconic Actors / Legendary Directors
for row_title, new_title, key in (("Actors", "Iconic Actors", "actors"), ("Legendary Directors", "Legendary Directors", "directors")):
    r = row(data, row_title)
    r["title"] = new_title
    kap = {f["title"]: f for f in r["folders"]}
    out, art_k = [], 0
    for p in INDEX[key]:
        rails = [lib(c["name"].split(" · ")[-1], c) for c in p["rails"]]
        k = kap.get(p["name"]) or kap.get(PERSON_ALIASES.get(p["name"], ""))
        art_k += bool(k)
        slug = "".join(ch for ch in p["name"].lower() if ch.isalnum())
        out.append(folder(None if k else f"folder-lib-{key}-{slug}", p["name"], rails, kaptain=k, poster=p.get("portrait")))
    r["folders"] = out
    report.append(f"## {new_title}: {len(out)} folders, Kaptain art {art_k}, TMDB portrait {len(out) - art_k}")

save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} universes & franchises, {len(genre)} collection folders, {len(INDEX['actors'])} actors, {len(INDEX['directors'])} directors -> {OUT}")
