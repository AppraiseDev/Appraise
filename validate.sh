#!/bin/sh -e

export PYLINT_THRESHOLD=6
export BLACK_LINE_MAXLEN=88

pip install black==21.7b0 mypy==0.900 pylint==2.9.6 pylint-fail-under==0.3.0 reorder-python-imports==2.6.0 safety==1.10.3
pip install -r requirements.txt

black -S -l $BLACK_LINE_MAXLEN --check .
find . -name "*.py" -not -path "./.venv/*" | xargs mypy
find . -name "*.py" -not -path "./.venv/*" | xargs pylint-fail-under --fail_under $PYLINT_THRESHOLD
find . -name "*.py" -not -path "./.venv/*" | xargs reorder-python-imports --diff-only
cat requirements.txt | safety check --stdin
