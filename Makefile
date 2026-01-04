PYTHON := ./venv/bin/python
STREAMLIT := ./venv/bin/streamlit

.PHONY: help web cli clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

web: ## Start Streamlit Web UI (Headless by default for server)
	@echo "Starting Web UI..."
	PYTHONPATH=. $(STREAMLIT) run src/web_ui.py --server.headless true

cli: ## Run CLI help
	PYTHONPATH=. $(PYTHON) src/cli.py --help

app: ## Start GUI Launcher App
	PYTHONPATH=. $(PYTHON) src/launcher.py

clean: ## Clean up logs and cache
	rm -rf __pycache__ src/__pycache__ logs/*.log output/*.png output/*.html
