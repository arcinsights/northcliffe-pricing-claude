# Python Virtual Environment Setup

## Why Virtual Environment?

Modern macOS and many Linux distributions use **externally-managed Python environments** to prevent system Python corruption. This means you can't install packages globally with `pip install`.

The solution: Use a **virtual environment** (venv) for the project.

---

## Automatic Setup

The `setup-property.sh` script **automatically handles this** for you:

```bash
./setup-property.sh
```

It will:
1. Create `venv/` directory (if it doesn't exist)
2. Install all dependencies inside venv
3. Run the extraction script
4. Deactivate venv when done

**You don't need to do anything manually!**

---

## Manual Virtual Environment Setup (Optional)

If you want to manage the venv manually:

### Create Virtual Environment

```bash
python3 -m venv venv
```

### Activate Virtual Environment

```bash
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

Your prompt will change to show `(venv)`.

### Install Dependencies

```bash
pip install -r scripts/requirements.txt
```

### Run Scripts

```bash
python scripts/extract-property-details.py
```

### Deactivate

```bash
deactivate
```

---

## What Gets Installed?

The virtual environment includes:

```
apify-client==1.7.*    # For scraping Airbnb data
pyyaml==6.0.*          # For config.yaml handling
python-dotenv==1.0.*   # For .env file loading
```

---

## Location

- **Virtual environment**: `venv/` (gitignored)
- **Installed packages**: `venv/lib/python3.x/site-packages/`
- **Python executable**: `venv/bin/python`
- **Pip**: `venv/bin/pip`

---

## Common Questions

### Q: Do I need to activate venv every time?

**A: No!** The `setup-property.sh` script handles activation/deactivation automatically.

If running Python scripts directly:
```bash
# Option 1: Activate first
source venv/bin/activate
python scripts/extract-property-details.py
deactivate

# Option 2: Use venv python directly
venv/bin/python scripts/extract-property-details.py
```

### Q: Can I delete venv/?

**A: Yes!** Just run `./setup-property.sh` again and it will recreate it.

```bash
rm -rf venv
./setup-property.sh  # Recreates venv automatically
```

### Q: Does GitHub Actions need venv?

**A: No!** GitHub Actions uses its own Python environment. The venv is only for local development.

### Q: What about production deployment?

**A: Not needed!** Cloud Functions and Cloud Run use their own isolated environments defined by `requirements.txt`.

---

## Troubleshooting

### "externally-managed-environment" Error

This is why we use venv! The error means you tried:
```bash
pip3 install package  # ❌ Won't work on modern systems
```

Solution (automatic):
```bash
./setup-property.sh  # ✅ Creates venv automatically
```

### Python Version Issues

Check your Python version:
```bash
python3 --version
```

Should be Python 3.8 or higher. If not, install a newer version:

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Then recreate venv
rm -rf venv
python3.11 -m venv venv
```

### "No module named 'apify_client'"

The virtual environment isn't activated. Either:

```bash
# Re-run setup script
./setup-property.sh

# Or activate manually
source venv/bin/activate
pip install -r scripts/requirements.txt
```

---

## Development Workflow

### First Time Setup

```bash
git clone <repo>
cd pricing
./setup-property.sh  # Creates venv + installs deps
```

### Daily Usage

```bash
# Just run the script - venv handled automatically
./setup-property.sh
```

### Adding New Dependencies

If you add packages to `scripts/requirements.txt`:

```bash
# Venv will auto-install on next run
./setup-property.sh

# Or manually:
source venv/bin/activate
pip install -r scripts/requirements.txt
deactivate
```

---

## Cleanup

To remove everything:

```bash
# Remove virtual environment
rm -rf venv

# Remove any installed Python packages cache
rm -rf __pycache__
```

Venv will be recreated automatically next time you run `./setup-property.sh`.

---

## Alternative: Use System Python (Not Recommended)

If you really want to avoid venv, you can use:

```bash
# macOS with Homebrew
brew install python-apify-client python-yaml python-dotenv

# Then run with system python
python3 scripts/extract-property-details.py
```

But this is **not recommended** because:
- Version conflicts with other projects
- Pollutes system Python
- Different behavior across systems
- Can break system tools

**Use venv instead!** It's the standard practice.

---

## Summary

**The setup script handles everything automatically.**

You don't need to:
- ❌ Manually create venv
- ❌ Remember to activate/deactivate
- ❌ Install packages yourself

Just run:
```bash
./setup-property.sh
```

And it works! 🎉
