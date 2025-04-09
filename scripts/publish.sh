#!/bin/bash

uv pip install build
python -m build
uv pip install twine
twine upload dist/*
