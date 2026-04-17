#!/bin/bash
set -e

echo "Setting up ContentWise environment..."

# Activate base conda environment if it exists
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate base
else
    echo "Conda not found. Skipping conda environment activation."
fi

# Install python dependencies for server
echo "Installing Python dependencies..."
pip install -r requirements-server.txt

echo "Setup complete!"
echo "To start the backend server, run: ./start.sh"
