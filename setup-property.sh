#!/bin/bash

# Quick setup script - extracts property details from Airbnb

set -e

echo "🏠 Smart Pricing - Quick Property Setup"
echo "========================================"
echo ""

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 Creating .env from template..."
        cp .env.example .env
        echo "✅ Created .env file"
        echo ""
        echo "⚠️  Please edit .env and add your:"
        echo "  - APIFY_API_TOKEN (get from https://console.apify.com/account/integrations)"
        echo "  - AIRBNB_LISTING_URL (your listing URL)"
        echo ""
        echo "Then run this script again."
        exit 0
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi

# Load .env
export $(grep -v '^#' .env | xargs)

# Check if Python installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3 first"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -q -r scripts/requirements.txt

# Extract property details
echo ""
if [ -n "$1" ]; then
    # URL provided as argument
    echo "🔍 Extracting property details from provided URL..."
    python scripts/extract-property-details.py "$1"
else
    # Use URL from .env or prompt
    echo "🔍 Extracting property details..."
    python scripts/extract-property-details.py
fi

# Deactivate virtual environment
deactivate

# Success!
echo ""
echo "✅ Property setup complete!"
echo ""
echo "Next steps:"
echo "1. Review config.yaml (auto-generated)"
echo "2. Run ./scripts/setup-gcp.sh to configure Google Cloud"
echo "3. Add GitHub secrets (see setup script output)"
echo "4. git push to deploy!"
echo ""
