"""Build the static Stremio addon (manifest + catalogs) from data/.

data/base/<catalog>.txt   imdb|tmdb|year|title   (seed lists, copied from MDBList)
data/additions.txt        catalog|year|imdb|tmdb|title   (winners added since)
data/catalogs.json        catalog ids, display names and order

Every catalog is newest winner first. Pagination: the whole list is in the first page; skip=N files
return the rest so clients that page by `skip` still work. Run: python3 scripts/build.py
"""
import json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
VERSION = "1.0.0"


def read_base(cid):
    rows = []
    for line in open(D("data", "base", f"{cid}.txt"), encoding="utf-8"):
        imdb, tmdb, year, title = line.rstrip("\n").split("|", 3)
        rows.append(dict(imdb=imdb, tmdb=int(tmdb), year=int(year), title=title))
    return rows


def read_additions():
    add = {}
    for line in open(D("data", "additions.txt"), encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        cid, year, imdb, tmdb, title = line.rstrip("\n").split("|", 4)
        add.setdefault(cid, []).append(dict(imdb=imdb, tmdb=int(tmdb), year=int(year), title=title))
    return add


def meta(r):
    return {"id": r["imdb"], "type": "movie", "name": r["title"], "releaseInfo": str(r["year"]),
            "poster": f"https://images.metahub.space/poster/medium/{r['imdb']}/img",
            "posterShape": "poster"}


def main():
    cats = json.load(open(D("data", "catalogs.json"), encoding="utf-8"))
    additions = read_additions()
    unknown = set(additions) - {c["id"] for c in cats}
    assert not unknown, f"additions for unknown catalogs: {unknown}"
    out = D("catalog")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(D("catalog", "movie"))
    summary = []
    for c in cats:
        rows = read_base(c["id"]) + additions.get(c["id"], [])
        seen, uniq = set(), []
        for r in rows:  # one entry per film per catalog
            if r["imdb"] not in seen:
                seen.add(r["imdb"]); uniq.append(r)
        uniq.sort(key=lambda r: -r["year"])  # stable: keeps list order inside a year
        metas = [meta(r) for r in uniq]
        base = D("catalog", "movie", c["id"])
        json.dump({"metas": metas}, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False)
        os.makedirs(base)
        for skip in sorted(set(list(range(10, len(metas) + 1, 10)) + [len(metas)])):
            json.dump({"metas": metas[skip:]}, open(os.path.join(base, f"skip={skip}.json"), "w", encoding="utf-8"),
                      ensure_ascii=False)
        summary.append((c["id"], len(metas), uniq[0]["year"], uniq[0]["title"]))
    manifest = {
        "id": "community.oblivioustr.nuvio-awards",
        "version": VERSION,
        "name": "Nuvio Awards",
        "description": "Award winner lists (Oscars, Golden Globes, Cannes, Venice, TIFF), newest winner first.",
        "resources": ["catalog"],
        "types": ["movie"],
        "idPrefixes": ["tt"],
        "catalogs": [{"type": "movie", "id": c["id"], "name": c["name"]} for c in cats],
        "behaviorHints": {"configurable": False, "configurationRequired": False},
    }
    json.dump(manifest, open(D("manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for s in summary:
        print(f"{s[0]:26} {s[1]:4} items   newest: {s[2]} {s[3]}")


if __name__ == "__main__":
    main()
