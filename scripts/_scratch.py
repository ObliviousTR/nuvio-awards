import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spotlight import tmdb
os.makedirs("refs/q", exist_ok=True)
out = []
for kind in ("tv", "movie"):
    for p in (tmdb(f"/watch/providers/{kind}", watch_region="TR") or {}).get("results", []):
        out.append(f"PROVIDER {kind} | {p['provider_id']} | {p['provider_name']} | prio {p.get('display_priorities', {}).get('TR')}")
for q in ["sitcom", "british sitcom", "workplace comedy", "mockumentary", "multi-camera", "single-camera", "laugh track"]:
    for r in (tmdb("/search/keyword", query=q) or {}).get("results", [])[:5]:
        out.append(f"KW {q} | {r['id']} | {r['name']}")
for q in ["Gibi", "Behzat Ç.", "Saygı", "Kuş Uçuşu", "Bartu Ben", "Leyla ile Mecnun", "Organize İşler", "Hükümsüz", "Yeşilçam",
          "Aynen Aynen", "Prens", "Bi Kahve Söyle", "Ayak İşleri", "Kafa Sıking", "Yakamoz S-245", "Erşan Kuneri", "Zeytin Ağacı",
          "Şahsiyet", "Masum", "Persona", "Aile Saadeti", "Kızılcık Şerbeti", "Mezarlık", "Kübra", "Kulüp"]:
    for r in (tmdb("/search/tv", query=q) or {}).get("results", [])[:2]:
        d = tmdb(f"/tv/{r['id']}") or {}
        out.append(f"SHOW {q} | {d.get('name')} ({(d.get('first_air_date') or '')[:4]}) | " +
                   "; ".join(f"{n['id']}:{n['name']}" for n in d.get("networks", [])))
for kw in ("193171",):
    d = tmdb("/discover/tv", with_keywords=kw, sort_by="vote_count.desc") or {}
    out.append(f"KWTOP {kw} total {d.get('total_results')} | " + " | ".join(r["name"] for r in d.get("results", [])[:20]))
open("refs/q/out.txt", "w").write("\n".join(out))
