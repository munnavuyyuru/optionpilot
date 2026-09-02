.PHONY: verify install test lint format clean scan ci

# Default target
all: verify

# Install dependencies
install:
	pip install -e ".[dev]"

# Run verification script
verify:
	@python scripts/verify_alpaca.py

# Run tests
test:
	pytest tests/ -v

# Lint code
lint:
	ruff check src/ scripts/

# Format code
format:
	ruff format src/ scripts/
	black src/ scripts/

# Run market scanner
scan:
	python scripts/scan_market.py --top 10

# Run market scanner with output
scan-output:
	python scripts/scan_market.py --top 10 --output scan_results.json

# Run full CI pipeline locally
ci: lint test verify

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true