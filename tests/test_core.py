import unittest
import os
import tempfile
import sqlite3
import pandas as pd
import numpy as np

from auth import AuthManager
from database import DatabaseManager
from inventory_forecasting import InventoryForecaster
from smart_recommendations import SmartRecommendationEngine
from drug_interactions import DrugInteractionChecker


class TestAuthManager(unittest.TestCase):
    def test_hash_and_verify_success(self):
        password = "SecurePassword123!"
        pwd_hash, salt = AuthManager.hash_password(password)
        stored = f"{pwd_hash}${salt}"
        self.assertTrue(AuthManager.verify_password(password, stored))

    def test_verify_failure(self):
        pwd_hash, salt = AuthManager.hash_password("correct_password")
        stored = f"{pwd_hash}${salt}"
        self.assertFalse(AuthManager.verify_password("wrong_password", stored))
        self.assertFalse(AuthManager.verify_password("correct_password", "invalid_format"))


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_foreign_keys_enabled(self):
        conn = self.db.get_connection()
        val = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        self.assertEqual(val, 1)

    def test_default_users_creation(self):
        conn = self.db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 3)

    def test_inventory_crud_and_balance(self):
        conn = self.db.get_connection()
        conn.execute("""
            INSERT INTO inventory (drug_name, category, manufacturer, batch_number, current_stock, minimum_stock, unit_price)
            VALUES ('Amoxicillin 500mg', 'Antibiotics', 'BioLab', 'BTEST001', 100, 10, 25.0)
        """)
        conn.commit()
        item_id = conn.execute("SELECT id FROM inventory WHERE batch_number='BTEST001'").fetchone()[0]
        conn.close()

        # Update price and check consistency
        ok = self.db.update_item_prices(item_id=item_id, per_tablet_price=30.0, tablets_per_sheet=10)
        self.assertTrue(ok)

        conn = self.db.get_connection()
        row = conn.execute("SELECT unit_price, per_sheet_price FROM inventory WHERE id=?", (item_id,)).fetchone()
        conn.close()
        self.assertEqual(row["unit_price"], 30.0)
        self.assertEqual(row["per_sheet_price"], 300.0)


class TestForecasting(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = DatabaseManager(db_path=self.db_path)

        # Seed synthetic daily history (60 days) for existing first inventory item
        conn = self.db.get_connection()
        row = conn.execute("SELECT id FROM inventory LIMIT 1").fetchone()
        item_id = row["id"] if row else 1
        base_date = pd.to_datetime("2026-01-01")
        for i in range(60):
            d = (base_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            qty = 10 + (i % 7) * 2  # deterministic pattern
            conn.execute("""
                INSERT INTO consumption_patterns (drug_id, date, quantity_consumed)
                VALUES (?, ?, ?)
            """, (item_id, d, qty))
        conn.commit()
        conn.close()
        self.forecaster = InventoryForecaster(self.db)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_regression_models(self):
        res = self.forecaster.train_regression_models()
        self.assertIsNotNone(res)
        self.assertIn("best_model", res)
        self.assertIn(res["best_model"], ["linear", "polynomial", "ridge", "lasso", "elasticnet"])
        self.assertIn("mae", res[res["best_model"]])
        self.assertGreaterEqual(res[res["best_model"]]["mae"], 0.0)

    def test_time_series_model(self):
        res = self.forecaster.train_lstm_model(forecast_days=14)
        self.assertIsNotNone(res)
        self.assertEqual(len(res["future_pred"]), 14)
        self.assertTrue(all(p >= 0 for p in res["future_pred"]))


class TestRecommendationsAndSafety(unittest.TestCase):
    def test_drug_interaction_checker(self):
        checker = DrugInteractionChecker()
        results = checker.check_interactions(["Aspirin 75mg", "Warfarin 5mg"])
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["severity"], "Severe")

    def test_drug_interaction_unknown(self):
        checker = DrugInteractionChecker()
        results = checker.check_interactions(["UnknownHerb 10mg", "RandomMolecule 20mg"])
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
