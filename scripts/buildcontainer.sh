#!/bin/bash

# Get the directory of this script and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Syncing version from pyproject.toml to cumulocity.json..."

# Extract version from pyproject.toml
VERSION=$(grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')

if [ -z "$VERSION" ]; then
    echo "Error: Could not extract version from pyproject.toml"
    exit 1
fi

echo "Found version: $VERSION"

# Update version in cumulocity.json using a more robust approach
python3 -c "
import json
import sys

try:
    with open('$PROJECT_ROOT/docker/cumulocity.json', 'r') as f:
        data = json.load(f)
    
    data['version'] = '$VERSION'
    
    with open('$PROJECT_ROOT/docker/cumulocity.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f'Updated cumulocity.json version to: $VERSION')
except Exception as e:
    print(f'Error updating cumulocity.json: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Error: Failed to update cumulocity.json"
    exit 1
fi

uv lock

docker build -t mcp-c8y -f docker/Dockerfile --platform linux/amd64 .

cd docker

docker save mcp-c8y > "image.tar"

zip mcp-server-c8y cumulocity.json image.tar

echo "Build completed successfully with version $VERSION"