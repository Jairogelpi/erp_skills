.PHONY: format format-check lint typecheck test coverage build up down logs compose-config bootstrap-codebase-memory remove-codebase-memory validate-dataset benchmark-smoke

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

bootstrap-codebase-memory:
	python scripts/bootstrap-codebase-memory.py

remove-codebase-memory:
	python scripts/bootstrap-codebase-memory.py --remove
