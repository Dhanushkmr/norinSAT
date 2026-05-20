PYTHON ?= python3
UV ?= uv
PYSAT_PYTHON = $(UV) run --python 3.12 --with python-sat python
JOBS ?= 0

PY_SOURCES = \
	enc/induction_probe.py \
	enc/component_chain_classifier.py \
	enc/paired_slice_witness_sat.py \
	enc/one_connector_witness_sat.py \
	enc/bicross_probe.py \
	enc/bicross_cube_search.py \
	enc/bicross_adaptive_cube_search.py \
	enc/bicross_extremal_analysis.py \
	enc/bad_set_structure.py \
	enc/bicross_frontier_construction.py \
	enc/group_structure_probe.py \
	enc/bicross_lift_search.py \
	enc/sat_portfolio.py \
	enc/sat_utils.py \
	enc/test_sat_portfolio.py \
	enc/test_component_chain_classifier.py \
	enc/test_bicross_adaptive_cube_search.py \
	enc/test_bicross_cube_search.py \
	enc/test_bicross_extremal_analysis.py \
	enc/test_bicross_frontier_construction.py \
	enc/test_group_structure_probe.py \
	enc/test_bicross_probe.py

.PHONY: test test-sat test-all list-solvers group-structure-probes group-affine-falsification bicross-quantitative-construction bicross-good-count-falsification bicross-bad-structure bicross-branch-samples bicross-branch-falsification bicross-branch-cubes bicross-branch-adaptive-cubes bicross-extremal-shapes bicross-no-cell-frontier bicross-dichotomy-checks bicross-q7-portfolio bicross-q7-full-cubes bicross-q7-lift-search bicross-q6-frontier bicross-q6-cubes bicross-q6-hit31-proof bicross-q6-hit30-proof bicross-q6-hit29-proof

test:
	$(PYTHON) -m py_compile $(PY_SOURCES)
	$(PYTHON) enc/test_bicross_probe.py
	$(PYTHON) enc/test_bicross_adaptive_cube_search.py
	$(PYTHON) enc/test_bicross_cube_search.py
	$(PYTHON) enc/test_bicross_extremal_analysis.py
	$(PYTHON) enc/test_bicross_frontier_construction.py
	$(PYTHON) enc/test_group_structure_probe.py
	$(PYTHON) enc/test_sat_portfolio.py
	$(PYTHON) enc/test_component_chain_classifier.py

test-sat:
	$(PYSAT_PYTHON) enc/test_bicross_probe.py
	$(PYSAT_PYTHON) enc/test_bicross_adaptive_cube_search.py
	$(PYSAT_PYTHON) enc/test_bicross_cube_search.py
	$(PYSAT_PYTHON) enc/test_bicross_extremal_analysis.py
	$(PYSAT_PYTHON) enc/test_bicross_frontier_construction.py
	$(PYSAT_PYTHON) enc/test_group_structure_probe.py
	$(PYSAT_PYTHON) enc/test_sat_portfolio.py
	$(PYSAT_PYTHON) enc/test_component_chain_classifier.py

test-all: test test-sat

list-solvers:
	$(PYSAT_PYTHON) enc/sat_portfolio.py --list-solvers

group-structure-probes:
	$(PYTHON) enc/group_structure_probe.py -m 3 --enumerate --max-edges 12 --stop-on-failure
	$(PYTHON) enc/group_structure_probe.py -m 6 --paired-construction --show-first
	$(PYSAT_PYTHON) enc/group_structure_probe.py \
		-m 6 \
		--sat-frontier \
		--hit-bound 28 \
		--models 50 \
		--exact-hit \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--stop-on-failure

group-affine-falsification:
	$(PYSAT_PYTHON) enc/group_structure_probe.py \
		-m 3 \
		--sat-no-affine-survivor
	$(PYSAT_PYTHON) enc/group_structure_probe.py \
		-m 4 \
		--sat-no-affine-survivor \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 12
	$(PYSAT_PYTHON) enc/group_structure_probe.py \
		-m 5 \
		--sat-no-affine-survivor \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/group_structure_probe.py \
		-m 6 \
		--sat-no-affine-cubes \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 0-3,6-7,14-15,30-31,66-71,76-79,92-95,125,198-203,206-207,216-219,222-223,249,251,462-467,470-471,478-479,497,499,503 \
		--jobs $(JOBS) \
		--batch-size 2 \
		--conflict-budget 200000 \
		--stop-on-sat \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-quantitative-construction:
	$(PYTHON) enc/bicross_frontier_construction.py -m 8 --show-components
	$(PYTHON) enc/bicross_frontier_construction.py -m 12

bicross-good-count-falsification:
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 6 \
		--sat-bad-at-least 38 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-bad-structure:
	$(PYTHON) enc/bad_set_structure.py \
		-m 6 \
		--paired-construction \
		--show-cell-details
	$(PYSAT_PYTHON) enc/bad_set_structure.py \
		-m 6 \
		--sat-bad-at-least 38 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--show-cell-details

bicross-branch-samples:
	$(PYSAT_PYTHON) enc/bicross_extremal_analysis.py \
		-m 5 \
		--hit-bound 12 \
		--models 20 \
		--exact-hit \
		--forbid-cell-pairs \
		--summary-only \
		--signature-limit 3
	$(PYSAT_PYTHON) enc/bicross_extremal_analysis.py \
		-m 6 \
		--hit-bound 28 \
		--models 20 \
		--exact-hit \
		--summary-only \
		--signature-limit 3 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-branch-falsification:
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 4 \
		--sat-pairs-hit-at-least 6 \
		--forbid-frontier-branches \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 12 \
		--postcheck-limit 200 \
		--postcheck-report-first 5 \
		--postcheck-report-every 50
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 5 \
		--sat-pairs-hit-at-least 12 \
		--forbid-frontier-branches \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--postcheck-limit 1000 \
		--postcheck-report-first 5 \
		--postcheck-report-every 100
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 6 \
		--sat-pairs-hit-at-least 28 \
		--forbid-frontier-branches \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--postcheck-limit 100 \
		--postcheck-report-first 5 \
		--postcheck-report-every 20

bicross-branch-cubes:
	$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 4 \
		--hit-bound 6 \
		--forbid-frontier-branches \
		--cube-depth 4 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 2 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 12 \
		--postcheck-limit-per-cube 0
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 28 \
		--forbid-frontier-branches \
		--cube-depth 6 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 50000 \
		--stop-on-sat \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--postcheck-limit-per-cube 5

bicross-branch-adaptive-cubes:
	-$(PYSAT_PYTHON) enc/bicross_adaptive_cube_search.py \
		-m 6 \
		--hit-bound 28 \
		--forbid-frontier-branches \
		--parent-depth 6 \
		--parent-indexes 0,1,3,7 \
		--depths 8,10,12 \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 50000 \
		--stop-on-sat \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--postcheck-limit-per-cube 5

bicross-extremal-shapes:
	$(PYSAT_PYTHON) enc/bicross_extremal_analysis.py \
		-m 4 \
		--hit-bound 6 \
		--models 100 \
		--exact-hit \
		--summary-only
	$(PYSAT_PYTHON) enc/bicross_extremal_analysis.py \
		-m 5 \
		--hit-bound 12 \
		--models 100 \
		--exact-hit \
		--summary-only
	$(PYSAT_PYTHON) enc/bicross_extremal_analysis.py \
		-m 6 \
		--hit-bound 28 \
		--models 100 \
		--exact-hit \
		--summary-only \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-no-cell-frontier:
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 4 \
		--sat-pairs-hit-at-least 6 \
		--forbid-cell-pairs
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 5 \
		--sat-pairs-hit-at-least 12 \
		--forbid-cell-pairs
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 28 \
		--forbid-cell-pairs \
		--cube-depth 8 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 50000 \
		--stop-on-sat \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-dichotomy-checks:
	$(PYSAT_PYTHON) enc/bicross_probe.py \
		-m 4 \
		--sat-pairs-hit-at-least 6 \
		--forbid-cell-pairs \
		--forbid-perfect-inherited-splits
	$(PYSAT_PYTHON) enc/bicross_extremal_analysis.py \
		-m 5 \
		--hit-bound 12 \
		--models 100 \
		--exact-hit \
		--forbid-cell-pairs \
		--summary-only
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 28 \
		--forbid-cell-pairs \
		--forbid-perfect-inherited-splits \
		--cube-depth 6 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 50000 \
		--stop-on-sat \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--postcheck-limit-per-cube 5

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
		--jobs $(JOBS) \
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
		--jobs $(JOBS) \
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
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 2000000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-q6-hit30-proof:
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 30 \
		--cube-depth 8 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 20000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 30 \
		--cube-depth 8 \
		--cube-mode prefix \
		--only-cube-indexes 0,1,4,5,12,13,15,28,29,31 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 2000000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 30 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 64-79,192-207,464-479 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 50000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 30 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 66,68,69,70,71,76,77,78,79,198,199,200,201,202,203,206,207,464,465,466,467,470,471,478,479 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 500000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 30 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 68,70,78,198,200,202,206,467,471 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 2000000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-q6-hit29-proof:
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 8 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 20000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 8 \
		--cube-mode prefix \
		--only-cube-indexes 0,1,4,5,12,13,15,28,29,31 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 2000000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 0-15,64-79,192-207,448-479 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 50000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 0,1,2,3,6,7,14,15,66,67,68,69,70,71,76,77,78,79,198,199,200,201,202,203,206,207,462,463,464,465,466,467,470,471,478,479 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 500000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 0,2,6,14,66,68,70,76,78,79,198,200,202,203,206,207,462,463,464,465,466,467,470,471,479 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 2000000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 16 \
		--cube-mode prefix \
		--only-cube-indexes 1120-1135,1248-1263,3168-3183,3200-3215,3232-3247,3296-3311,7392-7407 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 50000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 16 \
		--cube-mode prefix \
		--only-cube-indexes 1123,1124,1125,1126,1127,1132,1133,1134,1135,1255,1256,1257,1258,1259,1262,1263,3171,3172,3173,3175,3180,3181,3204,3205,3207,3208,3209,3211,3212,3213,3215,3237,3238,3239,3240,3241,3242,3243,3244,3245,3246,3247,3303,3304,3305,3307,3308,3309,3311,7399,7400,7401,7403,7407 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 500000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 6 \
		--hit-bound 29 \
		--cube-depth 16 \
		--cube-mode prefix \
		--only-cube-indexes 1123,1125,1126,1127,1257,3171,3173,3175,3238,3239,3241,3243,3303,3305,3307,3309,7399,7403 \
		--jobs $(JOBS) \
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

bicross-q7-full-cubes:
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 7 \
		--hit-bound 64 \
		--cube-depth 8 \
		--cube-mode prefix \
		--jobs $(JOBS) \
		--batch-size 4 \
		--conflict-budget 20000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 7 \
		--hit-bound 64 \
		--cube-depth 8 \
		--cube-mode prefix \
		--only-cube-indexes 0,1,2,3,6,7,14,15 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 500000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20
	-$(PYSAT_PYTHON) enc/bicross_cube_search.py \
		-m 7 \
		--hit-bound 64 \
		--cube-depth 12 \
		--cube-mode prefix \
		--only-cube-indexes 0-15,32-47,96-127,224-255 \
		--jobs $(JOBS) \
		--batch-size 1 \
		--conflict-budget 50000 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20

bicross-q7-lift-search:
	$(PYSAT_PYTHON) enc/bicross_lift_search.py \
		-m 7 \
		--seed-hit-bound 28 \
		--sort-zero-edges \
		--zero-red-degree-at-most-half \
		--partial-sym-break 20 \
		--scan-neighborhood \
		--greedy-passes 5 \
		--steps 5000 \
		--restarts 8
