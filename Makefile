.PHONY: format format-check lint typecheck test coverage build up down logs compose-config bootstrap-codebase-memory remove-codebase-memory validate-dataset benchmark-smoke experiment verify-freeze demo export-results figures compare-retrievers v2-readiness competition-readiness

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

v2-readiness:
	powershell -NoProfile -Command "if (Test-Path 'data/bench_v2.jsonl') { uv run python scripts/validate_bench_v2.py; if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }; if (Test-Path 'data/bench_v2_freeze_manifest.json') { uv run python scripts/freeze_protocol_v2.py --verify; exit $$LASTEXITCODE } else { Write-Host 'V2 dataset valid; freeze manifest still pending' } } else { Write-Host 'V2 pending: dataset and freeze manifest are absent' }"

competition-readiness:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/competition_readiness.ps1

bootstrap-codebase-memory:
	python scripts/bootstrap-codebase-memory.py

remove-codebase-memory:
	python scripts/bootstrap-codebase-memory.py --remove
