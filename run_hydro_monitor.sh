#!/bin/bash

# Define variables
CODE_DIR="pi_code"               # Directory containing Python code and virtual environment
VENV_DIR="$CODE_DIR/venv"        # Path to the virtual environment
REQUIREMENTS_FILE="$CODE_DIR/requirements.txt"
SCRIPT_NAME="hydroponics_gui.py" # Main Python script name

echo "==== Hydro Monitor Script ===="

# Check if the code directory exists
if [ ! -d "$CODE_DIR" ]; then
    echo "Error: Code directory '$CODE_DIR' not found!"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv "$VENV_DIR"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install required packages
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing required packages from requirements.txt..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "No requirements.txt file found in $CODE_DIR. Skipping package installation."
fi

# Run the Python script
if [ -f "$CODE_DIR/$SCRIPT_NAME" ]; then
    echo "Running the main script: $SCRIPT_NAME..."
    python "$CODE_DIR/$SCRIPT_NAME"
else
    echo "Error: $SCRIPT_NAME not found in $CODE_DIR."
    deactivate
    exit 1
fi

# Deactivate virtual environment
echo "Deactivating virtual environment..."
deactivate

echo "==== Script Completed ===="