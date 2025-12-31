#!/usr/bin/env python3
"""
Test the analyzer function locally with current BigQuery data.
"""

import sys
import os

# Add functions directory to path
sys.path.insert(0, 'functions/analyzer')

# Set required environment variables
os.environ['GCP_PROJECT'] = 'northcliffe-claude'
os.environ['PROPERTY_BEDROOMS'] = '2'
os.environ['PROPERTY_BATHROOMS'] = '1'
os.environ['PROPERTY_MAX_GUESTS'] = '6'
os.environ['PROPERTY_TYPE'] = 'Entire cottage'

from main import run_analysis
from unittest.mock import Mock

def test_analyzer():
    """Test the analyzer function."""
    print("=" * 70)
    print("TESTING ANALYZER FUNCTION")
    print("=" * 70)

    # Create mock request
    request = Mock()
    request.get_json = Mock(return_value=None)
    request.args = {}

    print("\n1. Running analyzer...")
    result, status_code = run_analysis(request)

    print(f"\n2. Result (status {status_code}):")
    print(f"   Status: {result.get('status')}")

    if result.get('status') == 'success':
        print(f"   Recommendations generated: {result.get('recommendations_generated')}")
        print(f"   Comp set size: {result.get('comp_set_size')}")
        print(f"   Recommendation date: {result.get('recommendation_date')}")

        print("\n3. ✅ Analyzer test PASSED!")
        print("\n   Next: Check BigQuery table pricing.price_recommendations")

    elif result.get('status') == 'warning':
        print(f"   Warning: {result.get('message')}")
        print("\n3. ⚠️  Analyzer ran but with warnings")
        print("   This is expected if there's limited data")

    else:
        print(f"   Error: {result.get('message')}")
        print("\n3. ❌ Analyzer test FAILED")

    return result, status_code


if __name__ == "__main__":
    result, status = test_analyzer()

    if status == 200:
        print("\n" + "=" * 70)
        print("Analyzer function is working!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("Analyzer function encountered errors")
        print("=" * 70)
        sys.exit(1)
