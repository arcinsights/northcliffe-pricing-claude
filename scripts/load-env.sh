#!/bin/bash

# Helper script to load .env file
# Source this in other scripts: source scripts/load-env.sh

if [ -f .env ]; then
    # Load .env file
    export $(grep -v '^#' .env | xargs)
    echo "✅ Loaded environment from .env"
elif [ -f .env.example ]; then
    echo "⚠️  No .env file found"
    echo ""
    echo "Please create .env from template:"
    echo "  cp .env.example .env"
    echo "  nano .env  # Fill in your values"
    echo ""
    return 1
else
    echo "⚠️  No .env or .env.example found"
    return 1
fi
