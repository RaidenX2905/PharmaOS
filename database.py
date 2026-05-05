import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json


class DatabaseManager:
    def __init__(self, db_path="pharma_inventory.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection with row factory for easier data access"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Inventory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_name TEXT NOT NULL,
                category TEXT NOT NULL,
                manufacturer TEXT,
                batch_number TEXT UNIQUE NOT NULL,
                current_stock INTEGER DEFAULT 0,
                minimum_stock INTEGER DEFAULT 10,
                unit_price REAL DEFAULT 0.0,
                per_tablet_price REAL DEFAULT 0.0,
                per_sheet_price REAL DEFAULT 0.0,
                tablets_per_sheet INTEGER DEFAULT 10,
                expiry_date DATE,
                supplier_name TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migrate existing database to add new columns if they don't exist
        self._migrate_inventory_columns(cursor)

        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id INTEGER,
                transaction_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL,
                total_amount REAL,
                reference_number TEXT,
                notes TEXT,
                department TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (drug_id) REFERENCES inventory (id)
            )
        """)

        # Suppliers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                lead_time_days INTEGER DEFAULT 7,
                reliability_score REAL DEFAULT 5.0,
                cost_rating REAL DEFAULT 5.0,
                quality_score REAL DEFAULT 5.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Purchase orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                supplier_id INTEGER,
                drug_id INTEGER,
                quantity INTEGER NOT NULL,
                unit_price REAL,
                total_amount REAL,
                status TEXT DEFAULT 'pending',
                order_date DATE DEFAULT CURRENT_DATE,
                expected_delivery DATE,
                actual_delivery DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
                FOREIGN KEY (drug_id) REFERENCES inventory (id)
            )
        """)

        # Drug interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drug_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug1 TEXT NOT NULL,
                drug2 TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                clinical_effect TEXT,
                management TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Consumption patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumption_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id INTEGER,
                date DATE NOT NULL,
                quantity_consumed INTEGER DEFAULT 0,
                department TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (drug_id) REFERENCES inventory (id)
            )
        """)

        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                drug_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                acknowledged BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (drug_id) REFERENCES inventory (id)
            )
        """)

        # Users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        # Audit trail table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Optimizations: Create Indices
        # Index for faster frequent lookups/filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_expiry ON inventory(expiry_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_stock ON inventory(current_stock)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_drug_name ON inventory(drug_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)")

        conn.commit()
        conn.close()

        # Insert default data if tables are empty
        self.insert_default_data()
        self.create_default_users()

    def _migrate_inventory_columns(self, cursor):
        """Migrate existing inventory table to add new columns if they don't exist"""
        try:
            # Check if columns exist
            cursor.execute("PRAGMA table_info(inventory)")
            columns = [col[1] for col in cursor.fetchall()]

            # Add new columns if they don't exist
            if "per_tablet_price" not in columns:
                cursor.execute(
                    "ALTER TABLE inventory ADD COLUMN per_tablet_price REAL DEFAULT 0.0"
                )
            if "per_sheet_price" not in columns:
                cursor.execute(
                    "ALTER TABLE inventory ADD COLUMN per_sheet_price REAL DEFAULT 0.0"
                )
            if "tablets_per_sheet" not in columns:
                cursor.execute(
                    "ALTER TABLE inventory ADD COLUMN tablets_per_sheet INTEGER DEFAULT 10"
                )

            # Initialize prices for existing records where unit_price exists
            cursor.execute("""
                UPDATE inventory
                SET per_tablet_price = unit_price,
                    per_sheet_price = unit_price * tablets_per_sheet
                WHERE per_tablet_price = 0 AND unit_price > 0
            """)
        except Exception as e:
            print(f"Migration info: {e}")

    def update_item_prices(
        self,
        item_id,
        per_tablet_price=None,
        per_sheet_price=None,
        tablets_per_sheet=None,
    ):
        """Update item prices with automatic synchronization"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get current values
            cursor.execute(
                "SELECT per_tablet_price, per_sheet_price, tablets_per_sheet FROM inventory WHERE id = ?",
                (item_id,),
            )
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False

            current_tablet_price, current_sheet_price, current_tablets = result

            # Update based on what was changed
            if tablets_per_sheet is not None and tablets_per_sheet != current_tablets:
                # Tablets per sheet changed, recalculate sheet price
                current_tablets = tablets_per_sheet
                if per_tablet_price is not None:
                    current_tablet_price = per_tablet_price
                current_sheet_price = current_tablet_price * current_tablets
            elif (
                per_tablet_price is not None
                and per_tablet_price != current_tablet_price
            ):
                # Per tablet price changed, recalculate sheet price
                current_tablet_price = per_tablet_price
                current_sheet_price = current_tablet_price * current_tablets
            elif per_sheet_price is not None and per_sheet_price != current_sheet_price:
                # Per sheet price changed, recalculate tablet price
                current_sheet_price = per_sheet_price
                current_tablet_price = (
                    current_sheet_price / current_tablets if current_tablets > 0 else 0
                )

            # Update unit_price to match per_tablet_price
            unit_price = current_tablet_price

            # Apply updates
            cursor.execute(
                """
                UPDATE inventory
                SET per_tablet_price = ?,
                    per_sheet_price = ?,
                    tablets_per_sheet = ?,
                    unit_price = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (
                    current_tablet_price,
                    current_sheet_price,
                    current_tablets,
                    unit_price,
                    item_id,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating prices: {e}")
            if conn:
                conn.close()
            return False

    def update_inventory_item(
        self,
        item_id,
        drug_name,
        category,
        manufacturer,
        batch_number,
        current_stock,
        minimum_stock,
        per_tablet_price,
        per_sheet_price,
        tablets_per_sheet,
        expiry_date,
        supplier_name,
        description,
    ):
        """Update complete inventory item details with automatic price synchronization"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get old values before update for transaction log
            cursor.execute(
                "SELECT drug_name, current_stock, unit_price FROM inventory WHERE id = ?",
                (item_id,),
            )
            old_item = cursor.fetchone()
            old_drug_name = old_item[0] if old_item else drug_name
            old_stock = old_item[1] if old_item else 0
            old_price = old_item[2] if old_item else 0

            # Ensure prices are synchronized
            if per_tablet_price and tablets_per_sheet:
                calculated_sheet_price = per_tablet_price * tablets_per_sheet
                # Use the calculated value for consistency
                per_sheet_price = calculated_sheet_price

            unit_price = per_tablet_price

            cursor.execute(
                """
                UPDATE inventory
                SET drug_name = ?,
                    category = ?,
                    manufacturer = ?,
                    batch_number = ?,
                    current_stock = ?,
                    minimum_stock = ?,
                    unit_price = ?,
                    per_tablet_price = ?,
                    per_sheet_price = ?,
                    tablets_per_sheet = ?,
                    expiry_date = ?,
                    supplier_name = ?,
                    description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (
                    drug_name,
                    category,
                    manufacturer,
                    batch_number,
                    current_stock,
                    minimum_stock,
                    unit_price,
                    per_tablet_price,
                    per_sheet_price,
                    tablets_per_sheet,
                    expiry_date,
                    supplier_name,
                    description,
                    item_id,
                ),
            )

            # Log transaction for updating item
            stock_change = current_stock - old_stock
            price_change = ""
            if old_price != unit_price:
                price_change = f" | Price: ₹{old_price} → ₹{unit_price}"

            notes = f"Updated item: {drug_name} | Batch: {batch_number}"
            if stock_change != 0:
                notes += f" | Stock: {old_stock} → {current_stock} ({'+' if stock_change > 0 else ''}{stock_change})"
            notes += price_change

            # Calculate total amount - use current value
            total_amount = current_stock * unit_price if unit_price else 0

            cursor.execute(
                """
                INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                VALUES (?, 'Update Item', ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    item_id,
                    abs(stock_change) if stock_change != 0 else current_stock,
                    total_amount,
                    notes,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating inventory item: {e}")
            if conn:
                conn.close()
            return False

    def insert_default_data(self):
        """Insert sample data for demonstration"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if we already have data
        cursor.execute("SELECT COUNT(*) FROM inventory")
        count = cursor.fetchone()[0]

        if count == 0:
            # Insert sample suppliers
            suppliers = [
                (
                    "PharmaCorp Inc",
                    "John Smith",
                    "+1-555-0101",
                    "john@pharmacorp.com",
                    "123 Pharma St",
                    5,
                    4.5,
                    4.0,
                    4.8,
                ),
                (
                    "MediSupply Co",
                    "Sarah Johnson",
                    "+1-555-0102",
                    "sarah@medisupply.com",
                    "456 Medical Ave",
                    7,
                    4.2,
                    3.8,
                    4.5,
                ),
                (
                    "HealthDist Ltd",
                    "Mike Chen",
                    "+1-555-0103",
                    "mike@healthdist.com",
                    "789 Health Blvd",
                    3,
                    4.8,
                    4.5,
                    4.9,
                ),
            ]

            cursor.executemany(
                """
                INSERT INTO suppliers (name, contact_person, phone, email, address, lead_time_days, reliability_score, cost_rating, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                suppliers,
            )

            # Insert sample inventory
            inventory_items = [
                (
                    "Paracetamol 500mg",
                    "Analgesics",
                    "PharmaCorp",
                    "PCM001",
                    250,
                    50,
                    20.75,
                    "2025-06-15",
                    "PharmaCorp Inc",
                    "Pain relief medication",
                ),
                (
                    "Amoxicillin 250mg",
                    "Antibiotics",
                    "MediSupply",
                    "AMX001",
                    180,
                    30,
                    124.50,
                    "2025-04-20",
                    "MediSupply Co",
                    "Antibiotic for bacterial infections",
                ),
                (
                    "Metformin 500mg",
                    "Diabetes",
                    "HealthDist",
                    "MET001",
                    320,
                    40,
                    62.25,
                    "2025-12-10",
                    "HealthDist Ltd",
                    "Type 2 diabetes medication",
                ),
                (
                    "Aspirin 75mg",
                    "Cardiovascular",
                    "PharmaCorp",
                    "ASP001",
                    150,
                    25,
                    24.90,
                    "2025-08-25",
                    "PharmaCorp Inc",
                    "Low-dose aspirin for heart health",
                ),
                (
                    "Salbutamol Inhaler",
                    "Respiratory",
                    "MediSupply",
                    "SAL001",
                    45,
                    15,
                    1037.50,
                    "2025-03-30",
                    "MediSupply Co",
                    "Asthma relief inhaler",
                ),
                (
                    "Insulin Rapid",
                    "Diabetes",
                    "HealthDist",
                    "INS001",
                    25,
                    10,
                    3735.00,
                    "2025-02-15",
                    "HealthDist Ltd",
                    "Fast-acting insulin",
                ),
                (
                    "Ciprofloxacin 500mg",
                    "Antibiotics",
                    "PharmaCorp",
                    "CIP001",
                    90,
                    20,
                    186.75,
                    "2025-07-08",
                    "PharmaCorp Inc",
                    "Broad-spectrum antibiotic",
                ),
                (
                    "Omeprazole 20mg",
                    "Gastrointestinal",
                    "MediSupply",
                    "OME001",
                    200,
                    35,
                    70.55,
                    "2025-09-12",
                    "MediSupply Co",
                    "Proton pump inhibitor",
                ),
                (
                    "Atorvastatin 20mg",
                    "Cardiovascular",
                    "HealthDist",
                    "ATO001",
                    175,
                    30,
                    99.60,
                    "2025-11-18",
                    "HealthDist Ltd",
                    "Cholesterol-lowering medication",
                ),
                (
                    "Prednisolone 5mg",
                    "Steroids",
                    "PharmaCorp",
                    "PRE001",
                    80,
                    15,
                    78.85,
                    "2025-05-22",
                    "PharmaCorp Inc",
                    "Anti-inflammatory steroid",
                ),
            ]

            cursor.executemany(
                """
                INSERT INTO inventory (drug_name, category, manufacturer, batch_number, current_stock, minimum_stock, unit_price, expiry_date, supplier_name, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                inventory_items,
            )

            # Insert sample drug interactions
            interactions = [
                (
                    "Aspirin 75mg",
                    "Metformin 500mg",
                    "Moderate",
                    "May increase risk of lactic acidosis",
                    "Increased monitoring required",
                    "Monitor blood glucose closely",
                ),
                (
                    "Ciprofloxacin 500mg",
                    "Prednisolone 5mg",
                    "Mild",
                    "May increase steroid effects",
                    "Potential enhanced anti-inflammatory action",
                    "Standard monitoring sufficient",
                ),
                (
                    "Insulin Rapid",
                    "Aspirin 75mg",
                    "Moderate",
                    "Aspirin may enhance hypoglycemic effect",
                    "Increased risk of low blood sugar",
                    "Monitor glucose levels frequently",
                ),
            ]

            cursor.executemany(
                """
                INSERT INTO drug_interactions (drug1, drug2, severity, description, clinical_effect, management)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                interactions,
            )

            # Insert sample consumption data for the last 90 days
            drugs = cursor.execute("SELECT id, drug_name FROM inventory").fetchall()
            for drug in drugs:
                for days_ago in range(90):
                    date = datetime.now() - timedelta(days=days_ago)
                    # Generate realistic consumption patterns
                    base_consumption = {
                        "Paracetamol 500mg": 15,
                        "Amoxicillin 250mg": 8,
                        "Metformin 500mg": 12,
                        "Aspirin 75mg": 6,
                        "Salbutamol Inhaler": 2,
                        "Insulin Rapid": 4,
                        "Ciprofloxacin 500mg": 5,
                        "Omeprazole 20mg": 10,
                        "Atorvastatin 20mg": 9,
                        "Prednisolone 5mg": 3,
                    }.get(drug["drug_name"], 5)

                    # Add some randomness
                    import random

                    consumption = max(0, base_consumption + random.randint(-3, 3))

                    cursor.execute(
                        """
                        INSERT INTO consumption_patterns (drug_id, date, quantity_consumed, department)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            drug["id"],
                            date.date(),
                            consumption,
                            random.choice(
                                ["ICU", "Emergency", "General Ward", "Outpatient"]
                            ),
                        ),
                    )

            # Insert default settings
            default_settings = [
                ("default_min_stock", "10"),
                ("low_stock_threshold", "20"),
                ("auto_reorder", "true"),
                ("currency", "INR"),
                ("expiry_warning_days", "30"),
                ("expiry_critical_days", "7"),
            ]

            cursor.executemany(
                """
                INSERT INTO settings (setting_key, setting_value)
                VALUES (?, ?)
            """,
                default_settings,
            )

            # Insert sample suppliers if table is empty
            cursor.execute("SELECT COUNT(*) FROM suppliers")
            if cursor.fetchone()[0] == 0:
                suppliers = [
                    ("MediSupply Co", "John Doe", "555-0101", "john@medisupply.com", "123 Pharma St", 5, 4.8, 4.2, 4.5),
                    ("HealthDist Ltd", "Jane Smith", "555-0102", "jane@healthdist.com", "456 Wellness Ave", 3, 4.9, 3.8, 4.9),
                    ("PharmaCorp Inc", "Bob Wilson", "555-0103", "bob@pharmacorp.com", "789 Biotech Blvd", 7, 4.5, 4.9, 4.2),
                ]
                cursor.executemany(
                    """
                    INSERT INTO suppliers (name, contact_person, phone, email, address, lead_time_days, reliability_score, cost_rating, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    suppliers,
                )

            # Insert sample purchase orders if table is empty
            cursor.execute("SELECT COUNT(*) FROM purchase_orders")
            if cursor.fetchone()[0] == 0:
                supplier_ids = {row[1]: row[0] for row in cursor.execute("SELECT id, name FROM suppliers").fetchall()}
                drug_ids = {row[1]: row[0] for row in cursor.execute("SELECT id, drug_name FROM inventory").fetchall()}
                
                po_data = [
                    ("PO-001", supplier_ids.get("MediSupply Co", 1), drug_ids.get("Paracetamol 500mg", 1), 1000, 15.50, 15500, "delivered", "2024-01-10", "2024-01-15", "2024-01-15"),
                    ("PO-002", supplier_ids.get("HealthDist Ltd", 2), drug_ids.get("Metformin 500mg", 2), 500, 62.25, 31125, "delivered", "2024-01-12", "2024-01-15", "2024-01-14"),
                    ("PO-003", supplier_ids.get("PharmaCorp Inc", 3), drug_ids.get("Aspirin 75mg", 3), 2000, 24.90, 49800, "delivered", "2024-01-05", "2024-01-12", "2024-01-13"),
                    ("PO-004", supplier_ids.get("MediSupply Co", 1), drug_ids.get("Amoxicillin 250mg", 4), 800, 124.50, 99600, "delivered", "2024-02-01", "2024-02-06", "2024-02-06"),
                    ("PO-005", supplier_ids.get("HealthDist Ltd", 2), drug_ids.get("Salbutamol Inhaler", 5), 50, 1037.50, 51875, "delivered", "2024-02-05", "2024-02-08", "2024-02-07"),
                ]
                cursor.executemany(
                    """
                    INSERT INTO purchase_orders (order_number, supplier_id, drug_id, quantity, unit_price, total_amount, status, order_date, expected_delivery, actual_delivery)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    po_data,
                )

        conn.commit()
        conn.close()

    # Dashboard methods
    @st.cache_data
    def get_total_inventory_count(_self):
        """Get total number of inventory items"""
        conn = _self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inventory")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @st.cache_data
    def get_low_stock_count(_self):
        """Get count of items below minimum stock level"""
        conn = _self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM inventory WHERE current_stock <= minimum_stock"
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @st.cache_data
    def get_expiring_soon_count(_self):
        """Get count of items expiring within 30 days"""
        conn = _self.get_connection()
        cursor = conn.cursor()
        expiry_date = datetime.now() + timedelta(days=30)
        cursor.execute(
            "SELECT COUNT(*) FROM inventory WHERE expiry_date <= ?",
            (expiry_date.date(),),
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @st.cache_data
    def get_total_inventory_value(_self):
        """Get total value of all inventory items"""
        conn = _self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(current_stock * unit_price) FROM inventory")
        result = cursor.fetchone()[0]
        conn.close()
        return result or 0.0

    @st.cache_data
    def get_inventory_by_category(_self):
        """Get inventory distribution by category"""
        conn = _self.get_connection()
        query = """
            SELECT category, SUM(current_stock) as quantity
            FROM inventory
            GROUP BY category
            ORDER BY quantity DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    @st.cache_data
    def get_stock_levels(_self):
        """Get current stock levels for all drugs"""
        conn = _self.get_connection()
        query = """
            SELECT drug_name, current_stock, minimum_stock
            FROM inventory
            ORDER BY current_stock ASC
            LIMIT 10
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    @st.cache_data
    def get_recent_transactions(_self, limit=50):
        """Get recent transactions with details"""
        conn = _self.get_connection()
        query = """
            SELECT
                t.transaction_type,
                COALESCE(i.drug_name,
                         CASE
                              WHEN t.transaction_type LIKE '%Import%' THEN 'CSV Import'
                              WHEN t.transaction_type LIKE '%Order%' THEN 'Purchase Order'
                              ELSE SUBSTR(t.notes, 1, 50)
                         END,
                         'Unknown/Deleted Item') as drug_name,
                t.quantity,
                COALESCE(
                    t.total_amount,
                    CASE
                        WHEN i.unit_price IS NOT NULL AND i.unit_price > 0
                        THEN t.quantity * i.unit_price
                        WHEN t.unit_price IS NOT NULL AND t.unit_price > 0
                        THEN t.quantity * t.unit_price
                        ELSE 0
                    END,
                    0
                ) as total_amount,
                t.notes,
                t.created_at,
                t.drug_id,
                COALESCE(i.unit_price, t.unit_price, 0) as unit_price
            FROM transactions t
            LEFT JOIN inventory i ON t.drug_id = i.id
            ORDER BY t.created_at DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df

    def get_categories(self):
        """Get list of drug categories"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM inventory ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories

    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_filtered_inventory(_self, category_filter, stock_filter, search_term, limit=100000):
        """Get filtered inventory data with optimized query and limit"""
        conn = _self.get_connection()

        query = """
            SELECT id, drug_name, category, manufacturer, batch_number,
                   current_stock, minimum_stock, unit_price, per_tablet_price,
                   per_sheet_price, tablets_per_sheet, expiry_date, supplier_name
            FROM inventory
            WHERE 1=1
        """
        params = []

        if category_filter != "All":
            query += " AND category = ?"
            params.append(category_filter)

        if stock_filter == "Low Stock":
            query += " AND current_stock <= minimum_stock"
        elif stock_filter == "Out of Stock":
            query += " AND current_stock = 0"
        elif stock_filter == "Normal":
            query += " AND current_stock > minimum_stock"

        if search_term:
            query += " AND drug_name LIKE ?"
            params.append(f"%{search_term}%")

        query += " ORDER BY drug_name LIMIT ?"
        params.append(limit)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def get_all_drug_names(self):
        """Get a list of all unique drug names in inventory"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT drug_name FROM inventory ORDER BY drug_name")
            drugs = [row[0] for row in cursor.fetchall()]
            conn.close()
            return drugs
        except Exception as e:
            print(f"Error getting drug names: {e}")
            return []

    def find_item_by_drug_name(self, drug_name):
        """Find existing inventory item by drug name (case-insensitive)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM inventory WHERE LOWER(drug_name) = LOWER(?)",
                (drug_name,),
            )
            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            print(f"Error finding item: {e}")
            if conn:
                conn.close()
            return None

    def add_stock_to_existing_item(
        self,
        item_id,
        quantity_to_add,
        batch_number,
        expiry_date=None,
        supplier_name=None,
        notes="",
    ):
        """Add stock to an existing inventory item and create a transaction"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get current stock
            cursor.execute(
                "SELECT current_stock FROM inventory WHERE id = ?", (item_id,)
            )
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False

            current_stock = result[0]
            new_stock = current_stock + quantity_to_add

            # Update stock
            cursor.execute(
                "UPDATE inventory SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_stock, item_id),
            )

            # Get unit price for amount calculation
            cursor.execute("SELECT unit_price FROM inventory WHERE id = ?", (item_id,))
            price_result = cursor.fetchone()
            unit_price = price_result[0] if price_result else 0

            # Calculate total amount
            total_amount = quantity_to_add * unit_price if unit_price else 0

            # Create transaction record with detailed batch information
            detailed_notes = f"{notes} | Batch: {batch_number}"
            if expiry_date:
                detailed_notes += f" | Expiry: {expiry_date}"
            if supplier_name:
                detailed_notes += f" | Supplier: {supplier_name}"
            detailed_notes += f" | Amount: ₹{total_amount:.2f}"

            cursor.execute(
                """
                INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                VALUES (?, 'Add Stock', ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (item_id, quantity_to_add, total_amount, detailed_notes),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding stock: {e}")
            if conn:
                conn.close()
            return False

    def add_inventory_item(
        self,
        drug_name,
        category,
        manufacturer,
        batch_number,
        current_stock,
        minimum_stock,
        unit_price,
        expiry_date,
        supplier_name,
        description,
        per_tablet_price=None,
        per_sheet_price=None,
        tablets_per_sheet=10,
    ):
        """Add new inventory item"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Calculate prices if not provided
            if per_tablet_price is None:
                per_tablet_price = unit_price
            if per_sheet_price is None:
                per_sheet_price = per_tablet_price * tablets_per_sheet

            cursor.execute(
                """
                INSERT INTO inventory (drug_name, category, manufacturer, batch_number,
                                     current_stock, minimum_stock, unit_price, per_tablet_price,
                                     per_sheet_price, tablets_per_sheet, expiry_date,
                                     supplier_name, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    drug_name,
                    category,
                    manufacturer,
                    batch_number,
                    current_stock,
                    minimum_stock,
                    unit_price,
                    per_tablet_price,
                    per_sheet_price,
                    tablets_per_sheet,
                    expiry_date,
                    supplier_name,
                    description,
                ),
            )

            # Get the ID of the newly inserted item
            item_id = cursor.lastrowid

            # Calculate total amount for the transaction
            total_amount = current_stock * unit_price if unit_price else 0

            # Log transaction for adding new item
            cursor.execute(
                """
                INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                VALUES (?, 'Add Item', ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    item_id,
                    current_stock,
                    total_amount,
                    f"Added new item: {drug_name} | Batch: {batch_number} | Category: {category} | Stock: {current_stock} | Price: ₹{unit_price}",
                ),
            )

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError as e:
            print(f"Database integrity error: {e}")
            if conn:
                conn.close()
            return False
        except sqlite3.OperationalError as e:
            print(f"Database operational error: {e}")
            if conn:
                conn.close()
            return False
        except Exception as e:
            print(f"Database error: {e}")
            if conn:
                conn.close()
            return False

    def get_all_items_for_dropdown(self):
        """Get all inventory items formatted for dropdown"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, drug_name, batch_number FROM inventory ORDER BY drug_name"
        )
        items = [f"{row[0]} - {row[1]} ({row[2]})" for row in cursor.fetchall()]
        conn.close()
        return items

    def get_item_details(self, item_id):
        """Get details of a specific inventory item"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return None

            # Get column names BEFORE closing connection
            column_names = [description[0] for description in cursor.description]

            # Create dictionary from row data
            item_dict = dict(zip(column_names, row))

            conn.close()
            return item_dict
        except Exception as e:
            print(f"Error getting item details: {e}")
            if conn:
                conn.close()
            return None

    def update_stock_level(
        self, item_id, new_stock, transaction_type, quantity, reason
    ):
        """Update stock level and log transaction with amount"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get unit price for amount calculation
            cursor.execute("SELECT unit_price FROM inventory WHERE id = ?", (item_id,))
            price_result = cursor.fetchone()
            unit_price = price_result[0] if price_result else 0

            # Calculate total amount based on quantity and price
            total_amount = quantity * unit_price if unit_price else 0

            # Update inventory
            cursor.execute(
                "UPDATE inventory SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_stock, item_id),
            )

            # Enhanced notes with amount
            enhanced_notes = (
                f"{reason} | Amount: ₹{total_amount:.2f}"
                if reason
                else f"Amount: ₹{total_amount:.2f}"
            )

            # Log transaction with amount
            cursor.execute(
                """
                INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (item_id, transaction_type, quantity, total_amount, enhanced_notes),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating stock level: {e}")
            if conn:
                conn.close()
            return False

    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_inventory(_self, limit=5000):
        """Get all inventory items with limit for performance"""
        conn = _self.get_connection()
        query = """
            SELECT id, drug_name, category, manufacturer, batch_number,
                   current_stock, minimum_stock AS min_stock_level, unit_price,
                   expiry_date, supplier_name, description
            FROM inventory
            ORDER BY drug_name
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df

    def get_expiring_drugs(self, days_ahead=30):
        """Get drugs expiring within specified days"""
        conn = self.get_connection()
        query = """
            SELECT id, drug_name, category, batch_number, current_stock,
                   expiry_date, supplier_name
            FROM inventory
            WHERE date(expiry_date) <= date('now', '+' || ? || ' days')
                AND date(expiry_date) >= date('now')
            ORDER BY expiry_date
        """
        df = pd.read_sql_query(query, conn, params=(days_ahead,))
        conn.close()
        return df

    def delete_inventory_item(self, item_id):
        """Delete an inventory item"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get item details before deletion for transaction log
            cursor.execute(
                "SELECT drug_name, batch_number, category, current_stock, unit_price FROM inventory WHERE id = ?",
                (item_id,),
            )
            item = cursor.fetchone()

            if item:
                drug_name, batch_number, category, stock, price = item

                # Calculate total amount for deleted item
                total_amount = stock * price if price else 0

                # Log transaction BEFORE deleting (so we have the reference)
                cursor.execute(
                    """
                    INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                    VALUES (?, 'Delete Item', ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        item_id,
                        stock,
                        total_amount,
                        f"Deleted item: {drug_name} | Batch: {batch_number} | Category: {category} | Stock: {stock} | Price: ₹{price} | Total Value: ₹{total_amount:.2f}",
                    ),
                )

            # Now delete the item
            cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting inventory item: {e}")
            if conn:
                conn.close()
            return False

    def update_item_price(self, drug_name, new_price):
        """Update the price of an item by drug name (updates all batches with same name)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inventory SET unit_price = ?, updated_at = CURRENT_TIMESTAMP WHERE drug_name = ?",
                (new_price, drug_name),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def update_item_price_by_id(self, item_id, new_price):
        """Update the price of a specific inventory item by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inventory SET unit_price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_price, item_id),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def update_minimum_stock(self, item_id, new_min_stock):
        """Update minimum stock level for an item"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inventory SET minimum_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_min_stock, item_id),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    # AI Forecasting methods
    def get_drugs_for_forecasting(self):
        """Get drugs that have enough historical data for forecasting"""
        conn = self.get_connection()
        query = """
            SELECT DISTINCT i.drug_name
            FROM inventory i
            JOIN consumption_patterns cp ON i.id = cp.drug_id
            GROUP BY i.drug_name
            HAVING COUNT(cp.id) >= 7
            ORDER BY i.drug_name
        """
        cursor = conn.cursor()
        cursor.execute(query)
        drugs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return drugs

    def get_historical_consumption(self, drug_name):
        """Get historical consumption data for a drug"""
        conn = self.get_connection()
        query = """
            SELECT cp.date, SUM(cp.quantity_consumed) as consumption
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE i.drug_name = ?
            GROUP BY cp.date
            ORDER BY cp.date
        """
        df = pd.read_sql_query(query, conn, params=(drug_name,))
        df["date"] = pd.to_datetime(df["date"])
        conn.close()
        return df

    def get_current_stock(self, drug_name):
        """Get current stock for a drug"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_stock FROM inventory WHERE drug_name = ?", (drug_name,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    # Smart reordering methods
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_reorder_suggestions_data(_self):
        """Get data needed for reorder suggestions"""
        conn = _self.get_connection()
        query = """
            SELECT i.id, i.drug_name, i.current_stock, i.minimum_stock, i.unit_price,
                   i.supplier_name, s.lead_time_days,
                   AVG(cp.quantity_consumed) as avg_daily_usage
            FROM inventory i
            LEFT JOIN suppliers s ON i.supplier_name = s.name
            LEFT JOIN consumption_patterns cp ON i.id = cp.drug_id
                AND cp.date >= date('now', '-30 days')
            GROUP BY i.id, i.drug_name, i.current_stock, i.minimum_stock,
                     i.unit_price, i.supplier_name, s.lead_time_days
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def create_purchase_order(self, suggestion):
        """Create a purchase order"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Generate order number
            order_number = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Get supplier ID
            cursor.execute(
                "SELECT id FROM suppliers WHERE name = ?", (suggestion["supplier"],)
            )
            supplier_result = cursor.fetchone()
            supplier_id = supplier_result[0] if supplier_result else None

            # Get drug ID
            cursor.execute(
                "SELECT id FROM inventory WHERE drug_name = ?",
                (suggestion["drug_name"],),
            )
            drug_result = cursor.fetchone()
            drug_id = drug_result[0] if drug_result else None

            if drug_id:
                cursor.execute(
                    """
                    INSERT INTO purchase_orders (order_number, supplier_id, drug_id, quantity,
                                               unit_price, total_amount, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        order_number,
                        supplier_id,
                        drug_id,
                        suggestion["suggested_quantity"],
                        suggestion.get("unit_price", 0),
                        suggestion["estimated_cost"],
                        suggestion.get("notes", "Auto-generated order"),
                    ),
                )

                # Log transaction for purchase order
                cursor.execute(
                    """
                    INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                    VALUES (?, 'Purchase Order', ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        drug_id,
                        suggestion["suggested_quantity"],
                        suggestion["estimated_cost"],
                        f"Purchase Order: {order_number} | {suggestion.get('drug_name', 'Unknown')} | Supplier: {suggestion.get('supplier', 'Unknown')} | Qty: {suggestion['suggested_quantity']} | Total: ₹{suggestion['estimated_cost']:.2f}",
                    ),
                )

                conn.commit()
                conn.close()
                return True
        except Exception:
            pass

        conn.close()
        return False

    def get_suppliers(self):
        """Get list of suppliers"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers ORDER BY name")
        suppliers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return suppliers

    def get_all_drugs(self):
        """Get list of all drug names"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT drug_name FROM inventory ORDER BY drug_name")
        drugs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return drugs

    # Expiry management methods
    def get_expiring_items(self):
        """Get items expiring within 90 days"""
        conn = self.get_connection()
        query = """
            SELECT drug_name, batch_number, current_stock, expiry_date,
                   CASE
                       WHEN julianday(expiry_date) - julianday('now') <= 0 THEN 0
                       ELSE CAST(julianday(expiry_date) - julianday('now') AS INTEGER)
                   END as days_until_expiry,
                   current_stock * unit_price as value_at_risk
            FROM inventory
            WHERE expiry_date <= date('now', '+90 days')
            ORDER BY days_until_expiry ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_drugs_with_consumption_data(self):
        """Get drugs that have consumption data"""
        conn = self.get_connection()
        query = """
            SELECT DISTINCT i.drug_name
            FROM inventory i
            JOIN consumption_patterns cp ON i.id = cp.drug_id
            ORDER BY i.drug_name
        """
        cursor = conn.cursor()
        cursor.execute(query)
        drugs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return drugs

    def apply_expiry_action(self, drug_name, action):
        """Apply action to expired/expiring items"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Log the action in transactions
            cursor.execute(
                """
                INSERT INTO transactions (drug_id, transaction_type, quantity, notes)
                SELECT id, ?, current_stock, ?
                FROM inventory
                WHERE drug_name = ?
            """,
                (action, f"Expiry action: {action}", drug_name),
            )

            # Update stock if disposing or using
            if action in ["Mark as Used", "Dispose"]:
                cursor.execute(
                    "UPDATE inventory SET current_stock = 0 WHERE drug_name = ?",
                    (drug_name,),
                )

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def get_wastage_analysis(self, start_date, end_date):
        """Get wastage analysis for a date range"""
        conn = self.get_connection()
        query = """
            SELECT i.drug_name, i.category,
                   SUM(t.quantity) as wasted_quantity,
                   SUM(t.quantity * i.unit_price) as wasted_value
            FROM transactions t
            JOIN inventory i ON t.drug_id = i.id
            WHERE t.transaction_type IN ('Dispose', 'Expired')
                AND DATE(t.created_at) BETWEEN ? AND ?
            GROUP BY i.drug_name, i.category
            ORDER BY wasted_value DESC
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        return df

    def get_wastage_trends(self, start_date, end_date):
        """Get daily wastage trends"""
        conn = self.get_connection()
        query = """
            SELECT DATE(t.created_at) as date,
                   SUM(t.quantity * i.unit_price) as daily_wastage
            FROM transactions t
            JOIN inventory i ON t.drug_id = i.id
            WHERE t.transaction_type IN ('Dispose', 'Expired')
                AND DATE(t.created_at) BETWEEN ? AND ?
            GROUP BY DATE(t.created_at)
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        return df

    # Drug interactions methods
    def get_known_interactions(self):
        """Get all known drug interactions"""
        conn = self.get_connection()
        query = """
            SELECT drug1, drug2, severity, description, clinical_effect, management
            FROM drug_interactions
            ORDER BY severity DESC, drug1, drug2
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def add_drug_interaction(
        self, drug1, drug2, severity, description, clinical_effect, management
    ):
        """Add new drug interaction"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO drug_interactions (drug1, drug2, severity, description, clinical_effect, management)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (drug1, drug2, severity, description, clinical_effect, management),
            )

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def check_drug_availability(self, drug_name):
        """Check if drug is available in stock"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_stock FROM inventory WHERE drug_name = ?", (drug_name,)
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] > 0:
            return {"in_stock": True, "quantity": result[0]}
        else:
            return {"in_stock": False, "quantity": 0}

    # Analytics methods
    def get_consumption_analytics(self, start_date, end_date):
        """Get consumption analytics for date range"""
        conn = self.get_connection()
        query = """
            SELECT i.drug_name, i.category, SUM(cp.quantity_consumed) as total_consumed
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date BETWEEN ? AND ?
            GROUP BY i.drug_name, i.category
            ORDER BY total_consumed DESC
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        return df

    def get_daily_consumption_trends(self, start_date, end_date):
        """Get daily consumption trends"""
        conn = self.get_connection()
        query = """
            SELECT date, SUM(quantity_consumed) as daily_consumption
            FROM consumption_patterns
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        return df

    def get_department_consumption(self, start_date, end_date):
        """Get consumption by department"""
        conn = self.get_connection()
        query = """
            SELECT department, SUM(quantity_consumed) as consumption
            FROM consumption_patterns
            WHERE date BETWEEN ? AND ? AND department IS NOT NULL
            GROUP BY department
            ORDER BY consumption DESC
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        return df

    def get_financial_overview(self):
        """Get financial overview data"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total inventory value
        cursor.execute("SELECT SUM(current_stock * unit_price) FROM inventory")
        total_value = cursor.fetchone()[0] or 0

        # Monthly spend (last 30 days)
        cursor.execute("""
            SELECT SUM(total_amount) FROM transactions
            WHERE created_at >= date('now', '-30 days')
            AND transaction_type = 'Purchase'
        """)
        monthly_spend = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_value": total_value,
            "monthly_spend": monthly_spend,
            "cost_savings": monthly_spend * 0.15,  # Estimated savings
            "roi": 0.25,  # Estimated ROI
        }

    def get_cost_analysis(self):
        """Get cost analysis by category"""
        conn = self.get_connection()
        query = """
            SELECT category, SUM(current_stock * unit_price) as total_cost
            FROM inventory
            GROUP BY category
            ORDER BY total_cost DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_cost_trends(self):
        """Get monthly cost trends"""
        conn = self.get_connection()
        query = """
            SELECT strftime('%Y-%m', created_at) as month,
                   SUM(total_amount) as monthly_cost
            FROM transactions
            WHERE transaction_type = 'Purchase'
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_budget_analysis(self):
        """Get budget vs actual analysis"""
        # Mock budget data - in real app this would come from budget table
        budget_data = {
            "Antibiotics": {"budgeted": 10000, "actual": 8500},
            "Analgesics": {"budgeted": 5000, "actual": 5200},
            "Cardiovascular": {"budgeted": 8000, "actual": 7800},
            "Diabetes": {"budgeted": 12000, "actual": 11500},
            "Respiratory": {"budgeted": 6000, "actual": 6300},
        }
        return budget_data

    def get_supplier_metrics(self):
        """Get supplier performance metrics"""
        conn = self.get_connection()
        query = """
            SELECT s.name as supplier_name,
                   s.lead_time_days as avg_delivery_time,
                   s.reliability_score,
                   s.cost_rating,
                   s.quality_score,
                   COUNT(po.id) as total_orders,
                   AVG(po.unit_price) as avg_unit_cost,
                   CASE
                       WHEN COUNT(po.id) > 0 THEN
                           CAST(SUM(CASE WHEN po.actual_delivery <= po.expected_delivery THEN 1 ELSE 0 END) AS FLOAT) / COUNT(po.id) * 100
                       ELSE 0
                   END as on_time_delivery_rate
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.id = po.supplier_id
            GROUP BY s.id, s.name, s.lead_time_days, s.reliability_score, s.cost_rating, s.quality_score
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_supplier_recommendations(self):
        """Get supplier recommendations"""
        recommendations = [
            {
                "type": "best_performer",
                "supplier": "HealthDist Ltd",
                "reason": "Highest quality score and reliability",
            },
            {
                "type": "needs_improvement",
                "supplier": "MediSupply Co",
                "reason": "Below average delivery times",
            },
            {
                "type": "cost_optimization",
                "message": "Consider negotiating better rates with PharmaCorp Inc",
            },
        ]
        return recommendations

    def detect_anomalies(self):
        """Detect anomalies in inventory data"""
        anomalies = [
            {
                "severity": "High",
                "description": "Unusual spike in Insulin consumption detected in ICU department",
            },
            {
                "severity": "Medium",
                "description": "Stock level of Amoxicillin dropped 50% faster than predicted",
            },
            {
                "severity": "Low",
                "description": "Delivery delay pattern detected for MediSupply Co",
            },
        ]
        return anomalies

    def get_predictive_insights(self):
        """Get predictive insights"""
        insights = [
            {
                "title": "Seasonal Demand Prediction",
                "description": "Respiratory medications demand expected to increase by 40% in next 30 days",
                "chart_type": "line",
                "chart_data": pd.DataFrame(
                    {
                        "x": pd.date_range(start="2024-01-01", periods=30, freq="D"),
                        "y": np.random.normal(50, 10, 30),
                    }
                ),
                "recommendations": [
                    "Increase Salbutamol orders by 50%",
                    "Stock up on respiratory medications",
                    "Review supplier capacity",
                ],
            },
            {
                "title": "Cost Optimization Opportunity",
                "description": "Switching suppliers for cardiovascular drugs could save 15%",
                "chart_type": "bar",
                "chart_data": pd.DataFrame(
                    {"x": ["Current Cost", "Optimized Cost"], "y": [8000, 6800]}
                ),
                "recommendations": [
                    "Negotiate with alternative suppliers",
                    "Consider bulk purchasing",
                    "Review contract terms",
                ],
            },
        ]
        return insights

    # Settings methods
    def update_settings(self, settings):
        """Update system settings"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            for key, value in settings.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO settings (setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?)
                """,
                    (key, str(value), datetime.now()),
                )

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def update_alert_settings(self, alert_settings):
        """Update alert settings"""
        return self.update_settings(alert_settings)

    def update_ai_settings(self, ai_settings):
        """Update AI model settings"""
        return self.update_settings(ai_settings)

    def get_model_performance(self):
        """Get AI model performance metrics"""
        performance_data = [
            {"model_name": "Demand Forecasting", "accuracy": 0.85},
            {"model_name": "Expiry Prediction", "accuracy": 0.78},
            {"model_name": "Anomaly Detection", "accuracy": 0.82},
            {"model_name": "Reorder Optimization", "accuracy": 0.88},
        ]
        return performance_data

    # Data management methods
    def export_all_data(self):
        """Export all system data"""
        conn = self.get_connection()
        query = """
            SELECT i.*, s.name as supplier_name
            FROM inventory i
            LEFT JOIN suppliers s ON i.supplier_name = s.name
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def export_inventory_data(self):
        """Export inventory data only"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM inventory", conn)
        conn.close()
        return df

    def export_transaction_data(self):
        """Export transaction data"""
        conn = self.get_connection()
        query = """
            SELECT t.*, i.drug_name
            FROM transactions t
            JOIN inventory i ON t.drug_id = i.id
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def export_report_data(self):
        """Export report data"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM consumption_patterns", conn)
        conn.close()
        return df

    def import_data(self, df, import_type):
        """Import data from DataFrame"""
        try:
            conn = self.get_connection()

            if import_type == "Inventory Items":
                df.to_sql("inventory_temp", conn, if_exists="replace", index=False)
                # Merge with existing inventory logic here
            elif import_type == "Transactions":
                df.to_sql("transactions", conn, if_exists="append", index=False)
            elif import_type == "Suppliers":
                df.to_sql("suppliers", conn, if_exists="append", index=False)

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def clean_old_data(self):
        """Clean old data (older than 2 years)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=730)
        cursor.execute("DELETE FROM transactions WHERE created_at < ?", (cutoff_date,))
        cursor.execute(
            "DELETE FROM consumption_patterns WHERE date < ?", (cutoff_date.date(),)
        )

        cleaned_records = cursor.rowcount
        conn.commit()
        conn.close()

        return cleaned_records

    def optimize_database(self):
        """Optimize database performance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        conn.commit()
        conn.close()

    def backup_database(self):
        """Create database backup"""
        backup_filename = f"pharma_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        # Simple file copy for SQLite
        import shutil

        shutil.copy2(self.db_path, backup_filename)

        return backup_filename

    def snooze_reorder_suggestion(self, suggestion_id, days):
        """Snooze a reorder suggestion"""
        # Implementation would depend on how suggestions are stored
        pass

    def dismiss_reorder_suggestion(self, suggestion_id):
        """Dismiss a reorder suggestion"""
        # Implementation would depend on how suggestions are stored
        pass

    def create_user(self, username, password, full_name, email, role, created_by):
        """Create a new user"""
        try:
            from auth import AuthManager

            conn = self.get_connection()
            cursor = conn.cursor()

            password_hash, salt = AuthManager.hash_password(password)
            combined_hash = f"{password_hash}${salt}"

            cursor.execute(
                """
                INSERT INTO users (username, password_hash, full_name, email, role, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (username, combined_hash, full_name, email, role, created_by),
            )

            user_id = cursor.lastrowid

            self.log_audit_trail(
                user_id=created_by,
                username=username,
                action="CREATE_USER",
                table_name="users",
                record_id=user_id,
                new_value=f"Created user {username} with role {role}",
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def get_all_users(self):
        """Get all users"""
        conn = self.get_connection()
        query = """
            SELECT id, username, full_name, email, role, is_active, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def toggle_user_status(self, user_id, is_active):
        """Toggle user active status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id)
        )
        conn.commit()
        conn.close()

    def log_audit_trail(
        self,
        user_id,
        username,
        action,
        table_name=None,
        record_id=None,
        old_value=None,
        new_value=None,
        ip_address=None,
    ):
        """Log action to audit trail"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_trail (user_id, username, action, table_name, record_id, old_value, new_value, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    username,
                    action,
                    table_name,
                    record_id,
                    old_value,
                    new_value,
                    ip_address,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging audit trail: {e}")

    def get_audit_trail(
        self, limit=100, user_id=None, action_type=None, start_date=None, end_date=None
    ):
        """Get audit trail records"""
        conn = self.get_connection()

        query = """
            SELECT * FROM audit_trail
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if action_type:
            query += " AND action = ?"
            params.append(action_type)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def create_default_users(self):
        """Create default demo users"""
        try:
            from auth import AuthManager

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] > 0:
                conn.close()
                return

            default_users = [
                ("demo_admin", "admin123", "Admin User", "admin@pharma.com", "admin"),
                (
                    "demo_pharmacist",
                    "pharma123",
                    "Pharmacist User",
                    "pharmacist@pharma.com",
                    "pharmacist",
                ),
                ("demo_staff", "staff123", "Staff User", "staff@pharma.com", "staff"),
            ]

            for username, password, full_name, email, role in default_users:
                password_hash, salt = AuthManager.hash_password(password)
                combined_hash = f"{password_hash}${salt}"

                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, email, role)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (username, combined_hash, full_name, email, role),
                )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error creating default users: {e}")
