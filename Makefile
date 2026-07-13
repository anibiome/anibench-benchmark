PYTHON ?= python
SOURCE_DATE_EPOCH ?= 1783900800
export SOURCE_DATE_EPOCH

.PHONY: test lint metadata level1-authority web-test protocol-smoke verify-corpus-fields package studio-e2e \
	verify-distributions verify public-export release-candidate paper serve-studio clean

test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src $(PYTHON) -m pytest -q

lint:
	PYTHONPATH=src $(PYTHON) -m ruff check src tests scripts

metadata:
	$(PYTHON) scripts/verify_release_metadata.py --pretty

level1-authority:
	PYTHONPATH=src $(PYTHON) scripts/build_level1_target_v3.py --check

web-test:
	node --test web/v2.test.js

protocol-smoke:
	PYTHONPATH=src $(PYTHON) -m anibench.cli v2-protocol-capacity \
		web/protocol-capacity-example.json --out /tmp/anibench-protocol-capacity.json --pretty
	$(PYTHON) -c "import json, pathlib; base=json.loads(pathlib.Path('web/protocol-capacity-example.json').read_text()); request=json.loads(pathlib.Path('web/optimizer-protocol-example.json').read_text()); request['base_protocol']=base; pathlib.Path('/tmp/anibench-optimizer-request.json').write_text(json.dumps(request))"
	PYTHONPATH=src $(PYTHON) -m anibench.cli v2-optimize-protocol \
		/tmp/anibench-optimizer-request.json --out /tmp/anibench-optimizer-result.json --pretty

verify-corpus-fields:
	$(PYTHON) scripts/verify_external_field_receipts.py --pretty

package:
	rm -rf build dist
	$(PYTHON) -m build
	$(PYTHON) scripts/verify_distribution_boundary.py dist/*.whl dist/*.tar.gz --pretty

studio-e2e: package
	$(PYTHON) scripts/verify_installed_studio.py \
		--wheel dist/*.whl --receipt dist/INSTALLED_STUDIO_E2E_RECEIPT.json --pretty

verify-distributions:
	@test -n "$(DISTRIBUTIONS)" || (echo "Set DISTRIBUTIONS to wheel/sdist paths" && exit 2)
	$(PYTHON) scripts/verify_distribution_boundary.py $(DISTRIBUTIONS) --pretty

verify: lint metadata level1-authority test web-test protocol-smoke verify-corpus-fields studio-e2e

public-export:
	@test -n "$(OUTPUT)" || (echo "Set OUTPUT to a new directory outside this repository" && exit 2)
	PYTHONPATH=src $(PYTHON) scripts/export_public_repository.py \
		--output "$(OUTPUT)" --source-date-epoch "$(SOURCE_DATE_EPOCH)" --init-git

release-candidate: verify

paper:
	$(PYTHON) paper/v2/build_method_figures.py \
		--out-dir paper/v2/figures \
		--source-date-epoch "$(SOURCE_DATE_EPOCH)"
	$(PYTHON) scripts/build_docx_package.py \
		--source paper/v2/AniBench_v2_benchmark_protocol.md \
		--out-dir paper/build/v2 \
		--stem AniBench_v2_benchmark_protocol \
		--title "AniBench: reconstructive and causal capacity of human trials" \
		--preset narrative_proposal \
		--header "ANIBENCH / BENCHMARK PROTOCOL / V2" \
		--footer "ANI BIOME PBC / OPEN-SOURCE RELEASE CANDIDATE" \
		--figures-dir paper/v2/figures \
		--figures-already-inline \
		--source-date-epoch "$(SOURCE_DATE_EPOCH)"

serve-studio:
	PYTHONPATH=src $(PYTHON) -m anibench.cli studio

clean:
	rm -rf .pytest_cache .ruff_cache .coverage build dist *.egg-info src/*.egg-info
