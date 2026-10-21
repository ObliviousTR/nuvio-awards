"""Rebuild the AIOMetadata catalog setup file (format: {version, exportedAt, catalogs}).
usage: python3 update_aio_config.py in.json out.json"""
import json, sys, datetime
from build_awards import AIO_CATALOGS

# MDBList IDs Gemini added that don't exist on MDBList (API returns an error for each)
GONE = {"mdblist.1371", "mdblist.28412", "mdblist.28415", "mdblist.14949", "mdblist.16535", "mdblist.25849"}
src = json.load(open(sys.argv[1]))
cats = [c for c in src["catalogs"] if c["id"] not in GONE]
have = {(c["id"], c["type"]) for c in cats}
added = [c for c in AIO_CATALOGS if (c["id"], c["type"]) not in have]
cats += added
keys = [(c["id"], c["type"]) for c in cats]
assert len(keys) == len(set(keys)), "duplicate catalog"
out = {"version": src["version"], "exportedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
       "catalogs": cats}
json.dump(out, open(sys.argv[2], "w"), indent=2, ensure_ascii=False)
print(f"removed {len(src['catalogs']) + len(added) - len(cats)} missing lists, added {len(added)} award lists -> {len(cats)} catalogs")
