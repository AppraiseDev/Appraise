#!/bin/sh -e

pip install black mypy pylint-fail-under reorder-python-imports safety
pip install -r requirements.txt

export PYLINT_THRESHOLD=8

black -S -l 75 --check .
find . -name "*.py" -not -path "./.venv/*" | xargs mypy
find . -name "*.py" -not -path "./.venv/*" | xargs pylint-fail-under --fail_under $PYLINT_THRESHOLD
find . -name "*.py" -not -path "./.venv/*" | xargs reorder-python-imports --diff-only
cat requirements.txt | safety check --stdin
