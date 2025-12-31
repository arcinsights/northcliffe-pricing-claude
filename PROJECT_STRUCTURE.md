# Project Structure

Clean, organized structure for the Airbnb pricing system.

## Directory Layout

```
pricing/
├── README.md                           # Main documentation (START HERE)
├── .env                               # Environment variables (secrets)
├── .gitignore                         # Git ignore rules
├── ENV_CONFIGURATION.md               # Environment setup guide
│
├── config/
│   ├── competitors.yaml               # List of competitor properties
│   └── config.yaml                    # (Auto-generated property config)
│
├── scripts/                           # All executable scripts
│   ├── generate_full_calendar.py      # Creates 365-day calendar
│   ├── load_collected_pricing.py      # Loads first batch data
│   ├── load_comprehensive_pricing.py  # Loads comprehensive seasonal data
│   ├── load_manual_pricing.py         # Loads from YAML notes
│   ├── test_analyzer.py               # Tests analyzer function
│   └── test_dashboard.py              # Tests dashboard function
│
├── functions/                         # Cloud Functions (for GCP deployment)
│   ├── scraper/                       # Competitor scraping (Apify)
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── analyzer/                      # Pricing analysis
│   │   ├── main.py
│   │   ├── pricing.py                 # Core pricing logic
│   │   └── requirements.txt
│   └── dashboard/                     # Web dashboard
│       ├── main.py
│       └── requirements.txt
│
├── outputs/                           # Generated outputs
│   ├── pricing_calendar_*.csv         # Full year calendar (CSV)
│   └── pricing_calendar_*.json        # Full year calendar (JSON)
│
├── test_data/                         # Test outputs
│   └── dashboard.html                 # Generated dashboard
│
├── docs/                              # Documentation
│   ├── calendar-guide.md              # How to use the pricing calendar
│   ├── pricing-methodology.md         # How pricing algorithms work
│   ├── deployment-guide.md            # Deploy to Google Cloud
│   └── whats-new.md                  # Latest features
│
├── terraform/                         # Infrastructure as code
│   └── *.tf                          # Terraform configs for GCP
│
└── venv/                             # Python virtual environment
```

## Key Files by Purpose

### Getting Started
- **README.md** - Start here! Complete system overview
- **docs/calendar-guide.md** - How to use your pricing calendar
- **ENV_CONFIGURATION.md** - Environment setup

### Daily Usage
- **outputs/pricing_calendar_*.csv** - Your pricing calendar
- **test_data/dashboard.html** - Visual dashboard

### Data Management
- **scripts/load_comprehensive_pricing.py** - Add new pricing data
- **scripts/generate_full_calendar.py** - Create 365-day calendar
- **config/competitors.yaml** - Manage competitor list

### Analysis
- **scripts/test_analyzer.py** - Generate recommendations
- **scripts/test_dashboard.py** - Create dashboard
- **functions/analyzer/pricing.py** - Pricing algorithms

### Deployment
- **docs/deployment-guide.md** - GCP deployment instructions
- **functions/** - Cloud Functions ready to deploy
- **terraform/** - Infrastructure automation

## What Was Removed

Cleaned up obsolete files:
- ❌ Old status documents (FINAL_STATUS.md, SYSTEM_READY.md, etc.)
- ❌ Obsolete test scripts (test_scraper.py, test_calendar_scraper.py, etc.)
- ❌ Redundant documentation (PROJECT_SUMMARY.md, QUICKSTART.md, etc.)
- ❌ Planning documents (PLAN.md, CHANGELOG.md)

## Quick Navigation

### I want to...

**View my pricing**
→ `open outputs/pricing_calendar_2025-12-31.csv`

**Update prices**
1. Edit `scripts/load_comprehensive_pricing.py`
2. Run `python scripts/load_comprehensive_pricing.py`
3. Run `python scripts/test_analyzer.py`
4. Run `python scripts/generate_full_calendar.py`

**View dashboard**
→ `python scripts/test_dashboard.py && open test_data/dashboard.html`

**Understand pricing**
→ Read `docs/pricing-methodology.md`

**Deploy to GCP**
→ Follow `docs/deployment-guide.md`

**Learn new features**
→ Read `docs/whats-new.md`

## File Count Summary

- **Root files**: 5 (README, .env, .gitignore, config files)
- **Scripts**: 6 (all in scripts/ directory)
- **Functions**: 3 directories (scraper, analyzer, dashboard)
- **Documentation**: 4 files (all in docs/ directory)
- **Outputs**: 1-2 files (calendars in outputs/ directory)
- **Total**: ~20 key files (down from 35+ before cleanup)

## Cloud Functions Status

All Cloud Functions remain fully functional and ready for deployment:

✅ **Scraper** (`functions/scraper/`) - Competitor data collection
✅ **Analyzer** (`functions/analyzer/`) - Pricing recommendations  
✅ **Dashboard** (`functions/dashboard/`) - Web visualization

No changes made to function code during cleanup.

## Next Steps

1. **Review README.md** - Complete overview
2. **Check outputs/pricing_calendar_*.csv** - Your pricing data
3. **Deploy when ready** - See docs/deployment-guide.md

Everything is now organized and ready to use! 🎯
