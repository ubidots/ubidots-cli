SHELL=/bin/bash
#vars
CELERY_LOG_LEVEL=info
PYTHON_VERSION=3.12.2
PYTHON_VERSIONS=3.9.18 3.10.13 3.11.5 $(PYTHON_VERSION)

.PHONY: help setup-dev validate_code setup-tox-env run-tox

help:
	@echo "Makefile commands:"
	@echo "test: run tests with pytest."
	@echo "black: run black to format code."
	@echo "isort: run isort to sort imports."
	@echo "ruff: run ruff for linting."
	@echo "setup-dev: setup the development environment."
	@echo "validate_code: run black, isort, ruff, and tests."
	@echo "setup-tox-env: install specified Python versions for tox compatibility using pyenv."
	@echo "run-tox: run tests with tox for multiple Python versions."

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

# Setup development environment
setup-dev:
	@PYTHON_VERSION=$(PYTHON_VERSION); \
	if ! pyenv versions --bare | grep -q "$$PYTHON_VERSION"; then \
		echo "Installing Python $$PYTHON_VERSION..."; \
		pyenv install "$$PYTHON_VERSION"; \
		echo ""; \
	else \
		echo "Python $$PYTHON_VERSION is already installed"; \
	fi; \
	pyenv local "$$PYTHON_VERSION"; \
	poetry env use "$$PYTHON_VERSION"; \
	poetry install --with dev

# Install specified Python versions for tox compatibility with pyenv
setup-tox-env:
	@for version in $(PYTHON_VERSIONS); do \
		if ! pyenv versions --bare | grep -q "$$version"; then \
			echo "Installing Python $$version..."; \
			pyenv install $$version; \
		else \
			echo "Python $$version is already installed"; \
		fi \
	done

# Run tox for multiple Python versions
run-tox: setup-tox-env
	@pyenv local $(PYTHON_VERSIONS)
	PYTHON_VERSION=$(PYTHON_VERSION); \
	pyenv local "$$PYTHON_VERSION"; \
	poetry run tox;
	
