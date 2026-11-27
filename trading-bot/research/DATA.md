# Raw data for the research scripts

Every script reads raw data and writes caches under one folder:

- default: `~/edge-data` (Windows: `C:\Users\<you>\edge-data`)
- to move it: set the environment variable `EDGE_DATA` to another folder.

The data itself is not in git (too large). Two ways to get the NQ 1-minute history:

## A. HistData (most reliable, ~15 manual downloads)
1. Open https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/nsxusd
2. Download each year 2012 → last full year, plus the months of the current year (one zip each).
3. Put the zips, unchanged, in `edge-data/histdata/` (names like `HISTDATA_COM_ASCII_NSXUSD_M1_2015.zip`).
Same for the S&P 500: `spxusd` → `SPXUSD`.

## B. Dukascopy (automatic, slow, may be throttled)
```
python multi/duka.py USATECHIDXUSD
```
Polite (2 requests at a time, backs off on 503), resumable year by year, saves `edge-data/duka/USATECHIDXUSD.npz`.
If no HistData NSXUSD files exist, `multi/mdata.py` falls back to this Dukascopy series (CFD prices differ slightly
from HistData, so numbers will not match earlier results to the decimal).
If Dukascopy keeps refusing (it stops with a clear message), use route A.
