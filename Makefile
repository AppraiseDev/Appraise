BLACK_LINE_MAXLEN = 88
PYLINT_THRESHOLD = 6
FIND_PY_FILES = find . -name "*.py" -not -path "./venv*" -not -path "*/migrations/*"

all: test check

# Start development server locally
run:
	python manage.py runserver

# Check code formatting and run static type checker
check: check-black check-pylint check-mypy check-safety

check-black:
	black --version
	black -S -l $(BLACK_LINE_MAXLEN) --check . --force-exclude '/migrations/'

check-pylint:
	pylint --version
	$(FIND_PY_FILES) | xargs pylint --fail-under $(PYLINT_THRESHOLD) --rcfile setup.cfg
	$(FIND_PY_FILES) | xargs reorder-python-imports --diff-only

check-mypy:
	$(FIND_PY_FILES) | xargs mypy

check-safety:
	cat requirements.txt | safety check --stdin

# Run regression tests
test:
	bash RegressionTests/run.sh

# Install requirements needed for app development
install: requirements-dev.txt
	pip install -r $<

.PHONY: all check check-black check-pylint check-mypy check-safety run test
