#!/bin/bash

# Check if a file path is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-env-file>"
    exit 1
fi

# Check if the file exists
if [ ! -f "$1" ]; then
    echo "Error: File '$1' not found"
    exit 1
fi

# Process the .env file
# - Ignores empty lines and comments
# - Preserves quotes in values
# - Adds -e prefix to each line
grep -v '^#' "$1" | grep -v '^$' | sed 's/^/-e /' 