.PHONY: format format-check lint typecheck test coverage build up down logs compose-config bootstrap-codebase-memory remove-codebase-memory validate-dataset benchmark-smoke experiment verify-freeze validate-claims prepare-v2 advance-v2 demo export-results figures compare-retrievers power-v2-1 freeze-v2-1 verify-tfm-closure verify-tfm-failed-external mutation-v2-1

up:
	docker compose --env-file config/development.defaults up --build

down:
	docker compose --env-file config/development.defaults down

logs:
	docker compose --env-file config/development.defaults logs

compose-config:
	docker compose --env-file config/development.defaults config

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

test:
	uv run pytest

coverage:
	uv run pytest --cov=erp_agent_os --cov-report=term-missing

build:
	uv run python -m build

validate-dataset:
	uv run pytest tests/test_catalog.py tests/test_bench_intents.py tests/test_bench_generator.py -q

benchmark-smoke:
	uv run python scripts/export_bench_v1.py
	uv run python scripts/run_bench_wiring_report.py

verify-freeze:
	uv run python scripts/freeze_protocol.py --verify

validate-claims:
	uv run python scripts/validate_claims.py

prepare-v2:
	uv run python scripts/prepare_v2_holdout.py

advance-v2:
	uv run python scripts/advance_v2_holdout.py

experiment:
	uv run python scripts/run_experiment.py

demo:
	uv run python scripts/demo.py

export-results:
	uv run python scripts/export_results.py

figures:
	uv run python scripts/make_figures.py

compare-retrievers:
	uv run python scripts/compare_retrievers.py

# --- v2.1 (docs/tfm-closure-no-human-v2.1.md, Task 12) ---
# None of these targets calls a real provider or consumes the holdout;
# see scripts/verify_tfm_closure_v2_1.py's own docstring for the exact
# guarantee each mode makes.

mutation-v2-1:
	uv run python scripts/run_targeted_mutations_v2_1.py --verify

power-v2-1:
	uv run python scripts/run_power_v2_1.py

freeze-v2-1:
	uv run python scripts/freeze_protocol_v2_1.py --verify

verify-tfm-closure:
	uv run python scripts/verify_tfm_closure_v2_1.py --pre-run

verify-tfm-failed-external:
	uv run python scripts/verify_tfm_closure_v2_1.py --failed-external

bootstrap-codebase-memory:
	python scripts/bootstrap-codebase-memory.py

remove-codebase-memory:
	python scripts/bootstrap-codebase-memory.py --remove
