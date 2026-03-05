# Release Guide

## Maintainer release flow

Workflow file:

- `.github/workflows/publish-pypi.yml`

How release works:

1. Push a git tag like `v0.1.1`.
2. GitHub Action builds the package.
3. Workflow sets `pyproject.toml` version from the tag.
4. Package is published to PyPI using `PYPI_API_TOKEN`.

Required GitHub repository secret:

- `PYPI_API_TOKEN`: PyPI API token with publish permission for this package.
