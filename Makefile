.PHONY: up down lint test compose demo sample

up:
	docker compose up --build -d

down:
	docker compose down

lint:
	python -m ruff check .

test:
	python -m pytest -q

compose:
	docker compose config

demo:
	python scripts/demo_pipeline.py

sample:
	python scripts/generate_sample_data.py
