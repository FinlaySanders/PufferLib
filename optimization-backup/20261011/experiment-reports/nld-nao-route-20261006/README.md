# NAO route analysis

This is a metadata-only pass over the standalone NAO xlog archive. It does not
include ttyrecs or permit reconstructing action order or the kit used at a
milestone. The untouched archive is `nld-nao_xlogfiles.zip`; `outputs/REPORT.md`
contains the findings and caveats.

Run once in order with the local `.venv/bin/python`:

1. `01_ingest.py` parses 3.6 and 3.4.3 xlogs into `outputs/nld_metadata.sqlite`.
2. `02_clean.py` creates `outputs/route.duckdb` and `games_clean.parquet`.
3. `03_skill.py` adds prior-history bands and `games_skill.parquet`.
4. `04_describe.py` writes role, milestone, hazard, death and plot outputs.
5. `05_associations.py` writes descriptive milestone associations.
6. `06_report.py` validates decoding and writes `outputs/REPORT.md`.

The scripts have fixed random seeds. To rebuild, move aside or remove only the
generated SQLite/DuckDB/CSV/Parquet files; keep the original archive. The main
3.6 cohort includes xlogs through 2022 and is larger than NLD's recorded-game
subset.
