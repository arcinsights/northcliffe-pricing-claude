#!/usr/bin/env python3
"""
Unit test for scraper normalization functions.
Tests using real Apify output without making API calls.
"""

import json
import sys
from datetime import date
from typing import List, Dict

# Add functions directory to path
sys.path.insert(0, 'functions/scraper')
from main import normalize_calendar_data, extract_daily_prices_from_calendar, ensure_string_fields


def load_test_data() -> List[Dict]:
    """Load sample Apify data."""
    with open('test_data/apify_sample.json', 'r') as f:
        return json.load(f)


def test_normalize_calendar_data():
    """Test that normalization produces valid data for BigQuery."""
    raw_listings = load_test_data()
    scrape_date = date.today()

    print(f"Testing with {len(raw_listings)} listings...")

    for i, listing in enumerate(raw_listings):
        print(f"\n--- Listing {i+1}: {listing.get('id')} ---")

        normalized = normalize_calendar_data(listing, scrape_date)

        # Check listing_id is a string
        listing_id = normalized.get('listing_id')
        print(f"  listing_id: {listing_id} (type: {type(listing_id).__name__})")
        assert isinstance(listing_id, str), f"listing_id should be string, got {type(listing_id)}"

        # Check rating is a float or None
        rating = normalized.get('rating')
        print(f"  rating: {rating} (type: {type(rating).__name__ if rating is not None else 'None'})")
        assert rating is None or isinstance(rating, (int, float)), \
            f"rating should be float/int/None, got {type(rating)}: {rating}"

        # Check review_count
        review_count = normalized.get('review_count')
        print(f"  review_count: {review_count} (type: {type(review_count).__name__ if review_count is not None else 'None'})")
        assert review_count is None or isinstance(review_count, int), \
            f"review_count should be int/None, got {type(review_count)}"

        # Check name
        print(f"  name: {normalized.get('name')}")

        # Check location
        lat = normalized.get('latitude')
        lng = normalized.get('longitude')
        print(f"  location: ({lat}, {lng})")

        # Extract daily prices
        prices = extract_daily_prices_from_calendar(normalized, scrape_date)
        print(f"  calendar prices: {len(prices)} days")

        if prices:
            print(f"    First day: {prices[0]['check_in_date']} = £{prices[0]['price_per_night']}")

    print("\n✅ All normalization tests passed!")


def test_ensure_string_fields():
    """Test that ensure_string_fields converts properly."""
    test_data = [
        {"listing_id": 123456, "name": "Test"},
        {"listing_id": "789012", "name": "Test 2"},
    ]

    result = ensure_string_fields(test_data, ["listing_id"])

    for item in result:
        assert isinstance(item["listing_id"], str), \
            f"listing_id should be string after conversion, got {type(item['listing_id'])}"

    print("✅ ensure_string_fields test passed!")


def test_bigquery_compatibility():
    """Test that the final data structure is compatible with BigQuery."""
    raw_listings = load_test_data()
    scrape_date = date.today()

    # Normalize all listings
    normalized_listings = [
        normalize_calendar_data(listing, scrape_date)
        for listing in raw_listings
    ]

    # Apply string field conversion (as done in load_to_bigquery)
    normalized_listings = ensure_string_fields(normalized_listings, ["listing_id"])

    print(f"\nTesting BigQuery compatibility for {len(normalized_listings)} listings...")

    for i, listing in enumerate(normalized_listings):
        # Check all required fields
        assert isinstance(listing.get('listing_id'), str), "listing_id must be string"
        assert isinstance(listing.get('source'), str), "source must be string"
        assert isinstance(listing.get('first_seen_date'), str), "first_seen_date must be string"
        assert isinstance(listing.get('last_seen_date'), str), "last_seen_date must be string"
        assert isinstance(listing.get('is_active'), bool), "is_active must be bool"

        # Check nullable fields have correct types when present
        rating = listing.get('rating')
        if rating is not None:
            assert isinstance(rating, (int, float)), \
                f"Listing {i}: rating must be numeric, got {type(rating)}: {rating}"

        review_count = listing.get('review_count')
        if review_count is not None:
            assert isinstance(review_count, int), \
                f"Listing {i}: review_count must be int, got {type(review_count)}"

        # Print first listing for inspection
        if i == 0:
            print("\nFirst listing structure:")
            print(json.dumps(listing, indent=2, default=str)[:500])

    print("\n✅ BigQuery compatibility test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("SCRAPER UNIT TESTS")
    print("=" * 60)

    test_ensure_string_fields()
    test_normalize_calendar_data()
    test_bigquery_compatibility()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)
