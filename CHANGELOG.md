# Changelog

## [Enhanced] - 2025-12-30

### ✨ Major Improvements

#### 🎯 .env File Configuration
- **Added `.env.example`** - Template for environment variables
- **Auto-loads configuration** - No more repeated command-line arguments
- **Secure by default** - .env gitignored automatically

#### 🔄 Simplified Property Setup
- **One-time configuration** - Set APIFY_API_TOKEN and AIRBNB_LISTING_URL once
- **Automatic fallback** - Script checks .env → env vars → prompts
- **Command-line override** - Can still pass URL as argument if needed

### 📁 New Files

- `.env.example` - Environment variable template
- `ENV_CONFIGURATION.md` - Complete .env usage guide
- `scripts/load-env.sh` - Helper for loading .env in shell scripts
- Updated `scripts/requirements.txt` - Added python-dotenv

### 🔧 Modified Files

- `scripts/extract-property-details.py`
  - Now loads .env automatically using python-dotenv
  - Checks .env for AIRBNB_LISTING_URL first
  - Better error messages with .env guidance

- `setup-property.sh`
  - Creates .env from template if missing
  - Loads variables from .env automatically
  - Supports both .env and command-line usage

- `.gitignore`
  - Added .env.local to ignored files

- `QUICKSTART.md`
  - Updated Step 5 to show .env approach first
  - Clearer, simpler instructions

---

## Usage Comparison

### Before (Manual Arguments)

```bash
# Every single time you run it:
export APIFY_API_TOKEN='abc123...'
./setup-property.sh https://www.airbnb.com/rooms/12345678
```

### After (.env File)

```bash
# One-time setup:
cp .env.example .env
nano .env  # Add token and URL

# Every time after:
./setup-property.sh  # That's it!
```

---

## Benefits

✅ **No repeated typing** - Set once, use forever
✅ **Cleaner commands** - No long command-line arguments
✅ **Industry standard** - .env is widely used practice
✅ **Easy updates** - Edit one file to change configuration
✅ **Secure** - .env never committed to git
✅ **Backward compatible** - Old approach still works

---

## Migration Guide

If you were using the old approach:

### Option 1: Create .env (Recommended)

```bash
# Create .env
cat > .env <<EOF
APIFY_API_TOKEN=your_token_here
AIRBNB_LISTING_URL=https://www.airbnb.com/rooms/12345678
GCP_PROJECT_ID=your-project-id
GCP_REGION=europe-west2
EOF

# Now just run:
./setup-property.sh
```

### Option 2: Keep Using Environment Variables

```bash
# Old way still works!
export APIFY_API_TOKEN='your-token'
./setup-property.sh https://www.airbnb.com/rooms/12345678
```

---

## Breaking Changes

**None!** This is a backward-compatible enhancement.

All old scripts and commands continue to work exactly as before.

---

## Future Enhancements (Roadmap)

- [ ] Load .env in all utility scripts (manual-trigger.sh, view-data.sh)
- [ ] Support for multiple .env files (.env.dev, .env.prod)
- [ ] Automatic .env validation
- [ ] Encrypted .env for extra security

---

## Documentation Updates

Updated files:
- ✅ `QUICKSTART.md` - Shows .env as primary method
- ✅ `ENV_CONFIGURATION.md` - New comprehensive guide
- ✅ `README.md` - Updated Quick Start section
- ✅ `SETUP_CHECKLIST.md` - Shows both options

---

## Developer Notes

### .env Loading Priority

Scripts check for values in this order:

1. Command-line argument (highest priority)
2. .env file
3. Environment variable
4. User prompt (fallback)

### Python .env Loading

Uses `python-dotenv` library:
- Automatically loads .env from project root
- Doesn't override existing environment variables
- Graceful fallback if library not installed

### Shell .env Loading

```bash
export $(grep -v '^#' .env | xargs)
```

Simple, no dependencies, works everywhere.

---

## Testing

Tested scenarios:

- ✅ .env file with all variables
- ✅ .env file with partial variables
- ✅ No .env file (falls back to prompts)
- ✅ Command-line override of .env values
- ✅ Environment variable override
- ✅ Missing .env.example (error handling)

---

## Feedback

This enhancement makes the system significantly easier to use while maintaining full backward compatibility.

**Before:** 5 steps, repeated typing
**After:** 3 steps, one-time setup

Much better developer experience! 🎉
