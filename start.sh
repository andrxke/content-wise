#!/bin/bash
set -e

# Activate base conda environment if it exists
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate base
fi

# Run the app programmatic wrapper
python app.py "$@"
