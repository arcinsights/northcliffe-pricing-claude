# Environment Configuration (.env)

## Overview

All sensitive configuration (API tokens, URLs) is now managed through a `.env` file instead of command-line arguments or manual typing.

---

## Quick Start

### 1. Create .env File

```bash
cp .env.example .env
```

### 2. Edit .env

```bash
nano .env  # or your favorite editor
```

### 3. Fill in Your Values

```bash
# Apify API Token (get from https://console.apify.com/account/integrations)
APIFY_API_TOKEN=your_actual_token_here

# Your Airbnb listing URL
AIRBNB_LISTING_URL=https://www.airbnb.com/rooms/12345678

# GCP Configuration (filled during setup)
GCP_PROJECT_ID=my-pricing-project-123
GCP_REGION=europe-west2
```

### 4. Run Setup (No Arguments Needed!)

```bash
./setup-property.sh
```

That's it! The script automatically reads from `.env`.

---

## Benefits of .env Approach

✅ **No repeated typing** - Set once, use everywhere
✅ **No command-line arguments** - Cleaner commands
✅ **Easy updates** - Just edit one file
✅ **Secure** - .env is gitignored, never committed
✅ **Standard practice** - Industry-standard approach
✅ **Multiple environments** - Can have .env.dev, .env.prod

---

## How It Works

### Priority Order

Scripts check for values in this order:

1. **Command-line argument** (if provided) - highest priority
2. **.env file** (if exists)
3. **Environment variable** (if set)
4. **Prompt user** (if none of the above)

### Examples

**Using .env only:**
```bash
# .env contains AIRBNB_LISTING_URL
./setup-property.sh
# ✅ Uses URL from .env
```

**Override with command line:**
```bash
# .env contains AIRBNB_LISTING_URL
./setup-property.sh https://www.airbnb.com/rooms/99999999
# ✅ Uses URL from command line (overrides .env)
```

**No .env, will prompt:**
```bash
# No .env file
./setup-property.sh
# ⚠️ Creates .env from template, asks you to fill it
```

---

## .env File Structure

```bash
# ============================================
# REQUIRED - Fill these in first
# ============================================

# Apify API Token
# Get from: https://console.apify.com/account/integrations
APIFY_API_TOKEN=

# Your Airbnb listing URL
# Format: https://www.airbnb.com/rooms/YOUR-LISTING-ID
AIRBNB_LISTING_URL=

# ============================================
# AUTO-FILLED - Setup script fills these
# ============================================

# GCP Project ID (from setup-gcp.sh)
GCP_PROJECT_ID=

# GCP Region
GCP_REGION=europe-west2

# ============================================
# OPTIONAL - Future features
# ============================================

# Booking.com listing URL (Phase 4)
BOOKING_LISTING_URL=

# Email for alerts (Phase 5)
ALERT_EMAIL=
```

---

## Security Best Practices

### ✅ DO:
- Keep `.env` in `.gitignore` (already configured)
- Share `.env.example` in git (template without secrets)
- Use different `.env` files for dev/staging/prod
- Rotate tokens periodically

### ❌ DON'T:
- Commit `.env` to git
- Share `.env` publicly
- Put `.env` in Docker images
- Hard-code secrets in scripts

---

## Multiple Environments

You can have different .env files:

```bash
# Development
.env.dev

# Staging
.env.staging

# Production
.env  # or .env.prod
```

Load specific environment:

```bash
# Load dev environment
cp .env.dev .env
./setup-property.sh

# Load prod environment
cp .env.prod .env
./setup-property.sh
```

---

## Scripts That Use .env

All these scripts now support `.env`:

1. **`setup-property.sh`** - Property extraction
   - Reads: `APIFY_API_TOKEN`, `AIRBNB_LISTING_URL`

2. **`extract-property-details.py`** - Core extractor
   - Reads: `APIFY_API_TOKEN`, `AIRBNB_LISTING_URL`

3. **`setup-gcp.sh`** - GCP setup
   - Can read: `GCP_PROJECT_ID` (optional)

4. **Future scripts** - Will all use `.env`

---

## Troubleshooting

### "APIFY_API_TOKEN not found"

**Solution:**
```bash
# Check .env exists
ls -la .env

# Check .env has token
grep APIFY .env

# If empty, edit .env
nano .env
# Add: APIFY_API_TOKEN=your_token_here
```

### ".env file not loading"

**Solution:**
```bash
# Ensure no syntax errors in .env
cat .env

# Lines should be: KEY=value
# No spaces around =
# No quotes needed (unless value has spaces)

# Good:
APIFY_API_TOKEN=abc123

# Bad:
APIFY_API_TOKEN = abc123  # spaces around =
APIFY_API_TOKEN="abc123"  # unnecessary quotes
```

### "Want to use environment variable instead"

**Still works!**
```bash
# Old way still supported
export APIFY_API_TOKEN='your-token'
./setup-property.sh https://www.airbnb.com/rooms/12345678
```

---

## Migration from Old Approach

### Before (Manual Arguments)

```bash
# Had to type this every time
export APIFY_API_TOKEN='abc123...'
./setup-property.sh https://www.airbnb.com/rooms/12345678
```

### After (.env File)

```bash
# One-time setup
cp .env.example .env
nano .env  # Add token and URL

# Every time after (much simpler!)
./setup-property.sh
```

---

## Example .env (Complete)

```bash
# Smart Pricing - Environment Configuration

# Apify API Token
APIFY_API_TOKEN=apify_api_abc123xyz456789

# Your Airbnb listing URL
AIRBNB_LISTING_URL=https://www.airbnb.com/rooms/12345678

# GCP Configuration
GCP_PROJECT_ID=my-pricing-system-123456
GCP_REGION=europe-west2

# Optional: Future features
BOOKING_LISTING_URL=https://www.booking.com/hotel/gb/my-listing.html
ALERT_EMAIL=me@example.com
```

---

## FAQ

**Q: Can I still use command-line arguments?**
A: Yes! Command-line arguments override `.env` values.

**Q: Do I need .env for production deployment?**
A: No, GitHub Actions uses GitHub Secrets. `.env` is for local development only.

**Q: What if I have multiple properties?**
A: Use different `.env` files (`.env.property1`, `.env.property2`) and copy the one you need.

**Q: Is .env secure?**
A: Yes, as long as it's gitignored (already configured) and not shared publicly.

**Q: Can I commit .env.example?**
A: Yes! `.env.example` is a template with no secrets. It should be committed.

---

## Summary

**Old way:**
```bash
export APIFY_API_TOKEN='...'
./setup-property.sh https://www.airbnb.com/rooms/12345678
```

**New way:**
```bash
cp .env.example .env  # Once
nano .env             # Fill in values once
./setup-property.sh   # Use anytime, no arguments!
```

**Much better!** ✨
