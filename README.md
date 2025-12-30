# Smart Pricing for Short-Term Rentals

Automated pricing intelligence system for Airbnb and Booking.com properties.

## Features

- 🤖 **Automated daily competitor tracking** via Apify
- 📊 **Smart price recommendations** based on market data
- 📅 **Event-aware pricing** (holidays, local events)
- 🎯 **Intelligent comp set** matching
- 📈 **Web dashboard** for viewing recommendations
- ☁️ **Fully automated** deployment on Google Cloud
- 💰 **Cost-effective** (~$55/month total vs $20/listing/month for competitors)

## Architecture

```
Cloud Scheduler → Cloud Functions (Scraper) → BigQuery → Cloud Run (Dashboard)
                        ↓
                    Apify API
```

## Quick Start

### Prerequisites

1. **Google Cloud account** with billing enabled
2. **GitHub account**
3. **Apify account** (free tier available)

### Setup (10 minutes)

1. **Clone repository:**
   ```bash
   git clone <your-repo>
   cd pricing
   ```

2. **Auto-extract your property details (recommended):**
   ```bash
   pip install -r scripts/requirements.txt
   export APIFY_API_TOKEN='your-token'
   python scripts/extract-property-details.py https://www.airbnb.com/rooms/YOUR-LISTING-ID
   ```

   This automatically creates `config.yaml` with all your property details!

   *Or manually create config.yaml: `cp config.example.yaml config.yaml` and edit*

3. **Set up GCP:**
   ```bash
   ./scripts/setup-gcp.sh
   ```

4. **Configure GitHub secrets:**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add:
     - `GCP_PROJECT_ID`: Your GCP project ID
     - `GCP_WORKLOAD_IDENTITY_PROVIDER`: From setup script output
     - `GCP_SERVICE_ACCOUNT`: From setup script output
     - `APIFY_API_TOKEN`: From https://console.apify.com/account/integrations

5. **Deploy:**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push origin main
   ```

GitHub Actions will automatically deploy everything!

## Usage

### View Dashboard

After deployment, get your dashboard URL:
```bash
gcloud run services describe pricing-dashboard --region=europe-west2 --format='value(status.url)'
```

Visit the URL to see:
- 📅 90-day price calendar
- 💡 Daily price recommendations with explanations
- 🏠 Competitor tracking
- 📊 Market insights

### Manual Scrape

Trigger a manual competitor scrape:
```bash
gcloud functions call scraper --region=europe-west2
```

### View Data

Query BigQuery directly:
```sql
-- Today's price recommendations
SELECT * FROM pricing.price_recommendations
WHERE recommendation_date = CURRENT_DATE()
ORDER BY target_date;

-- Competitor prices
SELECT * FROM pricing.daily_prices
WHERE scrape_date = CURRENT_DATE()
ORDER BY price_per_night;
```

## Project Structure

```
pricing/
├── config.yaml                    # Your property configuration
├── terraform/                     # Infrastructure as code
│   ├── main.tf                   # GCP resources
│   ├── variables.tf
│   └── environments/
│       └── prod.tfvars
├── functions/
│   ├── scraper/                  # Scrapes competitor data
│   │   ├── main.py
│   │   └── requirements.txt
│   └── analyzer/                 # Generates price recommendations
│       ├── main.py
│       ├── pricing.py           # Pricing logic
│       └── requirements.txt
├── dashboard/                     # Web UI
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   └── templates/           # HTML templates
│   └── requirements.txt
├── .github/workflows/            # CI/CD
│   ├── deploy-infra.yml
│   ├── deploy-functions.yml
│   └── deploy-dashboard.yml
└── scripts/
    └── setup-gcp.sh              # Initial GCP setup
```

## Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| Google Cloud Platform | ~$5-10 |
| Apify (scraping) | ~$49 |
| **Total** | **~$55-60** |

**Compare to:**
- PriceLabs: $20/listing/month
- Wheelhouse: $20/listing/month
- Break-even at 3 listings

## Development

### Local Testing

```bash
# Install dependencies
cd functions/scraper
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest

# Test locally
functions-framework --target=trigger_scrape --debug
```

### Deploy Specific Component

```bash
# Deploy only infrastructure
git commit -m "Update terraform" terraform/
git push

# Deploy only functions
git commit -m "Update scraper" functions/
git push

# Deploy only dashboard
git commit -m "Update dashboard" dashboard/
git push
```

## Customization

### Adjust Pricing Logic

Edit [functions/analyzer/pricing.py](functions/analyzer/pricing.py:1-400) to customize:
- Seasonality multipliers
- Day-of-week premiums
- Event impact factors
- Demand scarcity adjustments

### Add Events

```sql
INSERT INTO pricing.events (event_date, event_name, event_type, expected_impact, source)
VALUES
  ('2025-12-25', 'Christmas Day', 'holiday', 'high', 'manual'),
  ('2025-12-31', 'New Years Eve', 'holiday', 'high', 'manual');
```

### Change Scraping Schedule

Edit [terraform/scheduler.tf](terraform/scheduler.tf:1-20) and change the cron schedule.

## Troubleshooting

### Scraper not running

```bash
# Check scheduler
gcloud scheduler jobs describe daily-scrape --location=europe-west2

# Check function logs
gcloud functions logs read scraper --region=europe-west2 --limit=50
```

### No price recommendations

```bash
# Check if data was scraped
bq query --use_legacy_sql=false '
SELECT scrape_date, COUNT(*) as listings
FROM pricing.daily_prices
GROUP BY scrape_date
ORDER BY scrape_date DESC
LIMIT 7'

# Check analyzer logs
gcloud functions logs read analyzer --region=europe-west2 --limit=50
```

### Dashboard not loading

```bash
# Check Cloud Run logs
gcloud run services logs read pricing-dashboard --region=europe-west2
```

## Roadmap

- [x] Phase 0: Infrastructure & CI/CD
- [x] Phase 1: Airbnb scraping
- [x] Phase 2: Price analysis engine
- [x] Phase 3: Web dashboard
- [ ] Phase 4: Booking.com integration
- [ ] Phase 5: Email alerts
- [ ] Phase 6: Multi-property support

## Contributing

This is a personal project, but suggestions welcome via issues!

## License

MIT

## Support

For issues: https://github.com/YOUR-USERNAME/pricing/issues

---

**Sources:**
- [Firebase Firestore Pricing](https://firebase.google.com/docs/firestore/pricing)
- [BigQuery Pricing](https://cloud.google.com/bigquery/pricing)
- [Firestore vs BigQuery Comparison](https://slashdot.org/software/comparison/BigQuery-vs-Google-Cloud-Firestore/)
