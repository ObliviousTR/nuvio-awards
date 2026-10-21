"""Awards & Festivals: the 5 agreed folders, MDBList lists via AIOMetadata (TMDB has no award data).

Agreed folders: The Oscars, The Emmy Awards, Cannes Venice & Sundance, Golden Globes & BAFTA,
Criterion Collection & Arthouse. Kaptain's rows (Academy Awards 22 categories, Cannes 8, Golden Globes 25)
set the line-up. Every list was opened through the MDBList API; Gemini's 3865 / 34110 / 3842 / 1371 /
28412 / 28415 don't exist. Preference: dynamic lists (auto-updating), then static lists updated after the
2026 ceremonies; qjao's category lists stop at the 2024 Oscars and are used only where nothing newer exists.
Winner lists are sorted newest first (sort released desc); ranked lists keep their own order.
usage: python3 build_awards.py in.json out.json report.txt  (also importable: AIO_CATALOGS)
"""
import sys
from common import src, addon_src, load, save, row, placeholder_folder, POP

AWARDS_ADDON = "community.oblivioustr.nuvio-awards"  # our static addon: github.com/ObliviousTR/nuvio-awards
NEW_FIRST = ("released", "asc")  # MDBList's order is inverted: asc = newest first (checked on the API)
RANKED = ("default", "asc")

# (rail title, media, catalog, source, sort): source AWARDS_ADDON = our GitHub addon (we keep it up to date);
# otherwise an MDBList list id + author. The MDBList ones left are dynamic lists MDBList fills itself.
OSCARS = [
    ("Latest Oscar Nominees", "MOVIE", "oscar-latest-nominees", AWARDS_ADDON, None),
    ("Best Picture Winners", "MOVIE", "oscar-best-picture", AWARDS_ADDON, None),
    ("Best Picture Nominees", "MOVIE", "oscar-best-picture-nominees", AWARDS_ADDON, None),
    ("Best Director Winners", "MOVIE", "oscar-director", AWARDS_ADDON, None),
    ("Best Director Nominees", "MOVIE", "oscar-director-nominees", AWARDS_ADDON, None),
    ("Best Actor Winners", "MOVIE", "oscar-actor", AWARDS_ADDON, None),
    ("Best Actor Nominees", "MOVIE", "oscar-actor-nominees", AWARDS_ADDON, None),
    ("Best Actress Winners", "MOVIE", "oscar-actress", AWARDS_ADDON, None),
    ("Best Actress Nominees", "MOVIE", "oscar-actress-nominees", AWARDS_ADDON, None),
    ("Best Supporting Actor Winners", "MOVIE", "oscar-supporting-actor", AWARDS_ADDON, None),
    ("Best Supporting Actor Nominees", "MOVIE", "oscar-supporting-actor-nominees", AWARDS_ADDON, None),
    ("Best Supporting Actress Winners", "MOVIE", "oscar-supporting-actress", AWARDS_ADDON, None),
    ("Best Supporting Actress Nominees", "MOVIE", "oscar-supporting-actress-nominees", AWARDS_ADDON, None),
    ("Best Original Screenplay Winners", "MOVIE", "oscar-original-screenplay", AWARDS_ADDON, None),
    ("Best Adapted Screenplay Winners", "MOVIE", "oscar-adapted-screenplay", AWARDS_ADDON, None),
    ("Best International Feature Winners", "MOVIE", "oscar-international", AWARDS_ADDON, None),
    ("Best International Feature Nominees", "MOVIE", "oscar-international-nominees", AWARDS_ADDON, None),
    ("Best Animated Feature Winners", "MOVIE", "oscar-animated", AWARDS_ADDON, None),
    ("Best Animated Feature Nominees", "MOVIE", "oscar-animated-nominees", AWARDS_ADDON, None),
    ("Best Documentary Feature Winners", "MOVIE", "oscar-documentary", AWARDS_ADDON, None),
    ("Best Cinematography Winners", "MOVIE", "oscar-cinematography", AWARDS_ADDON, None),
    ("Best Visual Effects Winners", "MOVIE", "oscar-visual-effects", AWARDS_ADDON, None),
    ("Best Original Score Winners", "MOVIE", "oscar-score", AWARDS_ADDON, None),
    ("Best Film Editing Winners", "MOVIE", "oscar-editing", AWARDS_ADDON, None),
    ("Best Production Design Winners", "MOVIE", "oscar-production-design", AWARDS_ADDON, None),
    ("Best Costume Design Winners", "MOVIE", "oscar-costume", AWARDS_ADDON, None),
    ("Best Makeup & Hairstyling Winners", "MOVIE", "oscar-makeup", AWARDS_ADDON, None),
    ("Best Sound Winners", "MOVIE", "oscar-sound", AWARDS_ADDON, None),
    ("Best Original Song Winners", "MOVIE", "oscar-song", AWARDS_ADDON, None),
    ("All Oscar-Winning Films", "MOVIE", "oscar-all-winners", AWARDS_ADDON, None),
]
EMMYS = [
    ("Outstanding Drama Series", "TV", "emmy-drama-series", AWARDS_ADDON, None),
    ("Outstanding Comedy Series", "TV", "emmy-comedy-series", AWARDS_ADDON, None),
    ("Outstanding Limited Series", "TV", "emmy-limited-series", AWARDS_ADDON, None),
    ("Emmy-Winning Series", "TV", 122821, "danypolonio33", NEW_FIRST),
    ("Emmy Nominees", "TV", 34134, "cookies6996", NEW_FIRST),
]
FESTIVALS = [
    ("Palme d'Or Winners", "MOVIE", "cannes-palme", AWARDS_ADDON, None),
    ("Cannes Grand Prix Winners", "MOVIE", "cannes-grand-prix", AWARDS_ADDON, None),
    ("Cannes Jury Prize Winners", "MOVIE", "cannes-jury-prize", AWARDS_ADDON, None),
    ("All Cannes Winners", "MOVIE", 146624, "atalante421", NEW_FIRST),
    ("Venice Golden Lion Winners", "MOVIE", "venice-golden-lion", AWARDS_ADDON, None),
    ("All Venice Winners", "MOVIE", 146622, "atalante421", NEW_FIRST),
    ("Sundance Grand Jury Prize · Dramatic", "MOVIE", "sundance-grand-jury", AWARDS_ADDON, None),
    ("All Sundance Winners", "MOVIE", 146625, "atalante421", NEW_FIRST),
    ("Berlinale Golden Bear Winners", "MOVIE", "berlinale-golden-bear", AWARDS_ADDON, None),
    ("TIFF People's Choice Award", "MOVIE", "tiff-peoples-choice", AWARDS_ADDON, None),
]
GLOBES_BAFTA = [
    ("Golden Globes · Best Picture – Drama", "MOVIE", "gg-drama-picture", AWARDS_ADDON, None),
    ("Golden Globes · Best Drama Series", "TV", "gg-drama-series", AWARDS_ADDON, None),
    ("Golden Globes · Best Picture – Musical or Comedy", "MOVIE", "gg-comedy-picture", AWARDS_ADDON, None),
    ("Golden Globes · Best Musical or Comedy Series", "TV", "gg-comedy-series", AWARDS_ADDON, None),
    ("Golden Globes · Best Limited Series", "TV", "gg-limited-series", AWARDS_ADDON, None),
    ("Golden Globes · Best Non-English Language Film", "MOVIE", "gg-non-english", AWARDS_ADDON, None),
    ("Golden Globes · Best Director", "MOVIE", "gg-director", AWARDS_ADDON, None),
    ("All Golden Globe-Winning Films", "MOVIE", 146627, "atalante421", NEW_FIRST),
    ("Golden Globe Nominees", "MOVIE", 32972, "premisrepresentation2", NEW_FIRST),
    ("BAFTA · Best Film", "MOVIE", "bafta-best-film", AWARDS_ADDON, None),
    ("BAFTA Nominees", "MOVIE", 32970, "internationalization22", NEW_FIRST),
]
CRITERION = [
    ("Criterion Collection · Essentials", "MOVIE", 13676, "linvo", RANKED),
    ("Criterion Collection · Popular", "MOVIE", 13675, "linvo", RANKED),
    ("Criterion Collection · New Additions", "MOVIE", 13674, "linvo", RANKED),
    None,  # native: Now on The Criterion Channel
    ("Letterboxd Top 500", "MOVIE", 205902, "pgibbens", RANKED),
    ("Sight and Sound · Greatest Films of All Time", "MOVIE", 207869, "pgibbens", RANKED),
    ("IMDb Top 250", "MOVIE", 205811, "pgibbens", RANKED),
    ("Arthouse & Independent Cinema", "MOVIE", 132014, "atalante421", RANKED),
]
CRITERION_CHANNEL = src("Now on The Criterion Channel", "MOVIE", POP, withWatchProviders="258",
                        watchRegion="US", voteCountGte=50)

FOLDERS = [
    ("The Oscars", "Academy Awards", OSCARS),
    ("The Emmy Awards", "🏅", EMMYS),
    ("Cannes, Venice & Sundance", "Festival de Cannes", FESTIVALS),
    ("Golden Globes & BAFTA", "Golden Globes", GLOBES_BAFTA),
    ("Criterion Collection & Arthouse", "🎞️", CRITERION),
]

AIO_CATALOGS = [
    {"id": f"mdblist.{lid}", "listId": lid, "name": title, "type": "movie" if media == "MOVIE" else "series",
     "source": "mdblist", "enabled": True, "showInHome": False, "sort": sort, "order": order,
     "genreSelection": "standard", "enableRatingPosters": True, "metadata": {"author": author}}
    for _, _, lists in FOLDERS for e in lists if e and e[3] != AWARDS_ADDON
    for title, media, lid, author, (sort, order) in [e]
]


def awards_src(title, media, catalog_id):
    """Our static awards addon: catalogs take no extras, so genre must stay empty."""
    s = addon_src(title, media, catalog_id, addon_id=AWARDS_ADDON)
    s["genre"] = None
    return s


def rails(lists):
    out = []
    for e in lists:
        if e is None:
            out.append(CRITERION_CHANNEL)
        elif e[3] == AWARDS_ADDON:
            out.append(awards_src(e[0], e[1], e[2]))
        else:
            out.append(addon_src(e[0], e[1], f"mdblist.{e[2]}"))
    return out


if __name__ == "__main__":
    SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
    data = load(SRC)
    awards = row(data, "Awards")
    awards["title"] = "Awards & Festivals"
    kaptain = {f["title"]: f for f in awards["folders"]}
    folders, report = [], []
    for title, art, lists in FOLDERS:
        if art in kaptain:
            f = {k: v for k, v in kaptain[art].items() if k not in ("sources", "catalogSources")}
            f["title"] = title
        else:
            f = placeholder_folder(title, art)
        f["sources"], f["catalogSources"] = rails(lists), []
        folders.append(f)
        report.append(f"## {title} ({len(f['sources'])} rails)")
        report += [f"   {i+1:2}. {s['title']}" for i, s in enumerate(f["sources"])]
    awards["folders"] = folders
    save(data, OUT)
    open(REPORT, "w").write("\n".join(report) + "\n")
    print(f"ok: {len(folders)} folders, {len(AIO_CATALOGS)} MDBList catalogs -> {OUT}")
