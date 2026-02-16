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
        .header-panel { background-color: rgba(0,0,0,0.4); color: #fff; padding: 80px 0; margin-bottom: 60px; border-bottom: 1px solid rgba(176, 196, 217, 0.1); text-align: center; }
        .header-panel h1 { font-weight: 900; margin: 0; letter-spacing: 4px; text-transform: uppercase; text-shadow: 0 0 30px rgba(4, 216, 139, 0.3); }
        .header-panel p { font-size: 1.3rem; color: var(--ocean-neon); opacity: 0.9; margin-top: 15px; font-family: monospace; }
        
        .section-title { color: var(--ocean-neon); text-transform: uppercase; font-weight: 900; letter-spacing: 2px; margin-bottom: 30px; border-left: 5px solid var(--ocean-neon); padding-left: 15px; }
        
        .comparison-card { background: rgba(3, 88, 140, 0.1); border: 1px solid rgba(176, 196, 217, 0.1); border-radius: 16px; padding: 30px; margin-bottom: 60px; }
        .comparison-table { width: 100%; color: var(--ocean-light); }
        .comparison-table th { color: var(--ocean-neon); text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px; }
        .comparison-table td { padding: 12px 5px; border-bottom: 1px solid rgba(176, 196, 217, 0.05); }
        .comparison-table tr:hover { background: rgba(4, 216, 139, 0.05); }

        .card { background-color: rgba(3, 88, 140, 0.15); border: 1px solid rgba(176, 196, 217, 0.1); border-radius: 16px; backdrop-filter: blur(10px); transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        .card:hover { transform: translateY(-10px) scale(1.02); border-color: var(--ocean-neon); background-color: rgba(3, 88, 140, 0.25); box-shadow: 0 15px 45px rgba(0,0,0,0.5); }
        .card-title { color: #fff !important; font-weight: 800 !important; text-transform: uppercase; letter-spacing: 1px; }
        .card-action { border-top: 1px solid rgba(176, 196, 217, 0.1) !important; background: transparent !important; }
        .card-action a { color: var(--ocean-neon) !important; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }
        .container { width: 95%; max-width: 1400px; }
        .ticker-badge { background: linear-gradient(45deg, var(--ocean-neon), var(--ocean-forest)); color: #000; padding: 4px 12px; border-radius: 6px; font-weight: 900; font-size: 1rem; margin-bottom: 15px; display: inline-block; }
        .footer { padding: 80px 0; text-align: center; color: rgba(176, 196, 217, 0.2); font-size: 0.8rem; letter-spacing: 3px; text-transform: uppercase; }
        
        .val-high { color: #fd4600; font-weight: 800; }
        .val-low { color: var(--ocean-neon); font-weight: 800; }
        .bias-up { color: #4caf50; font-weight: 800; }
        .bias-down { color: #ef5350; font-weight: 800; }
    </style>
</head>
<body>
    <div class="header-panel">
        <div class="container">
            <h1>ALPHA INTELLIGENCE</h1>
            <p>> STRATEGY_DISTRIBUTION_DASHBOARD v1.3</p>
        </div>
    </div>

    <div class="container">
        <!-- Comparison Pulse -->
        <h4 class="section-title">Watchlist Alpha comparison</h4>
        <div class="comparison-card">
            <table class="comparison-table centered">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Extreme Volatility (%)</th>
                        <th>Directional Bias (Up %)</th>
                        <th>Avg Swing Delay</th>
                        <th>Quiet frequency</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in summary %}
                    <tr>
                        <td style="font-weight: 900; color: #fff;">{{ item.ticker }}</td>
                        <td class="{{ 'val-high' if item.extreme_pct|float > 10 else '' }}">{{ item.extreme_pct }}%</td>
                        <td class="{{ 'bias-up' if item.up_pct|float > 52 else ('bias-down' if item.up_pct|float < 48 else '') }}">{{ item.up_pct }}%</td>
                        <td>{{ item.avg_swing }} Days</td>
                        <td class="{{ 'val-low' if item.quiet_pct|float > 30 else '' }}">{{ item.quiet_pct }}%</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <h4 class="section-title">Individual reports</h4>
        <div class="row">
            {% for ticker in watchlist %}
            <div class="col s12 m6 l4 xl3">
                <div class="card">
                    <div class="card-content">
                        <div class="ticker-badge">{{ ticker }}</div>
                        <span class="card-title">Strategy Report</span>
                        <p style="color: var(--ocean-light); font-size: 0.95rem; line-height: 1.6;">Tactical volatility distribution and swing duration metrics for {{ ticker }}.</p>
                    </div>
                    <div class="card-action">
                        <a href="{{ ticker }}_report.html">Initialize Analysis <i class="material-icons right">chevron_right</i></a>
                    </div>
                </div>
            </div>
            {% endfor %}
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
        
        # Run the full report generation script via subprocess to ensure HTML files are created
        subprocess.run(["python3", "generate_strategy_report.py", ticker, "--html", "--output-dir", output_dir], check=True)
        
        # Analyze locally for the comparison table
        try:
            df, info = fetch_data(ticker)
            df_moves, dist_data, _ = analyze_daily_moves(df)
            bias, swing_data, _ = analyze_swing_duration(df_moves)
            
            # Extract comparison metrics
            extreme_pct = 0
            quiet_pct = 0
            for d in dist_data:
                prob = float(d['probability'].strip('%'))
                if "Extreme" in d['range']:
                    extreme_pct += prob
                if "Quiet" in d['range']:
                    quiet_pct = prob
            
            # Avg swing (idxmax of streak counts is a good proxy for modal swing)
            avg_swing = 1
            max_freq = 0
            for s in swing_data:
                if s['count'] > max_freq:
                    max_freq = s['count']
                    avg_swing = s['length'].split('-')[0]

            summary_data.append({
                'ticker': ticker,
                'extreme_pct': f"{extreme_pct:.1f}",
                'up_pct': bias['up_pct'].strip('%'),
                'avg_swing': avg_swing,
                'quiet_pct': f"{quiet_pct:.1f}"
            })
        except Exception as e:
            print(f"Skipping summary for {ticker} due to error: {e}")

    print("Generating landing page...")
    from jinja2 import Template
    template = Template(INDEX_TEMPLATE)
    html_content = template.render(watchlist=WATCHLIST, summary=summary_data)
    
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(html_content)
    
    print(f"Done! Open {index_path} to view the dashboard.")

if __name__ == "__main__":
    main()
