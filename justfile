set default-list := true

# Synchronize runtime and development dependencies from the lockfile
sync:
    uv sync --locked

# Install Python 3.14, the development environment and Git hooks
setup: sync
    uv run --locked prek install

# Check code style and formatting without changing files
lint:
    uv run --locked ruff check .
    uv run --locked ruff format --check .

# Apply code style and formatting fixes
format:
    uv run --locked ruff check . --fix
    uv run --locked ruff format .

# Check types with the project's Python environment
type-check:
    uv run --locked ty check

# Run all Git hooks
check:
    uv run --locked prek run --all-files

# Run tests; additional pytest arguments are accepted
test *args:
    uv run --locked pytest --cov=signpy --cov-report=term-missing {{args}}

# Run every quality check and the tests
all:
    just lint
    just type-check
    just check
    just test

# Run the Streamlit application
run:
    uv run --locked streamlit run signpy/signstream.py

# Build the wheel and source distribution
build:
    uv build

# Build Sphinx documentation
docs:
    uv run --locked --group docs sphinx-build -W --keep-going docs docs/_build

# Register a Jupyter kernel for the project
install-kernel:
    uv run --locked --group notebooks python -m ipykernel install --user --name=signpy

# Build and run the Docker application
docker:
    sh .streamlit/build.sh
