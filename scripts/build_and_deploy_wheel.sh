#!/usr/bin/env bash
if [[ "${TRAVIS_PULL_REQUEST}" == "false" ]] && [[ "${TRAVIS_BRANCH}" == "master" ]]; then
    python3 setup.py sdist bdist_wheel
    python3 -m twine upload -u "${PYPI_USER}" -p "${PYPI_PASS}" dist/*
else
    echo "Skipping deployment as we are on a Pull Request"
fi
