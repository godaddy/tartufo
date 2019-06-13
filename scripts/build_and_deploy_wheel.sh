#!/usr/bin/env bash
python3 setup.py sdist bdist_wheel
python3 -m twine upload -u $PYPI_USER -p $PYPI_PASS --repository-url https://pypi.org/project/gd-truffleHog dist/*
