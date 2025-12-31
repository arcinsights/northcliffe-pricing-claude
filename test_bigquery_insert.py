#!/usr/bin/env python3
"""
Full integration test including BigQuery insertion.
Tests the complete flow locally before deploying.
"""

import json
import sys
from datetime import date
from google.cloud import bigquery

# Add functions directory to path
sys.path.insert(0, 'functions/scraper')
from main import (
    normalize_calendar_data,
    extract_daily_prices_from_calendar,
    ensure_string_fields,
    load_to_bigquery
)


def load_test_data():
    """Load sample Apify data."""
    with open('test_data/apify_sample.json', 'r') as f:
        return json.load(f)


def test_full_flow():
    """Test complete flow: normalize -> insert to BigQuery."""
    print("=" * 70)
    print("FULL INTEGRATION TEST - LOCAL TO BIGQUERY")
    print("=" * 70)

    project_id = "northcliffe-claude"
    scrape_date = date.today()

    # Load and normalize data
    print("\n1. Loading test data...")
    raw_listings = load_test_data()
    print(f"   Loaded {len(raw_listings)} listings")

    print("\n2. Normalizing listings...")
    normalized_listings = [
        normalize_calendar_data(listing, scrape_date)
        for listing in raw_listings
    ]
    print(f"   Normalized {len(normalized_listings)} listings")

    # Print first listing for inspection
    print("\n3. Sample normalized listing:")
    print(json.dumps(normalized_listings[0], indent=2, default=str)[:800])

    print("\n4. Extracting daily prices...")
    all_prices = []
    for i, raw_listing in enumerate(raw_listings):
        # Merge listing_id from normalized version
        raw_listing_with_id = raw_listing.copy()
        raw_listing_with_id["listing_id"] = normalized_listings[i]["listing_id"]
        prices = extract_daily_prices_from_calendar(raw_listing_with_id, scrape_date)
        all_prices.extend(prices)
    print(f"   Extracted {len(all_prices)} price records")

    # Test BigQuery insertion
    print("\n5. Testing BigQuery insertion...")
    try:
        load_to_bigquery(normalized_listings, all_prices, project_id)
        print("   ✅ BigQuery insertion SUCCESSFUL!")

        # Query to verify
        client = bigquery.Client(project=project_id)

        query = f"""
            SELECT COUNT(*) as count, MAX(last_seen_date) as last_update
            FROM `{project_id}.pricing.competitor_listings`
        """
        results = list(client.query(query).result())
        row = results[0]
        print(f"\n6. Verification query:")
        print(f"   Total listings in table: {row['count']}")
        print(f"   Last update: {row['last_update']}")

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED! ✅")
        print("Ready to deploy to Cloud Functions!")
        print("=" * 70)

    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        print("\n   Details:")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("TEST FAILED - FIX BEFORE DEPLOYING!")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    test_full_flow()
