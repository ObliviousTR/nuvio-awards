"""Shared helpers for the Nuvio collection builders."""
import datetime
import json

NOISE = "10763|10767|10766"  # News, Talk, Soap
CURRENT_YEAR = datetime.date.today().year  # the calendar: "right now" windows (last year + this year)
# the year the "of the year" rails show: the new year only from March, when it has films (builder/new_year.py)
SHOWCASE_YEAR = CURRENT_YEAR if datetime.date.today().month >= 3 else CURRENT_YEAR - 1
INTL_LANGS = "ko|es|fr|de|it|da|sv|no|pt|ja|zh|cn|hi|te|ta|tr|pl|nl|he|fa|th|ru"
POP, TOP = "popularity.desc", "vote_average.desc"
NEW = {"MOVIE": "primary_release_date.desc", "TV": "first_air_date.desc"}
AIO = "aio-metadata"  # AIOMetadata manifest id


def src(title, media, sort=POP, stype="DISCOVER", tmdb_id=None, **filters):
    """Native Nuvio TMDB source. mediaType must be upper-case (TV app uses Enum.valueOf)."""
    if media == "TV":
        filters.setdefault("withoutGenres", NOISE)
    return {
        "type": None, "genre": None, "title": title, "sortBy": sort, "tmdbId": tmdb_id,
        "addonId": None, "filters": {k: v for k, v in filters.items() if v is not None},
        "sortHow": None, "provider": "tmdb", "catalogId": None, "mediaType": media,
        "traktListId": None, "tmdbSourceType": stype,
    }


def addon_src(title, media, catalog_id, addon_id=AIO):
    """Addon catalog source. AIOMetadata catalogs hidden from home require genre 'None'.
    media: MOVIE, TV, or ALL (FlixPatrol services that only publish one combined chart)."""
    t = {"MOVIE": "movie", "TV": "series", "ALL": "all"}[media]
    return {
        "type": t, "genre": "None", "title": title, "sortBy": None, "tmdbId": None,
        "addonId": addon_id, "filters": None, "sortHow": None, "provider": "addon",
        "catalogId": catalog_id, "mediaType": None, "traktListId": None, "tmdbSourceType": None,
    }


def span(a, b=None):
    """Release-date window. Never use the `year` filter: for movies Nuvio sends TMDB `year`,
    which matches ANY release (re-releases, Blu-ray), so 2021 rails showed 1990s films."""
    b = b or a
    return {"releaseDateGte": f"{a}-01-01", "releaseDateLte": f"{b}-12-31"}


def add(f, **extra):
    """Merge filter dicts; withoutGenres values are OR-joined instead of overwritten."""
    out = dict(f)
    for k, v in extra.items():
        if v is None:
            continue
        if k == "withoutGenres" and out.get(k):
            parts = out[k].split("|") + [p for p in v.split("|") if p not in out[k].split("|")]
            out[k] = "|".join(parts)
        else:
            out[k] = v
    return out


def placeholder_folder(title, emoji):
    return {"id": "folder-new-" + "".join(ch for ch in title.lower() if ch.isalnum()),
            "title": title, "hideTitle": False, "tileShape": "LANDSCAPE", "coverImageUrl": None,
            "coverEmoji": emoji, "titleLogoUrl": None, "focusGifUrl": None,
            "focusGifEnabled": False, "heroBackdropUrl": None}


def validate(data):
    """Mirror Nuvio's validateImportModel, plus the TV app's MOVIE/TV requirement."""
    cids = set()
    for c in data:
        assert c["id"] and c["id"] not in cids and c["title"], c.get("title")
        cids.add(c["id"])
        fids = set()
        for f in c["folders"]:
            assert f["id"] and f["id"] not in fids and f["title"], (c["title"], f.get("title"))
            fids.add(f["id"])
            for s in f["sources"]:
                if s["provider"] == "tmdb":
                    assert s["tmdbSourceType"] and s["mediaType"] in ("MOVIE", "TV"), s
                    assert "year" not in (s.get("filters") or {}), ("year filter", s["title"])
                else:
                    assert s["addonId"] and s["type"] and s["catalogId"], s


def load(p):
    return json.load(open(p))


def save(data, p):
    validate(data)
    json.dump(data, open(p, "w"), ensure_ascii=False, separators=(",", ":"))


def row(data, title):
    return next(c for c in data if c["title"] == title)


# Our own addons and art (github.com/ObliviousTR/nuvio-awards)
SPOT = "community.oblivioustr.nuvio-spotlight"
SPOT_ART = "https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/main/spotlight/art"


def spot_src(title, media, cid):
    """A Spotlight-addon catalog (static files: no extras, so genre stays empty)."""
    s = addon_src(title, media, cid, addon_id=SPOT)
    s["genre"] = None
    return s


def art_folder(fid, title, path, rails, hero=True, gif=None):
    """Folder with our generated cover (text is on the image, so the title is hidden)."""
    return {"id": fid, "title": title, "hideTitle": True, "tileShape": "LANDSCAPE",
            "coverImageUrl": f"{SPOT_ART}/{path}/cover.jpg", "coverEmoji": None, "titleLogoUrl": None,
            "focusGifUrl": gif, "focusGifEnabled": bool(gif),
            "heroBackdropUrl": f"{SPOT_ART}/{path}/backdrop.jpg" if hero else None,
            "sources": rails, "catalogSources": []}
