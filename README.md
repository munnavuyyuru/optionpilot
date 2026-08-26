# OptionPilot

Options trading automation and analysis platform.

## Structure

```
optionpilot/
├── src/        # Source code
├── tests/      # Test suite
├── scripts/    # Utility scripts
├── config/     # Configuration files
├── docs/       # Documentation
└── logs/       # Log files
```

## Setup

```bash
pip install -e .
```

## Development

```bash
# Run tests
pytest tests/

# Run linting
ruff check src/
```

## Configuration

Copy `.env.example` to `.env` and configure your settings.