# Smart Pricing System - Technical Plan

## Overview

A fully automated pricing intelligence system for short-term rentals, deployed on Google Cloud with complete CI/CD automation.

**Philosophy:** Start minimal, prove end-to-end automation works, then add features incrementally.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GOOGLE CLOUD                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐   │
│   │   Cloud      │     │   Cloud      │     │      Cloud Run           │   │
│   │   Scheduler  │────▶│   Functions  │────▶│      (Web Dashboard)     │   │
│   │   (Cron)     │     │   (Scraper)  │     │                          │   │
│   └──────────────┘     └──────────────┘     └──────────────────────────┘   │
│          │                    │                         │                   │
│          │                    ▼                         │                   │
│          │            ┌──────────────┐                  │                   │
│          │            │   Cloud      │                  │                   │
│          │            │   Storage    │                  │                   │
│          │            │   (Raw JSON) │                  │                   │
│          │            └──────────────┘                  │                   │
│          │                    │                         │                   │
│          │                    ▼                         │                   │
│          │            ┌──────────────┐                  │                   │
│          └───────────▶│   BigQuery   │◀─────────────────┘                   │
│                       │   (Analytics)│                                      │
│                       └──────────────┘                                      │
│                              │                                              │
│                              ▼                                              │
│                       ┌──────────────┐                                      │
│                       │   Looker     │                                      │
│                       │   Studio     │                                      │
│                       │  (Optional)  │                                      │
│                       └──────────────┘                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL SERVICES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐   │
│   │   Apify      │     │   GitHub     │     │      SendGrid/           │   │
│   │   (Scraping) │     │   Actions    │     │      Email               │   │
│   │              │     │   (CI/CD)    │     │      (Alerts)            │   │
│   └──────────────┘     └──────────────┘     └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Foundation (Week 1)

### Goal
Set up infrastructure-as-code and CI/CD pipeline. No features yet - just the bones.

### Deliverables

1. **Repository Structure**
```
pricing/
├── .github/
│   └── workflows/
│       ├── deploy-infra.yml      # Terraform deployment
│       ├── deploy-functions.yml  # Cloud Functions deployment
│       └── deploy-dashboard.yml  # Cloud Run deployment
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── environments/
│       ├── dev.tfvars
│       └── prod.tfvars
├── functions/
│   └── scraper/
│       ├── main.py
│       ├── requirements.txt
│       └── tests/
├── dashboard/
│   ├── Dockerfile
│   ├── app/
│   └── tests/
├── scripts/
│   └── setup-gcp.sh
└── README.md
```

2. **GCP Project Setup**
   - Create GCP project
   - Enable required APIs
   - Set up service accounts
   - Configure GitHub secrets for deployment

3. **Terraform Resources**
   - Cloud Storage bucket (raw data)
   - BigQuery dataset + tables
   - Cloud Scheduler job (placeholder)
   - Cloud Functions (placeholder)
   - Cloud Run service (placeholder)
   - IAM bindings

4. **CI/CD Pipelines**
   - Infrastructure deployment on `terraform/*` changes
   - Function deployment on `functions/*` changes
   - Dashboard deployment on `dashboard/*` changes
   - All deployments require PR approval for prod

### Infrastructure Costs (Estimated)
| Resource | Free Tier | Estimated Monthly |
|----------|-----------|-------------------|
| Cloud Functions | 2M invocations | ~$0 |
| Cloud Storage | 5GB | ~$0.50 |
| BigQuery | 10GB storage, 1TB query | ~$0 |
| Cloud Run | 2M requests | ~$0-5 |
| Cloud Scheduler | 3 free jobs | ~$0 |
| **Total** | | **~$5-10/month** |

---

## Phase 1: Data Collection (Week 2-3)

### Goal
Automated daily scraping of competitor listings from Airbnb (and optionally Booking.com).

### Components

#### 1.1 Apify Integration

**Why Apify:**
- Pre-built Airbnb & Booking.com scrapers
- Handles anti-bot measures
- $49/month for 49 Actor compute units (plenty for MVP)
- No infrastructure to maintain

**Scrapers to Use:**
- `dtrungtin/airbnb-scraper` - Airbnb listings
- `voyager/booking-scraper` - Booking.com (Phase 1.5)

#### 1.2 Competitor Configuration

```python
# config/competitors.yaml
property:
  name: "Northcliffe Property"
  airbnb_id: "YOUR_LISTING_ID"  # Optional - for tracking your own
  location:
    lat: 51.5074
    lng: -0.1278
    radius_km: 5
  attributes:
    bedrooms: 2
    bathrooms: 1
    max_guests: 4
    property_type: "entire_home"

search_config:
  # Define the search criteria for competitors
  location: "London, UK"  # Or coordinates
  checkin_offset_days: [7, 14, 30, 60, 90]  # Check prices for different lead times
  nights: [2, 3, 7]  # Different stay lengths
  guests: 4

filters:
  min_bedrooms: 1
  max_bedrooms: 3
  property_types: ["Entire home", "Entire apartment"]
  # Will filter results to similar properties
```

#### 1.3 Cloud Function: Scraper Trigger

```python
# functions/scraper/main.py
import functions_framework
from google.cloud import storage, bigquery
from apify_client import ApifyClient
import json
from datetime import datetime, timedelta

@functions_framework.http
def trigger_scrape(request):
    """
    Triggered by Cloud Scheduler daily.
    Initiates Apify scraper and stores results.
    """
    client = ApifyClient(os.environ['APIFY_TOKEN'])

    # Load config
    config = load_config()

    # Build search URLs for different date ranges
    searches = build_search_inputs(config)

    # Run Apify actor
    run = client.actor("dtrungtin/airbnb-scraper").call(
        run_input={
            "search": config['search_config']['location'],
            "startUrls": searches,
            "maxListings": 50,  # Limit for MVP
            "includeCalendar": True,  # Get availability
            "calendarMonths": 3,
        }
    )

    # Get results
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    # Store raw JSON to Cloud Storage
    store_raw_data(items)

    # Process and load to BigQuery
    process_and_load(items)

    return {"status": "success", "listings_scraped": len(items)}
```

#### 1.4 BigQuery Schema

```sql
-- Table: competitor_listings
CREATE TABLE pricing.competitor_listings (
  listing_id STRING,
  name STRING,
  url STRING,
  property_type STRING,
  room_type STRING,
  bedrooms INT64,
  bathrooms FLOAT64,
  max_guests INT64,
  latitude FLOAT64,
  longitude FLOAT64,
  rating FLOAT64,
  review_count INT64,
  amenities ARRAY<STRING>,
  host_is_superhost BOOLEAN,
  instant_bookable BOOLEAN,
  first_seen_date DATE,
  last_seen_date DATE,
  is_active BOOLEAN
);

-- Table: daily_prices (partitioned by scrape_date)
CREATE TABLE pricing.daily_prices (
  scrape_date DATE,
  listing_id STRING,
  check_in_date DATE,
  price_per_night FLOAT64,
  cleaning_fee FLOAT64,
  service_fee FLOAT64,
  total_price FLOAT64,
  nights INT64,
  is_available BOOLEAN,
  min_nights INT64,
  currency STRING
)
PARTITION BY scrape_date
CLUSTER BY listing_id, check_in_date;

-- Table: events (manual or API populated)
CREATE TABLE pricing.events (
  event_date DATE,
  event_name STRING,
  event_type STRING,  -- concert, sports, conference, holiday
  expected_impact STRING,  -- low, medium, high
  source STRING
);

-- Table: price_recommendations (generated)
CREATE TABLE pricing.price_recommendations (
  recommendation_date DATE,
  target_date DATE,
  recommended_price FLOAT64,
  min_price FLOAT64,
  max_price FLOAT64,
  comp_set_median FLOAT64,
  comp_set_min FLOAT64,
  comp_set_max FLOAT64,
  factors JSON,  -- {"seasonality": 1.2, "day_of_week": 1.1, ...}
  confidence STRING  -- low, medium, high
)
PARTITION BY recommendation_date;
```

#### 1.5 Cloud Scheduler

```hcl
# terraform/scheduler.tf
resource "google_cloud_scheduler_job" "daily_scrape" {
  name        = "daily-competitor-scrape"
  description = "Trigger daily competitor price scraping"
  schedule    = "0 6 * * *"  # 6 AM daily
  time_zone   = "Europe/London"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.scraper.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}
```

---

## Phase 2: Price Analysis Engine (Week 4-5)

### Goal
Calculate price recommendations based on competitor data.

### Components

#### 2.1 Comp Set Definition

```python
# functions/analyzer/comp_set.py

def calculate_similarity_score(listing, target_property):
    """
    Score how similar a listing is to our property.
    Higher score = more similar = better comp.
    """
    score = 0

    # Bedroom match (most important)
    bedroom_diff = abs(listing['bedrooms'] - target_property['bedrooms'])
    if bedroom_diff == 0:
        score += 30
    elif bedroom_diff == 1:
        score += 15

    # Bathroom match
    bathroom_diff = abs(listing['bathrooms'] - target_property['bathrooms'])
    if bathroom_diff <= 0.5:
        score += 15
    elif bathroom_diff <= 1:
        score += 8

    # Distance (within radius already, but closer is better)
    distance_km = calculate_distance(listing, target_property)
    if distance_km < 1:
        score += 20
    elif distance_km < 2:
        score += 15
    elif distance_km < 5:
        score += 10

    # Property type match
    if listing['property_type'] == target_property['property_type']:
        score += 15

    # Guest capacity
    guest_diff = abs(listing['max_guests'] - target_property['max_guests'])
    if guest_diff <= 1:
        score += 10
    elif guest_diff <= 2:
        score += 5

    # Amenity overlap
    common_amenities = set(listing['amenities']) & set(target_property['amenities'])
    key_amenities = {'Wifi', 'Kitchen', 'Washer', 'Free parking', 'Air conditioning'}
    key_overlap = common_amenities & key_amenities
    score += len(key_overlap) * 2

    return score


def select_comp_set(all_listings, target_property, max_comps=15):
    """Select the most relevant competitors."""
    scored = [
        (listing, calculate_similarity_score(listing, target_property))
        for listing in all_listings
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [listing for listing, score in scored[:max_comps]]
```

#### 2.2 Price Recommendation Engine

```python
# functions/analyzer/pricing.py

from dataclasses import dataclass
from typing import List, Dict
import statistics

@dataclass
class PriceFactor:
    name: str
    multiplier: float
    reason: str

@dataclass
class PriceRecommendation:
    target_date: date
    recommended_price: float
    min_price: float
    max_price: float
    factors: List[PriceFactor]
    comp_set_stats: Dict
    confidence: str


def calculate_base_price(comp_set_prices: List[float],
                         your_amenity_premium: float = 0) -> float:
    """
    Calculate base price from comp set.
    Uses median to avoid outlier influence.
    """
    if not comp_set_prices:
        return None

    median_price = statistics.median(comp_set_prices)
    return median_price + your_amenity_premium


def get_seasonality_factor(target_date: date,
                           historical_data: pd.DataFrame) -> PriceFactor:
    """
    Determine seasonality multiplier based on historical patterns.
    """
    month = target_date.month

    # Simple initial seasonality (can be refined with data)
    SEASONALITY = {
        1: 0.85,   # January - low
        2: 0.85,   # February - low
        3: 0.95,   # March - shoulder
        4: 1.05,   # April - shoulder/Easter
        5: 1.10,   # May - bank holidays
        6: 1.15,   # June - summer starts
        7: 1.25,   # July - peak
        8: 1.25,   # August - peak
        9: 1.05,   # September - shoulder
        10: 1.00,  # October - standard
        11: 0.90,  # November - low
        12: 1.10,  # December - holidays
    }

    multiplier = SEASONALITY.get(month, 1.0)
    season = "peak" if multiplier > 1.15 else "low" if multiplier < 0.9 else "standard"

    return PriceFactor(
        name="seasonality",
        multiplier=multiplier,
        reason=f"{target_date.strftime('%B')} is {season} season"
    )


def get_day_of_week_factor(target_date: date) -> PriceFactor:
    """Weekend premium."""
    day = target_date.weekday()

    if day == 4:  # Friday
        return PriceFactor("day_of_week", 1.15, "Friday night premium")
    elif day == 5:  # Saturday
        return PriceFactor("day_of_week", 1.20, "Saturday night premium")
    elif day == 6:  # Sunday
        return PriceFactor("day_of_week", 0.95, "Sunday discount")
    else:
        return PriceFactor("day_of_week", 1.0, "Weekday standard rate")


def get_lead_time_factor(days_until: int) -> PriceFactor:
    """Adjust price based on how far out the booking is."""
    if days_until <= 3:
        return PriceFactor("lead_time", 0.85, "Last-minute discount to fill gap")
    elif days_until <= 7:
        return PriceFactor("lead_time", 0.95, "Short notice slight discount")
    elif days_until > 90:
        return PriceFactor("lead_time", 0.95, "Far-out booking discount")
    else:
        return PriceFactor("lead_time", 1.0, "Standard lead time")


def get_demand_factor(comp_set_availability: float,
                      your_booking_pace: float = None) -> PriceFactor:
    """
    Adjust based on market scarcity.
    comp_set_availability: % of comp set still available for this date
    """
    if comp_set_availability < 0.3:  # 70%+ booked
        return PriceFactor("demand", 1.20, "High demand - most competitors booked")
    elif comp_set_availability < 0.5:
        return PriceFactor("demand", 1.10, "Moderate demand - competitors filling up")
    elif comp_set_availability > 0.8:
        return PriceFactor("demand", 0.95, "Low demand - many options available")
    else:
        return PriceFactor("demand", 1.0, "Normal market availability")


def get_event_factor(target_date: date, events: List[Dict]) -> PriceFactor:
    """Check for local events on this date."""
    date_events = [e for e in events if e['event_date'] == target_date]

    if not date_events:
        return PriceFactor("events", 1.0, "No major events")

    # Find highest impact event
    impact_multipliers = {"high": 1.5, "medium": 1.25, "low": 1.1}
    max_impact = max(date_events, key=lambda e: impact_multipliers.get(e['expected_impact'], 1.0))

    multiplier = impact_multipliers.get(max_impact['expected_impact'], 1.0)
    return PriceFactor(
        "events",
        multiplier,
        f"Event: {max_impact['event_name']} ({max_impact['expected_impact']} impact)"
    )


def generate_recommendation(
    target_date: date,
    comp_set_prices: List[float],
    comp_set_availability: float,
    events: List[Dict],
    amenity_premium: float = 0,
    historical_data: pd.DataFrame = None
) -> PriceRecommendation:
    """Generate a price recommendation for a specific date."""

    # Calculate base price
    base_price = calculate_base_price(comp_set_prices, amenity_premium)

    if base_price is None:
        return None

    # Gather all factors
    days_until = (target_date - date.today()).days
    factors = [
        get_seasonality_factor(target_date, historical_data),
        get_day_of_week_factor(target_date),
        get_lead_time_factor(days_until),
        get_demand_factor(comp_set_availability),
        get_event_factor(target_date, events),
    ]

    # Apply all multipliers
    total_multiplier = 1.0
    for factor in factors:
        total_multiplier *= factor.multiplier

    recommended = round(base_price * total_multiplier, 0)

    # Calculate range (±15%)
    min_price = round(recommended * 0.85, 0)
    max_price = round(recommended * 1.15, 0)

    # Determine confidence
    confidence = "high" if len(comp_set_prices) >= 10 else \
                 "medium" if len(comp_set_prices) >= 5 else "low"

    return PriceRecommendation(
        target_date=target_date,
        recommended_price=recommended,
        min_price=min_price,
        max_price=max_price,
        factors=factors,
        comp_set_stats={
            "median": statistics.median(comp_set_prices),
            "min": min(comp_set_prices),
            "max": max(comp_set_prices),
            "count": len(comp_set_prices),
            "availability_pct": comp_set_availability,
        },
        confidence=confidence
    )
```

#### 2.3 Daily Analysis Job

```python
# functions/analyzer/main.py

@functions_framework.http
def run_analysis(request):
    """
    Triggered after scraping completes.
    Generates price recommendations for next 90 days.
    """
    bq_client = bigquery.Client()

    # Load today's scraped data
    comp_listings = load_comp_set()
    events = load_events()

    recommendations = []

    for day_offset in range(1, 91):  # Next 90 days
        target_date = date.today() + timedelta(days=day_offset)

        # Get competitor prices and availability for this date
        prices, availability = get_comp_data_for_date(comp_listings, target_date)

        rec = generate_recommendation(
            target_date=target_date,
            comp_set_prices=prices,
            comp_set_availability=availability,
            events=events,
            amenity_premium=CONFIG['amenity_premium']
        )

        if rec:
            recommendations.append(rec)

    # Store to BigQuery
    save_recommendations(recommendations)

    # Optional: Send daily email summary
    send_summary_email(recommendations)

    return {"status": "success", "recommendations": len(recommendations)}
```

---

## Phase 3: Dashboard (Week 6-7)

### Goal
Simple web dashboard to view recommendations and competitor data.

### Tech Stack
- **Framework:** FastAPI + Jinja2 templates (simple, fast)
- **Styling:** Tailwind CSS (via CDN)
- **Charts:** Chart.js
- **Deployment:** Cloud Run

### Pages

#### 3.1 Home / Calendar View
```
┌─────────────────────────────────────────────────────────────┐
│  SMART PRICING DASHBOARD                     [Settings] [?] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ◀ January 2025 ▶                                           │
│  ┌────┬────┬────┬────┬────┬────┬────┐                       │
│  │Mon │Tue │Wed │Thu │Fri │Sat │Sun │                       │
│  ├────┼────┼────┼────┼────┼────┼────┤                       │
│  │    │    │ 1  │ 2  │ 3  │ 4  │ 5  │                       │
│  │    │    │£85 │£85 │£110│£125│£95 │                       │
│  ├────┼────┼────┼────┼────┼────┼────┤                       │
│  │ 6  │ 7  │ 8  │ 9  │ 10 │ 11 │ 12 │                       │
│  │£80 │£80 │£80 │£80 │£105│£120│£90 │                       │
│  └────┴────┴────┴────┴────┴────┴────┘                       │
│                                                              │
│  Legend: [Low £70-90] [Standard £90-110] [High £110+]       │
│                                                              │
│  📅 Events This Month:                                       │
│  • Jan 3-5: New Year Weekend (High impact)                  │
│  • Jan 25: Rugby Six Nations (Medium impact)                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 Date Detail View
```
┌─────────────────────────────────────────────────────────────┐
│  Friday, January 17, 2025                          [← Back] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RECOMMENDED PRICE                                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           £115 / night                                  │ │
│  │     Range: £98 - £132                                  │ │
│  │     Confidence: HIGH (12 comps)                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  WHY THIS PRICE                                             │
│  ├── Base (comp median): £95                               │
│  ├── Seasonality (Jan): ×0.85 (-15%)                       │
│  ├── Day of week (Fri): ×1.15 (+15%)                       │
│  ├── Lead time (30 days): ×1.00                            │
│  ├── Demand (40% avail): ×1.10 (+10%)                      │
│  └── Events: None                                           │
│      ─────────────────────                                  │
│      Final: £95 × 1.08 = £115                               │
│                                                              │
│  COMPETITOR SNAPSHOT                                         │
│  ┌──────────────────┬───────┬──────────┬─────────────────┐ │
│  │ Property         │ Price │ Status   │ Match Score     │ │
│  ├──────────────────┼───────┼──────────┼─────────────────┤ │
│  │ Cosy 2BR Flat    │ £110  │ Avail    │ ████████░░ 82%  │ │
│  │ Modern Apartment │ £125  │ Avail    │ ███████░░░ 75%  │ │
│  │ City View Studio │ £95   │ BOOKED   │ ██████░░░░ 65%  │ │
│  │ Luxury 2 Bed     │ £145  │ Avail    │ █████░░░░░ 55%  │ │
│  └──────────────────┴───────┴──────────┴─────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3 Competitors Page
```
┌─────────────────────────────────────────────────────────────┐
│  COMPETITOR TRACKING                         [+ Add Manual] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Your Comp Set (12 properties)                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ [Map showing your property + competitors]              │ │
│  │                      📍 You                             │ │
│  │           📍                    📍                      │ │
│  │                 📍        📍                            │ │
│  │      📍              📍                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Cosy 2BR Flat                              Score: 82%   ││
│  │ 2 bed · 1 bath · 4 guests · 0.8km away                 ││
│  │ ★ 4.85 (127 reviews) · Superhost                       ││
│  │ Avg price: £105/night · Occupancy: ~72%                ││
│  │ [View on Airbnb] [Price History]                       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dashboard Code Structure

```python
# dashboard/app/main.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from google.cloud import bigquery
import os

app = FastAPI(title="Smart Pricing Dashboard")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def home(request: Request):
    """Calendar view with price recommendations."""
    recommendations = get_recommendations_for_month()
    events = get_events_for_month()
    return templates.TemplateResponse(
        "calendar.html",
        {"request": request, "recommendations": recommendations, "events": events}
    )

@app.get("/date/{date}")
async def date_detail(request: Request, date: str):
    """Detailed view for a specific date."""
    recommendation = get_recommendation_for_date(date)
    competitors = get_competitor_prices_for_date(date)
    return templates.TemplateResponse(
        "date_detail.html",
        {"request": request, "rec": recommendation, "competitors": competitors}
    )

@app.get("/competitors")
async def competitors(request: Request):
    """View all tracked competitors."""
    comp_set = get_comp_set()
    return templates.TemplateResponse(
        "competitors.html",
        {"request": request, "competitors": comp_set}
    )

@app.get("/api/recommendations")
async def api_recommendations(start_date: str, end_date: str):
    """API endpoint for recommendations (for future integrations)."""
    return get_recommendations_range(start_date, end_date)
```

---

## Phase 4: Booking.com Integration (Week 8)

### Goal
Add Booking.com as a second data source for more comprehensive competitor view.

### Changes Required

1. **Add Booking.com Scraper**
```python
# Additional Apify actor
run = client.actor("voyager/booking-scraper").call(
    run_input={
        "search": config['search_config']['location'],
        "checkIn": check_in_date,
        "checkOut": check_out_date,
        "rooms": 1,
        "adults": config['search_config']['guests'],
    }
)
```

2. **Unified Data Model**
```sql
-- Add source column to track origin
ALTER TABLE pricing.competitor_listings ADD COLUMN source STRING;  -- 'airbnb' or 'booking'

-- Add cross-platform matching
ALTER TABLE pricing.competitor_listings ADD COLUMN canonical_id STRING;  -- For deduplication
```

3. **Price Comparison View**
```
┌─────────────────────────────────────────────────────────────┐
│  January 17, 2025 - Cross-Platform Comparison               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Airbnb Average: £115        Booking.com Average: £125      │
│  ████████████░░░░░░░░        ████████████████░░░░           │
│                                                              │
│  Your recommended price: £120 (split the difference)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## CI/CD Pipeline Details

### GitHub Actions Workflows

#### Infrastructure Deployment
```yaml
# .github/workflows/deploy-infra.yml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ['terraform/**']
  pull_request:
    paths: ['terraform/**']

env:
  TF_VERSION: '1.6.0'
  WORKLOAD_IDENTITY_PROVIDER: 'projects/123/locations/global/workloadIdentityPools/github/providers/github'
  SERVICE_ACCOUNT: 'terraform@project.iam.gserviceaccount.com'

jobs:
  plan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ env.WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ env.SERVICE_ACCOUNT }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Init
        working-directory: terraform
        run: terraform init

      - name: Terraform Plan
        working-directory: terraform
        run: terraform plan -var-file=environments/prod.tfvars -out=tfplan

      - name: Post Plan to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            // Post terraform plan output to PR

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4
      # ... auth steps ...

      - name: Terraform Apply
        working-directory: terraform
        run: terraform apply -auto-approve tfplan
```

#### Functions Deployment
```yaml
# .github/workflows/deploy-functions.yml
name: Deploy Cloud Functions

on:
  push:
    branches: [main]
    paths: ['functions/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install & Test
        working-directory: functions
        run: |
          pip install -r requirements-dev.txt
          pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        function: [scraper, analyzer]

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ env.WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ env.SERVICE_ACCOUNT }}

      - name: Deploy Function
        uses: google-github-actions/deploy-cloud-functions@v2
        with:
          name: ${{ matrix.function }}
          runtime: python311
          source_dir: functions/${{ matrix.function }}
          entry_point: main
          region: europe-west2
```

#### Dashboard Deployment
```yaml
# .github/workflows/deploy-dashboard.yml
name: Deploy Dashboard

on:
  push:
    branches: [main]
    paths: ['dashboard/**']

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ env.WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ env.SERVICE_ACCOUNT }}

      - name: Build & Push to Artifact Registry
        run: |
          gcloud builds submit dashboard \
            --tag europe-west2-docker.pkg.dev/$PROJECT_ID/pricing/dashboard:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy pricing-dashboard \
            --image europe-west2-docker.pkg.dev/$PROJECT_ID/pricing/dashboard:${{ github.sha }} \
            --region europe-west2 \
            --allow-unauthenticated
```

---

## Cost Summary

### Monthly Costs (MVP)

| Service | Estimated Cost |
|---------|----------------|
| GCP (Functions, Storage, BigQuery, Cloud Run) | ~$5-15 |
| Apify (scraping) | ~$49 |
| Domain (optional) | ~$1 |
| **Total** | **~$55-65/month** |

### Comparison
- PriceLabs: $20/listing/month
- Wheelhouse: $20/listing/month
- Your system: ~$55/month TOTAL (regardless of listings)

Break-even: 3 listings

---

## Future Enhancements (Post-MVP)

### V2 Features
- [ ] Email/SMS alerts for price recommendations
- [ ] Historical price trend charts
- [ ] Occupancy tracking for your property
- [ ] Multiple property support
- [ ] Mobile-friendly dashboard

### V3 Features (SaaS Ready)
- [ ] User authentication
- [ ] Property onboarding wizard
- [ ] Multi-tenant architecture
- [ ] Stripe billing integration
- [ ] ML-based recommendations (train on actual bookings)

### Data Enhancements
- [ ] Weather API integration
- [ ] Local events API (Ticketmaster, Eventbrite)
- [ ] School holiday calendars
- [ ] Flight price data (tourism demand proxy)

---

## Getting Started Checklist

### Prerequisites
- [ ] Google Cloud account with billing enabled
- [ ] GitHub repository created
- [ ] Apify account created
- [ ] Domain name (optional)

### Phase 0 Steps
1. [ ] Create GCP project
2. [ ] Enable APIs (Cloud Functions, Cloud Run, BigQuery, Cloud Storage, Cloud Scheduler)
3. [ ] Create service accounts
4. [ ] Set up Workload Identity Federation for GitHub Actions
5. [ ] Initialize Terraform state bucket
6. [ ] Create initial Terraform configs
7. [ ] Set up GitHub Actions workflows
8. [ ] Verify end-to-end deployment works (empty functions)

### Phase 1 Steps
1. [ ] Create Apify account and get API token
2. [ ] Define your property configuration
3. [ ] Implement scraper function
4. [ ] Set up BigQuery tables
5. [ ] Configure Cloud Scheduler
6. [ ] Test end-to-end scraping pipeline

---

## Questions to Decide

1. **Location**: Where is your property? (Needed for initial config)
2. **Property details**: Bedrooms, bathrooms, key amenities?
3. **Comp radius**: How far to look for competitors? (1km? 5km?)
4. **Budget priority**: Start with Apify ($49/mo) or free manual tracking first?
5. **Dashboard auth**: Password protected or public?
