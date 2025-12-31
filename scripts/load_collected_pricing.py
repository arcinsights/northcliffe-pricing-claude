#!/usr/bin/env python3
"""
Load collected pricing data from your seasonal research into BigQuery.

This script processes the raw pricing data you collected from Airbnb
and loads it into the daily_prices table with proper per-night calculations.
"""

import sys
from datetime import date, datetime
from google.cloud import bigquery

# Add functions directory to path
sys.path.insert(0, 'functions/scraper')
from main import ensure_string_fields

# Your collected pricing data
# Format: listing_id, check_in, check_out, nights, total_price
COLLECTED_PRICING = [
    # 769491896844949884 - Stunningly stylish cottage
    ("769491896844949884", "2026-01-19", "2026-01-21", 2, 288),
    ("769491896844949884", "2026-04-03", "2026-04-06", 3, 540),
    ("769491896844949884", "2026-08-10", "2026-08-13", 3, 540),
    ("769491896844949884", "2026-12-23", "2026-12-27", 4, 720),

    # 27303065 - Stylish Peak District holiday let cottage
    ("27303065", "2026-01-19", "2026-01-21", 2, 274),
    ("27303065", "2026-04-03", "2026-04-06", 3, 480),
    ("27303065", "2026-08-10", "2026-08-13", 3, 540),
    ("27303065", "2026-12-23", "2026-12-27", 4, 720),

    # 666713250735128129 - Heather Chapel (main competitor)
    ("666713250735128129", "2026-01-19", "2026-01-21", 2, 237),
    ("666713250735128129", "2026-04-06", "2026-04-09", 3, 655),
    ("666713250735128129", "2026-08-10", "2026-08-13", 3, 655),
    ("666713250735128129", "2026-12-23", "2026-12-27", 4, 795),

    # 10248357 - Castleton Stunning Peak Cavern Gorge Location
    ("10248357", "2026-01-19", "2026-01-21", 2, 237),
    ("10248357", "2026-04-06", "2026-04-09", 3, 655),

    # 51677503 - Sleeps 4 immaculate cottage
    ("51677503", "2026-01-19", "2026-01-21", 2, 288),
    ("51677503", "2026-04-03", "2026-04-06", 3, 540),
    ("51677503", "2026-08-10", "2026-08-13", 3, 720),

    # 36221807 - Happy Feet Cottage
    ("36221807", "2026-01-19", "2026-01-21", 2, 274),

    # 592668802244780107 - Columbine Barn
    ("592668802244780107", "2026-01-19", "2026-01-20", 1, 140),
    ("592668802244780107", "2026-08-10", "2026-08-13", 3, 702),

    # 930826141684315288 - Brookside Barn
    ("930826141684315288", "2026-04-03", "2026-04-06", 3, 777),
    ("930826141684315288", "2026-08-10", "2026-08-13", 3, 1063),

    # 1082375796939549018 - 3 Bed in Hope Valley
    ("1082375796939549018", "2026-04-03", "2026-04-06", 3, 1371),
    ("1082375796939549018", "2026-08-10", "2026-08-13", 3, 1523),
]


def create_price_records():
    """Convert collected pricing data into BigQuery format."""
    scrape_date = date.today()
    price_records = []

    for listing_id, check_in, check_out, nights, total_price in COLLECTED_PRICING:
        # Calculate per-night price
        price_per_night = total_price / nights if nights > 0 else total_price

        price_records.append({
            "scrape_date": scrape_date.isoformat(),
            "listing_id": listing_id,
            "check_in_date": check_in,
            "price_per_night": price_per_night,
            "cleaning_fee": None,  # Included in total
            "service_fee": None,   # Included in total
            "total_price": float(total_price),
            "nights": nights,
            "is_available": True,
            "min_nights": None,
            "currency": "GBP",
        })

    return price_records


def load_pricing_data():
    """Load collected pricing data to BigQuery."""
    print("=" * 70)
    print("LOADING COLLECTED PRICING DATA")
    print("=" * 70)

    project_id = "northcliffe-claude"
    scrape_date = date.today()

    # Create price records
    print("\n1. Creating price records...")
    price_records = create_price_records()
    print(f"   Created {len(price_records)} price records")

    # Group by listing to show summary
    by_listing = {}
    for rec in price_records:
        listing_id = rec['listing_id']
        if listing_id not in by_listing:
            by_listing[listing_id] = []
        by_listing[listing_id].append(rec)

    print("\n2. Summary by competitor:")
    for listing_id, records in sorted(by_listing.items()):
        prices = [r['price_per_night'] for r in records]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        print(f"   {listing_id}:")
        print(f"      {len(records)} dates, £{min_price:.0f}-{max_price:.0f}/night (avg £{avg_price:.0f})")

    # Ensure listing_id is string
    price_records = ensure_string_fields(price_records, ["listing_id"])

    # Load to BigQuery
    print("\n3. Loading to BigQuery...")
    try:
        client = bigquery.Client(project=project_id)
        table_id = f"{project_id}.pricing.daily_prices"

        # Get the table's schema
        table = client.get_table(table_id)

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,
        )

        job = client.load_table_from_json(price_records, table_id, job_config=job_config)
        job.result()

        print(f"   ✅ Successfully loaded {len(price_records)} price records!")

        # Verify
        query = f"""
            SELECT
                COUNT(*) as total_prices,
                COUNT(DISTINCT listing_id) as unique_listings,
                MIN(price_per_night) as min_price,
                MAX(price_per_night) as max_price,
                AVG(price_per_night) as avg_price
            FROM `{project_id}.pricing.daily_prices`
        """
        results = list(client.query(query).result())
        row = results[0]

        print("\n4. Verification - Total database state:")
        print(f"   Total price records: {row['total_prices']}")
        print(f"   Unique listings: {row['unique_listings']}")
        print(f"   Price range: £{row['min_price']:.0f} - £{row['max_price']:.0f}")
        print(f"   Average price: £{row['avg_price']:.0f}/night")

        # Show coverage by date
        query = f"""
            SELECT
                check_in_date,
                COUNT(*) as competitor_count,
                MIN(price_per_night) as min_price,
                MAX(price_per_night) as max_price,
                AVG(price_per_night) as avg_price
            FROM `{project_id}.pricing.daily_prices`
            WHERE scrape_date = '{scrape_date.isoformat()}'
            GROUP BY check_in_date
            ORDER BY check_in_date
        """
        results = list(client.query(query).result())

        print("\n5. Today's data by check-in date:")
        for row in results:
            print(f"   {row['check_in_date']}: {row['competitor_count']} competitors")
            print(f"      £{row['min_price']:.0f} - £{row['max_price']:.0f} (avg £{row['avg_price']:.0f})")

        print("\n" + "=" * 70)
        print("✅ SUCCESS! Pricing data loaded")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Run: python test_analyzer.py")
        print("  2. Run: python test_dashboard.py")
        print("  3. Open: test_data/dashboard.html")

    except Exception as e:
        print(f"\n❌ ERROR loading to BigQuery: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    load_pricing_data()
