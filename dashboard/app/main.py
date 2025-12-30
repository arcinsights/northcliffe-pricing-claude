"""
Smart Pricing Dashboard - FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import bigquery
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import calendar as cal

app = FastAPI(
    title="Smart Pricing Dashboard",
    description="Airbnb pricing intelligence system",
    version="1.0.0"
)

templates = Jinja2Templates(directory="app/templates")

# BigQuery client
PROJECT_ID = os.getenv("GCP_PROJECT")
bq_client = bigquery.Client(project=PROJECT_ID)


def get_recommendations_for_month(year: int, month: int) -> Dict[str, Dict]:
    """Get price recommendations for a specific month."""
    first_day = date(year, month, 1)
    last_day = date(year, month, cal.monthrange(year, month)[1])

    query = f"""
        SELECT
            target_date,
            recommended_price,
            min_price,
            max_price,
            comp_set_count,
            confidence
        FROM `{PROJECT_ID}.pricing.price_recommendations`
        WHERE target_date BETWEEN @start_date AND @end_date
        AND recommendation_date = (
            SELECT MAX(recommendation_date)
            FROM `{PROJECT_ID}.pricing.price_recommendations`
        )
        ORDER BY target_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", first_day),
            bigquery.ScalarQueryParameter("end_date", "DATE", last_day),
        ]
    )

    results = bq_client.query(query, job_config=job_config).result()

    # Convert to dict keyed by date
    recs = {}
    for row in results:
        recs[str(row.target_date)] = dict(row)

    return recs


def get_recommendation_for_date(target_date: str) -> Optional[Dict]:
    """Get detailed recommendation for a specific date."""
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
        FROM `{PROJECT_ID}.pricing.price_recommendations`
        WHERE target_date = @target_date
        AND recommendation_date = (
            SELECT MAX(recommendation_date)
            FROM `{PROJECT_ID}.pricing.price_recommendations`
            WHERE target_date = @target_date
        )
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("target_date", "DATE", target_date),
        ]
    )

    results = bq_client.query(query, job_config=job_config).result()

    for row in results:
        return dict(row)

    return None


def get_competitor_prices_for_date(target_date: str) -> List[Dict]:
    """Get competitor prices for a specific date with listing details."""
    query = f"""
        WITH latest_prices AS (
            SELECT
                p.listing_id,
                p.price_per_night,
                p.is_available
            FROM `{PROJECT_ID}.pricing.daily_prices` p
            WHERE p.check_in_date = @target_date
            AND p.scrape_date = (
                SELECT MAX(scrape_date)
                FROM `{PROJECT_ID}.pricing.daily_prices`
                WHERE check_in_date = @target_date
            )
        )
        SELECT
            l.listing_id,
            l.name,
            l.bedrooms,
            l.bathrooms,
            l.max_guests,
            l.rating,
            l.review_count,
            l.url,
            p.price_per_night,
            p.is_available
        FROM latest_prices p
        JOIN `{PROJECT_ID}.pricing.competitor_listings` l
            ON p.listing_id = l.listing_id
        WHERE p.price_per_night IS NOT NULL
        ORDER BY p.price_per_night ASC
        LIMIT 20
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("target_date", "DATE", target_date),
        ]
    )

    results = bq_client.query(query, job_config=job_config).result()
    return [dict(row) for row in results]


def get_events_for_month(year: int, month: int) -> List[Dict]:
    """Get events for a specific month."""
    first_day = date(year, month, 1)
    last_day = date(year, month, cal.monthrange(year, month)[1])

    query = f"""
        SELECT
            event_date,
            event_name,
            event_type,
            expected_impact
        FROM `{PROJECT_ID}.pricing.events`
        WHERE event_date BETWEEN @start_date AND @end_date
        ORDER BY event_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", first_day),
            bigquery.ScalarQueryParameter("end_date", "DATE", last_day),
        ]
    )

    results = bq_client.query(query, job_config=job_config).result()
    return [dict(row) for row in results]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, year: Optional[int] = None, month: Optional[int] = None):
    """Home page with calendar view."""
    today = date.today()
    year = year or today.year
    month = month or today.month

    # Get data
    recommendations = get_recommendations_for_month(year, month)
    events = get_events_for_month(year, month)

    # Build calendar structure
    month_name = cal.month_name[month]
    first_weekday, num_days = cal.monthrange(year, month)

    # Previous/next month navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "year": year,
            "month": month,
            "month_name": month_name,
            "first_weekday": first_weekday,
            "num_days": num_days,
            "recommendations": recommendations,
            "events": events,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "today": today.isoformat(),
        },
    )


@app.get("/date/{date_str}", response_class=HTMLResponse)
async def date_detail(request: Request, date_str: str):
    """Detailed view for a specific date."""
    recommendation = get_recommendation_for_date(date_str)
    competitors = get_competitor_prices_for_date(date_str)

    if not recommendation:
        return templates.TemplateResponse(
            "no_data.html",
            {"request": request, "date": date_str},
        )

    return templates.TemplateResponse(
        "date_detail.html",
        {
            "request": request,
            "date": date_str,
            "rec": recommendation,
            "competitors": competitors,
        },
    )


@app.get("/api/recommendations")
async def api_recommendations(start_date: str, end_date: str):
    """API endpoint for recommendations."""
    query = f"""
        SELECT
            target_date,
            recommended_price,
            min_price,
            max_price,
            confidence
        FROM `{PROJECT_ID}.pricing.price_recommendations`
        WHERE target_date BETWEEN @start_date AND @end_date
        AND recommendation_date = (
            SELECT MAX(recommendation_date)
            FROM `{PROJECT_ID}.pricing.price_recommendations`
        )
        ORDER BY target_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    results = bq_client.query(query, job_config=job_config).result()
    recs = [dict(row) for row in results]

    # Convert dates to strings for JSON
    for rec in recs:
        rec["target_date"] = str(rec["target_date"])

    return JSONResponse(content=recs)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
