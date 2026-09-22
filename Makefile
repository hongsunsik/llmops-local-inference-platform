.PHONY: install run test lint eval load-test up down

install:
	python3 -m pip install -e '.[dev]'

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

test:
	pytest -q

lint:
	ruff check .

eval:
	python3 scripts/evaluate_routing.py

load-test:
	docker run --rm -i --network host grafana/k6 run -e BASE_URL=http://host.docker.internal:8080 - < load-test/k6-chat.js

up:
	docker compose up --build

down:
	docker compose down
