.PHONY: test spotcheck-prod spotcheck-diag check-prod check-diag
test:
	mkdir -p .tmp/pytest .tmp/hf_cache
	TMPDIR=$(PWD)/.tmp/pytest HF_HOME=$(PWD)/.tmp/hf_cache \
	TRANSFORMERS_CACHE=$(PWD)/.tmp/hf_cache XDG_CACHE_HOME=$(PWD)/.tmp/hf_cache \
	TRANSFORMERS_OFFLINE=1 pytest

spotcheck-prod:
	DETECTOR_NO_EMBED=1 python scripts/spotcheck.py --mode production tests/fixtures/toc_heavy_sample.txt

spotcheck-diag:
	DETECTOR_NO_EMBED=1 python scripts/spotcheck.py --diagnostic tests/fixtures/toc_heavy_sample.txt

check-prod:
	mkdir -p .local_out
	DETECTOR_NO_EMBED=1 python scripts/spotcheck.py --mode production tests/fixtures/toc_heavy_sample.txt > .local_out/out.json; \
		diff -u ci/baselines/spotcheck_production.json .local_out/out.json

check-diag:
	DETECTOR_NO_EMBED=1 python scripts/test_diag_cap.py
