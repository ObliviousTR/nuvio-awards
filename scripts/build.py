"""Build the static Stremio addon (manifest.json + catalog/) from data/.

Sources
  data/sources/oscars.csv   Academy Awards, every nomination with IMDb ids (github.com/DLu/oscar_data);
                            refresh with scripts/update_sources.py after each ceremony.
  data/base/<catalog>.txt   other awards: imdb|tmdb|year|title, newest winner first
  data/additions.txt        winners added since: catalog|year|imdb|tmdb|title (tmdb may be empty)
  data/catalogs.json        catalog ids, names, types and how each one is built

Oscar catalog modes: winners (newest ceremony first), nominees (newest ceremony first, winner first inside a
ceremony), latest (every film nominated at the most recent ceremony, Best Picture first).
List catalogs: order "list" keeps the file order (newest win first, needed for series whose first-air year
says nothing about the award year); order "year" sorts by year. Additions always go on top.
Paging: 100 items per page; catalog/<type>/<id>/skip=N.json serves the next pages.
Run: python3 scripts/build.py
"""
import csv, json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
VERSION = "2.0.0"
PAGE = 100


def oscar_rows():
    rows = []
    for r in csv.DictReader(open(D("data", "sources", "oscars.csv"), encoding="utf-8"), delimiter="\t"):
        ids, films = r["FilmId"].split("|"), r["Film"].split("|")
        for i, imdb in enumerate(ids):
            if not imdb.startswith("tt"):
                continue
            rows.append(dict(ceremony=int(r["Ceremony"]), year=int(r["Year"][:4]), cat=r["CanonicalCategory"],
                             win=r["Winner"] == "True", imdb=imdb, title=films[i] if i < len(films) else films[0]))
    return rows


def oscar_catalog(c, rows, cat_map):
    cats = [x for key in c["categories"] for x in cat_map[key]]
    prio = {x: i for i, x in enumerate(cats)}
    sel = [r for r in rows if r["cat"] in prio]
    if c["mode"] == "winners":
        sel = [r for r in sel if r["win"]]
        sel.sort(key=lambda r: -r["ceremony"])
    elif c["mode"] == "nominees":
        sel.sort(key=lambda r: (-r["ceremony"], not r["win"]))
    elif c["mode"] == "latest":
        last = max(r["ceremony"] for r in sel)
        sel = [r for r in sel if r["ceremony"] == last]
        sel.sort(key=lambda r: (prio[r["cat"]], not r["win"]))
    return [dict(imdb=r["imdb"], year=r["year"], title=r["title"]) for r in sel]


def list_catalog(c, additions):
    base = []
    for line in open(D("data", "base", f"{c['id']}.txt"), encoding="utf-8"):
        imdb, tmdb, year, title = line.rstrip("\n").split("|", 3)
        base.append(dict(imdb=imdb, year=int(year), title=title))
    if c.get("order") == "year":
        rows = additions.get(c["id"], []) + base
        rows.sort(key=lambda r: -r["year"])
    else:
        rows = sorted(additions.get(c["id"], []), key=lambda r: -r["year"]) + base
    return rows


def read_additions():
    add = {}
    for line in open(D("data", "additions.txt"), encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        cid, year, imdb, tmdb, title = line.rstrip("\n").split("|", 4)
        add.setdefault(cid, []).append(dict(imdb=imdb, year=int(year), title=title))
    return add


def meta(r, typ):
    return {"id": r["imdb"], "type": typ, "name": r["title"], "releaseInfo": str(r["year"]),
            "poster": f"https://images.metahub.space/poster/medium/{r['imdb']}/img", "posterShape": "poster",
            # a full-size landscape image: Nuvio's home hero uses it instead of blowing the poster up
            "background": f"https://images.metahub.space/background/medium/{r['imdb']}/img"}


def write_pages(typ, cid, metas):
    base = D("catalog", typ, cid)
    json.dump({"metas": metas[:PAGE]}, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs(base, exist_ok=True)
    for skip in range(PAGE, len(metas) + PAGE, PAGE):
        json.dump({"metas": metas[skip:skip + PAGE]}, open(os.path.join(base, f"skip={skip}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False)


def main():
    cfg = json.load(open(D("data", "catalogs.json"), encoding="utf-8"))
    additions = read_additions()
    ids = {c["id"] for c in cfg["catalogs"]}
    assert not set(additions) - ids, f"additions for unknown catalogs: {set(additions) - ids}"
    rows = oscar_rows()
    last = max(r["ceremony"] for r in rows)
    ceremony_year = max(r["year"] for r in rows if r["ceremony"] == last) + 1
    shutil.rmtree(D("catalog"), ignore_errors=True)
    manifest_catalogs = []
    for c in cfg["catalogs"]:
        items = oscar_catalog(c, rows, cfg["oscar_categories"]) if c["source"] == "oscars" else list_catalog(c, additions)
        seen, uniq = set(), []
        for r in items:  # one entry per title per catalog (the most recent one)
            if r["imdb"] not in seen:
                seen.add(r["imdb"]); uniq.append(r)
        os.makedirs(D("catalog", c["type"]), exist_ok=True)
        write_pages(c["type"], c["id"], [meta(r, c["type"]) for r in uniq])
        name = c["name"].format(ceremony_year=ceremony_year)
        # folder-only: a required search + folder extra keeps it out of Nuvio's Discover menu, Home and search
        manifest_catalogs.append({"type": c["type"], "id": c["id"], "name": name, "extra": [{"name": "search", "isRequired": True}, {"name": "folder", "isRequired": True}]})
        print(f"{c['id']:34} {len(uniq):5}  newest: {uniq[0]['year']} {uniq[0]['title']}")
    manifest = {
        "id": "community.oblivioustr.nuvio-awards",
        "version": VERSION,
        "name": "Nuvio Awards",
        "description": "Award winners and nominees (Oscars, Golden Globes, BAFTA, Emmys, Cannes, Venice, Berlinale, Sundance, TIFF), newest first.",
        "resources": ["catalog"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt"],
        "catalogs": manifest_catalogs,
        "behaviorHints": {"configurable": False, "configurationRequired": False},
    }
    json.dump(manifest, open(D("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
