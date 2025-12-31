"""
Cloud Function to serve pricing dashboard.

Displays competitor pricing analysis and recommendations in a web interface.
"""

import functions_framework
import os
from datetime import date, timedelta
from google.cloud import bigquery
import json
from jinja2 import Template


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Northcliffe Pricing Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #1d1d1f; margin-bottom: 10px; font-size: 32px; }
        .subtitle { color: #86868b; margin-bottom: 30px; }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .card h3 { color: #86868b; font-size: 14px; font-weight: 500; margin-bottom: 8px; }
        .card .value { color: #1d1d1f; font-size: 36px; font-weight: 600; }
        .card .subvalue { color: #86868b; font-size: 14px; margin-top: 4px; }
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .chart-container h2 { color: #1d1d1f; font-size: 20px; margin-bottom: 20px; }
        canvas { max-height: 400px; }
        .recommendations {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            color: #86868b;
            font-size: 12px;
            font-weight: 500;
            padding: 12px 16px;
            border-bottom: 1px solid #f5f5f7;
        }
        td {
            padding: 16px;
            border-bottom: 1px solid #f5f5f7;
            color: #1d1d1f;
        }
        tr:hover { background: #fafafa; }
        .price { font-weight: 600; color: #0071e3; }
        .confidence-high { color: #34c759; }
        .confidence-medium { color: #ff9500; }
        .confidence-low { color: #ff3b30; }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        .badge-high { background: #d1f4e0; color: #157347; }
        .badge-medium { background: #fff3cd; color: #997404; }
        .badge-low { background: #f8d7da; color: #842029; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Pricing Dashboard</h1>
        <p class="subtitle">Competitor analysis & pricing recommendations · Updated {{update_date}}</p>

        <div class="cards">
            <div class="card">
                <h3>COMPETITORS TRACKED</h3>
                <div class="value">{{stats.competitor_count}}</div>
                <div class="subvalue">Active listings</div>
            </div>
            <div class="card">
                <h3>MARKET MEDIAN</h3>
                <div class="value">£{{stats.market_median}}</div>
                <div class="subvalue">Per night</div>
            </div>
            <div class="card">
                <h3>PRICE RANGE</h3>
                <div class="value">£{{stats.price_min}}-{{stats.price_max}}</div>
                <div class="subvalue">Competitor range</div>
            </div>
            <div class="card">
                <h3>RECOMMENDATIONS</h3>
                <div class="value">{{stats.rec_count}}</div>
                <div class="subvalue">Next 90 days</div>
            </div>
        </div>

        <div class="chart-container">
            <h2>Price Recommendations vs Market</h2>
            <canvas id="priceChart"></canvas>
        </div>

        <div class="recommendations">
            <h2 style="margin-bottom: 20px;">Upcoming Recommendations</h2>
            <table>
                <thead>
                    <tr>
                        <th>DATE</th>
                        <th>RECOMMENDED PRICE</th>
                        <th>MARKET MEDIAN</th>
                        <th>MARKET RANGE</th>
                        <th>COMP SET</th>
                        <th>CONFIDENCE</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rec in recommendations %}
                    <tr>
                        <td>{{rec.target_date}}</td>
                        <td class="price">£{{rec.recommended_price}}</td>
                        <td>£{{rec.comp_set_median}}</td>
                        <td>£{{rec.min_price}}-£{{rec.max_price}}</td>
                        <td>{{rec.comp_set_count}} listings</td>
                        <td>
                            <span class="badge badge-{{rec.confidence}}">{{rec.confidence.upper()}}</span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const priceData = {{price_data|safe}};

        const ctx = document.getElementById('priceChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: priceData.dates,
                datasets: [
                    {
                        label: 'Recommended Price',
                        data: priceData.recommended,
                        borderColor: '#0071e3',
                        backgroundColor: 'rgba(0, 113, 227, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Market Median',
                        data: priceData.median,
                        borderColor: '#86868b',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: 'Market Min',
                        data: priceData.min,
                        borderColor: '#ff3b30',
                        borderWidth: 1,
                        borderDash: [2, 2],
                        fill: false,
                        pointRadius: 0
                    },
                    {
                        label: 'Market Max',
                        data: priceData.max,
                        borderColor: '#34c759',
                        borderWidth: 1,
                        borderDash: [2, 2],
                        fill: false,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return '£' + value;
                            }
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""


def get_dashboard_data(project_id: str):
    """Fetch all data needed for dashboard."""
    client = bigquery.Client(project=project_id)

    # Get latest recommendations
    rec_query = """
        SELECT
            target_date,
            recommended_price,
            min_price,
            max_price,
            comp_set_median,
            comp_set_count,
            confidence
        FROM `{project_id}.pricing.price_recommendations`
        WHERE recommendation_date = (
            SELECT MAX(recommendation_date)
            FROM `{project_id}.pricing.price_recommendations`
        )
        ORDER BY target_date
        LIMIT 30
    """.format(project_id=project_id)

    recommendations = [dict(row) for row in client.query(rec_query).result()]

    # Get competitor count
    comp_query = """
        SELECT COUNT(DISTINCT listing_id) as count
        FROM `{project_id}.pricing.competitor_listings`
        WHERE is_active = TRUE
    """.format(project_id=project_id)

    comp_count_result = list(client.query(comp_query).result())
    comp_count = comp_count_result[0]['count'] if comp_count_result else 0

    # Get market stats
    market_query = """
        SELECT
            MIN(price_per_night) as min_price,
            MAX(price_per_night) as max_price,
            APPROX_QUANTILES(price_per_night, 2)[OFFSET(1)] as median_price
        FROM `{project_id}.pricing.daily_prices`
        WHERE price_per_night IS NOT NULL
    """.format(project_id=project_id)

    market_result = list(client.query(market_query).result())
    market_stats = dict(market_result[0]) if market_result else {}

    # Format data for chart
    price_data = {
        'dates': [str(r['target_date']) for r in recommendations],
        'recommended': [float(r['recommended_price']) for r in recommendations],
        'median': [float(r['comp_set_median']) if r['comp_set_median'] else 0 for r in recommendations],
        'min': [float(r['min_price']) for r in recommendations],
        'max': [float(r['max_price']) for r in recommendations],
    }

    # Format recommendations for display
    formatted_recs = []
    for rec in recommendations:
        formatted_recs.append({
            'target_date': str(rec['target_date']),
            'recommended_price': f"{rec['recommended_price']:.0f}",
            'comp_set_median': f"{rec['comp_set_median']:.0f}" if rec['comp_set_median'] else "N/A",
            'min_price': f"{rec['min_price']:.0f}",
            'max_price': f"{rec['max_price']:.0f}",
            'comp_set_count': rec['comp_set_count'],
            'confidence': rec['confidence']
        })

    stats = {
        'competitor_count': comp_count,
        'market_median': f"{market_stats.get('median_price', 0):.0f}" if market_stats else "0",
        'price_min': f"{market_stats.get('min_price', 0):.0f}" if market_stats else "0",
        'price_max': f"{market_stats.get('max_price', 0):.0f}" if market_stats else "0",
        'rec_count': len(recommendations),
    }

    return {
        'recommendations': formatted_recs,
        'price_data': price_data,
        'stats': stats,
        'update_date': date.today().strftime('%B %d, %Y')
    }


@functions_framework.http
def dashboard(request):
    """HTTP Cloud Function to serve dashboard."""
    try:
        project_id = os.getenv("GCP_PROJECT")
        data = get_dashboard_data(project_id)

        # Convert price_data to JSON for JavaScript
        data['price_data'] = json.dumps(data['price_data'])

        # Use Jinja2 template directly (no Flask app context needed)
        template = Template(DASHBOARD_HTML)
        return template.render(**data)

    except Exception as e:
        print(f"Error rendering dashboard: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error</h1><p>{str(e)}</p>", 500
