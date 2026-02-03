#!/bin/bash

# Define the location of the valid virtual environment
# We use the one in the grandparent directory because the current directory name contains ':'
VENV_PATH="../../venv"

if [ -d "$VENV_PATH" ]; then
    EXEC="$VENV_PATH/bin/python3"
    echo "Using virtual environment at: $VENV_PATH"
else
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please ensure the environment is set up correctly."
    exit 1
fi

# Run the script
"$EXEC" gen_scenarios_from_convo.py "$@"
