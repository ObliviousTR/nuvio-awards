"""Moods & Vibes (Kaptain's 10 folders + rails), Based On (5), Documentaries (Kaptain's 7 + Trending).

Moods / Documentaries reproduce Kaptain's own rail line-up per folder with native TMDB Discover queries,
then add a few extra rails (our earlier agreed themes) and International Hits for moods.
Every keyword below was looked up on the TMDB API (search/keyword); the risky ones were also run
through discover to check the titles they return.
"""
import sys
from common import src, span, load, save, row, add, placeholder_folder, NOISE, CURRENT_YEAR, INTL_LANGS, TOP, NEW

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]
DATE_M, DATE_T = NEW["MOVIE"], NEW["TV"]

K = {
    "mind": "362567|326438|10854|157171",   # mind-bending set incl. twist ending (326438), time loop (10854)
    "timeloop": "10854|366519|4379|175629",  # time loop(s), time travel, alternative reality
    "whodunit": "12570|207046|703",
    "heist": "10051|15363|191845",
    "survival": "10349",
    "martial": "779|780|184656|9917|384605|209476",  # martial arts + MMA + boxing
    "cyber": "12190|310",
    "dystopia": "4565|4458",
    "spaceopera": "161176|9882",
    "inspire": "281585|3993|383896|275276|319357",  # inspirational, inspiration, feel-good, heartwarming
    "roadbuddy": "7312|167541",               # road trip, buddy comedy
    "slowburn": "277551|386243|367766|374206",
    "neonoir": "207268|9807",
    "character": "164186",
    "tearjerker": "156924|346048|9872",       # tearjerker, grief
    "antihero": "2095|9748",                  # anti hero, revenge
    "haunted": "3358|162846|9853",            # haunted house, ghost, paranormal
    "horror_tv": "315058|9853|162846|3358|295907",
    "psychhorror": "295907",
    "monster": "1299|11100|161791|289108",
    "zombie": "12377",
    "disaster": "10617|5096",
    "satire": "8201",
    "darkcomedy": "10123",
    "mafia": "10391|3149",
    "truestory": "9672",
    "book": "818",
    "videogame": "41645",
    "comic": "9717",
    "myth": "2035|178856",
    # documentaries
    "truecrime": "33722|10714|9826",
    "serialkiller": "10714",
    "nature": "221355|9902",
    "ocean": "270",
    "wildlife": "9902",
    "climate": "2210|221355",
    "sports": "6075|209476|13042|6496",
    "motorsport": "242128|9571|377914",
    "combat": "209476|9917|384605",
    "musician": "4048",
    "rockhiphop": "11700|898",
    "concert": "156205",
    "ww2": "1956",
    "ancient": "179300|5049|157894|383073|162861|1405",  # + archaeology, ancient greece, roman empire
    "space": "9882|161176|3801",
    "tech": "1576|310",
    "medicine": "1279|3721|6514|188973",                  # medicine, health, health care, pandemic
    "journalism": "917|195240",
    "finance": "165193|4373",
    "cultfraud": "6158|162766|4373",
    "politics": "917|209817|10410|6078|417",             # + politics, corruption
    "conspiracy": "10410",
}
NO_ANIM = {"withoutGenres": "16"}
NO_ANIM_T = {"withoutGenres": "16|" + NOISE}


def kw(k, **extra):
    return {"withKeywords": K[k], **extra}


def m(title, sort="popularity.desc", vc=200, **f):
    return src(title, "MOVIE", sort, voteCountGte=vc, **f)


def t(title, sort="popularity.desc", vc=50, **f):
    return src(title, "TV", sort, voteCountGte=vc, **f)


def intl(mf, tf=None):
    r = [src("International Hits Movies", "MOVIE", voteCountGte=800,
             **add(mf, withOriginalLanguage=INTL_LANGS, withoutGenres="16"))]
    if tf is not None:
        r.append(src("International Hits Series", "TV", voteCountGte=300,
                     **add(tf, withOriginalLanguage=INTL_LANGS, withoutGenres="16|" + NOISE)))
    return r


# ------------------------------------------------------------------ Moods & Vibes (Kaptain line-up)
MOODS = [
    ("Cozy & Comforting", "Cozy & Comforting", [
        m("Live-Action Romantic Comedies", vc=300, withGenres="10749,35", **NO_ANIM),
        t("Heartwarming TV Comedies & Dramas", vc=100, withGenres="35,18", **NO_ANIM_T),
        m("Cozy Romantic Stories", vc=300, withGenres="10749,18", withoutGenres="16|27|53|80"),
        m("Acclaimed Feel-Good Classics", TOP, vc=500, **kw("inspire", withoutGenres="16|27|53|28|12|14|878|80|10752")),
        m("Cozy Animated Favorites", vc=1000, withGenres="16,10751"),
        m("Recent Cozy Releases", DATE_M, vc=40, withGenres="10751,35", **NO_ANIM),
    ] + intl({"withGenres": "10751,35"}, {"withGenres": "35,10751"})),
    ("Mind-Bending", "Mind-Bending", [
        m("Mind-Bending Sci-Fi Thrillers", vc=800, withGenres="878,53"),
        t("Psychological Mystery Shows", vc=150, withGenres="9648,18", **NO_ANIM_T),
        m("Twist Endings & Unpredictable", vc=300, **kw("mind")),
        m("Time Loops & Alternate Realities", vc=200, **kw("timeloop")),
        m("Top Rated Psychological Thrillers", TOP, vc=2000, withGenres="53,18,9648"),
        m("Recent Mind-Bending Releases", DATE_M, vc=40, **kw("mind")),
        m("Whodunits & Plot Twists", vc=300, **kw("whodunit")),           # agreed: Plot Twists & Mystery
        m("Cyberpunk & AI", vc=300, **kw("cyber")),                       # agreed: Cyberpunk & Sci-Fi
    ] + intl({"withGenres": "878,53"}, {"withGenres": "9648,18"})),
    ("Adrenaline Rush", "Adrenaline Rush", [
        m("High-Octane Action Blockbusters", vc=3000, withGenres="28"),
        m("Survival & Heist Movies", vc=300, withKeywords=K["survival"] + "|" + K["heist"]),
        t("Action & Thriller Series", vc=150, withGenres="10759", withoutGenres="16|10765|10751|10762|" + NOISE),
        m("Martial Arts & Combat", vc=300, **kw("martial")),
        m("Top Rated Action Hits", TOP, vc=3000, withGenres="28"),
        m("Recent High-Octane Releases", DATE_M, vc=50, withGenres="28"),
        m("Disaster Movies", vc=200, **kw("disaster")),
    ] + intl({"withGenres": "28"}, {"withGenres": "10759"})),
    ("Epic & Sweeping", "Epic & Sweeping", [
        m("Historical & War Epics", vc=2000, withGenres="36|10752"),
        m("Grand Fantasy Epics", vc=2000, withGenres="14,12", **NO_ANIM),
        t("Epic Scale TV Sagas", vc=800, withGenres="10765,10759,18", **NO_ANIM_T),  # GoT, House of the Dragon, Witcher
        m("Space Opera & Cosmic Journeys", vc=500, withGenres="878", **kw("spaceopera")),
        m("Top Rated Epic Masterpieces", TOP, vc=5000, withGenres="12|36|10752", **NO_ANIM),
        m("Recent Epic Releases", DATE_M, vc=80, withGenres="12|36|10752", **NO_ANIM),
    ] + intl({"withGenres": "36|10752|12"}, {"withGenres": "10765,18"})),
    ("Feel-Good", "Feel-Good", [
        m("Uplifting & Inspiring Movies", vc=150, **kw("inspire", withoutGenres="16|27|53|28|12|14|878|80|10752")),
        t("Joyful Comedy TV Series", vc=200, withGenres="35", withoutGenres="16|18|80|" + NOISE),
        m("Inspiring True Stories", vc=500, **kw("truestory", withoutGenres="27|80|53|10752")),
        m("Road Trips & Buddy Comedies", vc=150, **kw("roadbuddy", withoutGenres="16")),
        m("Top Rated Feel-Good Classics", TOP, vc=3000, withGenres="35", withoutGenres="16|27|80|53|18"),
        m("Recent Feel-Good Releases", DATE_M, vc=40, withGenres="35", withoutGenres="16|27|80|53"),
        m("Satire", vc=200, **kw("satire")),
    ] + intl({"withGenres": "35"}, {"withGenres": "35"})),
    ("Slow Burn", "Slow Burn", [
        m("Atmospheric Mystery Slow Burns", vc=30, **kw("slowburn")),
        t("Haunting Slow Burn TV", TOP, vc=300, withGenres="9648,18", **NO_ANIM_T),
        m("Neo-Noir & Moody Crime", vc=300, **kw("neonoir")),
        m("Deep Character Dramas", TOP, vc=500, withGenres="18", **kw("character")),
        m("Top Rated Atmospheric Masterpieces", TOP, vc=2000, withGenres="9648,18", **NO_ANIM),
        m("Recent Slow Burn Releases", DATE_M, vc=40, withGenres="9648,18", **NO_ANIM),
    ] + intl({"withGenres": "9648,18"}, {"withGenres": "9648,18"})),
    ("Tearjerkers", "Tearjerkers", [
        m("Acclaimed Tearjerker Movies", TOP, vc=500, withGenres="18", **kw("tearjerker", withoutGenres="16|27|53")),
        t("Emotional TV Series", vc=200, withGenres="18", withoutGenres="16|80|10765|10759|9648|" + NOISE),
        m("Romantic Heartbreaks", TOP, vc=1000, withGenres="10749,18", withoutGenres="16|35|27"),
        m("Family & Loss Stories", vc=100, withGenres="18,10751", withoutGenres="16|27"),
        m("Top Rated Emotional Masterpieces", TOP, vc=5000, withGenres="18", withoutGenres="16|80|10752|28|27|53"),
        m("Recent Emotional Releases", DATE_M, vc=40, withGenres="18,10749", withoutGenres="16|27|53"),
    ] + intl({"withGenres": "18"}, {"withGenres": "18"})),
    ("80s & 90s Vibes", "80s & 90s Vibes", [
        m("Iconic 80s Blockbusters", vc=1500, **span(1980, 1989)),
        m("Iconic 90s Blockbusters", vc=1500, **span(1990, 1999)),
        m("80s & 90s Popcorn Action", vc=800, withGenres="28", **span(1980, 1999)),
        m("80s & 90s Classic Comedies", vc=600, withGenres="35", withoutGenres="16", **span(1980, 1999)),
        t("Retro Sci-Fi & Mystery TV", vc=50, withGenres="10765|9648", **NO_ANIM_T, **span(1980, 1999)),
        m("90s Cult & Indie Hits", TOP, vc=300, withoutCompanies="174|33|4|2|25|5|420|3|7|521|1|12|21|56|34",
          withoutGenres="16|99", **span(1990, 1999)),
    ] + intl(span(1980, 1999))),
    ("Dark & Gritty", "Dark & Gritty", [
        m("Gritty Crime & Underworld", vc=1000, withGenres="80,18", withoutGenres="35|16"),
        t("Intense Dark TV Series", TOP, vc=500, withGenres="80,18", **NO_ANIM_T),
        m("Anti-Hero & Revenge Stories", vc=500, **kw("antihero")),
        m("Dystopian & Post-Apocalyptic", vc=400, **kw("dystopia")),
        m("Top Rated Gritty Crime", TOP, vc=3000, withGenres="80", withoutGenres="35|16"),
        m("Recent Dark & Gritty Releases", DATE_M, vc=40, withGenres="80,53", withoutGenres="35|16"),
        m("Mafia & Gangsters", vc=300, **kw("mafia")),
        m("Dark Comedies", vc=300, **kw("darkcomedy")),
    ] + intl({"withGenres": "80"}, {"withGenres": "80,18"})),
    ("Spooky & Creepy", "Spooky & Creepy", [
        m("Haunted Houses & Ghosts", vc=200, withGenres="27", **kw("haunted")),
        t("Creepy Paranormal TV Series", vc=50, **kw("horror_tv", withoutGenres="16|99|" + NOISE)),
        m("Psychological Horror & Dread", vc=150, withGenres="27", **kw("psychhorror")),
        m("Monsters & Creature Features", vc=300, withGenres="27|878", **kw("monster")),
        m("Top Rated Horror Masterpieces", TOP, vc=2000, withGenres="27"),
        m("Recent Spooky Releases", DATE_M, vc=40, withGenres="27"),
        m("Zombie Outbreaks", vc=200, **kw("zombie")),
    ] + intl({"withGenres": "27"})),
]

# ------------------------------------------------------------------ Based On (user rail order)
def based_on(f):
    return [
        m("New Movies", DATE_M, vc=20, **f), t("New Series", DATE_T, vc=10, **f),
        m("Popular Movies", vc=100, **f), t("Popular Series", vc=30, **f),
        m("Top All Time Movies", TOP, vc=500, **f), t("Top All Time Series", TOP, vc=100, **f),
    ] + intl(f, f)


BASED_ON = [
    ("True Stories & Biographies", "True Story", based_on(kw("truestory"))),
    ("Books & Literature", "Book", based_on(kw("book"))),
    ("Video Games", "Video Games", based_on(kw("videogame"))),
    ("Comics & Graphic Novels", "Comics", based_on(kw("comic"))),
    ("Mythology & Folklore", "Mythology", based_on(kw("myth"))),
]

# ------------------------------------------------------------------ Documentaries (Kaptain line-up)
D = {"withGenres": "99"}


def dm(title, sort="popularity.desc", vc=20, **f):
    return m(title, sort, vc, **add(D, **f))


def dt(title, sort="popularity.desc", vc=5, **f):
    return t(title, sort, vc, **add(D, **f))


DOCS = [
    ("Trending & Award-Winning Docs", None, [   # ours (agreed list), no Kaptain counterpart
        dm("Popular Documentaries", vc=50), dt("Popular Docuseries", vc=20),
        dm("New Documentaries", DATE_M, vc=10), dt("New Docuseries", DATE_T, vc=5),
        dm(f"Best Documentaries of {CURRENT_YEAR}", TOP, vc=15, **span(CURRENT_YEAR)),
        dm("All-Time Great Documentaries", TOP, vc=1000),
        dt("All-Time Great Docuseries", TOP, vc=200),
    ]),
    ("True Crime & Serial Killers", "True Crime & Serial Killers", [
        dt("Popular True Crime Series", vc=10, withGenres="99,80"),
        dm("Acclaimed True Crime Films", TOP, vc=100, withGenres="99,80"),
        dm("Serial Killers & Unsolved Cases", vc=20, **kw("serialkiller")),
        dm("Heists, Cons & Robberies", vc=20, **kw("heist")),
        dt("Top Rated True Crime Docuseries", TOP, vc=50, withGenres="99,80"),
        dt("Recent True Crime Releases", DATE_T, vc=3, withGenres="99,80"),
    ]),
    ("Nature, Wildlife & Earth", "Nature, Wildlife & Earth", [
        dt("Popular Nature & Wildlife Series", vc=10, **kw("nature")),
        dm("Acclaimed Nature Films", TOP, vc=100, **kw("nature")),
        dm("Deep Ocean & Marine Life", vc=10, **kw("ocean")),
        dm("Wild Animals & Wilderness", vc=20, **kw("wildlife")),
        dt("Top Rated Earth & Environment", TOP, vc=30, **kw("climate")),
        dt("Recent Nature Releases", DATE_T, vc=3, **kw("nature")),
    ]),
    ("Sports & Athletic Stories", "Sports & Athletic Stories", [
        dt("Popular Sports Docuseries", vc=10, **kw("sports")),
        dm("Acclaimed Sports Films", TOP, vc=100, **kw("sports")),
        dm("Motorsport & Racing", vc=10, **kw("motorsport")),
        dm("Combat Sports, Boxing & MMA", vc=10, **kw("combat")),
        dt("Top Rated Sports Series", TOP, vc=30, **kw("sports")),
        dt("Recent Sports Releases", DATE_T, vc=3, **kw("sports")),
    ]),
    ("Music & Concert Documentaries", "Music & Concert Documentaries", [
        dm("Popular Musician Documentaries", vc=30, **kw("musician")),
        dm("Acclaimed Music & Band Docs", TOP, vc=100, withGenres="99,10402"),
        dt("Popular Music Docuseries", vc=5, **kw("musician")),
        dm("Rock & Hip-Hop Spotlights", vc=20, **kw("rockhiphop")),
        dm("Live Concert Films", vc=20, **kw("concert")),
        dm("Recent Music Releases", DATE_M, vc=5, withGenres="99,10402"),
    ]),
    ("History, War & Civilizations", "History, War & Civilizations", [
        dm("Popular History Documentaries", vc=30, withGenres="99,36"),
        dt("Acclaimed Historical Docuseries", TOP, vc=50, withGenres="99,10768"),
        dm("WWII & World Conflict", vc=20, **kw("ww2")),
        dm("Ancient Empires & Civilizations", vc=5, **kw("ancient")),
        dt("Top Rated Military & War Series", TOP, vc=30, withGenres="99,10768"),
        dm("Recent History Releases", DATE_M, vc=5, withGenres="99,36"),
    ]),
    ("Science, Tech & Cosmos", "Science, Tech & Cosmos", [
        dt("Popular Science & Space Docuseries", vc=10, **kw("space")),
        dm("Acclaimed Cosmos & Universe Films", TOP, vc=50, **kw("space")),
        dm("Technology, AI & Cyber", vc=20, **kw("tech")),
        dm("Medical, Brain & Health", vc=10, **kw("medicine")),
        dt("Top Rated Space & Physics Series", TOP, vc=30, **kw("space")),
        dt("Recent Science Releases", DATE_T, vc=3, withKeywords=K["space"] + "|" + K["tech"]),
    ]),
    ("Investigative & Scandals", "Investigative & Scandals", [
        dm("Acclaimed Investigative Films", TOP, vc=100, **kw("journalism")),
        dm("Corporate & Financial Scandals", vc=20, **kw("finance")),
        dt("Political Scandals & Journalism", vc=5, **kw("politics")),
        dt("Cults, Scams & Fraud", vc=5, **kw("cultfraud")),
        dt("Top Rated Investigative Series", TOP, vc=20,
           withKeywords=K["journalism"] + "|" + K["cultfraud"] + "|" + K["finance"]),
        dm("Recent Investigative Releases", DATE_M, vc=5,
           withKeywords=K["journalism"] + "|" + K["cultfraud"] + "|" + K["finance"]),
        dm("Conspiracies & Cover-ups", vc=20, **kw("conspiracy")),   # ours
    ]),
]

data = load(SRC)
report = []


def rebuild(row_title, new_title, specs, emoji="🎬"):
    r_ = row(data, row_title)
    r_["title"] = new_title
    backup = {f["title"]: f for f in r_["folders"]}
    out = []
    for title, art, rails in specs:
        f = dict(backup[art]) if art else placeholder_folder(title, emoji)
        f["title"], f["sources"], f["catalogSources"] = title, rails, []
        out.append(f)
        report.append(f"{new_title} / {title}: " + " | ".join(s["title"] for s in rails))
    r_["folders"] = out


rebuild("Moods & Vibes", "Moods & Vibes", [(n, a, r) for n, a, r in MOODS])
rebuild("Based on", "Based On", BASED_ON)
rebuild("Documentaries", "Documentaries", DOCS)
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok -> {OUT}")
