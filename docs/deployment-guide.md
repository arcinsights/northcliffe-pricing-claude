# Deployment Guide - Pricing System

Complete guide to deploy and use your Airbnb pricing recommendation system.

## System Components

✅ **Scraper** - Stores competitor listings to BigQuery
✅ **Analyzer** - Generates pricing recommendations
✅ **Dashboard** - Visualizes pricing data
✅ **Manual Pricing** - Load manual price observations

## Current Status

### What's Working

- **BigQuery Tables**: All tables created and populated
  - `competitor_listings`: 11 competitors
  - `daily_prices`: 24 price records (4 competitors with pricing)
  - `price_recommendations`: 3 recommendations generated

- **Analyzer Function**: ✅ Tested locally, working
  - Generates pricing recommendations based on competitor data
  - Uses similarity scoring to select comparable properties
  - Adjusts prices based on demand and events

- **Dashboard**: ✅ Tested locally, working
  - Beautiful web interface showing pricing trends
  - Charts and tables with recommendations
  - Saved to `test_data/dashboard.html` for preview

- **Manual Pricing System**: ✅ Working
  - `load_manual_pricing.py` extracts pricing from competitors.yaml notes
  - Successfully loaded 24 price records

### What Needs More Data

- **Pricing Coverage**: Only 4 out of 11 competitors have pricing data
- **Recommendation**: Add pricing observations to competitors.yaml for remaining 7 properties

## Quick Start - Using Manual Pricing

### 1. Add More Pricing Observations

Edit [config/competitors.yaml](config/competitors.yaml) and add pricing observations in the `notes` field:

```yaml
- listing_id: "769491896844949884"
  name: "Stunningly stylish cottage"
  notes: "Charging 280 per night, 3 night min on weekends"
```

The script recognizes patterns like:
- "400 per night"
- "£240/night"
- "charging 170"
- "3 night min"

### 2. Load to BigQuery

```bash
source venv/bin/activate
python load_manual_pricing.py
```

This will:
- Parse pricing from your notes
- Create price records for 6 sample dates
- Load to BigQuery

### 3. Run Analyzer

```bash
python test_analyzer.py
```

This generates pricing recommendations for the next 90 days based on competitor data.

### 4. View Dashboard

```bash
python test_dashboard.py
open test_data/dashboard.html
```

The dashboard shows:
- Market statistics
- Price trends over time
- Specific recommendations for each day

## Full Deployment to Cloud Functions

When you're ready to deploy to production:

### Deploy Scraper (Optional - currently using manual pricing)

```bash
cd functions/scraper
gcloud functions deploy pricing-scraper \
  --gen2 \
  --runtime=python311 \
  --region=us-east1 \
  --source=. \
  --entry-point=trigger_scrape \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT=northcliffe-claude \
  --timeout=540s \
  --memory=512MB
```

### Deploy Analyzer

```bash
cd functions/analyzer
gcloud functions deploy pricing-analyzer \
  --gen2 \
  --runtime=python311 \
  --region=us-east1 \
  --source=. \
  --entry-point=run_analysis \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT=northcliffe-claude,PROPERTY_BEDROOMS=2,PROPERTY_BATHROOMS=1,PROPERTY_MAX_GUESTS=6 \
  --timeout=300s \
  --memory=512MB
```

### Deploy Dashboard

```bash
cd functions/dashboard
gcloud functions deploy pricing-dashboard \
  --gen2 \
  --runtime=python311 \
  --region=us-east1 \
  --source=. \
  --entry-point=dashboard \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT=northcliffe-claude \
  --timeout=60s \
  --memory=256MB
```

### Set Up Scheduler (Optional - for automation)

Run analyzer daily:

```bash
gcloud scheduler jobs create http pricing-daily-analysis \
  --location=us-east1 \
  --schedule="0 6 * * *" \
  --uri="https://us-east1-northcliffe-claude.cloudfunctions.net/pricing-analyzer" \
  --http-method=POST \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT@northcliffe-claude.iam.gserviceaccount.com
```

## Using the System

### View Current Recommendations

**Local testing:**
```bash
python test_dashboard.py
open test_data/dashboard.html
```

**After deployment:**
Navigate to your Cloud Function URL:
```
https://us-east1-northcliffe-claude.cloudfunctions.net/pricing-dashboard
```

### Update Pricing Data

#### Method 1: Manual (Recommended for now)

1. Check competitor listings on Airbnb
2. Note down prices in `competitors.yaml`
3. Run: `python load_manual_pricing.py`
4. Run: `python test_analyzer.py`
5. View: `python test_dashboard.py && open test_data/dashboard.html`

#### Method 2: Automated (When scraping works)

Configure scraper to run weekly via Cloud Scheduler.

### Interpret Recommendations

The analyzer provides:
- **Recommended Price**: Suggested nightly rate
- **Market Median**: What competitors are charging on average
- **Market Range**: Min/max competitor pricing
- **Confidence**:
  - High: 5+ similar competitors
  - Medium: 3-4 competitors
  - Low: 1-2 competitors (current state)

### Adjust Strategy

You can modify the pricing strategy by editing [functions/analyzer/pricing.py](functions/analyzer/pricing.py):

Current strategies:
- **Competitive** (default): Price at market median
- **Premium**: Price at 75th percentile
- **Value**: Price at 25th percentile
- **Aggressive**: Price 10% below median

## Maintenance

### Weekly Tasks

1. **Check competitor pricing** (10 minutes)
   - Browse 2-3 competitor listings on Airbnb
   - Update `competitors.yaml` with current prices

2. **Load new data** (2 minutes)
   ```bash
   python load_manual_pricing.py
   python test_analyzer.py
   ```

3. **Review recommendations** (5 minutes)
   ```bash
   python test_dashboard.py
   open test_data/dashboard.html
   ```

### Monthly Tasks

1. **Review competitor set**
   - Check if any competitors are no longer active
   - Add new competitors if they appear

2. **Analyze booking patterns**
   - Compare recommended prices vs actual bookings
   - Adjust strategy if needed

## Files Reference

### Core Functions
- `functions/scraper/main.py` - Scraper (currently unused)
- `functions/analyzer/main.py` - Analyzer (generates recommendations)
- `functions/analyzer/pricing.py` - Pricing logic
- `functions/dashboard/main.py` - Dashboard web interface

### Configuration
- `config/competitors.yaml` - Competitor listings and manual pricing
- `terraform/main.tf` - Infrastructure as code

### Data Loading
- `load_manual_pricing.py` - Load manual observations to BigQuery
- `test_analyzer.py` - Test analyzer locally
- `test_dashboard.py` - Test dashboard locally

### Documentation
- `PRICING_DATA_SOLUTION.md` - Manual pricing approach
- `DEPLOYMENT_GUIDE.md` - This file
- `README.md` - Project overview

## Troubleshooting

### "No price data for DATE, skipping"

This means there's no competitor pricing for that specific date in BigQuery.

**Solution**: Add more pricing observations to `competitors.yaml` and run `load_manual_pricing.py`.

### "No suitable competitors found"

The similarity scoring didn't find any comparable properties.

**Solution**: Check that competitors have bedrooms/bathrooms data. These fields are currently NULL for most listings.

### Dashboard shows old data

Recommendations are only regenerated when you run the analyzer.

**Solution**: Run `python test_analyzer.py` to generate fresh recommendations.

## Next Steps

1. ✅ System is functional with manual pricing
2. ⏳ Add pricing for remaining 7 competitors
3. ⏳ Deploy to Cloud Functions (optional - currently works locally)
4. ⏳ Set up weekly routine for updating prices
5. ⏳ Track actual bookings vs recommendations to refine strategy

## Support

If you encounter issues:
1. Check BigQuery tables have data
2. Review Cloud Function logs
3. Test functions locally first
4. Verify environment variables are set

The system is designed to work with minimal maintenance once pricing data is loaded.
