import yfinance as yf
import pandas as pd
import numpy as np
import sys
import argparse
import os
from jinja2 import Template
import markdown

def fetch_data(ticker):
    """Fetches 2 years of daily data using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        
        if df.empty:
            print(f"Error: No data found for ticker {ticker}")
            sys.exit(1)
            
        # Standardize columns to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        # Ensure we have required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                print(f"Error: Missing required column '{col}'")
                sys.exit(1)
                
        return df, stock.info
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        sys.exit(1)

def analyze_daily_moves(df):
    """Calculates Daily Move Distribution."""
    # Calculate daily returns
    df = df.copy()
    df['prev_close'] = df['close'].shift(1)
    df = df.dropna(subset=['prev_close']) # Drop first row
    df['pct_change'] = ((df['close'] - df['prev_close']) / df['prev_close']) * 100
    
    # Define buckets
    bins = [-float('inf'), -10, -5, -2.5, -1, 1, 2.5, 5, 10, float('inf')]
    labels = [
        'Extreme Drop (> -10%)', 
        'Large Drop (-5% to -10%)', 
        'Moderate Drop (-2.5% to -5%)', 
        'Normal Drop (-1% to -2.5%)', 
        'Quiet (< ±1%)', 
        'Normal Rise (1% to 2.5%)', 
        'Moderate Rise (2.5% to 5%)', 
        'Large Rise (5% to 10%)', 
        'Extreme Rise (> 10%)'
    ]
    
    df['move_bucket'] = pd.cut(df['pct_change'], bins=bins, labels=labels)
    distribution = df['move_bucket'].value_counts().sort_index()
    total_days = len(df)
    
    dist_data = []
    insight_text = ""
    
    for label in labels:
        count = int(distribution.get(label, 0))
        prob = (count / total_days) * 100
        dist_data.append({
            'range': label,
            'count': count,
            'probability': f"{prob:.1f}%"
        })
        
        # Simple insight logic based on probabilities
        if "Quiet" in label and prob > 30:
            insight_text += f"- Quiet Days: ~{int(prob)}% of the time. Don't force trades here.\n"
        if "Extreme" in label and prob > 5:
            insight_text += f"- Extreme moves ({label}): Occur {prob:.1f}% of the time. Risks are higher.\n"

    if not insight_text:
        quiet_prob = (distribution.get('Quiet (< ±1%)', 0) / total_days) * 100
        extreme_drop = (distribution.get('Extreme Drop (> -10%)', 0) / total_days) * 100
        extreme_rise = (distribution.get('Extreme Rise (> 10%)', 0) / total_days) * 100
        total_extreme = extreme_drop + extreme_rise
        
        insight_text = f"- Combined \"Extreme\" moves (>10% drop or rise) occur ~{total_extreme:.1f}% of the time.\n"
        insight_text += f"- \"Quiet\" days are {'common' if quiet_prob > 20 else 'relatively rare'} (~{quiet_prob:.1f}%)."

    return df, dist_data, insight_text

def analyze_swing_duration(df):
    """Calculates Trend & Swing Duration Metrics."""
    # Direction
    df['direction'] = df['pct_change'].apply(lambda x: 1 if x > 0 else -1)
    
    up_days = len(df[df['direction'] == 1])
    down_days = len(df[df['direction'] == -1])
    total = len(df)
    
    bias = {
        'up_days': up_days,
        'up_pct': f"{up_days/total*100:.1f}%",
        'down_days': down_days,
        'down_pct': f"{down_days/total*100:.1f}%"
    }
    
    # Streaks
    df['streak_id'] = (df['direction'] != df['direction'].shift(1)).cumsum()
    streak_lengths = df.groupby('streak_id').size()
    streak_counts = streak_lengths.value_counts().sort_index()
    
    swing_data = []
    max_count = streak_counts.max()
    for length, count in streak_counts.items():
        if length <= 5:
            term = "(Most Common - Reversal likely)" if count == max_count else ""
            swing_data.append({
                'length': f"{length}-Day",
                'count': int(count),
                'term': term
            })
        elif length == 6:
             swing_data.append({
                'length': "6+ Day",
                'count': int(streak_counts[streak_counts.index >= 6].sum()),
                'term': "(Rare)"
             })
             break

    most_common = int(streak_counts.idxmax())
    implication = f"- Most common swing duration: {most_common} days.\n"
    implication += "- Probability of verifying extended trends diminishes significantly after Day 3."

    return bias, swing_data, implication

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Strategy Report - {{ ticker }}</title>
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
        .card { background: rgba(3, 88, 140, 0.15); border: 1px solid rgba(176, 196, 217, 0.2); border-radius: 16px; backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0,0,0,0.4); }
        .card-content { color: var(--ocean-light) !important; }
        .card-title { font-weight: 800 !important; color: var(--ocean-neon) !important; text-transform: uppercase; letter-spacing: 2px; border-bottom: 3px solid var(--ocean-forest); padding-bottom: 15px; display: block; margin-bottom: 25px !important; }
        .insight-box { background: rgba(4, 216, 139, 0.05); padding: 20px; border-radius: 8px; border-left: 6px solid var(--ocean-neon); margin-top: 30px; color: #fff; font-size: 1.05rem; }
        .header-panel { background: rgba(0,0,0,0.3); padding: 50px 0; margin-bottom: 40px; border-bottom: 1px solid rgba(176, 196, 217, 0.1); }
        .header-panel h3 { font-weight: 900; color: #fff; text-shadow: 0 0 20px rgba(4, 216, 139, 0.4); }
        .header-panel p { color: var(--ocean-neon); font-family: monospace; font-size: 1.1rem; }
        .chart-container { position: relative; height:380px; width:100%; margin-top: 20px; background: rgba(0,0,0,0.4); border-radius: 12px; padding: 15px; border: 1px solid rgba(176, 196, 217, 0.05); }
        table { border-collapse: separate; border-spacing: 0 8px; }
        table.striped > tbody > tr:nth-child(odd) { background-color: rgba(176, 196, 217, 0.05); }
        table.striped > tbody > tr { border: none; transition: background 0.3s; }
        table.striped > tbody > tr:hover { background: rgba(4, 216, 139, 0.1); }
        thead { color: var(--ocean-neon); text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px; }
        .footer { padding: 60px 20px; text-align: center; color: rgba(176, 196, 217, 0.3); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 4px; }
        .bias-box-up { background: rgba(4, 216, 139, 0.15); border: 1px solid var(--ocean-neon); }
        .bias-box-down { background: rgba(253, 70, 0, 0.1); border: 1px solid #fd4600; }
        .bias-label { font-size: 0.75rem; color: var(--ocean-light); opacity: 0.6; font-weight: bold; }
        .bias-val { font-size: 1.6rem; font-weight: 900; color: #fff; }
    </style>
</head>
<body>
    <div class="header-panel">
        <div class="container">
            <h3 class="center-align" style="margin:0;">STRATEGY REPORT: {{ ticker }}</h3>
            <p class="center-align" style="margin-top: 15px;">// {{ company_name }} | {{ date }}</p>
        </div>
    </div>

    <div class="container">
        <div class="row">
            <div class="col s12 m10 offset-m1">
                <!-- Distribution Analysis -->
                <div class="card">
                    <div class="card-content">
                        <span class="card-title">Volatility Distribution</span>
                        <div class="chart-container">
                            <canvas id="moveChart"></canvas>
                        </div>
                        <table class="striped" style="margin-top: 40px;">
                            <thead>
                                <tr>
                                    <th>Market Move</th>
                                    <th class="right-align">Count</th>
                                    <th class="right-align">Probability</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in dist_data %}
                                <tr>
                                    <td style="color: #fff;">{{ row.range }}</td>
                                    <td class="right-align">{{ row.count }}</td>
                                    <td class="right-align" style="color: var(--ocean-neon); font-weight: 800;">{{ row.probability }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div class="insight-box">
                            <strong><i class="material-icons left" style="color: var(--ocean-neon)">analytics</i>DISTRIBUTION INSIGHTS</strong><br><br>
                            {{ insight_text | replace('\\n', '<br>') | safe }}
                        </div>
                    </div>
                </div>

                <!-- Swing Metrics -->
                <div class="card" style="margin-top: 40px;">
                    <div class="card-content">
                        <span class="card-title">Streak Analysis</span>
                        
                        <div class="row">
                            <div class="col s12 l5">
                                <p style="margin-bottom: 20px; font-weight: bold; color: var(--ocean-mid);">DIRECTIONAL BIAS [2Y]</p>
                                <div style="display: flex; gap: 15px; margin-bottom: 30px;">
                                    <div class="bias-box-up" style="flex: 1; padding: 15px; border-radius: 12px;">
                                        <div class="bias-label">UP DAYS</div>
                                        <div class="bias-val">{{ bias.up_pct }}</div>
                                    </div>
                                    <div class="bias-box-down" style="flex: 1; padding: 15px; border-radius: 12px;">
                                        <div class="bias-label">DOWN DAYS</div>
                                        <div class="bias-val">{{ bias.down_pct }}</div>
                                    </div>
                                </div>
                                <table class="striped">
                                    <thead>
                                        <tr>
                                            <th>Streak</th>
                                            <th class="right-align">Frequency</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for row in swing_data %}
                                        <tr>
                                            <td style="color: #fff;">{{ row.length }}</td>
                                            <td class="right-align">{{ row.count }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            <div class="col s12 l7">
                                <div class="chart-container">
                                    <canvas id="swingChart"></canvas>
                                </div>
                            </div>
                        </div>

                        <div class="insight-box" style="border-left-color: #fd4600;">
                            <strong><i class="material-icons left" style="color: #fd4600">bolt</i>TACTICAL IMPLICATION</strong><br><br>
                            {{ implication | replace('\\n', '<br>') | safe }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        ALPHA-PLAYBOOKS REPORTING ENGINE // STOCK-PRICE-DISTRIBUTION v1.2
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
    <script>
        const oceanNeon = '#04D88B';
        const oceanLight = '#B0C4D9';
        const oceanMid = '#03588C';
        const oceanForest = '#03734A';
        const deepBlue = '#022840';

        // Move Distribution Chart
        const moveCtx = document.getElementById('moveChart').getContext('2d');
        new Chart(moveCtx, {
            type: 'bar',
            data: {
                labels: {{ move_labels | safe }},
                datasets: [{
                    label: 'Day Count',
                    data: {{ move_counts | safe }},
                    backgroundColor: (context) => {
                        const index = context.dataIndex;
                        return (index < 2 || index > 6) ? '#fd4600' : oceanNeon;
                    },
                    borderRadius: 6,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(176, 196, 217, 0.1)' }, ticks: { color: oceanLight } },
                    x: { grid: { display: false }, ticks: { color: oceanLight } }
                },
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'DAILY VOLATILITY FREQUENCY', color: '#fff', font: { size: 16, weight: 'bold' } }
                }
            }
        });

        // Swing Duration Chart
        const swingCtx = document.getElementById('swingChart').getContext('2d');
        new Chart(swingCtx, {
            type: 'bar',
            data: {
                labels: {{ swing_labels | safe }},
                datasets: [{
                    label: 'Frequency',
                    data: {{ swing_counts | safe }},
                    backgroundColor: oceanMid,
                    borderColor: oceanNeon,
                    borderWidth: 2,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { beginAtZero: true, grid: { color: 'rgba(176, 196, 217, 0.1)' }, ticks: { color: oceanLight } },
                    y: { grid: { display: false }, ticks: { color: oceanLight } }
                },
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'CONSECUTIVE STREAKS', color: '#fff', font: { size: 16, weight: 'bold' } }
                }
            }
        });
    </script>
</body>
</html>
"""

def generate_markdown(ticker, info, dist_data, insight_text, bias, swing_data, implication):
    md = f"# Strategy Report: {ticker}\n"
    md += f"**Company**: {info.get('longName', 'N/A')}  \n"
    md += f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n"
    
    md += "## 1. Daily Move Distribution Analysis\n\n"
    md += "| Move Range | Count | Probability |\n"
    md += "| --- | --- | --- |\n"
    for row in dist_data:
        md += f"| {row['range']} | {row['count']} | {row['probability']} |\n"
    
    md += "\n### Insights\n"
    md += insight_text + "\n\n"
    
    md += "## 2. Swing Duration Metrics\n\n"
    md += "### Directional Bias\n"
    md += f"- Up Days: {bias['up_days']} ({bias['up_pct']})\n"
    md += f"- Down Days: {bias['down_days']} ({bias['down_pct']})\n\n"
    
    md += "### Swing Duration (Consecutive Days)\n\n"
    md += "| Duration | Frequency | Note |\n"
    md += "| --- | --- | --- |\n"
    for row in swing_data:
        md += f"| {row['length']} | {row['count']} | {row['term']} |\n"
    
    md += "\n### Strategy Implication\n"
    md += implication + "\n"
    
    return md

def generate_text_report(ticker, info, dist_data, insight_text, bias, swing_data, implication):
    report = f"\n{'='*50}\n"
    report += f"STRATEGY REPORT: {ticker}\n"
    report += f"{info.get('longName', 'N/A')}\n"
    report += f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += f"{'='*50}\n\n"
    
    report += "1. DAILY MOVE DISTRIBUTION\n"
    report += f"{'-'*30}\n"
    report += f"{'Range':<30} | {'Count':<5} | {'Prob':<6}\n"
    report += f"{'-'*30}\n"
    for row in dist_data:
        report += f"{row['range']:<30} | {row['count']:<5} | {row['probability']:<6}\n"
    
    report += "\nINSIGHTS:\n"
    report += insight_text + "\n\n"
    
    report += "2. SWING DURATION METRICS\n"
    report += f"{'-'*30}\n"
    report += f"Directional Bias: Up {bias['up_pct']} | Down {bias['down_pct']}\n\n"
    report += f"{'Duration':<10} | {'Freq':<5} | {'Note'}\n"
    for row in swing_data:
        report += f"{row['length']:<10} | {row['count']:<5} | {row['term']}\n"
    
    report += "\nSTRATEGY IMPLICATION:\n"
    report += implication + "\n"
    report += f"{'='*50}\n"
    return report

def main():
    parser = argparse.ArgumentParser(description='Generate Strategy Report (Distribution & Swings)')
    parser.add_argument('ticker', type=str, help='Stock Ticker Symbol')
    parser.add_argument('--markdown', '-m', action='store_true', help='Generate Markdown report file')
    parser.add_argument('--html', '-w', action='store_true', help='Generate HTML report file')
    parser.add_argument('--output-dir', '-o', type=str, default='.', help='Directory to save output files')
    args = parser.parse_args()
    
    ticker = args.ticker.upper()
    df, info = fetch_data(ticker)
    df, dist_data, insight_text = analyze_daily_moves(df)
    bias, swing_data, implication = analyze_swing_duration(df)
    
    # Ensure output directory exists
    if args.output_dir != '.' and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Text Report (Always generated or printed if no flags)
    text_report = generate_text_report(ticker, info, dist_data, insight_text, bias, swing_data, implication)
    
    if not (args.markdown or args.html):
        print(text_report)
    else:
        print(f"Analysis complete for {ticker}.")

    # Markdown Generation
    if args.markdown:
        markdown_content = generate_markdown(ticker, info, dist_data, insight_text, bias, swing_data, implication)
        md_filename = f"{ticker}_report.md"
        output_path = os.path.join(args.output_dir, md_filename)
        with open(output_path, "w") as f:
            f.write(markdown_content)
        print(f"Markdown report saved to {output_path}")
    
    # HTML Generation
    if args.html:
        move_labels = [row['range'] for row in dist_data]
        move_counts = [row['count'] for row in dist_data]
        swing_labels = [row['length'] for row in swing_data]
        swing_counts = [row['count'] for row in swing_data]
        
        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            ticker=ticker,
            company_name=info.get('longName', 'N/A'),
            date=pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
            dist_data=dist_data,
            insight_text=insight_text,
            bias=bias,
            swing_data=swing_data,
            implication=implication,
            move_labels=move_labels,
            move_counts=move_counts,
            swing_labels=swing_labels,
            swing_counts=swing_counts
        )
        html_filename = f"{ticker}_report.html"
        output_path = os.path.join(args.output_dir, html_filename)
        with open(output_path, "w") as f:
            f.write(html_content)
        print(f"HTML report saved to {output_path}")

if __name__ == "__main__":
    main()
