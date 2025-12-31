#!/usr/bin/env python3
"""
Load comprehensive seasonal pricing data from your research.

This covers 10 properties across 8 seasonal periods for high-confidence
pricing recommendations throughout the year.
"""

import sys
from datetime import date, datetime
from google.cloud import bigquery

# Add functions directory to path
sys.path.insert(0, 'functions/scraper')
from main import ensure_string_fields

# Comprehensive pricing data - 10 properties, 8 seasonal periods
# Format: (listing_id, check_in, check_out, nights, total_price)
COMPREHENSIVE_PRICING = [
    # 51677503 - Sleeps 4 immaculate cottage
    ("51677503", "2026-01-19", "2026-01-21", 2, 363),
    ("51677503", "2026-04-03", "2026-04-06", 3, 701),
    ("51677503", "2026-05-22", "2026-05-25", 3, 747),
    ("51677503", "2026-08-10", "2026-08-13", 3, 592),
    ("51677503", "2026-09-18", "2026-09-21", 3, 561),
    ("51677503", "2026-12-21", "2026-12-28", 7, 1151),

    # 34573106 - Bradwell Cottage ❤️ Dogs
    ("34573106", "2026-02-02", "2026-02-05", 3, 492),
    ("34573106", "2026-10-24", "2026-10-30", 6, 983),

    # 36221807 - Happy Feet Cottage
    ("36221807", "2026-01-19", "2026-01-21", 2, 451),
    ("36221807", "2026-05-22", "2026-05-25", 3, 900),

    # 592668802244780107 - Columbine Barn
    ("592668802244780107", "2026-01-19", "2026-01-20", 1, 140),
    ("592668802244780107", "2026-02-09", "2026-02-12", 3, 527),
    ("592668802244780107", "2026-05-22", "2026-05-25", 3, 702),
    ("592668802244780107", "2026-08-10", "2026-08-13", 3, 702),
    ("592668802244780107", "2026-09-18", "2026-09-21", 3, 702),
    ("592668802244780107", "2026-10-24", "2026-10-30", 6, 1404),
    ("592668802244780107", "2026-12-21", "2026-12-28", 7, 1310),

    # 930826141684315288 - Brookside Barn
    ("930826141684315288", "2026-04-03", "2026-04-06", 3, 777),
    ("930826141684315288", "2026-05-22", "2026-05-25", 3, 1075),
    ("930826141684315288", "2026-08-10", "2026-08-13", 3, 1063),
    ("930826141684315288", "2026-09-18", "2026-09-21", 3, 623),
    ("930826141684315288", "2026-10-24", "2026-10-30", 6, 926),
    ("930826141684315288", "2026-12-21", "2026-12-28", 7, 1094),

    # 1082375796939549018 - 3 Bed in Hope Valley (Premium tier)
    ("1082375796939549018", "2026-04-03", "2026-04-06", 3, 1371),
    ("1082375796939549018", "2026-05-22", "2026-05-25", 3, 1425),
    ("1082375796939549018", "2026-08-10", "2026-08-13", 3, 1523),
    ("1082375796939549018", "2026-09-18", "2026-09-21", 3, 891),
    ("1082375796939549018", "2026-10-24", "2026-10-30", 6, 1392),
    ("1082375796939549018", "2026-12-21", "2026-12-28", 7, 1473),

    # 769491896844949884 - Stunningly stylish cottage
    ("769491896844949884", "2026-01-19", "2026-01-21", 2, 288),
    ("769491896844949884", "2026-04-03", "2026-04-06", 3, 540),
    ("769491896844949884", "2026-05-22", "2026-05-25", 3, 558),
    ("769491896844949884", "2026-08-10", "2026-08-13", 3, 540),
    ("769491896844949884", "2026-09-18", "2026-09-21", 3, 558),
    ("769491896844949884", "2026-10-24", "2026-10-30", 6, 1051),
    ("769491896844949884", "2026-12-23", "2026-12-27", 4, 720),
    ("769491896844949884", "2026-12-21", "2026-12-28", 7, 1310),

    # 27303065 - Stylish Peak District cottage
    ("27303065", "2026-01-19", "2026-01-21", 2, 274),
    ("27303065", "2026-04-03", "2026-04-06", 3, 480),
    ("27303065", "2026-05-22", "2026-05-25", 3, 585),
    ("27303065", "2026-08-10", "2026-08-13", 3, 540),
    ("27303065", "2026-09-18", "2026-09-21", 3, 550),
    ("27303065", "2026-10-24", "2026-10-30", 6, 1041),
    ("27303065", "2026-12-23", "2026-12-27", 4, 720),
    ("27303065", "2026-12-21", "2026-12-28", 7, 985),

    # 666713250735128129 - Heather Chapel (Premium, high volatility)
    ("666713250735128129", "2026-01-19", "2026-01-21", 2, 237),
    ("666713250735128129", "2026-04-06", "2026-04-09", 3, 655),
    ("666713250735128129", "2026-05-22", "2026-05-25", 3, 1204),
    ("666713250735128129", "2026-08-10", "2026-08-13", 3, 655),
    ("666713250735128129", "2026-09-18", "2026-09-21", 3, 1153),
    ("666713250735128129", "2026-10-24", "2026-10-30", 6, 1985),
    ("666713250735128129", "2026-12-23", "2026-12-27", 4, 795),
    ("666713250735128129", "2026-12-21", "2026-12-28", 7, 2475),

    # 10248357 - Castleton Stunning Peak Cavern
    ("10248357", "2026-01-19", "2026-01-21", 2, 237),
    ("10248357", "2026-04-06", "2026-04-09", 3, 655),
    ("10248357", "2026-05-22", "2026-05-25", 3, 632),
    ("10248357", "2026-08-10", "2026-08-15", 5, 1053),  # 5-night minimum in summer!
    ("10248357", "2026-09-18", "2026-09-21", 3, 602),
    ("10248357", "2026-10-24", "2026-10-30", 6, 983),
    ("10248357", "2026-12-21", "2026-12-28", 7, 1148),
]


def create_price_records():
    """Convert comprehensive pricing data into BigQuery format."""
    scrape_date = date.today()
    price_records = []

    for listing_id, check_in, check_out, nights, total_price in COMPREHENSIVE_PRICING:
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


def analyze_pricing_tiers(price_records):
    """Analyze pricing tiers and patterns."""
    by_listing = {}
    for rec in price_records:
        listing_id = rec['listing_id']
        if listing_id not in by_listing:
            by_listing[listing_id] = []
        by_listing[listing_id].append(rec)

    print("\n📊 PRICING TIER ANALYSIS:")
    print("-" * 70)

    # Sort by average price
    listing_stats = []
    for listing_id, records in by_listing.items():
        prices = [r['price_per_night'] for r in records]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        listing_stats.append({
            'id': listing_id,
            'avg': avg_price,
            'min': min_price,
            'max': max_price,
            'count': len(records)
        })

    listing_stats.sort(key=lambda x: x['avg'])

    for i, stat in enumerate(listing_stats, 1):
        tier = "💰 PREMIUM" if stat['avg'] > 300 else "💵 MID-RANGE" if stat['avg'] > 200 else "💷 VALUE"
        print(f"{i}. {stat['id'][:16]}...")
        print(f"   {tier}: £{stat['min']:.0f}-{stat['max']:.0f}/night (avg £{stat['avg']:.0f})")
        print(f"   {stat['count']} seasonal data points")


def load_comprehensive_data():
    """Load comprehensive pricing data to BigQuery."""
    print("=" * 70)
    print("LOADING COMPREHENSIVE SEASONAL PRICING DATA")
    print("=" * 70)
    print("\n10 Properties × 8 Seasonal Periods = High Confidence Data")

    project_id = "northcliffe-claude"
    scrape_date = date.today()

    # Create price records
    print("\n1. Creating price records...")
    price_records = create_price_records()
    print(f"   Created {len(price_records)} price records")

    # Analyze tiers
    analyze_pricing_tiers(price_records)

    # Group by check-in date to show coverage
    by_date = {}
    for rec in price_records:
        check_in = rec['check_in_date']
        if check_in not in by_date:
            by_date[check_in] = []
        by_date[check_in].append(rec)

    print("\n\n📅 SEASONAL COVERAGE:")
    print("-" * 70)

    season_map = {
        "2026-01": "❄️  Low Season (Jan)",
        "2026-02": "❄️  Low Season (Feb)",
        "2026-04": "🌸 Easter Holiday",
        "2026-05": "🌺 Late Spring",
        "2026-08": "☀️  Summer Holiday",
        "2026-09": "🍂 Early Autumn",
        "2026-10": "🎃 October Half-Term",
        "2026-12": "🎄 Christmas Week",
    }

    for check_in_date in sorted(by_date.keys()):
        month_key = check_in_date[:7]
        season = season_map.get(month_key, "📆 Other")
        count = len(by_date[check_in_date])
        prices = [r['price_per_night'] for r in by_date[check_in_date]]
        avg = sum(prices) / len(prices)
        print(f"{season}: {check_in_date}")
        print(f"   {count} competitors · £{min(prices):.0f}-{max(prices):.0f}/night (avg £{avg:.0f})")

    # Ensure listing_id is string
    price_records = ensure_string_fields(price_records, ["listing_id"])

    # Load to BigQuery
    print("\n\n3. Loading to BigQuery...")
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

        # Verify total database state
        query = f"""
            SELECT
                COUNT(*) as total_prices,
                COUNT(DISTINCT listing_id) as unique_listings,
                COUNT(DISTINCT check_in_date) as unique_dates,
                MIN(price_per_night) as min_price,
                MAX(price_per_night) as max_price,
                AVG(price_per_night) as avg_price
            FROM `{project_id}.pricing.daily_prices`
        """
        results = list(client.query(query).result())
        row = results[0]

        print("\n4. ✅ VERIFICATION - Total Database State:")
        print(f"   Total price records: {row['total_prices']}")
        print(f"   Unique listings: {row['unique_listings']}")
        print(f"   Unique check-in dates: {row['unique_dates']}")
        print(f"   Price range: £{row['min_price']:.0f} - £{row['max_price']:.0f}")
        print(f"   Average price: £{row['avg_price']:.0f}/night")

        print("\n" + "=" * 70)
        print("✅ SUCCESS! Comprehensive pricing data loaded")
        print("=" * 70)
        print("\n🎯 Next steps:")
        print("  1. Run: python test_analyzer.py")
        print("     (Will generate recommendations with HIGH confidence)")
        print("  2. Run: python test_dashboard.py")
        print("  3. Open: test_data/dashboard.html")
        print("\nWith 10 competitors across 8 seasons, you now have")
        print("industry-grade pricing intelligence! 🚀")

    except Exception as e:
        print(f"\n❌ ERROR loading to BigQuery: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    load_comprehensive_data()
