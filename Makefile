SHELL=/bin/bash
#vars
CELERY_LOG_LEVEL=info

.PHONY: help validate_code

help:
	@echo "Makefile commands:"
	@echo "test: run tests for mercury."
	@echo "black: update black."
	@echo "isort: run isort for code."
	@echo "validate_code: run black, isort, flake8, pylint and tests."

.DEFAULT_GOAL := validate_code


test:
	poetry run pytest

black:
	poetry run black .

isort:
	poetry run isort .

ruff:
	poetry run ruff check . --preview

validate_code: black isort ruff test

update:
	poetry update
