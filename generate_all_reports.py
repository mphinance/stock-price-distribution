import subprocess
import os
import sys

# Import analysis logic from the main script
from generate_strategy_report import fetch_data, analyze_daily_moves, analyze_swing_duration

WATCHLIST = [
    "ACHR", "AMT", "ASTS", "AVGO", "CLS", 
    "DDD", "DNN", "GLXY", "GOOGL", "ISRG", 
    "KTOS", "MU", "NFLX", "NVDA", "ONDS", 
    "PTRN", "RKLB", "RR", "TER", "TSM", "UAMY"
]

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Alpha Intelligence - Strategy Dashboard</title>
    <style>
        :root {
            --ocean-deep: #022840;
            --ocean-navy: #034C8C;
            --ocean-mid: #03588C;
            --ocean-light: #B0C4D9;
            --ocean-neon: #04D88B;
            --ocean-forest: #03734A;
        }
        body { background: radial-gradient(circle at top, var(--ocean-navy), var(--ocean-deep)); color: var(--ocean-light); font-family: 'Inter', sans-serif; min-height: 100vh; }
        .header-panel { background-color: rgba(0,0,0,0.4); color: #fff; padding: 60px 0; margin-bottom: 40px; border-bottom: 1px solid rgba(176, 196, 217, 0.1); text-align: center; }
        .header-panel h1 { font-weight: 900; margin: 0; letter-spacing: 4px; text-transform: uppercase; text-shadow: 0 0 30px rgba(4, 216, 139, 0.3); }
        .header-panel p { font-size: 1.1rem; color: var(--ocean-neon); opacity: 0.9; margin-top: 10px; font-family: monospace; }
        
        .section-title { color: var(--ocean-neon); text-transform: uppercase; font-weight: 900; letter-spacing: 2px; margin-bottom: 20px; border-left: 5px solid var(--ocean-neon); padding-left: 15px; }
        
        .comparison-card { background: rgba(3, 88, 140, 0.1); border: 1px solid rgba(176, 196, 217, 0.1); border-radius: 16px; padding: 30px; margin-bottom: 60px; backdrop-filter: blur(10px); }
        .comparison-table { width: 100%; color: var(--ocean-light); border-collapse: separate; border-spacing: 0 5px; }
        .comparison-table th { color: var(--ocean-neon); text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px; padding: 15px 5px; }
        .comparison-table td { padding: 15px 5px; border-top: 1px solid rgba(176, 196, 217, 0.05); border-bottom: 1px solid rgba(176, 196, 217, 0.05); }
        .comparison-table tr { transition: all 0.3s ease; }
        .comparison-table tr:hover { background: rgba(4, 216, 139, 0.1); cursor: pointer; }
        
        .ticker-link { 
            color: #fff; 
            font-weight: 900; 
            font-size: 1.2rem; 
            text-decoration: none; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            transition: color 0.3s ease;
        }
        .ticker-link:hover { color: var(--ocean-neon); }
        .ticker-link i { font-size: 1rem; margin-left: 5px; opacity: 0.5; }

        .container { width: 95%; max-width: 1400px; }
        .footer { padding: 80px 0; text-align: center; color: rgba(176, 196, 217, 0.2); font-size: 0.8rem; letter-spacing: 3px; text-transform: uppercase; }
        
        .val-high { color: #fd4600; font-weight: 800; }
        .val-stable { color: #4caf50; font-weight: 800; }
        .bias-up { color: #4caf50; font-weight: 800; }
        .bias-down { color: #ef5350; font-weight: 800; }
    </style>
</head>
<body>
    <div class="header-panel">
        <div class="container">
            <h1>ALPHA INTELLIGENCE</h1>
            <p>> STRATEGY_DISTRIBUTION_DASHBOARD v1.4</p>
        </div>
    </div>

    <div class="container">
        <h4 class="section-title">Market distribution Comparison</h4>
        <div class="comparison-card">
            <table class="comparison-table centered">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Extreme Volatility (%)</th>
                        <th>Stability (Normal Range %)</th>
                        <th>Directional Bias (Up %)</th>
                        <th>Quiet Frequency (%)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in summary %}
                    <tr onclick="window.location.href='{{ item.ticker }}_report.html'">
                        <td>
                            <a href="{{ item.ticker }}_report.html" class="ticker-link">
                                {{ item.ticker }} <i class="material-icons">open_in_new</i>
                            </a>
                        </td>
                        <td class="{{ 'val-high' if item.extreme_pct|float > 10 else '' }}">{{ item.extreme_pct }}%</td>
                        <td class="{{ 'val-stable' if item.stability_pct|float > 80 else '' }}">{{ item.stability_pct }}%</td>
                        <td class="{{ 'bias-up' if item.up_pct|float > 52 else ('bias-down' if item.up_pct|float < 48 else '') }}">{{ item.up_pct }}%</td>
                        <td>{{ item.quiet_pct }}%</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <div class="footer">
        POWERED BY ANTIGRAVITY | ALPHA-PLAYBOOKS SERIES
    </div>
</body>
</html>
"""

def main():
    print(f"Generating reports and aggregating comparison for: {', '.join(WATCHLIST)}")
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    summary_data = []

    for ticker in WATCHLIST:
        print(f"Processing {ticker}...")
        
        # Run the full report generation script via subprocess
        subprocess.run(["python3", "generate_strategy_report.py", ticker, "--html", "--output-dir", output_dir], check=True)
        
        # Analyze locally for the comparison table
        try:
            df, info = fetch_data(ticker)
            df_moves, dist_data, _ = analyze_daily_moves(df)
            bias, swing_data, _ = analyze_swing_duration(df_moves)
            
            # Extract comparison metrics
            extreme_pct = 0
            quiet_pct = 0
            stability_pct = 0
            
            # Stability = Quiet + Normal Rise + Normal Drop (which are the mid 3 buckets in analyze_daily_moves)
            # Labels: 'Normal Drop (-1% to -2.5%)', 'Quiet (< ±1%)', 'Normal Rise (1% to 2.5%)'
            stability_labels = ['Normal Drop (-1% to -2.5%)', 'Quiet (< ±1%)', 'Normal Rise (1% to 2.5%)']
            
            for d in dist_data:
                prob = float(d['probability'].strip('%'))
                if "Extreme" in d['range']:
                    extreme_pct += prob
                if "Quiet" in d['range']:
                    quiet_pct = prob
                if d['range'] in stability_labels:
                    stability_pct += prob

            summary_data.append({
                'ticker': ticker,
                'extreme_pct': f"{extreme_pct:.1f}",
                'stability_pct': f"{stability_pct:.1f}",
                'up_pct': bias['up_pct'].strip('%'),
                'quiet_pct': f"{quiet_pct:.1f}"
            })
        except Exception as e:
            print(f"Skipping summary for {ticker} due to error: {e}")

    print("Generating landing page...")
    from jinja2 import Template
    template = Template(INDEX_TEMPLATE)
    html_content = template.render(summary=summary_data)
    
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(html_content)
    
    print(f"Done! Open {index_path} to view the dashboard.")

if __name__ == "__main__":
    main()
