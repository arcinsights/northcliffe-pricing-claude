"""
Cloud Function to analyze competitor data and generate price recommendations.
Triggered after scraper completes or on its own schedule.

This function calculates pricing recommendations based on competitor data.
"""

import functions_framework
import os
from datetime import datetime, timedelta, date
from typing import List, Dict
from google.cloud import bigquery
from pricing import generate_recommendation, select_comp_set


def load_config() -> Dict:
    """Load property configuration."""
    return {
        "property": {
            "bedrooms": int(os.getenv("PROPERTY_BEDROOMS", "2")),
            "bathrooms": float(os.getenv("PROPERTY_BATHROOMS", "1")),
            "max_guests": int(os.getenv("PROPERTY_MAX_GUESTS", "4")),
            "property_type": os.getenv("PROPERTY_TYPE", "Entire home"),
            "amenities": os.getenv("PROPERTY_AMENITIES", "").split(",") if os.getenv("PROPERTY_AMENITIES") else [],
            "latitude": float(os.getenv("PROPERTY_LAT")) if os.getenv("PROPERTY_LAT") else None,
            "longitude": float(os.getenv("PROPERTY_LNG")) if os.getenv("PROPERTY_LNG") else None,
        },
        "amenity_premium": float(os.getenv("AMENITY_PREMIUM", "0")),
    }


def get_latest_listings(project_id: str) -> List[Dict]:
    """Fetch the latest competitor listings from BigQuery."""
    client = bigquery.Client(project=project_id)

    query = """
        SELECT
            listing_id,
            name,
            property_type,
            bedrooms,
            bathrooms,
            max_guests,
            latitude,
            longitude,
            rating,
            review_count,
            amenities,
            host_is_superhost,
            instant_bookable
        FROM `{project_id}.pricing.competitor_listings`
        WHERE is_active = TRUE
        AND last_seen_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        GROUP BY ALL  -- Deduplicate if needed
    """.format(project_id=project_id)

    results = client.query(query).result()
    return [dict(row) for row in results]


def get_comp_prices_for_date(
    project_id: str,
    comp_set_ids: List[str],
    target_date: date
) -> tuple[List[float], float]:
    """
    Get competitor prices and availability for a specific date.
    Returns (list of prices, availability_ratio)
    """
    client = bigquery.Client(project=project_id)

    query = """
        SELECT
            listing_id,
            price_per_night,
            is_available
        FROM `{project_id}.pricing.daily_prices`
        WHERE listing_id IN UNNEST(@listing_ids)
        AND check_in_date = @target_date
        AND scrape_date = (
            -- Get most recent scrape
            SELECT MAX(scrape_date)
            FROM `{project_id}.pricing.daily_prices`
            WHERE check_in_date = @target_date
        )
        AND price_per_night IS NOT NULL
        AND price_per_night > 0
    """.format(project_id=project_id)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("listing_ids", "STRING", comp_set_ids),
            bigquery.ScalarQueryParameter("target_date", "DATE", target_date),
        ]
    )

    results = client.query(query, job_config=job_config).result()
    rows = [dict(row) for row in results]

    if not rows:
        return [], 0.0

    # Extract prices and calculate availability
    prices = [row["price_per_night"] for row in rows if row["is_available"]]
    total_count = len(rows)
    available_count = sum(1 for row in rows if row["is_available"])
    availability_ratio = available_count / total_count if total_count > 0 else 0.0

    return prices, availability_ratio


def get_events(project_id: str, start_date: date, end_date: date) -> List[Dict]:
    """Fetch events from BigQuery for date range."""
    client = bigquery.Client(project=project_id)

    query = """
        SELECT
            event_date,
            event_name,
            event_type,
            expected_impact
        FROM `{project_id}.pricing.events`
        WHERE event_date BETWEEN @start_date AND @end_date
        ORDER BY event_date
    """.format(project_id=project_id)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    results = client.query(query, job_config=job_config).result()
    return [dict(row) for row in results]


def save_recommendations(project_id: str, recommendations: List[Dict]):
    """Save recommendations to BigQuery."""
    if not recommendations:
        print("No recommendations to save")
        return

    client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.pricing.price_recommendations"

    # Delete today's recommendations first (replace pattern)
    today = date.today().isoformat()
    delete_query = f"""
        DELETE FROM `{table_id}`
        WHERE recommendation_date = '{today}'
    """
    client.query(delete_query).result()

    # Insert new recommendations
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    job = client.load_table_from_json(
        recommendations, table_id, job_config=job_config
    )
    job.result()
    print(f"Saved {len(recommendations)} recommendations to {table_id}")


@functions_framework.http
def run_analysis(request):
    """
    Main entry point for analyzer function.
    Generates price recommendations for next 90 days.
    """
    try:
        project_id = os.getenv("GCP_PROJECT")
        config = load_config()

        print("Starting price analysis...")

        # Load competitor listings
        all_listings = get_latest_listings(project_id)
        print(f"Loaded {len(all_listings)} competitor listings")

        if not all_listings:
            return {
                "status": "warning",
                "message": "No competitor listings found"
            }, 200

        # Select comp set based on similarity
        comp_set = select_comp_set(
            all_listings,
            config["property"],
            max_comps=15
        )
        print(f"Selected comp set of {len(comp_set)} listings")

        if not comp_set:
            return {
                "status": "warning",
                "message": "No suitable competitors found"
            }, 200

        comp_set_ids = [c["listing_id"] for c in comp_set]

        # Get events for next 90 days
        start_date = date.today()
        end_date = start_date + timedelta(days=90)
        events = get_events(project_id, start_date, end_date)
        print(f"Loaded {len(events)} events")

        # Generate recommendations for each day
        recommendations = []
        recommendation_date = date.today()

        for day_offset in range(1, 91):  # Next 90 days
            target_date = date.today() + timedelta(days=day_offset)

            # Get competitor prices for this date
            prices, availability = get_comp_prices_for_date(
                project_id,
                comp_set_ids,
                target_date
            )

            if not prices:
                print(f"No price data for {target_date}, skipping")
                continue

            # Generate recommendation
            rec = generate_recommendation(
                target_date=target_date,
                comp_set_prices=prices,
                comp_set_availability=availability,
                events=events,
                amenity_premium=config["amenity_premium"],
            )

            if rec:
                recommendations.append(rec.to_bigquery_row(recommendation_date))

        print(f"Generated {len(recommendations)} recommendations")

        # Save to BigQuery
        save_recommendations(project_id, recommendations)

        return {
            "status": "success",
            "recommendations_generated": len(recommendations),
            "comp_set_size": len(comp_set),
            "recommendation_date": recommendation_date.isoformat(),
        }, 200

    except Exception as e:
        print(f"Error in analyzer: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500
