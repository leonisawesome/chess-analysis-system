# chess-analysis-system
### Spotcheck modes

- `--mode production` (default): Evaluates using full-file TOC negative logic. Baseline is CI-locked.
- `--diagnostic` (or `--mode diagnostic`): Caps early TOC negatives to `min(200, 5% of total lines)` and includes metadata:
  - `toc_diag_cap`
  - `total_lines`
  - per-item `mode`

Examples:

```
DETECTOR_NO_EMBED=1 python scripts/spotcheck.py --mode production tests/fixtures/toc_heavy_sample.txt
DETECTOR_NO_EMBED=1 python scripts/spotcheck.py --diagnostic tests/fixtures/toc_heavy_sample.txt
```
