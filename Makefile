.PHONY: test
test:
	mkdir -p .tmp/pytest .tmp/hf_cache
	TMPDIR=$(PWD)/.tmp/pytest HF_HOME=$(PWD)/.tmp/hf_cache \
	TRANSFORMERS_CACHE=$(PWD)/.tmp/hf_cache XDG_CACHE_HOME=$(PWD)/.tmp/hf_cache \
	TRANSFORMERS_OFFLINE=1 pytest

