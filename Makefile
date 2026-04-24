PYTHON ?= python3
UV ?= uv
PYSAT_PYTHON = $(UV) run --python 3.12 --with python-sat python

PY_SOURCES = \
	enc/induction_probe.py \
	enc/component_chain_classifier.py \
	enc/paired_slice_witness_sat.py \
	enc/one_connector_witness_sat.py \
	enc/bicross_probe.py \
	enc/bicross_cube_search.py \
	enc/sat_portfolio.py \
	enc/sat_utils.py \
	enc/test_component_chain_classifier.py \
	enc/test_bicross_probe.py

.PHONY: test test-sat test-all list-solvers bicross-q7-portfolio bicross-q6-frontier bicross-q6-cubes bicross-q6-hit31-proof

test:
	$(PYTHON) -m py_compile $(PY_SOURCES)
	$(PYTHON) enc/test_bicross_probe.py
	$(PYTHON) enc/test_component_chain_classifier.py

test-sat:
	$(PYSAT_PYTHON) enc/test_bicross_probe.py
	$(PYSAT_PYTHON) enc/test_component_chain_classifier.py

test-all: test test-sat

list-solvers:
	$(PYSAT_PYTHON) enc/sat_portfolio.py --list-solvers

bicross-q6-frontier:
	$(PYSAT_PYTHON) enc/sat_portfolio.py --timeout 300 -- \
		python enc/bicross_probe.py \
		-m 6 \
		--sat-pairs-hit-at-least 29 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half

bicross-q6-cubes:
	$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 8 \
		--cube-mode spread \
		--shuffle-cubes \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-q6-hit31-proof:
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 31 \
		--cube-depth 8 \
		--cube-mode prefix \
		--jobs 11 \
		--batch-size 4 \
		--conflict-budget 20000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 31 \
		--cube-depth 8 \
		--cube-mode prefix \
		--only-cube-indexes 0,1,4,5,12,13,28,29,31 \
		--jobs 9 \
		--batch-size 1 \
		--conflict-budget 500000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 31 \
		--cube-depth 8 \
		--cube-mode prefix \
		--only-cube-indexes 12,29 \
		--jobs 2 \
		--batch-size 1 \
		--conflict-budget 2000000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-q7-portfolio:
	$(PYSAT_PYTHON) enc/sat_portfolio.py --timeout 600 -- \
		python enc/bicross_probe.py \
		-m 7 \
		--sat-pairs-hit-at-least 64 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half
