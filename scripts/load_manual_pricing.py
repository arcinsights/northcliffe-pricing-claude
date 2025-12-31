#!/usr/bin/env python3
"""
Load manual pricing observations from competitors.yaml into BigQuery.

Since automated scraping is proving difficult, we'll use your manual research
from the competitor notes to populate initial pricing data.
"""

import yaml
import sys
from datetime import date, timedelta
from google.cloud import bigquery

# Add functions directory to path
sys.path.insert(0, 'functions/scraper')
from main import ensure_string_fields, load_to_bigquery


def parse_manual_pricing_notes():
    """
    Parse the manual pricing observations from competitors.yaml.

    Returns:
        List of competitor data with parsed pricing info
    """
    with open('config/competitors.yaml', 'r') as f:
        config = yaml.safe_load(f)

    competitors = config.get('competitors', [])

    parsed = []
    for comp in competitors:
        listing_id = str(comp.get('listing_id'))
        url = comp.get('url')
        name = comp.get('name')
        notes = comp.get('notes', '')

        # Extract pricing patterns from notes
        # Examples: "400 per night", "£240/night", "170", etc.
        import re

        # Try to find price mentions
        price_patterns = [
            r'(\d+)\s*per\s*night',
            r'£(\d+)/night',
            r'charging\s+(?:min\s+)?(\d+)',
            r'prices?\s+are\s+(\d+)',
        ]

        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, notes, re.IGNORECASE)
            prices.extend([int(m) for m in matches])

        # Find minimum night requirements
        min_nights = None
        min_night_match = re.search(r'(\d+)\s*nights?\s+min', notes, re.IGNORECASE)
        if min_night_match:
            min_nights = int(min_night_match.group(1))

        parsed.append({
            'listing_id': listing_id,
            'url': url,
            'name': name,
            'notes': notes,
            'observed_prices': prices,
            'min_nights': min_nights,
        })

    return parsed


def create_sample_price_records(competitors, scrape_date):
    """
    Create sample price records based on manual observations.

    We'll create records for upcoming dates using the observed prices.
    """
    price_records = []

    # Sample dates over next 6 months
    sample_dates = [
        scrape_date + timedelta(days=15),   # 2 weeks out
        scrape_date + timedelta(days=45),   # 1.5 months out
        scrape_date + timedelta(days=75),   # 2.5 months out
        scrape_date + timedelta(days=105),  # 3.5 months out
        scrape_date + timedelta(days=135),  # 4.5 months out
        scrape_date + timedelta(days=165),  # 5.5 months out
    ]

    for comp in competitors:
        listing_id = comp['listing_id']
        prices = comp['observed_prices']

        if not prices:
            continue  # Skip if no pricing info

        # Use average of observed prices
        avg_price = sum(prices) / len(prices)

        # Create price records for each sample date
        for check_in_date in sample_dates:
            price_records.append({
                "scrape_date": scrape_date.isoformat(),
                "listing_id": listing_id,
                "check_in_date": check_in_date.isoformat(),
                "price_per_night": avg_price,
                "cleaning_fee": None,
                "service_fee": None,
                "total_price": avg_price * 3,  # Assume 3 night stay
                "nights": 3,
                "is_available": True,
                "min_nights": comp.get('min_nights'),
                "currency": "GBP",
            })

    return price_records


def create_listing_records(competitors, scrape_date):
    """Create competitor listing records."""
    listings = []

    for comp in competitors:
        listings.append({
            "listing_id": comp['listing_id'],
            "source": "airbnb",
            "name": comp['name'],
            "url": comp['url'],
            "property_type": "Entire cottage",  # From your notes
            "room_type": "Entire home/apt",
            "bedrooms": None,  # Could extract from notes if needed
            "bathrooms": None,
            "max_guests": 4,  # Typical for your area
            "latitude": None,  # Could geocode if needed
            "longitude": None,
            "rating": None,
            "review_count": None,
            "host_is_superhost": False,
            "instant_bookable": False,
            "first_seen_date": scrape_date.isoformat(),
            "last_seen_date": scrape_date.isoformat(),
            "is_active": True
        })

    return listings


def load_manual_data():
    """Load manual pricing data to BigQuery."""
    print("=" * 70)
    print("LOADING MANUAL PRICING DATA")
    print("=" * 70)

    scrape_date = date.today()
    project_id = "northcliffe-claude"

    # Parse competitors
    print("\n1. Parsing competitors.yaml...")
    competitors = parse_manual_pricing_notes()
    print(f"   Found {len(competitors)} competitors")

    # Show parsed pricing
    print("\n2. Parsed pricing observations:")
    for comp in competitors:
        listing_id = comp['listing_id']
        prices = comp['observed_prices']
        min_nights = comp['min_nights']

        if prices:
            avg_price = sum(prices) / len(prices)
            print(f"   {listing_id}: £{avg_price:.0f}/night (from {len(prices)} observations)")
            if min_nights:
                print(f"      Min nights: {min_nights}")
        else:
            print(f"   {listing_id}: No pricing data in notes")

    # Create records
    print("\n3. Creating records...")
    listings = create_listing_records(competitors, scrape_date)
    prices = create_sample_price_records(competitors, scrape_date)

    print(f"   Listings: {len(listings)}")
    print(f"   Price records: {len(prices)}")

    # Filter to only those with pricing
    prices = [p for p in prices if p['price_per_night'] is not None]
    print(f"   Price records with data: {len(prices)}")

    if not prices:
        print("\n⚠️  NO PRICING DATA PARSED FROM NOTES")
        print("   Check that competitors.yaml has pricing info in notes")
        print("   Example: 'charging 240 per night' or '400 per night summer'")
        return

    # Show sample
    print("\n4. Sample price records:")
    for price in prices[:3]:
        print(f"   {price['listing_id']}: {price['check_in_date']} = £{price['price_per_night']:.0f}/night")

    # Load to BigQuery
    print("\n5. Loading to BigQuery...")
    try:
        load_to_bigquery(listings, prices, project_id)
        print("   ✅ Successfully loaded to BigQuery!")

        # Verify
        client = bigquery.Client(project=project_id)

        query = f"""
            SELECT COUNT(*) as count
            FROM `{project_id}.pricing.daily_prices`
            WHERE scrape_date = '{scrape_date.isoformat()}'
        """
        results = list(client.query(query).result())
        count_today = results[0]['count']

        print(f"\n6. Verification:")
        print(f"   Price records loaded today: {count_today}")

        print(f"\n{'='*70}")
        print("✅ MANUAL DATA LOAD SUCCESSFUL!")
        print(f"{'='*70}")
        print(f"\nNext steps:")
        print(f"  1. Check BigQuery pricing.daily_prices table")
        print(f"  2. Update competitor notes with more pricing observations")
        print(f"  3. Re-run this script to add new data")

    except Exception as e:
        print(f"\n❌ ERROR loading to BigQuery: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    load_manual_data()
