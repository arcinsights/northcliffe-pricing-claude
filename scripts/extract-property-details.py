#!/usr/bin/env python3
"""
Extract property details from Airbnb URL using Apify.
This populates config.yaml automatically.
"""

import os
import sys
import yaml
from apify_client import ApifyClient
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will use environment variables directly


def extract_from_airbnb_url(url: str, apify_token: str) -> dict:
    """Extract property details from Airbnb listing URL."""
    print(f"🔍 Extracting details from: {url}")

    client = ApifyClient(apify_token)

    # Use Apify's Airbnb scraper to get listing details
    print("⏳ Scraping listing details (this may take 30-60 seconds)...")
    print("   If this fails, the listing might be private or the scraper may need updating.")

    # Use the specialized room details scraper for direct listing URLs
    run_input = {
        "startUrls": [{"url": url}],  # Need to wrap URL in object with "url" key
        "maxListings": 1,
        "includeReviews": False,
        "currency": "GBP",
        "proxyConfiguration": {"useApifyProxy": True},
    }

    try:
        # Use tri_angle/airbnb-rooms-urls-scraper which is designed for direct room URLs
        run = client.actor("tri_angle/airbnb-rooms-urls-scraper").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    except Exception as e:
        print(f"\n❌ Apify scraper error: {str(e)}")
        print("\nPossible reasons:")
        print("1. Listing is private or unlisted")
        print("2. Apify token is invalid or out of credits")
        print("3. Rate limit reached")
        print("\nTry:")
        print("- Check the URL is accessible in a browser")
        print("- Verify your Apify account has credits")
        print("- Use manual configuration: cp config.example.yaml config.yaml")
        sys.exit(1)

    if not items:
        print("\n❌ No data returned from Apify scraper")
        print("\nDebugging info:")
        print(f"- Run ID: {run.get('id')}")
        print(f"- Status: {run.get('status')}")
        print(f"- Check run details: https://console.apify.com/actors/runs/{run.get('id')}")
        print("\nPossible solutions:")
        print("1. Check if listing is public (try opening URL in browser)")
        print("2. Try a different Airbnb listing URL to test")
        print("3. Use manual config: cp config.example.yaml config.yaml")
        sys.exit(1)

    listing = items[0]
    print(f"✅ Found listing: {listing.get('name', 'Unknown')}")

    # Extract relevant details
    details = {
        "property": {
            "name": listing.get("name", "My Airbnb Property"),
            "airbnb_id": listing.get("id"),
            "url": url,
            "location": {
                "city": listing.get("city") or extract_city_from_address(listing),
                "country": listing.get("country", "UK"),
                "lat": listing.get("coordinates", {}).get("latitude"),
                "lng": listing.get("coordinates", {}).get("longitude"),
                "radius_km": 3,  # Default search radius
            },
            "attributes": {
                "bedrooms": listing.get("bedrooms") or listing.get("beds", 1),
                "bathrooms": listing.get("bathrooms", 1),
                "max_guests": listing.get("maxGuests", 2),
                "property_type": listing.get("propertyType", "Entire home"),
            },
            "amenities": listing.get("amenities", [])[:10],  # Top 10 amenities
            "amenity_premium": 0,  # User can adjust this later
        },
        "search_config": {
            "platforms": ["airbnb"],
            "checkin_offset_days": [7, 14, 30, 60, 90],
            "nights": [2, 3, 7],
            "guests": listing.get("maxGuests", 2),
        },
        "filters": {
            "min_bedrooms": max(1, (listing.get("bedrooms") or 1) - 1),
            "max_bedrooms": (listing.get("bedrooms") or 1) + 1,
            "min_rating": 4.0,
            "max_comp_set_size": 15,
        },
        "gcp": {
            "project_id": "",  # User fills this
            "region": "europe-west2",
        },
        "apify": {
            "api_token": "",  # User fills this (or keeps in GitHub secrets)
        },
        "alerts": {
            "enabled": False,
            "email": "",
        },
    }

    return details


def extract_city_from_address(listing: dict) -> str:
    """Try to extract city from various address fields."""
    # Try different fields
    for field in ["city", "neighbourhood", "smartLocation", "publicAddress"]:
        if listing.get(field):
            # Extract first part before comma
            city = str(listing[field]).split(",")[0].strip()
            if city:
                return city

    # Fallback
    return "London"


def save_config(details: dict, output_path: str = "config.yaml"):
    """Save extracted details to config.yaml."""
    with open(output_path, 'w') as f:
        yaml.dump(details, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Configuration saved to {output_path}")


def display_summary(details: dict):
    """Display extracted details for user verification."""
    prop = details["property"]

    print("\n" + "="*60)
    print("📋 EXTRACTED PROPERTY DETAILS")
    print("="*60)
    print(f"Name:         {prop['name']}")
    print(f"Location:     {prop['location']['city']}, {prop['location']['country']}")
    print(f"Coordinates:  {prop['location']['lat']}, {prop['location']['lng']}")
    print(f"Bedrooms:     {prop['attributes']['bedrooms']}")
    print(f"Bathrooms:    {prop['attributes']['bathrooms']}")
    print(f"Max Guests:   {prop['attributes']['max_guests']}")
    print(f"Property Type: {prop['attributes']['property_type']}")
    print(f"\nTop Amenities:")
    for amenity in prop['amenities'][:5]:
        print(f"  - {amenity}")
    if len(prop['amenities']) > 5:
        print(f"  ... and {len(prop['amenities']) - 5} more")
    print("="*60)


def main():
    print("🏠 Airbnb Property Details Extractor")
    print("="*60)

    # Get Apify token from .env or environment
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        print("\n❌ APIFY_API_TOKEN not found")
        print("\nOption 1: Create .env file (recommended)")
        print("  cp .env.example .env")
        print("  # Edit .env and add your APIFY_API_TOKEN")
        print("\nOption 2: Set environment variable")
        print("  export APIFY_API_TOKEN='your-token-here'")
        print("\nGet your token from: https://console.apify.com/account/integrations")
        sys.exit(1)

    # Get Airbnb URL from .env, command line, or prompt
    url = os.getenv("AIRBNB_LISTING_URL")  # Try .env first

    if len(sys.argv) > 1:
        url = sys.argv[1]  # Command line overrides .env
    elif not url:
        # Not in .env or command line, prompt user
        print("\n💡 Tip: You can set AIRBNB_LISTING_URL in .env to avoid typing it each time")
        print("\nEnter your Airbnb listing URL:")
        print("(e.g., https://www.airbnb.com/rooms/12345678)")
        url = input("> ").strip()

    if not url or "airbnb." not in url or "/rooms/" not in url:
        print("❌ Invalid Airbnb URL")
        print("URL should be in format: https://www.airbnb.com/rooms/...")
        print("(works with .com, .co.uk, or any country domain)")
        sys.exit(1)

    # Extract details
    try:
        details = extract_from_airbnb_url(url, apify_token)
        display_summary(details)

        # Confirm
        print("\n💾 Save this configuration to config.yaml?")
        response = input("(y/n) > ").strip().lower()

        if response == 'y':
            save_config(details)
            print("\n✅ Done! You can now edit config.yaml if needed.")
            print("\nNext steps:")
            print("1. Update config.yaml with your GCP project_id")
            print("2. Run ./scripts/setup-gcp.sh")
            print("3. Deploy via git push")
        else:
            print("\n❌ Configuration not saved")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
