.PHONY: install run test lint up down

install:
	python3 -m pip install -e '.[dev]'

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

test:
	pytest -q

lint:
	ruff check .

up:
	docker compose up --build

down:
	docker compose down
