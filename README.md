# Nuvio Awards

A small static Stremio/Nuvio addon with award-winner catalogs, newest winner first:

- **Oscars:** Supporting Actor, Supporting Actress, Documentary Feature, Visual Effects, Original Score,
  Film Editing, Production Design, Costume Design, Makeup & Hairstyling, Sound, Original Song
- **Golden Globes:** Best Director, Best Non-English Language Film
- **Festivals:** Cannes (Palme d'Or, Grand Prix, Jury Prize), Venice Golden Lion, TIFF People's Choice

Install in Nuvio with this manifest URL:

```
https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/main/manifest.json
```

## Updating

1. Add new winners to `data/additions.txt` (`catalog|year|imdb_id|tmdb_id|title`).
2. Run `python3 scripts/build.py` — it rebuilds `manifest.json` and `catalog/`.
3. Commit and push. Nuvio picks the change up on its next refresh.

The seed lists in `data/base/` were copied from public MDBList lists and extended with recent winners.
