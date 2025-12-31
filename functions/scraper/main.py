"""
Cloud Function to scrape competitor calendar pricing data from Airbnb via Apify.
Uses manually-specified competitor listings to get full-year pricing data.
Updated to use new Apify token from Secret Manager.
"""

import functions_framework
import os
import json
from datetime import datetime, date
from typing import List, Dict, Any
from google.cloud import storage, bigquery, secretmanager
from apify_client import ApifyClient
import yaml


def load_competitors_config() -> List[Dict[str, str]]:
    """Load competitor listings from Cloud Storage config."""
    try:
        storage_client = storage.Client()
        bucket_name = f"{os.getenv('GCP_PROJECT')}-pricing-raw-data"
        bucket = storage_client.bucket(bucket_name)

        # Try to load from Cloud Storage first
        blob = bucket.blob("config/competitors.yaml")
        if blob.exists():
            config_content = blob.download_as_text()
            config = yaml.safe_load(config_content)
            return config.get('competitors', [])
    except Exception as e:
        print(f"Could not load competitors from Cloud Storage: {e}")

    # Fallback to empty list - user needs to upload competitors.yaml
    print("WARNING: No competitors configured. Upload competitors.yaml to Cloud Storage.")
    return []


def get_apify_token() -> str:
    """Retrieve Apify API token from Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT")
        name = f"projects/{project_id}/secrets/apify-api-token/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error retrieving Apify token: {e}")
        raise


def scrape_calendar_data(apify_token: str, competitor_urls: List[str]) -> List[Dict]:
    """
    Scrape full-year calendar pricing using Apify calendar scraper.

    This uses a calendar-focused scraper that provides 365 days of pricing data
    instead of just search results.
    """
    client = ApifyClient(apify_token)

    print(f"Starting calendar scrape for {len(competitor_urls)} listings...")

    # Try the calendar-focused scraper
    # simpleapi/airbnb-full-year-price-tracker-scraper expects listing URLs
    run_input = {
        "listingUrls": competitor_urls,
        "currency": "GBP",
        "proxyConfiguration": {"useApifyProxy": True},
    }

    try:
        # Use the full-year price tracker
        run = client.actor("simpleapi/airbnb-full-year-price-tracker-scraper").call(
            run_input=run_input
        )

        # Fetch results
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"Scraped calendar data for {len(items)} listings")
        return items

    except Exception as e:
        print(f"Calendar scraper failed: {e}")
        print("Falling back to alternative scraper...")

        # Fallback: Use room scraper with calendar data
        # This scraper provides detailed listing info including pricing calendars
        run_input_alt = {
            "startUrls": [{"url": url} for url in competitor_urls],
            "includeReviews": False,
            "currency": "GBP",
            "maxListings": len(competitor_urls),
            "proxyConfiguration": {"useApifyProxy": True},
        }

        run = client.actor("tri_angle/airbnb-rooms-urls-scraper").call(
            run_input=run_input_alt
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"Fallback scraper: Got {len(items)} listings")
        return items


def normalize_calendar_data(listing: Dict, scrape_date: date) -> Dict:
    """
    Normalize calendar scraper output to our schema.

    The calendar scraper provides daily pricing data - we need to extract:
    - Listing metadata (id, name, location, etc.)
    - Calendar array with dates and prices
    """
    # Extract listing ID from URL or id field
    listing_id = str(listing.get("id") or listing.get("listingId", "unknown"))

    # Basic listing info
    normalized = {
        "listing_id": listing_id,
        "source": "airbnb",
        "name": listing.get("name") or listing.get("title"),
        "url": listing.get("url"),
        "property_type": listing.get("propertyType") or listing.get("roomType"),
        "room_type": listing.get("roomType"),
        "bedrooms": listing.get("bedrooms"),
        "bathrooms": listing.get("bathrooms"),
        "max_guests": listing.get("maxGuests") or listing.get("personCapacity"),
        "latitude": listing.get("lat") or (listing.get("coordinates", {}).get("latitude") if listing.get("coordinates") else None),
        "longitude": listing.get("lng") or (listing.get("coordinates", {}).get("longitude") if listing.get("coordinates") else None),
        "rating": listing.get("rating", {}).get("guestSatisfaction") if isinstance(listing.get("rating"), dict) else listing.get("rating"),
        "review_count": listing.get("rating", {}).get("reviewsCount") if isinstance(listing.get("rating"), dict) else listing.get("reviewsCount") or listing.get("numberOfReviews"),
        "amenities": [],  # Empty array - amenities not needed for pricing
        "host_is_superhost": (listing.get("host") or {}).get("isSuperhost", False) if listing.get("host") else False,
        "instant_bookable": listing.get("instantBookable", False),
        "first_seen_date": scrape_date.isoformat(),
        "last_seen_date": scrape_date.isoformat(),
        "is_active": True,
        "calendar": listing.get("calendar") or listing.get("priceCalendar", [])
    }

    return normalized


def extract_daily_prices_from_calendar(listing: Dict, scrape_date: date) -> List[Dict]:
    """
    Extract daily pricing from calendar data.

    Calendar structure varies by scraper:
    - Full-year tracker: [{date, price, available}, ...]
    - Room scraper: {months: [{days: [{date, price, available}]}]}
    """
    prices = []
    listing_id = str(listing.get("listing_id") or listing.get("id"))

    calendar = listing.get("calendar") or listing.get("priceCalendar", [])

    # Handle array format (full-year tracker)
    if isinstance(calendar, list):
        for day in calendar:
            if day.get("date"):
                prices.append({
                    "scrape_date": scrape_date.isoformat(),
                    "listing_id": listing_id,
                    "check_in_date": day["date"],
                    "price_per_night": parse_price(day.get("price")),
                    "cleaning_fee": None,  # Not in calendar data
                    "service_fee": None,
                    "total_price": parse_price(day.get("price")),
                    "nights": 1,
                    "is_available": day.get("available", True),
                    "min_nights": day.get("minNights"),
                    "currency": "GBP",
                })

    # Handle nested format (room scraper)
    elif isinstance(calendar, dict):
        months = calendar.get("months", [])
        for month in months:
            for day in month.get("days", []):
                if day.get("date"):
                    prices.append({
                        "scrape_date": scrape_date.isoformat(),
                        "listing_id": listing_id,
                        "check_in_date": day["date"],
                        "price_per_night": parse_price(day.get("price")),
                        "cleaning_fee": None,
                        "service_fee": None,
                        "total_price": parse_price(day.get("price")),
                        "nights": 1,
                        "is_available": day.get("available", True),
                        "min_nights": day.get("minNights"),
                        "currency": "GBP",
                    })

    return prices


def parse_price(price_str):
    """Extract numeric price from string like '£150' or '$200.00'."""
    if not price_str:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)

    # Remove currency symbols and commas
    import re
    cleaned = re.sub(r'[£$,]', '', str(price_str))
    try:
        return float(cleaned)
    except ValueError:
        return None


def store_raw_data(data: List[Dict], bucket_name: str, scrape_date: date):
    """Store raw scraper output to Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    filename = f"raw/airbnb/{scrape_date.isoformat()}T{datetime.now().strftime('%H:%M:%S')}.json"
    blob = bucket.blob(filename)
    blob.upload_from_string(json.dumps(data, indent=2), content_type="application/json")

    print(f"Stored raw data to gs://{bucket_name}/{filename}")


def ensure_string_fields(data: List[Dict], string_fields: List[str]) -> List[Dict]:
    """Ensure specified fields are strings, not integers."""
    result = []
    for item in data:
        cleaned = item.copy()
        for field in string_fields:
            if field in cleaned and cleaned[field] is not None:
                cleaned[field] = str(cleaned[field])
        result.append(cleaned)
    return result


def load_to_bigquery(
    listings: List[Dict],
    prices: List[Dict],
    project_id: str,
    dataset_id: str = "pricing",
):
    """Load listings and pricing data to BigQuery."""
    client = bigquery.Client(project=project_id)

    # Load competitor listings (upsert logic - update if exists)
    if listings:
        # Ensure listing_id is always a string
        listings = ensure_string_fields(listings, ["listing_id"])

        # Debug: Print first listing to verify types
        if listings:
            print(f"DEBUG: First listing listing_id type: {type(listings[0].get('listing_id'))}, value: {listings[0].get('listing_id')}")

        listings_table = f"{project_id}.{dataset_id}.competitor_listings"

        # Get the table's schema to prevent auto-detection issues
        table = client.get_table(listings_table)

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,  # Use explicit schema
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        )

        job = client.load_table_from_json(
            listings, listings_table, job_config=job_config
        )
        try:
            job.result()
            print(f"Loaded {len(listings)} listings to {listings_table}")
        except Exception as e:
            if hasattr(job, 'errors') and job.errors:
                print(f"BigQuery load errors: {job.errors}")
            raise

    # Load daily prices
    if prices:
        # Ensure listing_id is always a string in prices too
        prices = ensure_string_fields(prices, ["listing_id"])

        prices_table = f"{project_id}.{dataset_id}.daily_prices"

        # Get the table's schema to prevent auto-detection issues
        table = client.get_table(prices_table)

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=table.schema,  # Use explicit schema
        )

        job = client.load_table_from_json(prices, prices_table, job_config=job_config)
        job.result()
        print(f"Loaded {len(prices)} price records to {prices_table}")


@functions_framework.http
def trigger_scrape(request):
    """
    HTTP Cloud Function entry point for scraping competitor pricing.
    """
    try:
        scrape_date = date.today()
        project_id = os.getenv("GCP_PROJECT")

        # Load competitor listings from config
        competitors = load_competitors_config()

        if not competitors:
            return {
                "error": "No competitors configured. Upload competitors.yaml to Cloud Storage.",
                "instructions": "Create config/competitors.yaml in gs://{project}-pricing-raw-data bucket"
            }, 400

        # Extract URLs
        competitor_urls = [c.get("url") for c in competitors if c.get("url")]

        if not competitor_urls:
            return {"error": "No valid competitor URLs found in config"}, 400

        print(f"Scraping {len(competitor_urls)} competitor listings...")

        # Get Apify token
        apify_token = get_apify_token()

        # Scrape calendar data
        raw_listings = scrape_calendar_data(apify_token, competitor_urls)

        # Store raw data
        bucket_name = f"{project_id}-pricing-raw-data"
        store_raw_data(raw_listings, bucket_name, scrape_date)

        # Normalize data
        normalized_listings = [
            normalize_calendar_data(l, scrape_date) for l in raw_listings
        ]

        # Extract daily prices from calendar
        all_prices = []
        for listing in normalized_listings:
            prices = extract_daily_prices_from_calendar(listing, scrape_date)
            all_prices.extend(prices)

        # Load to BigQuery
        load_to_bigquery(normalized_listings, all_prices, project_id)

        return {
            "status": "success",
            "scrape_date": scrape_date.isoformat(),
            "listings_scraped": len(normalized_listings),
            "price_records": len(all_prices),
            "competitors_configured": len(competitors),
        }

    except Exception as e:
        print(f"Error in scraper: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500

