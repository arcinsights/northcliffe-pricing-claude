# Competitor Configuration

## Setup Instructions

1. **Find Your Competitors**
   - Search Airbnb for properties in Bradwell/Peak District area
   - Look for properties similar to yours (2BR, sleeps 4-6, cottage/home)
   - Select 10-15 active listings with good reviews

2. **Edit competitors.yaml**
   - Copy listing URLs from Airbnb (e.g., `https://www.airbnb.com/rooms/123456789`)
   - Extract listing ID from URL (the numbers after `/rooms/`)
   - Add name and notes for your reference

3. **Upload to Cloud Storage**
   ```bash
   # Upload competitors.yaml to Cloud Storage
   gsutil cp competitors.yaml gs://northcliffe-claude-pricing-raw-data/config/competitors.yaml
   ```

## Example Configuration

```yaml
competitors:
  - listing_id: "12345678"
    url: "https://www.airbnb.com/rooms/12345678"
    name: "Cozy Peak District Cottage"
    notes: "2BR, sleeps 6, 1km from Bradwell"

  - listing_id: "87654321"
    url: "https://www.airbnb.com/rooms/87654321"
    name: "Stone Cottage with Garden"
    notes: "2BR, sleeps 4, similar amenities"
```

## How It Works

1. The scraper reads this config file from Cloud Storage
2. It uses Apify's calendar scraper to get 365 days of pricing for each listing
3. Daily prices are stored in BigQuery for analysis
4. The analyzer compares your property to these competitors

## Cost Note

- Using calendar scraper: $10/month unlimited listings
- Much cheaper than pay-per-result ($1.25/1000 results)
- Run monthly to track pricing trends over time
