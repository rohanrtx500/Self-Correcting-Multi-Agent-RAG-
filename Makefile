.PHONY: install format lint test run ingest docker-up docker-down clean

install:
	pip install -r requirements.txt

format:
	black .
	ruff check --fix .

lint:
	mypy app/

test:
	pytest --tb=short -v

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ingest:
	python scripts/ingest_data.py

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache chroma_db
