# Nuvio collection builder

Builds Ozzy's Nuvio collections JSON (import in Nuvio with "Replace"). `bash run.sh <name>.json` writes `out/<name>.json`.
No API keys live here: the TMDB key is read from `~/.tmdbkey` only by helper scripts that query TMDB.

- `run.sh` – the pipeline (one build_*.py per row, then language / animation policies, `apply_order.py`, `user_layer.py`)
- `apply_order.py` – agreed row and folder order; row ids are fixed (`ID_TAG`)
- `user_layer.py` + `user_overrides.json` – Ozzy's own changes in Nuvio (removed, renamed, reordered, added), kept
  on top of every build. Learn them from his export: `python3 user_layer.py learn out/delivered/baseline.json export.json`
- `deliver.sh <name>.json` – marks a build as delivered (new baseline for the next comparison)
