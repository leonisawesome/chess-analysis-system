#!/usr/bin/env bash
set -euo pipefail

# Run production mode on the fixture and compare to baseline
mkdir -p .local_out
DETECTOR_NO_EMBED=1 python scripts/spotcheck.py --mode production tests/fixtures/toc_heavy_sample.txt > .local_out/out.json

echo "Comparing production output to baseline..."
diff -u ci/baselines/spotcheck_production.json .local_out/out.json
echo "Spotcheck production invariance verified."

