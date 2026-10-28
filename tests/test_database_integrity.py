import unittest
import os
import tempfile
import sqlite3
import pandas as pd
import numpy as np

from database import DatabaseManager


class TestDatabaseIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_foreign_key_violation_rejected(self):
        """Ensure invalid drug_id cannot be inserted into transactions."""
        conn = self.db.get_connection()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO transactions (drug_id, transaction_type, quantity, unit_price)
                VALUES (999999, 'DISPENSE', 10, 15.0)
            """)
            conn.commit()
        conn.close()

    def test_unique_batch_number_constraint(self):
        """Ensure duplicate batch_number raises IntegrityError."""
        conn = self.db.get_connection()
        conn.execute("""
            INSERT INTO inventory (drug_name, category, batch_number, current_stock)
            VALUES ('Drug A', 'Category A', 'BATCH-DUP-01', 50)
        """)
        conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO inventory (drug_name, category, batch_number, current_stock)
                VALUES ('Drug B', 'Category B', 'BATCH-DUP-01', 100)
            """)
            conn.commit()
        conn.close()

    def test_atomic_transaction_rollback(self):
        """Ensure multi-statement transaction failure rolls back previous changes."""
        conn = self.db.get_connection()
        conn.execute("""
            INSERT INTO inventory (drug_name, category, batch_number, current_stock)
            VALUES ('Atomic Drug', 'Category A', 'BATCH-ATOMIC-01', 50)
        """)
        conn.commit()
        item_id = conn.execute("SELECT id FROM inventory WHERE batch_number='BATCH-ATOMIC-01'").fetchone()[0]

        try:
            with conn:
                conn.execute("UPDATE inventory SET current_stock = 40 WHERE id = ?", (item_id,))
                # Intentional FK violation to trigger rollback
                conn.execute("INSERT INTO transactions (drug_id, transaction_type, quantity) VALUES (888888, 'OUT', 10)")
        except sqlite3.IntegrityError:
            pass

        # Verify stock was not updated
        stock = conn.execute("SELECT current_stock FROM inventory WHERE id = ?", (item_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(stock, 50)


if __name__ == "__main__":
    unittest.main()

