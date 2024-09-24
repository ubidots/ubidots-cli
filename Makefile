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
	@echo "mypy: run mypy to check type annotations."
	@echo "setup-dev: setup the development environment."
	@echo "validate_code: run black, isort, ruff, and tests."
	@echo "setup-tox-env: install specified Python versions for tox compatibility using pyenv."
	@echo "run-tox: run tests with tox for multiple Python versions."
	@echo "config-testpypi: configure TestPyPI repository and set authentication token."
	@echo "config-pypi: configure PyPI repository and set authentication token."
	@echo "publish-testpypi: publish the package to TestPyPI."
	@echo "publish-pypi: publish the package to PyPI."
	@echo "install-testpypi: create a virtual environment, install the package from TestPyPI, and provide instructions for testing."


.DEFAULT_GOAL := validate_code


test:
	poetry run pytest

black:
	poetry run black .

isort:
	poetry run isort .

ruff:
	poetry run ruff check . --exclude cli/compat.py --preview

mypy:
	poetry run mypy .

validate_code: black isort ruff mypy test

update:
	poetry update

build:
	poetry build

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
	
# Configure TestPyPI repository and set authentication token
config-testpypi:
	@poetry config repositories.testpypi https://test.pypi.org/legacy/
	@echo "Please enter your TestPyPI token:"
	@read TESTPYPI_TOKEN; \
	poetry config pypi-token.testpypi $$TESTPYPI_TOKEN
	@echo "TestPyPI has been configured successfully."

# Configure PyPI repository and set authentication token
config-pypi:
	@poetry config repositories.pypi https://upload.pypi.org/legacy/
	@echo "Please enter your PyPI token:"
	@read PYPI_TOKEN; \
	poetry config pypi-token.pypi $$PYPI_TOKEN
	@echo "PyPI has been configured successfully."

# Publish the package to TestPyPI
publish-testpypi:
	poetry publish --repository testpypi

# Publish the package to PyPI
publish-pypi:
	poetry publish --repository pypi

# Create a virtual environment, install the package from TestPyPI, and provide instructions for testing
install-testpypi:
	@echo "Creating a new virtual environment for testing named 'testpypi-env'..."
	python -m venv testpypi-env
	@echo "To activate the environment, run the following command:"
	@echo "    source testpypi-env/bin/activate"
	@echo ""
	@echo "Activating the virtual environment..."
	@source testpypi-env/bin/activate && \
		echo "Installing the package from TestPyPI, and resolving dependencies from PyPI..." && \
		pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ubidots-cli && \
		echo "" && \
		echo "Package installed in test environment 'testpypi-env'. Ready for testing." && \
		echo "" && \
		echo "To activate the virtual environment, run the following command:" && \
		echo "    'source testpypi-env/bin/activate'" && \
		echo "" && \
		echo "Once activated, you can test the CLI by running the following command:" && \
		echo "    ubidots --help" && \
		echo "This will give you an overview of the available commands and options in the CLI."
