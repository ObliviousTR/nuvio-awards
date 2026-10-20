# Nuvio Awards

A small static Stremio/Nuvio addon with award catalogs, newest first (48 catalogs):

- **Oscars:** every major category's winners, nominees for Picture / Director / the four acting categories /
  International / Animated, all of the latest ceremony's nominees, and all winning films
- **Golden Globes:** Picture (Drama, Musical or Comedy), Drama / Comedy / Limited Series, Director, Non-English Film
- **BAFTA:** Best Film · **Emmys:** Drama, Comedy, Limited Series
- **Festivals:** Cannes (Palme d'Or, Grand Prix, Jury Prize), Venice, Berlinale, Sundance, TIFF

Install in Nuvio with this manifest URL:

```
https://raw.githubusercontent.com/ObliviousTR/nuvio-awards/main/manifest.json
```

## Updating

- **Oscars:** `python3 scripts/update_sources.py` pulls the latest `oscars.csv` from
  [DLu/oscar_data](https://github.com/DLu/oscar_data) (all nominations with IMDb ids).
- **Everything else:** add new winners to `data/additions.txt` (`catalog|year|imdb_id|tmdb_id|title`).
- Then run `python3 scripts/build.py` (rebuilds `manifest.json` and `catalog/`), commit and push.
  Nuvio picks the change up on its next refresh.

Seed lists in `data/base/` were copied from public MDBList lists and extended with recent winners.
