"""
Cloud Function to scrape competitor pricing data from Airbnb via Apify.
Triggered daily by Cloud Scheduler.

This function fetches competitor listings and pricing data.
"""

import functions_framework
import os
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from google.cloud import storage, bigquery, secretmanager
from apify_client import ApifyClient
import yaml


def load_config() -> Dict[str, Any]:
    """Load configuration from Cloud Storage or environment."""
    # In production, load from Cloud Storage
    # For now, using environment variables
    return {
        "property": {
            "location": {
                "city": os.getenv("PROPERTY_CITY", "London"),
                "country": os.getenv("PROPERTY_COUNTRY", "UK"),
                "radius_km": int(os.getenv("PROPERTY_RADIUS_KM", "3")),
            },
            "attributes": {
                "bedrooms": int(os.getenv("PROPERTY_BEDROOMS", "2")),
                "bathrooms": float(os.getenv("PROPERTY_BATHROOMS", "1")),
                "max_guests": int(os.getenv("PROPERTY_MAX_GUESTS", "4")),
            },
        },
        "search_config": {
            "location": os.getenv("SEARCH_LOCATION", "London, UK"),
            "checkin_offset_days": [7, 30, 60],  # Simplified for MVP
            "nights": [3, 7],
            "guests": int(os.getenv("PROPERTY_MAX_GUESTS", "4")),
        },
        "filters": {
            "min_bedrooms": 1,
            "max_bedrooms": 3,
            "min_rating": 4.0,
        },
    }


def get_apify_token() -> str:
    """Retrieve Apify API token from Secret Manager."""
    project_id = os.getenv("GCP_PROJECT")
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/apify-api-token/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def build_airbnb_search_urls(config: Dict) -> List[str]:
    """Build Airbnb search URLs for different date ranges."""
    base_location = config["search_config"]["location"]
    guests = config["search_config"]["guests"]

    urls = []
    for days_offset in config["search_config"]["checkin_offset_days"]:
        for nights in config["search_config"]["nights"]:
            checkin = date.today() + timedelta(days=days_offset)
            checkout = checkin + timedelta(days=nights)

            # Airbnb search URL format
            url = (
                f"https://www.airbnb.com/s/{base_location.replace(' ', '-')}/homes"
                f"?checkin={checkin.isoformat()}"
                f"&checkout={checkout.isoformat()}"
                f"&adults={guests}"
            )
            urls.append(url)

    return urls


def scrape_airbnb_data(apify_token: str, search_urls: List[str]) -> List[Dict]:
    """Run Apify Airbnb scraper and return results."""
    client = ApifyClient(apify_token)

    # Using the popular Airbnb scraper
    run_input = {
        "startUrls": [{"url": url} for url in search_urls],
        "maxListings": 50,  # Limit for MVP
        "includeReviews": False,  # Don't need reviews for pricing
        "calendarMonths": 3,  # Get 3 months of calendar data
        "currency": "GBP",
        "proxyConfiguration": {"useApifyProxy": True},
    }

    print(f"Starting Apify scraper with {len(search_urls)} search URLs...")
    run = client.actor("dtrungtin/airbnb-scraper").call(run_input=run_input)

    # Fetch results
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Scraped {len(items)} listings from Airbnb")

    return items


def store_raw_data(items: List[Dict], bucket_name: str):
    """Store raw JSON to Cloud Storage for backup."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    timestamp = datetime.now().isoformat()
    blob_name = f"raw/airbnb/{timestamp}.json"
    blob = bucket.blob(blob_name)

    blob.upload_from_string(
        json.dumps(items, indent=2),
        content_type="application/json"
    )

    print(f"Stored raw data to gs://{bucket_name}/{blob_name}")


def normalize_listing(listing: Dict) -> Dict:
    """Normalize Airbnb listing data to our schema."""
    return {
        "listing_id": str(listing.get("id")),
        "source": "airbnb",
        "name": listing.get("name"),
        "url": listing.get("url"),
        "property_type": listing.get("propertyType"),
        "room_type": listing.get("roomType"),
        "bedrooms": listing.get("beds") or listing.get("bedrooms"),
        "bathrooms": listing.get("bathrooms"),
        "max_guests": listing.get("maxGuests"),
        "latitude": listing.get("coordinates", {}).get("latitude"),
        "longitude": listing.get("coordinates", {}).get("longitude"),
        "rating": listing.get("rating"),
        "review_count": listing.get("reviewsCount"),
        "amenities": listing.get("amenities", []),
        "host_is_superhost": listing.get("host", {}).get("isSuperhost", False),
        "instant_bookable": listing.get("instantBookable", False),
        "first_seen_date": date.today().isoformat(),
        "last_seen_date": date.today().isoformat(),
        "is_active": True,
    }


def extract_calendar_prices(listing: Dict, scrape_date: date) -> List[Dict]:
    """Extract daily pricing from listing calendar data."""
    prices = []
    calendar = listing.get("calendar", {})

    # Calendar structure: {months: [{days: [{date, price, available}]}]}
    for month in calendar.get("months", []):
        for day in month.get("days", []):
            if day.get("date"):
                prices.append({
                    "scrape_date": scrape_date.isoformat(),
                    "listing_id": str(listing.get("id")),
                    "check_in_date": day["date"],
                    "price_per_night": day.get("price", {}).get("amount"),
                    "is_available": day.get("available", False),
                    "min_nights": listing.get("minNights"),
                    "currency": day.get("price", {}).get("currency", "GBP"),
                    "nights": 1,  # Single night price
                    "cleaning_fee": None,  # Not in calendar data
                    "service_fee": None,
                })

    return prices


def load_to_bigquery(listings: List[Dict], prices: List[Dict], project_id: str):
    """Load normalized data to BigQuery."""
    client = bigquery.Client(project=project_id)

    # Load listings (upsert logic)
    if listings:
        # For MVP, we'll just append and handle duplicates in queries
        # In production, use MERGE statement
        table_id = f"{project_id}.pricing.competitor_listings"

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION
            ],
        )

        job = client.load_table_from_json(
            listings, table_id, job_config=job_config
        )
        job.result()
        print(f"Loaded {len(listings)} listings to {table_id}")

    # Load daily prices
    if prices:
        table_id = f"{project_id}.pricing.daily_prices"

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        job = client.load_table_from_json(
            prices, table_id, job_config=job_config
        )
        job.result()
        print(f"Loaded {len(prices)} price records to {table_id}")


@functions_framework.http
def trigger_scrape(request):
    """
    Main entry point for Cloud Function.
    Triggered by Cloud Scheduler daily.
    """
    try:
        # Load configuration
        config = load_config()
        project_id = os.getenv("GCP_PROJECT")
        bucket_name = f"{project_id}-pricing-raw-data"

        # Get Apify token
        apify_token = get_apify_token()

        # Build search URLs
        search_urls = build_airbnb_search_urls(config)
        print(f"Built {len(search_urls)} search URLs")

        # Scrape Airbnb
        raw_listings = scrape_airbnb_data(apify_token, search_urls)

        if not raw_listings:
            return {"status": "warning", "message": "No listings scraped"}, 200

        # Store raw data
        store_raw_data(raw_listings, bucket_name)

        # Normalize listings
        normalized_listings = [normalize_listing(l) for l in raw_listings]

        # Extract pricing data
        all_prices = []
        scrape_date = date.today()
        for listing in raw_listings:
            prices = extract_calendar_prices(listing, scrape_date)
            all_prices.extend(prices)

        # Load to BigQuery
        load_to_bigquery(normalized_listings, all_prices, project_id)

        # Trigger analyzer function (will be implemented in Phase 2)
        # For now, analyzer will run on its own schedule

        return {
            "status": "success",
            "listings_scraped": len(normalized_listings),
            "price_records": len(all_prices),
            "scrape_date": scrape_date.isoformat(),
        }, 200

    except Exception as e:
        print(f"Error in scraper: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500
