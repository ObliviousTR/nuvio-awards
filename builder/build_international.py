"""International Cinema: 9 single countries + 6 regional groups (agreed 2026-10-20), native TMDB rails.

Every folder starts with Kaptain's six-rail country line-up turned into movie / series pairs:
  Popular, Top Rated & Acclaimed, Recent & New, Action/Crime/Thrillers, Drama/Romance/Comedy Hits.
Regional groups then get one Popular rail per member country so each country can be browsed on its own.
Countries with a strong animation scene (Japan, China, France) get dedicated animation rails at the end;
every other rail excludes animation. Documentaries, reality and soap/talk/news stay out (scripted only;
reality lives in the Reality TV row).
"""
import sys
from common import src, load, save, row, placeholder_folder, NOISE, POP, TOP, NEW

SRC, OUT, REPORT = sys.argv[1], sys.argv[2], sys.argv[3]

NO_M = "16|99"
NO_T = "16|99|10764|" + NOISE

FLOORS = {  # vote-count floors (movie, series)
    "big":   dict(pop=(50, 20), top=(500, 150), new=(5, 3), hits=(50, 20)),
    "mid":   dict(pop=(30, 10), top=(200, 50), new=(5, 3), hits=(30, 10)),
    "small": dict(pop=(15, 10), top=(100, 30), new=(3, 2), hits=(15, 5)),
    "thin":  dict(pop=(25, 40), top=(100, 40), new=(5, 10), hits=(25, 30)),  # lots of local filler TV
}
# Groups where popularity alone surfaces filler (direct-to-streaming erotica, sitcoms, soaps) get a
# vote-average floor on every rail that isn't already sorted by rating.
AVG = {"Southeast Asia": 6.5, "Middle East": 6.0, "Latin America": 6.0, "Central & Eastern Europe": 6.5}
ACTION = ({"withGenres": "28|80|53"}, {"withGenres": "10759|80|9648"})
DRAMA = ({"withGenres": "18|10749|35"}, {"withGenres": "18|35"})


def L(lang, country=None):
    return {k: v for k, v in (("withOriginalLanguage", lang), ("withOriginCountry", country)) if v}


def core(adj, region, size, avg=None):
    fl = FLOORS[size]
    q = {"voteAverageGte": avg} if avg else {}
    m = lambda t, sort, vc, **f: src(t, "MOVIE", sort, voteCountGte=vc, withoutGenres=NO_M, **region, **f)
    s = lambda t, sort, vc, **f: src(t, "TV", sort, voteCountGte=vc, withoutGenres=NO_T, **region, **f)
    return [
        m(f"Popular {adj} Movies", POP, fl["pop"][0], **q),
        s(f"Popular {adj} Series & Dramas", POP, fl["pop"][1], **q),
        m(f"Top Rated & Acclaimed {adj} Movies", TOP, fl["top"][0]),
        s(f"Top Rated & Acclaimed {adj} Series", TOP, fl["top"][1]),
        m(f"Recent & New {adj} Movies", NEW["MOVIE"], fl["new"][0], **q),
        s(f"Recent & New {adj} Series", NEW["TV"], fl["new"][1], **q),
        m(f"{adj} Action, Crime & Thrillers · Movies", POP, fl["hits"][0], **ACTION[0], **q),
        s(f"{adj} Action, Crime & Thrillers · Series", POP, fl["hits"][1], **ACTION[1], **q),
        m(f"{adj} Drama, Romance & Comedy Hits · Movies", POP, fl["hits"][0], **DRAMA[0], **q),
        s(f"{adj} Drama, Romance & Comedy Hits · Series", POP, fl["hits"][1], **DRAMA[1], **q),
    ]


def members(countries, avg=None):
    """Group folders: one Popular rail per member country (series only where the country has a TV scene)."""
    out = []
    q = {"voteAverageGte": avg} if avg else {}
    vm, vt = (25, 15) if avg else (10, 5)
    for adj, region, series in countries:
        out.append(src(f"Popular {adj} Movies", "MOVIE", POP, voteCountGte=vm, withoutGenres=NO_M, **region, **q))
        if series:
            out.append(src(f"Popular {adj} Series", "TV", POP, voteCountGte=vt, withoutGenres=NO_T, **region, **q))
    return out


def toons(label, region, series=True, top_vc=(100, 30)):
    """Dedicated animation rails for countries where animation is a big part of the output."""
    m = dict(withGenres="16", **region)
    s = dict(withGenres="16", withoutGenres="10762|" + NOISE, **region)
    out = [src(f"Popular {label} Movies", "MOVIE", POP, voteCountGte=20, **m)]
    if series:
        out.append(src(f"Popular {label} Series", "TV", POP, voteCountGte=10, **s))
    out.append(src(f"Top Rated {label} Movies", "MOVIE", TOP, voteCountGte=top_vc[0], **m))
    if series:
        out.append(src(f"Top Rated {label} Series", "TV", TOP, voteCountGte=top_vc[1], **s))
    return out


# (folder title, adjective, Kaptain art folder or emoji, region filters, floor size, extra rails)
FOLDERS = [
    ("Türkiye", "Turkish", "Turkish Cinema", L("tr"), "small", []),
    ("South Korea", "Korean", "Korean Cinema", L("ko"), "big", []),
    ("Japan", "Japanese", "Japanese Cinema", L("ja"), "big", toons("Anime", L("ja"), top_vc=(300, 150))),
    ("Greater China", "Chinese", "Chinese Cinema", L("zh|cn", "CN|HK|TW"), "mid",
     members([("Mainland Chinese", L("zh", "CN"), True), ("Hong Kong", L("cn|zh", "HK"), False),
              ("Taiwanese", L("zh", "TW"), True)])
     + toons("Chinese Animation", L("zh", "CN"), top_vc=(50, 20))),
    ("Southeast Asia", "Southeast Asian", "Southeast Asian Cinema",
     L("th|id|tl|vi|ms", "TH|ID|PH|VN|MY"), "small",
     members([("Thai", L("th", "TH"), True), ("Indonesian", L("id", "ID"), True),
              ("Filipino", L(None, "PH"), True), ("Vietnamese", L("vi", "VN"), False),
              ("Malaysian", L(None, "MY"), False)], avg=AVG["Southeast Asia"])),
    ("India", "Indian", "Indian Cinema", L("hi|te"), "mid", []),
    ("Middle East", "Middle Eastern", "Middle Eastern Cinema",
     L("fa|he|ar", "IR|IL|LB|PS|EG|SA|AE|JO|IQ|SY|TN|MA"), "small",
     members([("Iranian", L("fa", "IR"), False), ("Israeli", L("he", "IL"), True),
              ("Arab", L("ar"), True)], avg=AVG["Middle East"])),
    ("UK & Ireland", "British & Irish", "British Cinema", L("en", "GB|IE"), "big",
     members([("Irish", L("en|ga", "IE"), True)])
     + toons("British & Irish Animation", L("en", "GB|IE"), series=False, top_vc=(100, 0))),
    ("France", "French", "French Cinema", L("fr", "FR"), "big",
     toons("French Animation", L("fr", "FR"), series=False, top_vc=(100, 0))),
    ("Spain", "Spanish", "Spanish Cinema", L("es|ca|eu|gl", "ES"), "big", []),
    ("Italy", "Italian", "Italian Cinema", L("it", "IT"), "big", []),
    ("Germany", "German", "German Cinema", L("de", "DE|AT|CH"), "mid", []),
    ("Nordic Noir", "Nordic", "Nordic Cinema", L("da|sv|no|fi|is", "DK|SE|NO|FI|IS"), "small",
     members([("Danish", L("da", "DK"), True), ("Swedish", L("sv", "SE"), True),
              ("Norwegian", L("no", "NO"), True), ("Finnish", L("fi", "FI"), True),
              ("Icelandic", L("is", "IS"), True)])),
    ("Central & Eastern Europe", "Eastern European", "🏰",
     L("pl|cs|hu|ro|el|sr|hr|bs|sl|sk|bg|ru|uk",
       "PL|CZ|HU|RO|GR|RS|HR|BA|SI|SK|BG|RU|UA"), "thin",
     members([("Polish", L("pl", "PL"), True), ("Czech", L("cs", "CZ"), True),
              ("Hungarian", L("hu", "HU"), False), ("Romanian", L("ro", "RO"), False),
              ("Greek", L("el", "GR"), False), ("Russian & Soviet", L("ru"), True),
              ("Balkan", L("sr|hr|bs|sl", "RS|HR|BA|SI"), False)], avg=AVG["Central & Eastern Europe"])),
    ("Latin America", "Latin American", "Latin American Cinema",
     L("es|pt", "MX|AR|BR|CO|CL|PE|UY"), "mid",
     members([("Mexican", L("es", "MX"), True), ("Argentine", L("es", "AR"), True),
              ("Brazilian", L("pt", "BR"), True), ("Colombian", L("es", "CO"), True),
              ("Chilean", L("es", "CL"), False)], avg=AVG["Latin America"])),
]


data = load(SRC)
intl = row(data, "International Cinema")
kaptain = {f["title"]: f for f in intl["folders"]}
folders, report = [], []
for title, adj, art, region, size, extra in FOLDERS:
    if art in kaptain:  # keep Kaptain's artwork, rename to the agreed title
        f = {k: v for k, v in kaptain[art].items() if k not in ("sources", "catalogSources")}
        f["title"] = title
    else:
        f = placeholder_folder(title, art)
    f["sources"], f["catalogSources"] = core(adj, region, size, AVG.get(title)) + extra, []
    folders.append(f)
    report.append(f"## {title} ({len(f['sources'])} rails)")
    report += [f"   {i+1:2}. {s['title']}" for i, s in enumerate(f["sources"])]
intl["folders"] = folders
save(data, OUT)
open(REPORT, "w").write("\n".join(report) + "\n")
print(f"ok: {len(folders)} folders -> {OUT}")
