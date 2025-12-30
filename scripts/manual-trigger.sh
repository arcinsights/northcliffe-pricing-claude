#!/bin/bash

# Manual trigger script for scraping and analysis
# Usage: ./scripts/manual-trigger.sh [scraper|analyzer|both]

set -e

ACTION=${1:-both}
REGION=${GCP_REGION:-europe-west2}

echo "🎯 Manual Trigger Script"
echo "======================="
echo ""

trigger_scraper() {
    echo "🔍 Triggering scraper..."
    gcloud functions call scraper \
        --region=$REGION \
        --gen2
    echo "✅ Scraper triggered"
}

trigger_analyzer() {
    echo "📊 Triggering analyzer..."
    gcloud functions call analyzer \
        --region=$REGION \
        --gen2
    echo "✅ Analyzer triggered"
}

case $ACTION in
    scraper)
        trigger_scraper
        ;;
    analyzer)
        trigger_analyzer
        ;;
    both)
        trigger_scraper
        echo ""
        echo "⏳ Waiting 30 seconds for scraper to complete..."
        sleep 30
        echo ""
        trigger_analyzer
        ;;
    *)
        echo "❌ Invalid action: $ACTION"
        echo "Usage: $0 [scraper|analyzer|both]"
        exit 1
        ;;
esac

echo ""
echo "✅ Done!"
echo ""
echo "Check logs with:"
echo "  gcloud functions logs read scraper --region=$REGION --limit=50"
echo "  gcloud functions logs read analyzer --region=$REGION --limit=50"
echo ""
