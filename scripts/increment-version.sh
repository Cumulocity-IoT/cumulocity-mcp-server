#!/bin/bash

# Get the directory of this script and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Incrementing patch version in pyproject.toml..."

# Extract current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')

if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not extract version from pyproject.toml"
    exit 1
fi

echo "Current version: $CURRENT_VERSION"

# Parse version components (major.minor.patch)
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Validate version format
if [[ ! "$MAJOR" =~ ^[0-9]+$ ]] || [[ ! "$MINOR" =~ ^[0-9]+$ ]] || [[ ! "$PATCH" =~ ^[0-9]+$ ]]; then
    echo "Error: Invalid version format '$CURRENT_VERSION'. Expected format: major.minor.patch (e.g., 0.1.21)"
    exit 1
fi

# Increment patch version
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"

echo "New version: $NEW_VERSION"

# Update version in pyproject.toml
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS version of sed
    sed -i '' "s/^version = .*/version = \"$NEW_VERSION\"/" "$PROJECT_ROOT/pyproject.toml"
else
    # Linux version of sed
    sed -i "s/^version = .*/version = \"$NEW_VERSION\"/" "$PROJECT_ROOT/pyproject.toml"
fi

# Verify the change was made
UPDATED_VERSION=$(grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')

if [ "$UPDATED_VERSION" = "$NEW_VERSION" ]; then
    echo "✅ Successfully updated pyproject.toml version to: $NEW_VERSION"
    echo ""
    echo "Next steps:"
    echo "1. Review the changes: git diff pyproject.toml"
    echo "2. Build the container: ./scripts/buildcontainer.sh"
    echo "3. Commit the changes: git add pyproject.toml && git commit -m \"Bump version to $NEW_VERSION\""
else
    echo "Error: Failed to update version in pyproject.toml"
    exit 1
fi