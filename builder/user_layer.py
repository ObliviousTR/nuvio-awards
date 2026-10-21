"""Ozzy's own changes, kept on top of every build (agreed 2026-10-21).

Whatever Ozzy removes, hides, renames, reorders or adds himself in Nuvio (site or app) must survive our next
"Replace" import. Nuvio keeps no history we can read, so we compare two files:
  baseline  = the exact file we last delivered (out/delivered/baseline.json, written by deliver.sh)
  export    = his current collections, copied from the app (Collections > copy JSON) or the site
Every difference is his doing and goes into user_overrides.json, which the build applies last:
  - removed rows / folders / rails stay removed (until he adds them back: the next export shows them again)
  - changed fields (titles, art, view mode, GIF on/off, tile shape...) keep his value
  - his own order of rows, folders and rails is kept; new things we add land next to their neighbours
  - rows / folders / rails he created himself are carried over as they are
Home-screen settings (hidden rows, custom row names, GIF switches on mobile) are stored by Nuvio per collection id;
ids are fixed (apply_order.ID_TAG), so those survive imports on their own.

usage:
  python3 user_layer.py learn  baseline.json export.json     # record his changes
  python3 user_layer.py apply  in.json out.json              # build step
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "user_overrides.json")
EMPTY = {"removed": [], "fields": {}, "order": {}, "added": {}}


def jload(p, default=None):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def skey(s):
    """A rail has no id: title + what it points at."""
    if s.get("provider") == "addon":
        return f"{s.get('title')}|addon|{s.get('addonId')}|{s.get('catalogId')}|{s.get('type')}"
    return f"{s.get('title')}|{s.get('provider')}|{s.get('tmdbSourceType')}|{s.get('mediaType')}"


def tree(data):
    """{path: (node, kind, parent_path)} for rows 'r:<id>', folders 'r:<id>/f:<id>', rails '.../s:<key>'."""
    out = {}
    for c in data:
        rp = f"r:{c['id']}"
        out[rp] = (c, "row", "")
        for f in c.get("folders", []):
            fp = f"{rp}/f:{f['id']}"
            out[fp] = (f, "folder", rp)
            for s in f.get("sources", []):
                out[f"{fp}/s:{skey(s)}"] = (s, "rail", fp)
    return out


def children(node, kind):
    return node.get("folders", []) if kind == "row" else node.get("sources", []) if kind == "folder" else []


def own_fields(node, kind):
    skip = {"folders"} if kind == "row" else {"sources", "catalogSources"} if kind == "folder" else set()
    return {k: v for k, v in node.items() if k not in skip}


def child_paths(path, node, kind):
    if kind == "row":
        return [f"{path}/f:{f['id']}" for f in node.get("folders", [])]
    if kind == "folder":
        return [f"{path}/s:{skey(s)}" for s in node.get("sources", [])]
    return []


def learn(baseline, export):
    ov = jload(STORE, json.loads(json.dumps(EMPTY)))
    B, U = tree(baseline), tree(export)
    removed = set(ov["removed"])
    # removals: in what we gave him, gone from what he has now
    removed |= {p for p in B if p not in U}
    # anything present again was re-added by him
    removed = {p for p in removed if p not in U}
    # drop nested removals already covered by a removed parent
    removed = {p for p in removed if not any(p.startswith(q + "/") for q in removed if q != p)}
    ov["removed"] = sorted(removed)
    # field changes on rows and folders. Rails are kept whole (removed / added / moved), never field by field, so
    # the app's own re-serialisation of a rail can't freeze our filters. Keys the app adds with an empty value
    # (defaults) are not changes.
    for p, (n, kind, _) in U.items():
        if p in B and kind != "rail":
            bf, uf = own_fields(B[p][0], kind), own_fields(n, kind)
            diff = {k: v for k, v in uf.items() if (k in bf and bf[k] != v) or (k not in bf and v not in (None, "", False, [], {}))}
            if diff:
                ov["fields"].setdefault(p, {}).update(diff)
    # his order of rows / folders / rails, where it differs from ours
    top_b, top_u = [f"r:{c['id']}" for c in baseline], [f"r:{c['id']}" for c in export]
    if [x for x in top_u if x in top_b] != [x for x in top_b if x in top_u]:
        ov["order"][""] = top_u
    for p, (n, kind, _) in U.items():
        if kind == "rail" or p not in B:
            continue
        cu, cb = child_paths(p, n, kind), child_paths(p, B[p][0], kind)
        if [x for x in cu if x in cb] != [x for x in cb if x in cu]:
            ov["order"][p] = cu
    # things he made himself
    for p, (n, kind, parent) in U.items():
        if p not in B and (parent == "" or parent in B):
            ov["added"][p] = {"parent": parent, "node": n}
    json.dump(ov, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"learned: {len(ov['removed'])} removed, {len(ov['fields'])} changed, {len(ov['order'])} reordered, "
          f"{len(ov['added'])} added by hand")
    for p in ov["removed"]:
        print("  removed:", p)
    for p in ov["fields"]:
        print("  changed:", p, list(ov["fields"][p]))


def merge_order(current, wanted):
    """His saved order first; items he has never seen keep their place after their neighbour in our order."""
    keep = [x for x in wanted if x in current]
    for i, x in enumerate(current):
        if x in keep:
            continue
        prev = next((current[j] for j in range(i - 1, -1, -1) if current[j] in keep), None)
        keep.insert(keep.index(prev) + 1 if prev else 0, x)
    return keep


def apply(data):
    ov = jload(STORE, EMPTY)
    removed = set(ov["removed"])
    # removals
    data = [c for c in data if f"r:{c['id']}" not in removed]
    for c in data:
        rp = f"r:{c['id']}"
        c["folders"] = [f for f in c["folders"] if f"{rp}/f:{f['id']}" not in removed]
        for f in c["folders"]:
            fp = f"{rp}/f:{f['id']}"
            f["sources"] = [s for s in f["sources"] if f"{fp}/s:{skey(s)}" not in removed]
    # his own rows / folders / rails
    for p, a in ov["added"].items():
        T = tree(data)
        if p in T:
            continue
        if a["parent"] == "":
            data.append(a["node"])
        elif a["parent"] in T:
            parent, kind, _ = T[a["parent"]]
            (parent.setdefault("folders", []) if kind == "row" else parent.setdefault("sources", [])).append(a["node"])
    # field changes
    T = tree(data)
    for p, fields in ov["fields"].items():
        if p in T:
            T[p][0].update(fields)
    # order
    if "" in ov["order"]:
        by = {f"r:{c['id']}": c for c in data}
        data = [by[x] for x in merge_order(list(by), ov["order"][""])]
    T = tree(data)
    for p, wanted in ov["order"].items():
        if p not in T:
            continue
        n, kind, _ = T[p]
        lst = children(n, kind)
        by = dict(zip(child_paths(p, n, kind), lst))
        lst[:] = [by[x] for x in merge_order(list(by), wanted)]
    return data


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "learn":
        learn(json.load(open(sys.argv[2], encoding="utf-8")), json.load(open(sys.argv[3], encoding="utf-8")))
    elif mode == "apply":
        sys.path.insert(0, HERE)
        from common import save
        out = apply(json.load(open(sys.argv[2], encoding="utf-8")))
        save(out, sys.argv[3])
        ov = jload(STORE, EMPTY)
        print(f"user layer: {len(ov['removed'])} removed, {len(ov['fields'])} changed, {len(ov['order'])} reordered, "
              f"{len(ov['added'])} added by hand")
