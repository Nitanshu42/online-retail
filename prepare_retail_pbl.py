import pandas as pd
import re
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("Online Retail.xlsx")

OUTPUT_DIR = Path("WEKA_PBL_DATA")

OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# 1. READ EXCEL DATASET
# ============================================================

print("=" * 60)
print("RETAIL DATA MINING PBL - DATA PREPARATION")
print("=" * 60)

print("\n[1] Reading Excel file...")

df = pd.read_excel(INPUT_FILE)

print("Original dataset loaded successfully.")
print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nColumns found:")
print(df.columns.tolist())

# ============================================================
# 2. STANDARDIZE COLUMN NAMES
# ============================================================

df.columns = [
    str(col).strip().replace(" ", "_")
    for col in df.columns
]

# ============================================================
# 3. BASIC DATA CLEANING
# ============================================================

print("\n[2] Cleaning data...")

# Remove rows without CustomerID
before = len(df)

df = df.dropna(subset=["CustomerID"])

print(
    "Removed rows with missing CustomerID:",
    before - len(df)
)

# Convert CustomerID to integer
df["CustomerID"] = df["CustomerID"].astype(int)

# Remove cancelled invoices
# In this dataset cancellation invoices normally begin with C
before = len(df)

df = df[
    ~df["InvoiceNo"]
    .astype(str)
    .str.upper()
    .str.startswith("C")
]

print(
    "Removed cancelled transactions:",
    before - len(df)
)

# Remove negative or zero quantities
before = len(df)

df = df[df["Quantity"] > 0]

print(
    "Removed invalid quantities:",
    before - len(df)
)

# Remove zero/negative prices
before = len(df)

df = df[df["UnitPrice"] > 0]

print(
    "Removed invalid prices:",
    before - len(df)
)

# Remove missing product descriptions
df = df.dropna(subset=["Description"])

# Clean product descriptions
df["Description"] = (
    df["Description"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# ============================================================
# 4. CREATE TOTAL AMOUNT
# ============================================================

df["TotalAmount"] = df["Quantity"] * df["UnitPrice"]

# ============================================================
# 5. PROCESS DATE
# ============================================================

df["InvoiceDate"] = pd.to_datetime(
    df["InvoiceDate"],
    errors="coerce"
)

df = df.dropna(subset=["InvoiceDate"])

df["Year"] = df["InvoiceDate"].dt.year
df["Month"] = df["InvoiceDate"].dt.month
df["Day"] = df["InvoiceDate"].dt.day

# ============================================================
# 6. SAVE CLEAN RETAIL DATASET
# ============================================================

print("\n[3] Creating cleaned retail dataset...")

retail_columns = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
    "TotalAmount",
    "Year",
    "Month",
    "Day"
]

retail = df[retail_columns].copy()

retail.to_csv(
    OUTPUT_DIR / "retail_clean.csv",
    index=False
)

print("Saved:")
print(OUTPUT_DIR / "retail_clean.csv")

# ============================================================
# FUNCTION: WRITE ARFF
# ============================================================

def write_arff(
    dataframe,
    filename,
    relation_name,
    attribute_types
):

    with open(filename, "w", encoding="utf-8") as f:

        f.write(f"@relation {relation_name}\n\n")

        for column, attr_type in attribute_types.items():

            safe_name = re.sub(
                r"[^A-Za-z0-9_]",
                "_",
                str(column)
            )

            f.write(
                f"@attribute {safe_name} {attr_type}\n"
            )

        f.write("\n@data\n")

        for _, row in dataframe.iterrows():

            values = []

            for column in attribute_types.keys():

                value = row[column]

                if pd.isna(value):

                    values.append("?")

                elif attribute_types[column] == "numeric":

                    values.append(str(value))

                else:

                    # Escape backslash and single quote
                    value = str(value)
                    value = value.replace("\\", "\\\\")
                    value = value.replace("'", "\\'")

                    values.append("'" + value + "'")

            f.write(",".join(values) + "\n")


# ============================================================
# 7. CREATE RETAIL ARFF
# ============================================================

print("\n[4] Creating retail_clean.arff...")

retail_arff = retail.copy()

retail_arff["InvoiceNo"] = (
    retail_arff["InvoiceNo"].astype(str)
)

retail_arff["StockCode"] = (
    retail_arff["StockCode"].astype(str)
)

retail_arff["Country"] = (
    retail_arff["Country"].astype(str)
)

# Convert date to string
retail_arff["InvoiceDate"] = (
    retail_arff["InvoiceDate"]
    .dt.strftime("%Y-%m-%d %H:%M:%S")
)

retail_attributes = {
    "InvoiceNo": "string",
    "StockCode": "string",
    "Description": "string",
    "Quantity": "numeric",
    "InvoiceDate": "string",
    "UnitPrice": "numeric",
    "CustomerID": "numeric",
    "Country": "string",
    "TotalAmount": "numeric",
    "Year": "numeric",
    "Month": "numeric",
    "Day": "numeric"
}

write_arff(
    retail_arff,
    OUTPUT_DIR / "retail_clean.arff",
    "retail_clean",
    retail_attributes
)

print("Saved:")
print(OUTPUT_DIR / "retail_clean.arff")

# ============================================================
# 8. CUSTOMER SEGMENTATION DATASET
# ============================================================

print("\n[5] Creating customer segmentation dataset...")

customer = (
    df.groupby("CustomerID")
    .agg(
        NumberOfOrders=("InvoiceNo", "nunique"),
        TotalQuantity=("Quantity", "sum"),
        TotalSpending=("TotalAmount", "sum"),
        AverageOrderValue=("TotalAmount", "mean"),
        NumberOfProducts=("StockCode", "nunique"),
        Country=("Country", "first")
    )
    .reset_index()
)

# Round numerical values
customer["TotalSpending"] = customer[
    "TotalSpending"
].round(2)

customer["AverageOrderValue"] = customer[
    "AverageOrderValue"
].round(2)

customer.to_csv(
    OUTPUT_DIR / "customer_segments.csv",
    index=False
)

customer_attributes = {
    "CustomerID": "numeric",
    "NumberOfOrders": "numeric",
    "TotalQuantity": "numeric",
    "TotalSpending": "numeric",
    "AverageOrderValue": "numeric",
    "NumberOfProducts": "numeric",
    "Country": "string"
}

write_arff(
    customer,
    OUTPUT_DIR / "customer_segments.arff",
    "customer_segments",
    customer_attributes
)

print("Saved:")
print(OUTPUT_DIR / "customer_segments.arff")
# ============================================================
# 9. CREATE MARKET BASKET DATASET
# ============================================================

print("\n[6] Creating market basket dataset...")

# Make sure StockCode is consistently treated as text
df["StockCode"] = (
    df["StockCode"]
    .astype(str)
    .str.strip()
)

# Remove invalid/empty product codes
df = df[
    (df["StockCode"] != "") &
    (df["StockCode"].notna())
]

# Count how many invoices contain each product
product_frequency = (
    df.groupby("StockCode")["InvoiceNo"]
    .nunique()
    .sort_values(ascending=False)
)

# ------------------------------------------------------------
# Select the 100 most frequently purchased products
# ------------------------------------------------------------

TOP_PRODUCTS = 100

top_products = product_frequency.head(
    TOP_PRODUCTS
).index.tolist()

basket_df = df[
    df["StockCode"].isin(top_products)
].copy()

# Keep only transaction and product
basket_df = basket_df[
    ["InvoiceNo", "StockCode"]
]

# Remove duplicate product purchases within
# the same invoice
basket_df = basket_df.drop_duplicates()

# ------------------------------------------------------------
# Create transaction-product matrix
# ------------------------------------------------------------

basket = pd.crosstab(
    basket_df["InvoiceNo"],
    basket_df["StockCode"]
)

# Convert counts to binary values:
# 1 = product purchased
# 0 = product not purchased
basket = (basket > 0).astype(int)

# Make absolutely sure all column names are strings
basket.columns = basket.columns.astype(str)

# Sort product columns
basket = basket.reindex(
    sorted(basket.columns),
    axis=1
)

print(
    "Number of transactions:",
    len(basket)
)

print(
    "Number of product attributes:",
    len(basket.columns)
)

# ------------------------------------------------------------
# Save normal CSV
# ------------------------------------------------------------

basket.to_csv(
    OUTPUT_DIR / "market_basket.csv"
)

print(
    "Saved:",
    OUTPUT_DIR / "market_basket.csv"
)

# ============================================================
# 10. WRITE SPARSE ARFF FOR APRIORI
# ============================================================

print("\n[7] Creating market_basket.arff...")

basket_file = (
    OUTPUT_DIR / "market_basket.arff"
)

with open(
    basket_file,
    "w",
    encoding="utf-8"
) as f:

    # ARFF relation
    f.write("@relation market_basket\n\n")

    # --------------------------------------------------------
    # Create binary product attributes
    # --------------------------------------------------------

    for product in basket.columns:

        safe_product = re.sub(
            r"[^A-Za-z0-9_]",
            "_",
            str(product)
        )

        # Avoid attribute names beginning with a digit
        if safe_product and safe_product[0].isdigit():
            safe_product = "P_" + safe_product

        f.write(
            f"@attribute product_{safe_product} {{0,1}}\n"
        )

    f.write("\n@data\n")

    # --------------------------------------------------------
    # Sparse ARFF data
    # --------------------------------------------------------

    columns = list(basket.columns)

    for _, row in basket.iterrows():

        non_zero = []

        for index, product in enumerate(columns):

            if row[product] == 1:

                non_zero.append(
                    f"{index} 1"
                )

        f.write(
            "{" + ",".join(non_zero) + "}\n"
        )

print(
    "Saved:",
    basket_file
)

# ============================================================
# 11. SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("DATA PREPARATION COMPLETED SUCCESSFULLY")
print("=" * 60)

print(
    "\nClean retail records:",
    len(df)
)

print(
    "Unique customers:",
    df["CustomerID"].nunique()
)

print(
    "Unique products:",
    df["StockCode"].nunique()
)

print(
    "Unique invoices:",
    df["InvoiceNo"].nunique()
)

print(
    "Total sales amount:",
    round(df["TotalAmount"].sum(), 2)
)

print(
    "Market basket transactions:",
    len(basket)
)

print(
    "Market basket products:",
    len(basket.columns)
)

print("\nOutput folder:")
print(OUTPUT_DIR.resolve())

print("\nGenerated files:")

for file in OUTPUT_DIR.iterdir():
    print(" -", file.name)

print("\nDONE!")