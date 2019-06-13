#!/bin/bash
pip install -e .[tests]
tox -p auto -o
