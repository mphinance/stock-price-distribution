# 📊 Stock Strategy Distribution Reports

This tool analyzes 2 years of historical stock data to visualize volatility distributions and swing duration metrics. It helps traders understand the "normal" behavior of a stock and identify when moves are becoming extreme.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Basic Usage (Simple Text Output)
Print the report directly to your terminal:
```bash
python3 generate_strategy_report.py NVDA
```

### 3. Generate Enhanced Reports
Generate Markdown or Interactive HTML reports using flags:
```bash
# Generate a Markdown file (NVDA_report.md)
python3 generate_strategy_report.py NVDA --markdown

# Generate an Interactive HTML file (NVDA_report.html)
python3 generate_strategy_report.py NVDA --html

# Generate both
python3 generate_strategy_report.py NVDA -m -w
```

## 🏟 The Alpha Intelligence dashboard
To generate reports for the entire watchlist and create a central landing page:
```bash
python3 generate_all_reports.py
```
This will create an `index.html` file that links to all generated reports.

## 🛠 Features
- **Daily Move Distribution**: Categorizes every trading day for the last 2 years into buckets (Quiet, Normal, Large, Extreme).
- **Swing Duration Metrics**: Tracks how many consecutive days a stock moves in one direction.
- **Branded Design**: High-impact, dark-themed reports using canonical brand colors.
- **Interactive Charts**: Built-in Chart.js visualizations.
