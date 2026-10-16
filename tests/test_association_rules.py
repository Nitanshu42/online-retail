import unittest

import pandas as pd

from app import app, apriori, build_transactions


class AssociationRulesTests(unittest.TestCase):
    def test_apriori_generates_rules_from_clean_retail_data(self):
        df = pd.read_csv("WEKA_PBL_DATA/retail_clean.csv")
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
        df = df.dropna(subset=["InvoiceDate", "CustomerID"]).copy()

        rules = apriori(build_transactions(df), min_support=0.02, min_confidence=0.5)

        self.assertGreater(len(rules), 0)
        self.assertTrue(all("antecedent" in rule and "consequent" in rule for rule in rules))

    def test_filters_and_rule_thresholds_are_supported(self):
        client = app.test_client()

        overview = client.get("/api/overview?country=United Kingdom&year=2011")
        self.assertEqual(overview.status_code, 200)
        self.assertIsInstance(overview.get_json(), dict)

        rules = client.get("/api/association-rules?country=United Kingdom&year=2011&min_support=0.05&min_confidence=0.7")
        self.assertEqual(rules.status_code, 200)
        self.assertIsInstance(rules.get_json(), list)

        filters = client.get("/api/filters")
        self.assertEqual(filters.status_code, 200)
        payload = filters.get_json()
        self.assertIn("countries", payload)
        self.assertIn("years", payload)


if __name__ == "__main__":
    unittest.main()
