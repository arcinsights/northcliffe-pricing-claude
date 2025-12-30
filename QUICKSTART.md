# Quick Start Guide

Get your Smart Pricing system up and running in 15 minutes.

## Prerequisites

- [ ] Google Cloud account with billing enabled
- [ ] GitHub account
- [ ] Apify account (sign up at [apify.com](https://apify.com) - free tier available)
- [ ] `gcloud` CLI installed ([install guide](https://cloud.google.com/sdk/docs/install))
- [ ] Git installed

## Step 1: Create GCP Project (2 min)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note down your project ID (e.g., `my-pricing-system-123`)

## Step 2: Clone Repository (1 min)

```bash
git clone <your-repo-url>
cd pricing
```

## Step 3: Run Setup Script (5 min)

```bash
chmod +x scripts/setup-gcp.sh
./scripts/setup-gcp.sh
```

This script will:
- Enable required GCP APIs
- Create service accounts
- Set up Workload Identity Federation for GitHub Actions
- Generate configuration files

**Keep the output handy - you'll need it for GitHub secrets!**

## Step 4: Configure GitHub Secrets (3 min)

Go to your GitHub repository:
`https://github.com/YOUR-USERNAME/pricing/settings/secrets/actions`

Add these secrets (values from setup script output):

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | From setup script |
| `GCP_SERVICE_ACCOUNT` | `terraform@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_FUNCTIONS_SA` | `pricing-functions@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_SCHEDULER_SA` | `pricing-scheduler@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_DASHBOARD_SA` | `pricing-dashboard@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_REGION` | `europe-west2` (or your preferred region) |
| `APIFY_API_TOKEN` | Get from [Apify console](https://console.apify.com/account/integrations) |

## Step 5: Configure Your Property (1 min!)

### Option A: Automatic Extraction (Recommended) ⚡

Set up once, use forever with `.env` file:

```bash
# 1. Create .env file from template
cp .env.example .env

# 2. Edit .env and add your details
nano .env
# Add:
#   APIFY_API_TOKEN=your-token-here
#   AIRBNB_LISTING_URL=https://www.airbnb.com/rooms/YOUR-LISTING-ID

# 3. Run setup (reads from .env automatically!)
./setup-property.sh
```

This will:
- ✅ Extract property name, location, coordinates
- ✅ Get bedrooms, bathrooms, max guests
- ✅ Pull all amenities automatically
- ✅ Create `config.yaml` for you

**That's it! No repeated typing, no command-line arguments.**

See [ENV_CONFIGURATION.md](ENV_CONFIGURATION.md) for details.

### Option B: Manual Configuration

If you prefer manual setup:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and fill in your property details:

```yaml
property:
  name: "My Airbnb"
  location:
    city: "London"  # Your city
    country: "UK"
    radius_km: 3    # Search radius for competitors
  attributes:
    bedrooms: 2
    bathrooms: 1
    max_guests: 4
    property_type: "Entire home"
  amenities:
    - "Wifi"
    - "Kitchen"
    # Add your key amenities
```

## Step 6: Deploy! (2 min)

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

GitHub Actions will automatically:
1. Deploy infrastructure (Terraform)
2. Deploy Cloud Functions (scraper & analyzer)
3. Deploy dashboard (Cloud Run)

Watch the progress:
`https://github.com/YOUR-USERNAME/pricing/actions`

## Step 7: Get Dashboard URL

After deployment completes (~5 minutes), get your dashboard URL:

```bash
gcloud run services describe pricing-dashboard \
  --region=europe-west2 \
  --format='value(status.url)'
```

Visit the URL in your browser! 🎉

## Step 8: Trigger First Scrape (Optional)

Don't want to wait for the scheduled scrape? Trigger manually:

```bash
gcloud functions call scraper \
  --region=europe-west2 \
  --gen2
```

Then trigger the analyzer:

```bash
gcloud functions call analyzer \
  --region=europe-west2 \
  --gen2
```

Check your dashboard - you should see price recommendations!

---

## Troubleshooting

### "Permission denied" errors

Make sure you've added all GitHub secrets correctly. Check:
```bash
gcloud projects get-iam-policy YOUR-PROJECT-ID
```

### "No data in dashboard"

1. Check scraper ran successfully:
```bash
gcloud functions logs read scraper --region=europe-west2 --limit=50
```

2. Check BigQuery has data:
```bash
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM `YOUR-PROJECT-ID.pricing.daily_prices`'
```

### "Apify scraper failed"

- Verify your Apify token is correct
- Check you have credits in your Apify account
- Try the Apify free tier (49 Actor compute units/month)

---

## What's Next?

### Add Events

Boost pricing for major events in your area:

```bash
bq query --use_legacy_sql=false "
INSERT INTO \`YOUR-PROJECT-ID.pricing.events\` (event_date, event_name, event_type, expected_impact, source)
VALUES
  ('2025-12-25', 'Christmas', 'holiday', 'high', 'manual'),
  ('2025-12-31', 'New Years Eve', 'holiday', 'high', 'manual')
"
```

### Customize Pricing Logic

Edit [functions/analyzer/pricing.py](functions/analyzer/pricing.py:1-400) to adjust:
- Seasonality multipliers for your market
- Weekend premiums
- Lead time discounts

Then commit and push - GitHub Actions will redeploy.

### View Price History

```bash
bq query --use_legacy_sql=false "
SELECT
  recommendation_date,
  target_date,
  recommended_price
FROM \`YOUR-PROJECT-ID.pricing.price_recommendations\`
WHERE target_date = '2025-07-15'
ORDER BY recommendation_date DESC
LIMIT 30
"
```

### Export to CSV

```bash
bq extract \
  --destination_format=CSV \
  YOUR-PROJECT-ID:pricing.price_recommendations \
  gs://YOUR-BUCKET/recommendations_*.csv
```

---

## Support

- **Documentation**: See [README.md](README.md)
- **Technical Details**: See [PLAN.md](PLAN.md)
- **Issues**: https://github.com/YOUR-USERNAME/pricing/issues

---

## Costs

**Estimated monthly cost: ~$55-65**

| Service | Cost |
|---------|------|
| Google Cloud | ~$5-10 |
| Apify scraping | ~$49 |

Compare to:
- PriceLabs: $20/listing/month
- Wheelhouse: $20/listing/month
- **Break-even at 3 listings**

---

**You're all set! 🎉**

Your smart pricing system will:
- Scrape competitors daily at 6 AM
- Generate recommendations at 7 AM
- Update your dashboard automatically

Visit your dashboard daily to see optimal pricing for the next 90 days!
