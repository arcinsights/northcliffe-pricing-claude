#!/bin/bash

# Quick data viewer for BigQuery tables

set -e

PROJECT_ID=${GCP_PROJECT:-$(gcloud config get-value project)}

echo "📊 Smart Pricing - Data Viewer"
echo "=============================="
echo "Project: $PROJECT_ID"
echo ""

PS3="Select table to view: "
options=("Latest Recommendations" "Today's Scrape Stats" "Competitor Listings" "Events" "Quit")

select opt in "${options[@]}"
do
    case $opt in
        "Latest Recommendations")
            echo ""
            echo "Latest Price Recommendations (Next 7 days):"
            bq query --use_legacy_sql=false --format=pretty "
            SELECT
                target_date,
                recommended_price,
                comp_set_count,
                confidence
            FROM \`$PROJECT_ID.pricing.price_recommendations\`
            WHERE recommendation_date = (
                SELECT MAX(recommendation_date)
                FROM \`$PROJECT_ID.pricing.price_recommendations\`
            )
            AND target_date >= CURRENT_DATE()
            ORDER BY target_date
            LIMIT 7
            "
            ;;
        "Today's Scrape Stats")
            echo ""
            echo "Today's Scrape Statistics:"
            bq query --use_legacy_sql=false --format=pretty "
            SELECT
                COUNT(DISTINCT listing_id) as total_listings,
                COUNT(*) as total_price_records,
                MIN(price_per_night) as min_price,
                MAX(price_per_night) as max_price,
                AVG(price_per_night) as avg_price
            FROM \`$PROJECT_ID.pricing.daily_prices\`
            WHERE scrape_date = CURRENT_DATE()
            "
            ;;
        "Competitor Listings")
            echo ""
            echo "Active Competitor Listings:"
            bq query --use_legacy_sql=false --format=pretty "
            SELECT
                name,
                bedrooms,
                bathrooms,
                max_guests,
                rating,
                review_count
            FROM \`$PROJECT_ID.pricing.competitor_listings\`
            WHERE is_active = TRUE
            ORDER BY rating DESC
            LIMIT 10
            "
            ;;
        "Events")
            echo ""
            echo "Upcoming Events:"
            bq query --use_legacy_sql=false --format=pretty "
            SELECT
                event_date,
                event_name,
                event_type,
                expected_impact
            FROM \`$PROJECT_ID.pricing.events\`
            WHERE event_date >= CURRENT_DATE()
            ORDER BY event_date
            LIMIT 20
            "
            ;;
        "Quit")
            break
            ;;
        *)
            echo "Invalid option"
            ;;
    esac
    echo ""
done
