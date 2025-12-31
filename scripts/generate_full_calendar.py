#!/usr/bin/env python3
"""
Generate a full 365-day pricing calendar with:
- Real competitor data where available
- Interpolated prices for missing dates
- Length-of-stay discounts
"""

import sys
import os
from datetime import date, timedelta
from google.cloud import bigquery
import csv
import json

# Add functions directory to path
sys.path.insert(0, 'functions/analyzer')

# Set required environment variables
os.environ['GCP_PROJECT'] = 'northcliffe-claude'

from pricing import (
    generate_recommendation,
    interpolate_price,
    apply_length_of_stay_discount,
    PriceRecommendation
)


def get_existing_recommendations(project_id: str, recommendation_date: date):
    """Get all recommendations from most recent run."""
    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT
            target_date,
            recommended_price,
            min_price,
            max_price,
            comp_set_median,
            comp_set_min,
            comp_set_max,
            comp_set_count,
            factors,
            confidence
        FROM `{project_id}.pricing.price_recommendations`
        WHERE recommendation_date = @rec_date
        ORDER BY target_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("rec_date", "DATE", recommendation_date)
        ]
    )

    results = list(client.query(query, job_config=job_config).result())

    # Convert to PriceRecommendation objects
    recommendations = []
    for row in results:
        rec = PriceRecommendation(
            target_date=row.target_date.isoformat(),
            recommended_price=row.recommended_price,
            min_price=row.min_price,
            max_price=row.max_price,
            comp_set_median=row.comp_set_median,
            comp_set_min=row.comp_set_min,
            comp_set_max=row.comp_set_max,
            comp_set_count=row.comp_set_count,
            factors=row.factors,
            confidence=row.confidence
        )
        recommendations.append(rec)

    return recommendations


def get_events(project_id: str, start_date: date, end_date: date):
    """Get events for date range."""
    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT
            event_date,
            event_name,
            event_type,
            expected_impact
        FROM `{project_id}.pricing.events`
        WHERE event_date BETWEEN @start_date AND @end_date
        ORDER BY event_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    results = list(client.query(query, job_config=job_config).result())

    return [
        {
            "event_date": row.event_date.isoformat(),
            "event_name": row.event_name,
            "event_type": row.event_type,
            "expected_impact": row.expected_impact
        }
        for row in results
    ]


def generate_full_calendar(project_id: str, output_format: str = "csv"):
    """Generate 365-day pricing calendar."""

    print("=" * 90)
    print("GENERATING FULL 365-DAY PRICING CALENDAR")
    print("=" * 90)

    # Get existing recommendations
    print("\n1. Loading existing recommendations...")
    rec_date = date.today()
    known_recs = get_existing_recommendations(project_id, rec_date)
    print(f"   Found {len(known_recs)} recommendations with real competitor data")

    # Get events
    start_date = date.today()
    end_date = start_date + timedelta(days=365)
    events = get_events(project_id, start_date, end_date)
    print(f"   Loaded {len(events)} events for next year")

    # Generate full calendar
    print("\n2. Generating prices for all 365 days...")
    calendar = []
    known_dates = {date.fromisoformat(r.target_date) for r in known_recs}

    interpolated_count = 0
    real_data_count = 0

    for day_offset in range(1, 366):
        target_date = start_date + timedelta(days=day_offset)

        # Check if we have real data for this date
        if target_date in known_dates:
            # Use existing recommendation
            rec = next(r for r in known_recs if date.fromisoformat(r.target_date) == target_date)
            real_data_count += 1
        else:
            # Interpolate
            rec = interpolate_price(target_date, known_recs, events)
            if rec:
                interpolated_count += 1

        if rec:
            calendar.append(rec)

    print(f"   ✅ Generated {len(calendar)} daily prices")
    print(f"      - Real competitor data: {real_data_count} days")
    print(f"      - Interpolated: {interpolated_count} days")

    # Export calendar
    print(f"\n3. Exporting calendar as {output_format.upper()}...")

    if output_format == "csv":
        export_csv(calendar)
    elif output_format == "json":
        export_json(calendar)

    # Generate length-of-stay examples
    print("\n4. Length-of-Stay Discount Examples:")
    print("   " + "-" * 86)

    # Use a mid-range price for examples
    sample_price = 200
    for nights in [1, 2, 3, 7, 14]:
        result = apply_length_of_stay_discount(sample_price, nights)
        discount_text = f"({result['discount_percent']}% off)" if result['discount_percent'] > 0 else ""
        print(f"   {nights:2} night{'s' if nights > 1 else ' '}: "
              f"£{result['total_price']:,.0f} total "
              f"= £{result['effective_nightly_rate']:.0f}/night {discount_text}")

    print("\n" + "=" * 90)
    print("✅ FULL CALENDAR GENERATED!")
    print("=" * 90)
    print(f"\nFiles created:")
    print(f"  - pricing_calendar_{rec_date}.csv")
    print(f"  - pricing_calendar_{rec_date}.json")
    print(f"\nCalendar covers: {start_date + timedelta(days=1)} to {end_date}")


def export_csv(calendar: list):
    """Export calendar to CSV."""
    filename = f"pricing_calendar_{date.today()}.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'date', 'day_of_week', 'recommended_price', 'min_price', 'max_price',
            'confidence', 'competitor_count', 'data_type',
            # Length-of-stay totals
            '1_night_total', '3_nights_total', '3_nights_discount',
            '7_nights_total', '7_nights_discount',
            '14_nights_total', '14_nights_discount'
        ])
        writer.writeheader()

        for rec in calendar:
            target_date = date.fromisoformat(rec.target_date)

            # Calculate length-of-stay pricing
            stay_1 = apply_length_of_stay_discount(rec.recommended_price, 1)
            stay_3 = apply_length_of_stay_discount(rec.recommended_price, 3)
            stay_7 = apply_length_of_stay_discount(rec.recommended_price, 7)
            stay_14 = apply_length_of_stay_discount(rec.recommended_price, 14)

            writer.writerow({
                'date': rec.target_date,
                'day_of_week': target_date.strftime('%A'),
                'recommended_price': f"£{rec.recommended_price:.0f}",
                'min_price': f"£{rec.min_price:.0f}",
                'max_price': f"£{rec.max_price:.0f}",
                'confidence': rec.confidence,
                'competitor_count': rec.comp_set_count,
                'data_type': 'real' if rec.comp_set_count > 0 else 'interpolated',
                '1_night_total': f"£{stay_1['total_price']:.0f}",
                '3_nights_total': f"£{stay_3['total_price']:.0f}",
                '3_nights_discount': f"{stay_3['discount_percent']}%",
                '7_nights_total': f"£{stay_7['total_price']:.0f}",
                '7_nights_discount': f"{stay_7['discount_percent']}%",
                '14_nights_total': f"£{stay_14['total_price']:.0f}",
                '14_nights_discount': f"{stay_14['discount_percent']}%",
            })

    print(f"   ✅ Saved to: {filename}")


def export_json(calendar: list):
    """Export calendar to JSON."""
    filename = f"pricing_calendar_{date.today()}.json"

    calendar_data = {
        "generated_date": date.today().isoformat(),
        "total_days": len(calendar),
        "discount_tiers": {
            "3_nights": "5%",
            "7_nights": "10%",
            "14_nights": "15%"
        },
        "calendar": []
    }

    for rec in calendar:
        target_date = date.fromisoformat(rec.target_date)

        # Calculate length-of-stay pricing
        pricing_by_length = {}
        for nights in [1, 3, 7, 14, 30]:
            result = apply_length_of_stay_discount(rec.recommended_price, nights)
            pricing_by_length[f"{nights}_nights"] = result

        calendar_data["calendar"].append({
            "date": rec.target_date,
            "day_of_week": target_date.strftime('%A'),
            "nightly_rate": rec.recommended_price,
            "price_range": {
                "min": rec.min_price,
                "max": rec.max_price
            },
            "confidence": rec.confidence,
            "data_type": "real" if rec.comp_set_count > 0 else "interpolated",
            "competitor_count": rec.comp_set_count,
            "pricing_by_stay_length": pricing_by_length,
            "factors": rec.factors
        })

    with open(filename, 'w') as f:
        json.dump(calendar_data, f, indent=2)

    print(f"   ✅ Saved to: {filename}")


if __name__ == "__main__":
    project_id = "northcliffe-claude"

    # Generate both formats
    generate_full_calendar(project_id, "csv")

    print("\n💡 TIP: Length-of-stay discounts are included in the calendar!")
    print("   - 3+ nights: 5% off")
    print("   - 7+ nights: 10% off")
    print("   - 14+ nights: 15% off")
