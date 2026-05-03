#!/bin/bash
set -e

# Use Python 3.12 explicitly
export PYTHON_VERSION=3.12

pip install --upgrade pip
pip install -r vera-bot/requirements.txt

echo "✓ Build complete with Python 3.12"
