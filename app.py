from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Set, Tuple

import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DATA_PATH = "WEKA_PBL_DATA/retail_clean.csv"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["InvoiceDate", "CustomerID"]).copy()
    df["CustomerID"] = df["CustomerID"].astype(int)
    df["TotalAmount"] = pd.to_numeric(df["TotalAmount"], errors="coerce").fillna(0)
    df["Year"] = df["InvoiceDate"].dt.year
    df["MonthName"] = df["InvoiceDate"].dt.month_name()
    df["Weekday"] = df["InvoiceDate"].dt.day_name()
    return df


DATA = load_data()


def get_filtered_data(country: str | None = None, year: str | int | None = None) -> pd.DataFrame:
    filtered = DATA.copy()
    if country and country != "All":
        filtered = filtered[filtered["Country"] == country]
    if year not in (None, "", "All"):
        filtered = filtered[filtered["Year"] == int(year)]
    return filtered


def get_customer_metrics(df: pd.DataFrame) -> pd.DataFrame:
    customer = (
        df.groupby("CustomerID")
        .agg(
            NumberOfOrders=("InvoiceNo", "nunique"),
            TotalQuantity=("Quantity", "sum"),
            TotalSpending=("TotalAmount", "sum"),
            AverageOrderValue=("TotalAmount", "mean"),
            NumberOfProducts=("Description", "nunique"),
            Country=("Country", "first"),
            LastPurchase=("InvoiceDate", "max"),
            FirstPurchase=("InvoiceDate", "min"),
        )
        .reset_index()
    )
    customer["TotalSpending"] = customer["TotalSpending"].round(2)
    customer["AverageOrderValue"] = customer["AverageOrderValue"].round(2)
    return customer.sort_values("TotalSpending", ascending=False)


def build_transactions(df: pd.DataFrame) -> List[List[str]]:
    transactions = (
        df.groupby("InvoiceNo")["Description"]
        .apply(lambda items: sorted(set(str(x).strip() for x in items if str(x).strip())))
        .tolist()
    )
    return [txn for txn in transactions if txn]


def apriori(transactions: List[List[str]], min_support: float = 0.02, min_confidence: float = 0.5):
    total_transactions = len(transactions)
    if total_transactions == 0:
        return []

    transaction_sets = [set(str(item).strip() for item in transaction if str(item).strip()) for transaction in transactions]
    item_counts: Dict[frozenset, int] = defaultdict(int)
    for transaction in transaction_sets:
        for item in transaction:
            item_counts[frozenset([item])] += 1

    frequent_sets: List[Tuple[frozenset, int]] = []
    current = {
        itemset for itemset, count in item_counts.items() if count / total_transactions >= min_support
    }
    k = 1

    while current:
        valid = []
        for itemset in current:
            support_count = sum(1 for transaction in transaction_sets if itemset.issubset(transaction))
            support = support_count / total_transactions
            if support >= min_support:
                valid.append(itemset)
                frequent_sets.append((itemset, support_count))

        if not valid:
            break

        next_candidates = set()
        valid_list = list(valid)
        for i in range(len(valid_list)):
            for j in range(i + 1, len(valid_list)):
                union = valid_list[i].union(valid_list[j])
                if len(union) != k + 1:
                    continue

                subset_checks = [
                    frozenset(subset) for subset in combinations(sorted(union), k)
                ]
                if all(subset in set(valid_list) for subset in subset_checks):
                    next_candidates.add(frozenset(union))

        current = next_candidates
        k += 1

    frequent_map = {itemset: count for itemset, count in frequent_sets}
    rules = []

    for itemset, count in frequent_sets:
        if len(itemset) < 2:
            continue
        for r in range(1, len(itemset)):
            for antecedent in combinations(sorted(itemset), r):
                antecedent_set = frozenset(antecedent)
                consequent_set = itemset.difference(antecedent_set)
                if not consequent_set:
                    continue

                antecedent_count = frequent_map.get(antecedent_set, 0)
                consequent_count = frequent_map.get(consequent_set, 0)
                if antecedent_count == 0:
                    continue

                support = count / total_transactions
                confidence = count / antecedent_count
                lift = confidence / (consequent_count / total_transactions)

                if confidence >= min_confidence:
                    rules.append(
                        {
                            "antecedent": list(sorted(antecedent_set)),
                            "consequent": list(sorted(consequent_set)),
                            "support": round(support, 4),
                            "confidence": round(confidence, 4),
                            "lift": round(lift, 4),
                        }
                    )

    unique_rules = []
    seen = set()
    for rule in rules:
        key = (tuple(rule["antecedent"]), tuple(rule["consequent"]))
        if key not in seen:
            seen.add(key)
            unique_rules.append(rule)

    unique_rules.sort(key=lambda x: x["lift"], reverse=True)
    return unique_rules[:12]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/filters")
def filters():
    countries = ["All"] + sorted(DATA["Country"].dropna().unique().tolist())
    years = ["All"] + [str(year) for year in sorted(DATA["Year"].dropna().unique().tolist())]
    return jsonify({"countries": countries, "years": years})


@app.route("/api/overview")
def overview():
    country = request.args.get("country")
    year = request.args.get("year")
    filtered = get_filtered_data(country, year)

    if filtered.empty:
        return jsonify(
            {
                "total_orders": 0,
                "total_revenue": 0,
                "total_customers": 0,
                "repeat_customers": 0,
                "avg_order_value": 0,
                "top_country": "N/A",
            }
        )

    total_orders = filtered["InvoiceNo"].nunique()
    total_revenue = round(float(filtered["TotalAmount"].sum()), 2)
    total_customers = filtered["CustomerID"].nunique()
    repeat_customers = int((filtered.groupby("CustomerID").size() > 1).sum())
    avg_order = round(total_revenue / total_orders, 2) if total_orders else 0

    return jsonify(
        {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "repeat_customers": repeat_customers,
            "avg_order_value": avg_order,
            "top_country": filtered["Country"].value_counts().idxmax(),
        }
    )


@app.route("/api/trends")
def trends():
    country = request.args.get("country")
    year = request.args.get("year")
    filtered = get_filtered_data(country, year)

    if filtered.empty:
        return jsonify({"monthly": [], "yearly": [], "weekly": []})

    monthly = (
        filtered.groupby("MonthName", dropna=False)
        .agg(orders=("InvoiceNo", "nunique"), revenue=("TotalAmount", "sum"))
        .reset_index()
    )
    yearly = (
        filtered.groupby("Year", dropna=False)
        .agg(orders=("InvoiceNo", "nunique"), revenue=("TotalAmount", "sum"))
        .reset_index()
    )
    weekly = (
        filtered.groupby("Weekday", dropna=False)
        .agg(orders=("InvoiceNo", "nunique"), revenue=("TotalAmount", "sum"))
        .reset_index()
    )

    return jsonify(
        {
            "monthly": [{"label": row["MonthName"], "value": int(row["orders"])} for _, row in monthly.iterrows()],
            "yearly": [{"label": str(row["Year"]), "value": int(row["orders"])} for _, row in yearly.iterrows()],
            "weekly": [{"label": row["Weekday"], "value": int(row["orders"])} for _, row in weekly.iterrows()],
        }
    )


@app.route("/api/customers")
def customers():
    country = request.args.get("country")
    year = request.args.get("year")
    filtered = get_filtered_data(country, year)
    if filtered.empty:
        return jsonify([])

    customer_metrics = get_customer_metrics(filtered)
    return jsonify(
        [{
            "customer_id": int(row["CustomerID"]),
            "orders": int(row["NumberOfOrders"]),
            "spending": round(float(row["TotalSpending"]), 2),
            "country": row["Country"],
        } for _, row in customer_metrics.head(20).iterrows()]
    )


@app.route("/api/customer-analysis")
def customer_analysis():
    customer_id = int(request.args.get("customer_id", 12347))
    country = request.args.get("country")
    year = request.args.get("year")
    filtered = get_filtered_data(country, year)
    customer_df = filtered[filtered["CustomerID"] == customer_id].copy()

    if customer_df.empty:
        return jsonify({"error": "Customer not found"}), 404

    customer_metrics = get_customer_metrics(customer_df)
    summary = customer_metrics.iloc[0].to_dict()

    monthly = (
        customer_df.groupby("MonthName").agg(orders=("InvoiceNo", "nunique"), revenue=("TotalAmount", "sum"))
        .reset_index()
    )
    yearly = (
        customer_df.groupby("Year").agg(orders=("InvoiceNo", "nunique"), revenue=("TotalAmount", "sum"))
        .reset_index()
    )
    weekly = (
        customer_df.groupby("Weekday").agg(orders=("InvoiceNo", "nunique"), revenue=("TotalAmount", "sum"))
        .reset_index()
    )

    top_products = (
        customer_df.groupby("Description")
        .agg(total_quantity=("Quantity", "sum"), total_spend=("TotalAmount", "sum"))
        .sort_values(["total_quantity", "total_spend"], ascending=False)
        .head(5)
        .reset_index()
    )

    return jsonify(
        {
            "customer_id": customer_id,
            "summary": {
                "NumberOfOrders": int(summary["NumberOfOrders"]),
                "TotalQuantity": int(summary["TotalQuantity"]),
                "TotalSpending": round(float(summary["TotalSpending"]), 2),
                "AverageOrderValue": round(float(summary["AverageOrderValue"]), 2),
                "NumberOfProducts": int(summary["NumberOfProducts"]),
                "Country": summary["Country"],
                "FirstPurchase": str(summary["FirstPurchase"]),
                "LastPurchase": str(summary["LastPurchase"]),
            },
            "monthly": [{"label": row["MonthName"], "value": int(row["orders"])} for _, row in monthly.iterrows()],
            "yearly": [{"label": str(row["Year"]), "value": int(row["orders"])} for _, row in yearly.iterrows()],
            "weekly": [{"label": row["Weekday"], "value": int(row["orders"])} for _, row in weekly.iterrows()],
            "top_products": [{"name": row["Description"], "value": int(row["total_quantity"])} for _, row in top_products.iterrows()],
        }
    )


@app.route("/api/association-rules")
def association_rules():
    country = request.args.get("country")
    year = request.args.get("year")
    filtered = get_filtered_data(country, year)
    min_support = float(request.args.get("min_support", 0.02))
    min_confidence = float(request.args.get("min_confidence", 0.5))
    min_support = max(0.001, min(min_support, 0.5))
    min_confidence = max(0.1, min(min_confidence, 1.0))

    transactions = build_transactions(filtered)
    rules = apriori(transactions, min_support=min_support, min_confidence=min_confidence)
    return jsonify(rules)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
