.PHONY: demo-product demo-api demo-preflight format format-check lint typecheck test coverage build up down logs compose-config validate-dataset benchmark-smoke experiment verify-freeze validate-claims prepare-v2 advance-v2 demo export-results figures compare-retrievers power-v2-1 freeze-v2-1 verify-tfm-closure verify-tfm-failed-external mutation-v2-1

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

# No path argument: pyproject's `files` setting is the single source of
# truth for what gets type-checked (src + scripts). Passing `src` here
# would silently un-check the scripts that produce the published
# artifacts.
typecheck:
	uv run mypy

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

# --- comparative product demo (docs/product-demo.md) ---
# Reads the frozen v2.1.2 confirmatory report; recomputes nothing.

demo-preflight:
	uv run python scripts/demo_preflight.py

demo-api:
	uv run uvicorn erp_agent_os.demo_api:app --reload --port 8000

# Runs preflight first, on purpose: presenting a screen whose evidence
# artifacts are unreadable is the one failure mode worth blocking on.
demo-product: demo-preflight
	cd demo-ui && npm install --silent
	uv run uvicorn erp_agent_os.demo_api:app --port 8000 & 		cd demo-ui && npm run dev

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

# --pre-run only ever succeeds before any v2.1 receipts exist
# (DRAFT_PROTOCOL, per verify_tfm_closure_v2_1.py's own docstring) --
# it was the correct CI check while Task 12 was being built, but the
# real campaign has since run to completion (RUN_COMPLETED, receipts
# committed under data/protocol_v2_1/runs_v2/), so --pre-run can never
# pass again in this repo's history. Found live (docs/audit.md #17):
# this CI target had never actually run end-to-end until PR #3 first
# exercised it, well after the campaign completed. --final is the mode
# that verifies the campaign that actually happened, matching exactly
# the reproduction command documented in docs/memoria.md's Anexo A.
verify-tfm-closure:
	uv run python scripts/verify_tfm_closure_v2_1.py --final \
		--receipt-log data/protocol_v2_1/runs_v2/receipts_2.jsonl \
		--code-manifest-path data/protocol_v2_1/code_freeze_manifest.json \
		--report-path data/protocol_v2_1/confirmatory_report_v2_1_2.json

verify-tfm-failed-external:
	uv run python scripts/verify_tfm_closure_v2_1.py --failed-external
