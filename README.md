# signpy

Sign Language recognition, with a Streamlit application.

## Development setup

Requires Python 3.14, [uv](https://docs.astral.sh/uv/getting-started/installation/)
and [just](https://just.systems/man/en/packages.html).
`uv` installs Python automatically if it is missing.

```sh
just setup
just run
```

`just setup` installs the dependencies from `uv.lock` into `.venv` and activates
Git hooks with [prek](https://prek.j178.dev/). To install dependencies without
activating hooks, run `just sync`.

## Quality checks

```sh
just lint          # Ruff lint and format checks (no changes)
just format        # Ruff fixes and formatting
just type-check    # ty type checking
just check         # All prek hooks (can fix files)
just test          # pytest with coverage
just test -k app   # Forward additional arguments to pytest
just all           # All checks and tests
```

The hooks use Ruff and ty from the same lockfile as the command line and CI.
After a hook modifies files, review and stage the changes before committing again.
To remove the hooks, run `uv run --locked prek uninstall`.

## Application

`just run` starts the application at <http://localhost:8501>.
The two pages use Streamlit's native top navigation, replacing Hydralit.
The logo is included in the installed package.

With Docker installed, `just docker` builds and starts the Python 3.14 container.
The container also installs its dependencies from `uv.lock`.

## Dependencies

Runtime dependencies and development groups are defined in `pyproject.toml`.
`uv.lock` and `.python-version` are committed for reproducible environments.

```sh
uv add package-name
uv add --dev tool-name
uv lock --upgrade
just sync
just all
```

The `docs` and `notebooks` groups are optional:

```sh
just docs
just install-kernel
```

Documentation is generated in `docs/_build/index.html`.
Kaleido image exports require Chrome; install it when needed with
`uv run plotly_get_chrome`.

## Build and release

```sh
just build
```

This produces a wheel and source distribution in `dist/`.
Update the version in `pyproject.toml` and [CHANGELOG.md](CHANGELOG.md) before a release.
Publishing is explicit via `uv publish` with the intended registry and credentials;
the CI validates builds and does not publish packages.
