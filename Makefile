.PHONY: install db run test lint format notebook dfd

install:
	python -m pip install -r requirements.txt

db:
	cd fastapi && python sqlite_database.py --reset

run:
	cd fastapi && uvicorn main:app --reload

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

notebook:
	jupyter lab eda/eda_tp3.ipynb

dfd:
	python others/generate_dfd.py
