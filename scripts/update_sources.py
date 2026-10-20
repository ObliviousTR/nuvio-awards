"""Refresh data/sources/oscars.csv from github.com/DLu/oscar_data (updated after each ceremony).
Prints the newest ceremony before and after. Run: python3 scripts/update_sources.py"""
import csv, io, os, urllib.request

URL = "https://raw.githubusercontent.com/DLu/oscar_data/main/oscars.csv"
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sources", "oscars.csv")


def newest(text):
    return max(int(r["Ceremony"]) for r in csv.DictReader(io.StringIO(text), delimiter="\t"))


old = open(PATH, encoding="utf-8").read()
new = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8")
assert newest(new) >= newest(old), "downloaded file is older than the local copy"
open(PATH, "w", encoding="utf-8").write(new)
print(f"oscars.csv: ceremony {newest(old)} -> {newest(new)}")
