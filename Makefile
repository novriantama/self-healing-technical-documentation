ifneq (,$(wildcard .env))
    include .env
    export
endif

export OPENAGENTIC_BASE_URL := $(subst ",,$(subst ',,$(OPENAGENTIC_BASE_URL)))
export OPENAGENTIC_MODEL := $(subst ",,$(subst ',,$(OPENAGENTIC_MODEL)))
export OPENAGENTIC_API_KEY := $(subst ",,$(subst ',,$(OPENAGENTIC_API_KEY)))

# Map env variables to Action inputs
export INPUT_LLM_API_KEY ?= $(subst ",,$(subst ',,$(if $(ANTHROPIC_API_KEY),$(ANTHROPIC_API_KEY),$(OPENAGENTIC_API_KEY))))
export INPUT_CONFIDENCE_THRESHOLD ?= $(subst ",,$(subst ',,$(CONFIDENCE_THRESHOLD)))
export INPUT_AUTO_MERGE ?= $(subst ",,$(subst ',,$(AUTO_MERGE)))
export INPUT_INDEX_PATH ?= $(subst ",,$(subst ',,$(INDEX_PATH)))
export INPUT_WORKSPACE_DIR ?= $(subst ",,$(subst ',,$(WORKSPACE_DIR)))

.PHONY: help venv install test lint format clean run index


VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip3
PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff

help:
	@echo "Available commands:"
	@echo "  make venv     - Create a virtual environment"
	@echo "  make install  - Install production and development dependencies"
	@echo "  make test     - Run pytest unit tests"
	@echo "  make lint     - Run code style and syntax checks using Ruff"
	@echo "  make format   - Automatically format code using Ruff"
	@echo "  make clean    - Remove build artifacts, caches, and the virtual environment"
	@echo "  make run      - Run the main entrypoint script"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
	fi

install: venv
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt

test:
	@if [ ! -f "$(PYTEST)" ]; then \
		echo "pytest not found. Please run 'make install' first."; \
		exit 1; \
	fi
	$(PYTEST)

lint:
	@if [ ! -f "$(RUFF)" ]; then \
		echo "ruff not found. Please run 'make install' first."; \
		exit 1; \
	fi
	$(RUFF) check .
	$(RUFF) format --check .

format:
	@if [ ! -f "$(RUFF)" ]; then \
		echo "ruff not found. Please run 'make install' first."; \
		exit 1; \
	fi
	$(RUFF) format .

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf .chroma_db
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

run:
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "Python virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi
	@if [ -z "$(INPUT_LLM_API_KEY)" ]; then \
		echo "Error: ANTHROPIC_API_KEY or INPUT_LLM_API_KEY environment variable is required to run the tool."; \
		echo "Usage: Create a .env file with ANTHROPIC_API_KEY='key' OR run 'INPUT_LLM_API_KEY=key make run'"; \
		exit 1; \
	fi
	$(PYTHON) main.py

index:
	@if [ ! -f "$(PYTHON)" ]; then \
		echo "Python virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi
	@if [ -z "$(INPUT_LLM_API_KEY)" ]; then \
		echo "Error: ANTHROPIC_API_KEY or INPUT_LLM_API_KEY environment variable is required to run the indexer."; \
		echo "Usage: Create a .env file with ANTHROPIC_API_KEY='key' OR run 'INPUT_LLM_API_KEY=key make index'"; \
		exit 1; \
	fi
	$(PYTHON) index.py

