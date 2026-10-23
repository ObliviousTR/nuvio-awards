"""Pictures for the My Simkl Favourites card, from Ozzy's own Simkl lists (needs simkl/token.enc from the Simkl link
workflow, plus SIMKL_CLIENT_ID, SIMKL_CLIENT_SECRET, MDBLIST_API_KEY and TMDB_API_KEY; refreshes and re-saves the tokens). Writes simkl_1..3.jpg and their names to list.txt:
simkl_1 / simkl_2 = the two shows he watched most recently, simkl_3 = the newest plan-to-watch title.
usage: python3 scripts/simkl_favs.py OUT_DIR
"""
import io, json, os, sys, urllib.request

from PIL import Image

TMDB = os.environ["TMDB_API_KEY"].strip()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simkl_auth as S


def items(tok, kind, status):
    d = S.get(f"/sync/all-items/{kind}/{status}", tok)
    out = []
    for it in (d.get(kind) if isinstance(d, dict) else None) or []:
        m = it.get("show") or it.get("movie") or {}
        tid = (m.get("ids") or {}).get("tmdb")
        if tid:
            out.append({"tmdb": int(tid), "kind": "tv" if kind != "movies" else "movie", "title": m.get("title", ""),
                        "year": m.get("year") or "", "when": it.get("last_watched_at") or it.get("added_to_watchlist_at") or ""})
    return sorted(out, key=lambda x: x["when"], reverse=True)


def backdrop(kind, tid):
    u = f"https://api.themoviedb.org/3/{kind}/{tid}/images?api_key={TMDB}&include_image_language=null,en"
    d = json.loads(urllib.request.urlopen(u, timeout=60).read())
    bs = [b for b in d.get("backdrops", []) if not b.get("iso_639_1")] or d.get("backdrops", [])
    if not bs:
        return None
    b = max(bs, key=lambda b: (b.get("vote_average", 0), b.get("width", 0)))
    raw = urllib.request.urlopen("https://image.tmdb.org/t/p/w1280" + b["file_path"], timeout=60).read()
    return Image.open(io.BytesIO(raw)).convert("RGB")


def main(out):
    os.makedirs(out, exist_ok=True)
    tok = S.access_token()
    watching = items(tok, "shows", "watching") + items(tok, "anime", "watching")
    watching.sort(key=lambda x: x["when"], reverse=True)
    plan = items(tok, "shows", "plantowatch") + items(tok, "movies", "plantowatch") + items(tok, "anime", "plantowatch")
    plan.sort(key=lambda x: x["when"], reverse=True)
    picks, seen = [], set()
    for pool, n in ((watching, 2), (plan, 1), (watching + plan, 3)):
        for it in pool:
            if len(picks) >= 3 or n <= 0:
                break
            if it["tmdb"] in seen:
                continue
            img = backdrop(it["kind"], it["tmdb"])
            if img is None:
                continue
            seen.add(it["tmdb"])
            picks.append((it, img))
            n -= 1
    lst = os.path.join(out, "list.txt")
    keep = [l for l in open(lst, encoding="utf-8")] if os.path.exists(lst) else []
    keep = [l for l in keep if not l.startswith("simkl_")]
    for i, (it, img) in enumerate(picks, 1):
        img.save(os.path.join(out, f"simkl_{i}.jpg"), quality=92)
        keep.append(f"simkl_{i}\t{it['title']}\t{it['year']}\n")
    open(lst, "w", encoding="utf-8").writelines(keep)
    print("My Simkl:", " | ".join(f"{it['title']} ({it['year']})" for it, _ in picks))


if __name__ == "__main__":
    main(sys.argv[1])
