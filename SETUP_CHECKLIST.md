# Setup Checklist

Use this checklist to track your deployment progress.

## Pre-Deployment

- [ ] GCP account created with billing enabled
- [ ] GitHub repository created
- [ ] Apify account created (free tier is fine)
- [ ] `gcloud` CLI installed locally
- [ ] Git configured locally

## Step 1: Initial Setup

- [ ] Cloned repository locally
- [ ] Ran `./scripts/setup-gcp.sh`
- [ ] Noted down all outputs from setup script
- [ ] Created `terraform/environments/prod.tfvars` (auto-created by script)

## Step 2: GitHub Configuration

Go to: `https://github.com/YOUR-USERNAME/pricing/settings/secrets/actions`

Add these secrets:

- [ ] `GCP_PROJECT_ID`
- [ ] `GCP_WORKLOAD_IDENTITY_PROVIDER`
- [ ] `GCP_SERVICE_ACCOUNT`
- [ ] `GCP_FUNCTIONS_SA`
- [ ] `GCP_SCHEDULER_SA`
- [ ] `GCP_DASHBOARD_SA`
- [ ] `GCP_REGION` (set to `europe-west2` or your region)
- [ ] `APIFY_API_TOKEN` (from https://console.apify.com/account/integrations)

## Step 3: Property Configuration

**Option A: Automatic (Recommended)**

- [ ] Got Apify token from https://console.apify.com/account/integrations
- [ ] Set token: `export APIFY_API_TOKEN='your-token'`
- [ ] Ran: `./setup-property.sh https://www.airbnb.com/rooms/YOUR-LISTING-ID`
- [ ] Reviewed auto-generated `config.yaml`

**Option B: Manual**

- [ ] Copied `config.example.yaml` to `config.yaml`
- [ ] Filled in property location (city or coordinates)
- [ ] Filled in bedrooms, bathrooms, max guests
- [ ] Listed key amenities
- [ ] Set property type
- [ ] Set amenity premium (if applicable)

## Step 4: Deploy

- [ ] Committed all changes: `git add .`
- [ ] Created initial commit: `git commit -m "Initial deployment"`
- [ ] Pushed to GitHub: `git push origin main`
- [ ] Watched GitHub Actions deployment (all 3 workflows should succeed)
  - [ ] `deploy-infra.yml` completed ✅
  - [ ] `deploy-functions.yml` completed ✅
  - [ ] `deploy-dashboard.yml` completed ✅

## Step 5: Verify Deployment

- [ ] Got dashboard URL: `gcloud run services describe pricing-dashboard --region=europe-west2 --format='value(status.url)'`
- [ ] Visited dashboard in browser (should load, might show "no data" initially)
- [ ] Triggered first scrape: `./scripts/manual-trigger.sh scraper`
- [ ] Waited ~5 minutes
- [ ] Triggered analyzer: `./scripts/manual-trigger.sh analyzer`
- [ ] Refreshed dashboard - should now show price recommendations!

## Step 6: Optional Enhancements

- [ ] Added local events using `scripts/add-events.sql`
- [ ] Customized pricing factors in `functions/analyzer/pricing.py`
- [ ] Adjusted scraping schedule if needed
- [ ] Set up billing alerts in GCP Console

## Verification Commands

Run these to verify everything is working:

```bash
# Check if functions deployed
gcloud functions list --region=europe-west2

# Check if scheduler jobs exist
gcloud scheduler jobs list --location=europe-west2

# Check if BigQuery dataset created
bq ls

# Check if data is being collected
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`YOUR-PROJECT-ID.pricing.daily_prices\`"

# View function logs
gcloud functions logs read scraper --region=europe-west2 --limit=20
gcloud functions logs read analyzer --region=europe-west2 --limit=20

# Check Cloud Run service
gcloud run services list --region=europe-west2
```

## Troubleshooting

### GitHub Actions failing?
- [ ] Verified all GitHub secrets are set correctly
- [ ] Checked workflow logs in GitHub Actions tab
- [ ] Verified service accounts have correct permissions

### No data in dashboard?
- [ ] Ran manual scraper trigger
- [ ] Checked scraper logs for errors
- [ ] Verified Apify token is valid
- [ ] Checked BigQuery has data

### Dashboard not loading?
- [ ] Checked Cloud Run logs
- [ ] Verified service deployed successfully
- [ ] Tried accessing health endpoint: `DASHBOARD_URL/health`

## Post-Deployment

- [ ] Bookmarked dashboard URL
- [ ] Set calendar reminder to check dashboard daily
- [ ] Set calendar reminder to add events monthly
- [ ] Set up GCP budget alerts (optional but recommended)

## Monthly Maintenance

- [ ] Review cost report in GCP Console
- [ ] Check Apify usage and credits
- [ ] Add next month's events
- [ ] Review competitor set relevance

---

**Need Help?**

- Read [README.md](README.md) for full documentation
- Read [QUICKSTART.md](QUICKSTART.md) for step-by-step guide
- Check [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for architecture details
- Create an issue on GitHub

---

**Current Status**:
- [ ] Not started
- [ ] In progress
- [ ] Deployed and running! 🎉
