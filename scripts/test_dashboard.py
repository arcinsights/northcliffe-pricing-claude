#!/usr/bin/env python3
"""
Test the dashboard function locally.
"""

import sys
import os

# Add functions directory to path
sys.path.insert(0, 'functions/dashboard')

# Set required environment variables
os.environ['GCP_PROJECT'] = 'northcliffe-claude'

from main import dashboard
from unittest.mock import Mock

def test_dashboard():
    """Test the dashboard function."""
    print("=" * 70)
    print("TESTING DASHBOARD FUNCTION")
    print("=" * 70)

    # Create mock request
    request = Mock()

    print("\n1. Rendering dashboard...")
    result = dashboard(request)

    if isinstance(result, tuple):
        html, status_code = result
    else:
        html = result
        status_code = 200

    print(f"\n2. Result (status {status_code}):")

    if status_code == 200:
        print(f"   HTML length: {len(html)} characters")
        print(f"   Contains chart: {'priceChart' in html}")
        print(f"   Contains table: {'<table>' in html}")

        # Save HTML for inspection
        with open('test_data/dashboard.html', 'w') as f:
            f.write(html)

        print(f"\n3. ✅ Dashboard test PASSED!")
        print(f"   Saved to: test_data/dashboard.html")
        print(f"   Open in browser to view")

    else:
        print(f"   Error HTML:\n{html[:500]}")
        print(f"\n3. ❌ Dashboard test FAILED")

    return html, status_code


if __name__ == "__main__":
    html, status = test_dashboard()

    if status == 200:
        print("\n" + "=" * 70)
        print("Dashboard is ready!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("Dashboard encountered errors")
        print("=" * 70)
        sys.exit(1)
