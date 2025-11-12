.PHONY: install dev run lint format test alembic-upgrade

install:
	pip install --upgrade pip
	pip install .

dev:
	pip install --upgrade pip
	pip install -e .[dev]

run:
	uvicorn app.main:app --reload

lint:
	ruff check app
	mypy app

format:
	ruff check app --fix
	ruff format app

test:
	pytest

alembic-upgrade:
	alembic upgrade head
