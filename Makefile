.PHONY: install lint format type test cov run sample-chart test-alert docker-build docker-up docker-logs migrate clean

install:
	python -m pip install -e .[dev]

lint:
	ruff check .

format:
	ruff format .

type:
	mypy src/ict_scanner

test:
	pytest tests/

cov:
	pytest tests/ --cov=src.ict_scanner --cov-report=term-missing

run:
	python -m ict_scanner

sample-chart:
	python scripts/render_sample_chart.py

test-alert:
	python scripts/send_test_alert.py

docker-build:
	docker build -t ict-scanner .

docker-up:
	docker compose up -d --build

docker-logs:
	docker compose logs -f

migrate:
	alembic upgrade head

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
