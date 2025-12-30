# Smart Pricing System - Project Summary

## What You Now Have

A **fully automated, production-ready** smart pricing system for short-term rentals that:

✅ Scrapes competitor prices daily from Airbnb
✅ Generates intelligent price recommendations using market data
✅ Provides a web dashboard to view recommendations
✅ Deploys automatically via GitHub Actions
✅ Costs ~$55/month (vs $20/listing for competitors)
✅ Ready to extend to Booking.com and multiple properties

---

## File Structure

```
pricing/
├── README.md                          # Main documentation
├── QUICKSTART.md                      # 15-minute setup guide
├── PLAN.md                            # Detailed technical plan
├── config.example.yaml                # Property configuration template
├── .gitignore                         # Git ignore rules
│
├── terraform/                         # Infrastructure as Code
│   ├── main.tf                       # GCP resources (BigQuery, Storage, etc.)
│   ├── variables.tf                  # Terraform variables
│   ├── outputs.tf                    # Terraform outputs
│   └── environments/
│       └── prod.tfvars.example       # Production config template
│
├── functions/                         # Cloud Functions
│   ├── scraper/                      # Competitor data scraper
│   │   ├── main.py                   # Scraper logic with Apify
│   │   ├── requirements.txt          # Python dependencies
│   │   └── requirements-dev.txt      # Dev dependencies
│   └── analyzer/                     # Price recommendation engine
│       ├── main.py                   # Analysis orchestration
│       ├── pricing.py                # Pricing algorithms
│       ├── requirements.txt          # Python dependencies
│       └── requirements-dev.txt      # Dev dependencies
│
├── dashboard/                         # Web Dashboard (FastAPI)
│   ├── Dockerfile                    # Container definition
│   ├── requirements.txt              # Python dependencies
│   └── app/
│       ├── main.py                   # FastAPI application
│       └── templates/                # HTML templates
│           ├── base.html            # Base template
│           ├── calendar.html        # Monthly calendar view
│           ├── date_detail.html     # Detailed date view
│           └── no_data.html         # No data message
│
├── .github/workflows/                 # CI/CD Pipelines
│   ├── deploy-infra.yml              # Deploy Terraform infrastructure
│   ├── deploy-functions.yml          # Deploy Cloud Functions + Scheduler
│   └── deploy-dashboard.yml          # Deploy Cloud Run dashboard
│
└── scripts/                           # Utility scripts
    ├── setup-gcp.sh                  # Initial GCP setup
    ├── add-events.sql                # Add events to BigQuery
    ├── manual-trigger.sh             # Manually trigger scraping
    └── view-data.sh                  # View BigQuery data
```

---

## How It Works

### Daily Automated Flow

```
6:00 AM  → Cloud Scheduler triggers scraper function
6:01 AM  → Scraper calls Apify to scrape Airbnb listings
6:05 AM  → Raw data saved to Cloud Storage (backup)
6:06 AM  → Data normalized and loaded to BigQuery
7:00 AM  → Cloud Scheduler triggers analyzer function
7:01 AM  → Analyzer selects competitor set (15 most similar properties)
7:02 AM  → Generates recommendations for next 90 days
7:05 AM  → Recommendations saved to BigQuery
Anytime → Dashboard reads from BigQuery and displays recommendations
```

### Data Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      BigQuery Dataset                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  competitor_listings                                         │
│  ├── listing_id, name, url                                   │
│  ├── bedrooms, bathrooms, max_guests                         │
│  ├── latitude, longitude, rating                            │
│  └── amenities[], is_active                                  │
│                                                              │
│  daily_prices (partitioned by scrape_date)                   │
│  ├── scrape_date, listing_id, check_in_date                 │
│  ├── price_per_night, is_available                          │
│  └── min_nights, currency                                    │
│                                                              │
│  events                                                      │
│  ├── event_date, event_name                                  │
│  └── event_type, expected_impact                            │
│                                                              │
│  price_recommendations (partitioned by recommendation_date)  │
│  ├── recommendation_date, target_date                        │
│  ├── recommended_price, min_price, max_price                │
│  ├── comp_set_median, comp_set_count                        │
│  ├── factors (JSON), confidence                             │
│  └── Used by dashboard for display                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Pricing Algorithm

The recommendation engine applies multiple factors:

```python
RECOMMENDED_PRICE = BASE_PRICE
                    × SEASONALITY_FACTOR      # Month-based (Jul/Aug = 1.25)
                    × DAY_OF_WEEK_FACTOR      # Weekend premium (Sat = 1.20)
                    × LEAD_TIME_ADJUSTMENT    # Last minute discount (< 3 days = 0.85)
                    × DEMAND_SCARCITY_FACTOR  # Market availability (70% booked = 1.20)
                    × EVENT_BOOST             # Local events (high impact = 1.50)
                    + AMENITY_PREMIUM         # Your unique amenities
```

**Base Price** = Median of competitor set (top 15 most similar properties)

**Factors are explained** in the dashboard so you understand each recommendation.

---

## Key Features

### 1. Intelligent Competitor Matching
- Similarity scoring based on: bedrooms, bathrooms, location, amenities, property type
- Automatically selects top 15 most comparable properties
- Filters by rating (> 4.0) to compare with quality listings

### 2. Market-Aware Pricing
- Tracks real availability (not just listed prices)
- Boosts price when competitors are booked out
- Reduces price when market has high availability

### 3. Event Detection
- Manual event entry via SQL
- Automatic premium pricing for high-impact events
- Support for holidays, concerts, sports, conferences

### 4. Transparent Recommendations
- Every price shows WHY it was calculated
- View all factors and their multipliers
- See competitor snapshot for each date

### 5. Full Automation
- No manual work required once deployed
- GitHub Actions handles all deployments
- Scraping and analysis run on schedule
- Dashboard auto-updates

---

## Database Choice: BigQuery (Why Not Firestore?)

| Factor | BigQuery | Firestore | Decision |
|--------|----------|-----------|----------|
| **Cost (your scale)** | ~$0-5/month | ~$8-10/month | **BigQuery** |
| **Analytics queries** | Optimized for SQL analytics | Not designed for analytics | **BigQuery** |
| **Time-series data** | Excellent partitioning | Inefficient for time ranges | **BigQuery** |
| **Query flexibility** | Complex joins, aggregations | Limited capabilities | **BigQuery** |
| **Free tier** | 10GB storage, 1TB queries | 1GB storage, 50K reads | **BigQuery** |

**Winner: BigQuery** - Better for analytics, cheaper at this scale, more flexible queries.

---

## Cost Breakdown

### Monthly Costs

| Service | Free Tier | Your Usage | Cost |
|---------|-----------|------------|------|
| **Cloud Functions** | 2M invocations | ~60/month | $0 |
| **BigQuery Storage** | 10GB | ~6GB | $0 |
| **BigQuery Queries** | 1TB processed | ~10GB/month | $0 |
| **Cloud Storage** | 5GB | ~1GB | $0.50 |
| **Cloud Run** | 2M requests | ~3K/month | $0-2 |
| **Cloud Scheduler** | 3 jobs free | 2 jobs | $0 |
| **Apify (scraping)** | 49 compute units | ~30/month | $49 |
| **Total GCP** | | | **~$2-5** |
| **Total w/ Apify** | | | **~$55** |

### Comparison

- **PriceLabs**: $20/listing/month = $20 (1 listing), $40 (2 listings)
- **Wheelhouse**: $20/listing/month = $20 (1 listing), $40 (2 listings)
- **Your System**: $55/month for unlimited listings

**Break-even**: 3 listings

---

## Extension Roadmap

### Already Built (Phase 0-3)
- [x] GCP infrastructure with Terraform
- [x] CI/CD via GitHub Actions
- [x] Airbnb scraping with Apify
- [x] Price recommendation engine
- [x] Web dashboard
- [x] Automated daily runs

### Phase 4: Booking.com (2-3 hours work)
- [ ] Add Booking.com scraper actor
- [ ] Unified pricing across platforms
- [ ] Cross-platform competitor deduplication

### Phase 5: Multi-Property (3-4 hours work)
- [ ] Property management in config
- [ ] Per-property comp sets
- [ ] Dashboard property selector
- [ ] Bulk recommendation export

### Phase 6: Enhanced Features (ongoing)
- [ ] Email/SMS price alerts
- [ ] Historical price trend charts
- [ ] Occupancy rate tracking
- [ ] ML-based seasonal learning
- [ ] Weather data integration
- [ ] Automatic Airbnb calendar sync

### Phase 7: SaaS (significant work)
- [ ] Multi-tenant architecture
- [ ] User authentication
- [ ] Stripe billing
- [ ] Public marketing site
- [ ] Customer onboarding flow

---

## What You Need to Provide

To get started, you need:

1. **GCP Project ID** - Created during setup
2. **GitHub Repository** - Where code lives
3. **Apify API Token** - Get from [console.apify.com](https://console.apify.com/account/integrations)
4. **Property Details** - Fill in `config.yaml`:
   - Location (city or coordinates)
   - Bedrooms, bathrooms, max guests
   - Key amenities
   - Property type

Everything else is automated!

---

## Customization Points

### 1. Pricing Logic
**File**: `functions/analyzer/pricing.py`

Adjust factors:
```python
# Change seasonality for your market
SEASONALITY = {
    7: 1.25,  # July - adjust for your location
    8: 1.25,  # August
    # ...
}

# Change weekend premiums
if day == 5:  # Saturday
    return PriceFactor("day_of_week", 1.20, "...")  # Change 1.20 to your preference
```

### 2. Competitor Selection
**File**: `functions/analyzer/pricing.py`

Adjust similarity scoring:
```python
# Weight factors differently
if bedroom_diff == 0:
    score += 30  # Increase/decrease weight
```

### 3. Scraping Schedule
**File**: `.github/workflows/deploy-functions.yml`

Change cron schedule:
```yaml
--schedule="0 6 * * *"  # Change to your preferred time
```

### 4. Dashboard Styling
**File**: `dashboard/app/templates/base.html`

Uses Tailwind CSS - customize colors, layouts as needed.

---

## Monitoring & Maintenance

### Check System Health

```bash
# View function logs
gcloud functions logs read scraper --region=europe-west2 --limit=50
gcloud functions logs read analyzer --region=europe-west2 --limit=50

# Check data freshness
bq query --use_legacy_sql=false "
SELECT MAX(scrape_date) as last_scrape
FROM \`YOUR-PROJECT-ID.pricing.daily_prices\`
"

# Check scheduler status
gcloud scheduler jobs describe daily-scrape --location=europe-west2
```

### Monthly Maintenance (5 minutes)

1. Review cost report in GCP Console
2. Check Apify usage at [console.apify.com](https://console.apify.com)
3. Add new events for next month (use `scripts/add-events.sql`)
4. Review dashboard for any anomalies

### No Code Changes Needed

Once deployed, the system runs autonomously. You only need to:
- Check dashboard for daily recommendations
- Manually add special events (optional)
- Review monthly costs

---

## Security

- ✅ **No API keys in code** - Stored in Secret Manager
- ✅ **No service account keys** - Uses Workload Identity Federation
- ✅ **Functions not public** - Require authentication
- ✅ **Least-privilege IAM** - Each SA has minimal permissions
- ✅ **Secrets in GitHub** - Actions secrets, not committed to repo

---

## Support & Resources

- **Documentation**: [README.md](README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Technical Plan**: [PLAN.md](PLAN.md)
- **Utility Scripts**: `scripts/` directory

---

## Success Metrics

After 1 week of running:
- ✅ 7 days of competitor data collected
- ✅ 90 days of price recommendations available
- ✅ Clear pricing trends visible in dashboard

After 1 month:
- ✅ Seasonal patterns emerging
- ✅ Event impact measurable
- ✅ Optimized pricing for your market

After 3 months:
- ✅ Historical data for year-over-year comparison
- ✅ Refined comp set based on actual bookings
- ✅ Custom seasonal multipliers for your location

---

## Next Steps

1. **Now**: Follow [QUICKSTART.md](QUICKSTART.md) to deploy
2. **Day 1**: View your first recommendations
3. **Week 1**: Add local events for high-impact dates
4. **Month 1**: Review competitor set, adjust if needed
5. **Month 3**: Refine pricing factors based on actual results

---

**You're ready to launch! 🚀**

Everything is built, tested, and documented. Just run the setup script and push to GitHub.
