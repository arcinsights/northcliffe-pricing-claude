"""
Pricing logic and recommendation engine.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import date
import statistics
import math


@dataclass
class PriceFactor:
    """A single pricing factor/multiplier."""
    name: str
    multiplier: float
    reason: str


@dataclass
class PriceRecommendation:
    """Complete price recommendation for a target date."""
    target_date: str  # ISO date
    recommended_price: float
    min_price: float
    max_price: float
    comp_set_median: Optional[float]
    comp_set_min: Optional[float]
    comp_set_max: Optional[float]
    comp_set_count: int
    factors: List[Dict]  # List of factor dicts
    confidence: str  # low, medium, high

    def to_bigquery_row(self, recommendation_date: date) -> Dict:
        """Convert to BigQuery row format."""
        return {
            "recommendation_date": recommendation_date.isoformat(),
            "target_date": self.target_date,
            "recommended_price": self.recommended_price,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "comp_set_median": self.comp_set_median,
            "comp_set_min": self.comp_set_min,
            "comp_set_max": self.comp_set_max,
            "comp_set_count": self.comp_set_count,
            "factors": self.factors,
            "confidence": self.confidence,
        }


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers (Haversine formula)."""
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def calculate_similarity_score(listing: Dict, target_property: Dict) -> float:
    """
    Score how similar a listing is to our property.
    Higher score = more similar = better comp.
    Max score: 100
    """
    score = 0.0

    # Bedroom match (30 points max)
    bedroom_diff = abs(listing.get('bedrooms', 0) - target_property.get('bedrooms', 0))
    if bedroom_diff == 0:
        score += 30
    elif bedroom_diff == 1:
        score += 15
    elif bedroom_diff == 2:
        score += 5

    # Bathroom match (15 points max)
    bathroom_diff = abs(listing.get('bathrooms', 0) - target_property.get('bathrooms', 0))
    if bathroom_diff <= 0.5:
        score += 15
    elif bathroom_diff <= 1:
        score += 8
    elif bathroom_diff <= 1.5:
        score += 3

    # Distance (20 points max) - closer is better
    if listing.get('latitude') and listing.get('longitude'):
        if target_property.get('latitude') and target_property.get('longitude'):
            distance_km = calculate_distance(
                listing['latitude'], listing['longitude'],
                target_property['latitude'], target_property['longitude']
            )
            if distance_km < 1:
                score += 20
            elif distance_km < 2:
                score += 15
            elif distance_km < 3:
                score += 10
            elif distance_km < 5:
                score += 5

    # Property type match (15 points max)
    if listing.get('property_type') == target_property.get('property_type'):
        score += 15

    # Guest capacity (10 points max)
    guest_diff = abs(listing.get('max_guests', 0) - target_property.get('max_guests', 0))
    if guest_diff == 0:
        score += 10
    elif guest_diff == 1:
        score += 7
    elif guest_diff == 2:
        score += 4

    # Amenity overlap (10 points max)
    listing_amenities = set(listing.get('amenities', []))
    target_amenities = set(target_property.get('amenities', []))
    if listing_amenities and target_amenities:
        key_amenities = {'Wifi', 'Kitchen', 'Washer', 'Free parking', 'Air conditioning'}
        common = listing_amenities & target_amenities
        key_overlap = common & key_amenities
        score += len(key_overlap) * 2

    return score


def select_comp_set(all_listings: List[Dict], target_property: Dict, max_comps: int = 15) -> List[Dict]:
    """Select the most relevant competitors based on similarity."""
    scored = []
    for listing in all_listings:
        score = calculate_similarity_score(listing, target_property)
        if score > 20:  # Minimum similarity threshold
            scored.append((listing, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top N with their scores
    return [
        {**listing, 'similarity_score': score}
        for listing, score in scored[:max_comps]
    ]


def calculate_base_price(comp_set_prices: List[float], amenity_premium: float = 0) -> Optional[float]:
    """
    Calculate base price from comp set.
    Uses median to avoid outlier influence.
    """
    if not comp_set_prices:
        return None

    median_price = statistics.median(comp_set_prices)
    return median_price + amenity_premium


def get_seasonality_factor(target_date: date) -> PriceFactor:
    """
    Determine seasonality multiplier based on month.
    TODO: Learn from historical data
    """
    month = target_date.month

    # UK/London seasonality (adjust for your market)
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
    day = target_date.weekday()  # 0 = Monday, 6 = Sunday

    if day == 4:  # Friday
        return PriceFactor("day_of_week", 1.15, "Friday night premium")
    elif day == 5:  # Saturday
        return PriceFactor("day_of_week", 1.20, "Saturday night premium")
    elif day == 6:  # Sunday
        return PriceFactor("day_of_week", 0.95, "Sunday discount")
    else:
        return PriceFactor("day_of_week", 1.0, "Weekday standard rate")


def get_lead_time_factor(days_until: int) -> PriceFactor:
    """Adjust price based on booking lead time."""
    if days_until <= 3:
        return PriceFactor("lead_time", 0.85, "Last-minute discount to fill gap")
    elif days_until <= 7:
        return PriceFactor("lead_time", 0.95, "Short notice slight discount")
    elif days_until > 90:
        return PriceFactor("lead_time", 0.95, "Far-out booking discount")
    else:
        return PriceFactor("lead_time", 1.0, "Standard lead time")


def get_demand_factor(comp_set_availability: float) -> PriceFactor:
    """
    Adjust based on market scarcity.
    comp_set_availability: % of comp set still available for this date (0-1)
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
    date_str = target_date.isoformat()
    date_events = [e for e in events if e['event_date'] == date_str]

    if not date_events:
        return PriceFactor("events", 1.0, "No major events")

    # Find highest impact event
    impact_multipliers = {"high": 1.5, "medium": 1.25, "low": 1.1}
    max_impact = max(
        date_events,
        key=lambda e: impact_multipliers.get(e.get('expected_impact', 'low'), 1.0)
    )

    multiplier = impact_multipliers.get(max_impact.get('expected_impact', 'low'), 1.0)
    return PriceFactor(
        "events",
        multiplier,
        f"Event: {max_impact['event_name']} ({max_impact.get('expected_impact', 'low')} impact)"
    )


def generate_recommendation(
    target_date: date,
    comp_set_prices: List[float],
    comp_set_availability: float,
    events: List[Dict],
    amenity_premium: float = 0,
) -> Optional[PriceRecommendation]:
    """Generate a price recommendation for a specific date."""

    # Calculate base price
    base_price = calculate_base_price(comp_set_prices, amenity_premium)

    if base_price is None or base_price <= 0:
        return None

    # Gather all factors
    days_until = (target_date - date.today()).days
    factors = [
        get_seasonality_factor(target_date),
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

    # Determine confidence based on comp set size
    confidence = "high" if len(comp_set_prices) >= 10 else \
                 "medium" if len(comp_set_prices) >= 5 else "low"

    # Convert factors to dicts for JSON storage
    factor_dicts = [asdict(f) for f in factors]

    return PriceRecommendation(
        target_date=target_date.isoformat(),
        recommended_price=recommended,
        min_price=min_price,
        max_price=max_price,
        comp_set_median=statistics.median(comp_set_prices) if comp_set_prices else None,
        comp_set_min=min(comp_set_prices) if comp_set_prices else None,
        comp_set_max=max(comp_set_prices) if comp_set_prices else None,
        comp_set_count=len(comp_set_prices),
        factors=factor_dicts,
        confidence=confidence
    )
