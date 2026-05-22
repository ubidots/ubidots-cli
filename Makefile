SHELL=/bin/bash
#vars
CELERY_LOG_LEVEL=info
PYTHON_VERSION=3.12.2
PYTHON_VERSIONS=3.9.18 3.10.13 3.11.5 $(PYTHON_VERSION)

.PHONY: help setup-dev validate_code setup-tox-env run-tox lint-docs fmt ruff ruff_fix ruff_fix_unsafe mypy test

help: ## Show this help message
	@echo -e "\033[1;36mAvailable targets:\033[0m"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; category = ""} \
		/^# ===/ { \
			getline; \
			if ($$0 ~ /^# /) { \
				sub(/^# /, "", $$0); \
				category = $$0; \
			} \
		} \
		/^[a-zA-Z_-]+:.*?##/ { \
			if (category != "") { \
				printf "\n\033[1;34m%s\033[0m\n", category; \
				category = ""; \
			} \
			printf "  \033[32m%-30s\033[0m %s\n", $$1, $$2 \
		}' $(MAKEFILE_LIST)
	@echo ""

.DEFAULT_GOAL := help

# ============================================================================
# Code Quality
# ============================================================================

fmt: ## Format code with Ruff
	poetry run ruff format .

ruff: ## Run Ruff linter
	poetry run ruff check . --preview

ruff_fix: ## Auto-fix linting issues with Ruff
	poetry run ruff check . --fix --preview

ruff_fix_unsafe: ## Auto-fix linting issues with Ruff using unsafe mechanisms
	poetry run ruff check . --fix --preview --unsafe-fixes

mypy: ## Run mypy to check type annotations
	poetry run mypy .

lint-docs: ## Run markdownlint-cli2 on README, CHANGELOG and docs/
	npx markdownlint-cli2 README.md CHANGELOG.md "docs/development/**/*.md"

validate_code: fmt ruff mypy lint-docs test ## Run complete code validation pipeline

# ============================================================================
# Testing
# ============================================================================

test: ## Run tests with pytest
	poetry run pytest

# ============================================================================
# Environment
# ============================================================================

update: ## Update all dependencies
	poetry update

build: ## Build the package
	poetry build

setup-dev: ## Setup the development environment
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

setup-tox-env: ## Install specified Python versions for tox compatibility using pyenv
	@for version in $(PYTHON_VERSIONS); do \
		if ! pyenv versions --bare | grep -q "$$version"; then \
			echo "Installing Python $$version..."; \
			pyenv install $$version; \
		else \
			echo "Python $$version is already installed"; \
		fi \
	done

run-tox: setup-tox-env ## Run tests with tox for multiple Python versions
	@pyenv local $(PYTHON_VERSIONS)
	PYTHON_VERSION=$(PYTHON_VERSION); \
	pyenv local "$$PYTHON_VERSION"; \
	poetry run tox;

# ============================================================================
# Publishing
# ============================================================================

config-testpypi: ## Configure TestPyPI repository and set authentication token
	@poetry config repositories.testpypi https://test.pypi.org/legacy/
	@echo "Please enter your TestPyPI token:"
	@read TESTPYPI_TOKEN; \
	poetry config pypi-token.testpypi $$TESTPYPI_TOKEN
	@echo "TestPyPI has been configured successfully."

config-pypi: ## Configure PyPI repository and set authentication token
	@poetry config repositories.pypi https://upload.pypi.org/legacy/
	@echo "Please enter your PyPI token:"
	@read PYPI_TOKEN; \
	poetry config pypi-token.pypi $$PYPI_TOKEN
	@echo "PyPI has been configured successfully."

publish-testpypi: ## Publish the package to TestPyPI
	poetry publish --repository testpypi

publish-pypi: ## Publish the package to PyPI
	poetry publish --repository pypi

install-testpypi: ## Create a virtual environment and install the package from TestPyPI
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
