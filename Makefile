.PHONY: up down test lint format

up:
	docker compose up -d

down:
	docker compose down

test:
	cd backend && python -m pytest -q

lint:
	cd backend && ruff check .

format:
	cd backend && ruff format .
