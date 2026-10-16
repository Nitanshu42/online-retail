# Retail Intelligence Dashboard

This project is a lightweight data warehousing and data mining dashboard for the Online Retail dataset. It combines summary analytics, customer analysis, and association rule mining in a simple web interface.

## Features
- Total sales overview
- Monthly, yearly, and weekly transaction trend analysis
- Customer repeat-purchase and spending behavior analysis
- Product buying pattern analysis by customer
- Association rule mining using an Apriori-style algorithm
- Quick filter controls for country, year, minimum support, and minimum confidence
- Apply button to update the dashboard only after the user confirms the selected filters

## How to run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open:

http://localhost:5000

## How to use the dashboard

1. Select a country and year from the filter panel.
2. Set the minimum support and confidence values if needed.
3. Click the Apply button to refresh the statistics, charts, and association rules.
4. Use the customer dropdown to inspect a specific customer's behavior.
5. Use Reset to restore the default view.

## Data source
The dashboard reads the cleaned retail dataset from:

`WEKA_PBL_DATA/retail_clean.csv`

## Notes
This project is intentionally simple and beginner-friendly, similar to a compact Weka-style data exploration tool, but displayed in a browser dashboard with interactive filters.
