"""
PDF Report Generation Module
Professional PDF reports for inventory analytics
"""

from fpdf import FPDF
from datetime import datetime, timedelta
import pandas as pd


class PDFReportGenerator(FPDF):
    """Generate professional PDF reports for inventory management"""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header"""
        self.set_font("Arial", "B", 16)
        self.set_text_color(102, 126, 234)
        self.cell(0, 10, "AI Pharmaceutical Inventory Management System", 0, 1, "C")
        self.set_font("Arial", "I", 10)
        self.set_text_color(100, 100, 100)
        self.cell(
            0,
            5,
            f"Generated on: {datetime.now().strftime('%B %d, %Y %I:%M %p')}",
            0,
            1,
            "C",
        )
        self.ln(5)

    def footer(self):
        """Page footer"""
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def chapter_title(self, title):
        """Add a chapter title"""
        self.set_font("Arial", "B", 14)
        self.set_fill_color(102, 126, 234)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, title, 0, 1, "L", 1)
        self.ln(2)

    def section_title(self, title):
        """Add a section title"""
        self.set_font("Arial", "B", 12)
        self.set_text_color(118, 75, 162)
        self.cell(0, 8, title, 0, 1, "L")
        self.ln(1)

    def add_text_content(self, text, bold=False):
        """Add text content"""
        self.set_font("Arial", "B" if bold else "", 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def add_metrics_row(self, label, value, color="black"):
        """Add a metrics row"""
        self.set_font("Arial", "B", 10)
        self.set_text_color(0, 0, 0)
        self.cell(100, 8, label, 1, 0, "L")

        if color == "green":
            self.set_text_color(40, 167, 69)
        elif color == "red":
            self.set_text_color(220, 53, 69)
        elif color == "orange":
            self.set_text_color(255, 193, 7)
        else:
            self.set_text_color(0, 0, 0)

        self.set_font("Arial", "", 10)
        self.cell(0, 8, str(value), 1, 1, "R")

    def add_table(self, df, max_rows=20):
        """Add a dataframe as a table"""
        if df.empty:
            self.add_text_content("No data available")
            return

        # Limit rows
        df_display = df.head(max_rows)

        # Set font
        self.set_font("Arial", "B", 9)
        self.set_fill_color(102, 126, 234)
        self.set_text_color(255, 255, 255)

        # Calculate column widths
        num_cols = len(df_display.columns)
        col_width = (self.w - 20) / num_cols

        # Header
        for col in df_display.columns:
            self.cell(col_width, 7, str(col)[:20], 1, 0, "C", 1)
        self.ln()

        # Data rows
        self.set_font("Arial", "", 8)
        self.set_text_color(0, 0, 0)

        for idx, row in df_display.iterrows():
            for col in df_display.columns:
                value = str(row[col])[:20]
                self.cell(col_width, 6, value, 1, 0, "L")
            self.ln()

        self.ln(3)


class InventoryReportGenerator:
    """Generate comprehensive inventory reports"""

    def __init__(self, _db_manager):
        self._db = _db_manager

    def generate_comprehensive_report(self, filename="inventory_report.pdf"):
        """Generate a comprehensive inventory report"""
        pdf = PDFReportGenerator()
        pdf.add_page()

        # Title Page
        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(102, 126, 234)
        pdf.ln(50)
        pdf.cell(0, 15, "Comprehensive Inventory Report", 0, 1, "C")
        pdf.set_font("Arial", "I", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, "AI-Powered Pharmaceutical Inventory Management", 0, 1, "C")

        # Executive Summary
        pdf.add_page()
        pdf.chapter_title("1. Executive Summary")

        total_items = self._db.get_total_inventory_count()
        total_value = self._db.get_total_inventory_value()
        low_stock = self._db.get_low_stock_count()
        expiring = self._db.get_expiring_soon_count()

        pdf.add_metrics_row("Total Items in Inventory", f"{total_items:,}")
        pdf.add_metrics_row("Total Inventory Value", f"Rs. {total_value:,.2f}")
        pdf.add_metrics_row(
            "Low Stock Items", f"{low_stock}", "red" if low_stock > 10 else "green"
        )
        pdf.add_metrics_row(
            "Items Expiring Soon (30 days)",
            f"{expiring}",
            "orange" if expiring > 5 else "green",
        )

        pdf.ln(5)
        pdf.add_text_content(
            f"This comprehensive report provides detailed insights into the current state of "
            f"the pharmaceutical inventory as of {datetime.now().strftime('%B %d, %Y')}. "
            f"The inventory consists of {total_items} unique items with a total value of Rs. {total_value:,.2f}. "
        )

        # Inventory by Category
        pdf.add_page()
        pdf.chapter_title("2. Inventory Distribution by Category")

        category_data = self._db.get_inventory_by_category()
        if not category_data.empty:
            pdf.section_title("Top Categories by Quantity")
            pdf.add_table(category_data.head(15))

        # Low Stock Analysis
        pdf.add_page()
        pdf.chapter_title("3. Stock Alert Analysis")

        pdf.section_title("Low Stock Items Requiring Immediate Action")
        conn = self._db.get_connection()
        low_stock_query = """
            SELECT drug_name, category, current_stock, minimum_stock,
                   (minimum_stock - current_stock) as shortage
            FROM inventory
            WHERE current_stock < minimum_stock
            ORDER BY shortage DESC
            LIMIT 20
        """
        low_stock_df = pd.read_sql_query(low_stock_query, conn)
        pdf.add_table(low_stock_df)

        pdf.add_text_content(
            f"Critical Alert: {len(low_stock_df)} items are currently below minimum stock levels. "
            f"Immediate reordering is recommended to prevent stockouts.",
            bold=True,
        )

        # Expiry Analysis
        pdf.add_page()
        pdf.chapter_title("4. Expiry Risk Analysis")

        pdf.section_title("Items Expiring Within 60 Days")
        expiry_query = """
            SELECT drug_name, category, current_stock, expiry_date,
                   CAST(JULIANDAY(expiry_date) - JULIANDAY('now') AS INTEGER) as days_remaining,
                   (current_stock * unit_price) as potential_loss
            FROM inventory
            WHERE expiry_date IS NOT NULL
              AND JULIANDAY(expiry_date) - JULIANDAY('now') BETWEEN 0 AND 60
              AND current_stock > 0
            ORDER BY days_remaining
            LIMIT 20
        """
        expiry_df = pd.read_sql_query(expiry_query, conn)
        pdf.add_table(expiry_df)

        if not expiry_df.empty:
            total_potential_loss = expiry_df["potential_loss"].sum()
            pdf.add_text_content(
                f"Wastage Risk: Rs. {total_potential_loss:,.2f} worth of inventory at risk of expiry. "
                f"Implement discount strategies or transfer to high-demand locations.",
                bold=True,
            )

        # Financial Overview
        pdf.add_page()
        pdf.chapter_title("5. Financial Overview")

        financial_data = self._db.get_financial_overview()
        pdf.add_metrics_row(
            "Total Inventory Value", f"Rs. {financial_data['total_value']:,.2f}"
        )
        pdf.add_metrics_row(
            "Monthly Spending (Avg)", f"Rs. {financial_data['monthly_spend']:,.2f}"
        )
        pdf.add_metrics_row(
            "Estimated Cost Savings Potential",
            f"Rs. {financial_data['cost_savings']:,.2f}",
            "green",
        )
        pdf.add_metrics_row(
            "Projected ROI", f"{financial_data['roi'] * 100:.1f}%", "green"
        )

        # Top Value Items
        pdf.add_page()
        pdf.chapter_title("6. High-Value Inventory Items")

        value_query = """
            SELECT drug_name, category, current_stock, unit_price,
                   (current_stock * unit_price) as total_value
            FROM inventory
            WHERE current_stock > 0
            ORDER BY total_value DESC
            LIMIT 20
        """
        value_df = pd.read_sql_query(value_query, conn)
        pdf.add_table(value_df)

        # Recommendations
        pdf.add_page()
        pdf.chapter_title("7. Key Recommendations")

        pdf.section_title("Priority Actions")
        pdf.add_text_content(
            "1. URGENT: Restock low inventory items to prevent stockouts", bold=True
        )
        pdf.add_text_content("   - Focus on critical medications with high demand")
        pdf.add_text_content("   - Review supplier delivery times for expedited orders")
        pdf.ln(3)

        pdf.add_text_content(
            "2. HIGH: Address expiring inventory to minimize wastage", bold=True
        )
        pdf.add_text_content(
            "   - Implement promotional pricing for items expiring within 30 days"
        )
        pdf.add_text_content(
            "   - Transfer slow-moving expiring items to high-demand branches"
        )
        pdf.ln(3)

        pdf.add_text_content("3. MEDIUM: Optimize inventory carrying costs", bold=True)
        pdf.add_text_content(
            "   - Review overstocked items and adjust reorder quantities"
        )
        pdf.add_text_content(
            "   - Implement Just-In-Time ordering for non-critical items"
        )
        pdf.ln(3)

        pdf.add_text_content(
            "4. ONGOING: Monitor consumption patterns using AI forecasting", bold=True
        )
        pdf.add_text_content("   - Leverage ML models for demand prediction")
        pdf.add_text_content(
            "   - Adjust minimum stock levels based on seasonal trends"
        )

        conn.close()

        # Save PDF
        pdf.output(filename)
        return filename

    def generate_analytics_report(
        self, start_date, end_date, filename="analytics_report.pdf"
    ):
        """Generate an analytics-focused report for a date range"""
        pdf = PDFReportGenerator()
        pdf.add_page()

        pdf.chapter_title(f"Analytics Report: {start_date} to {end_date}")

        conn = self._db.get_connection()

        # Consumption Analytics
        pdf.section_title("Consumption Analysis")
        consumption_query = """
            SELECT i.drug_name, i.category, SUM(cp.quantity_consumed) as total_consumed
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date BETWEEN ? AND ?
            GROUP BY i.drug_name, i.category
            ORDER BY total_consumed DESC
            LIMIT 20
        """
        consumption_df = pd.read_sql_query(
            consumption_query, conn, params=(start_date, end_date)
        )
        pdf.add_table(consumption_df)

        # Transaction Summary
        pdf.add_page()
        pdf.section_title("Transaction Summary")
        transaction_query = """
            SELECT transaction_type, COUNT(*) as count, SUM(quantity) as total_quantity
            FROM transactions
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY transaction_type
        """
        transaction_df = pd.read_sql_query(
            transaction_query, conn, params=(start_date, end_date)
        )
        pdf.add_table(transaction_df)

        conn.close()

        pdf.output(filename)
        return filename
