.PHONY: all black lint clean

all: black  lint

black:
	black -l 99 XYZHubConnector

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .mypy_cache
	rm -fr .pytest_cache
	find . -name '.ipynb_checkpoints' -exec rm -fr {} +


lint:
	flake8 -v --statistics --count XYZHubConnector
	black -l 99 --diff --check XYZHubConnector
