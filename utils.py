from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import streamlit as st

def format_currency(value, currency_symbol="₹"):
    """Formats a numeric value as a currency string with Indian numbering system."""
    if value is None:
        return f"{currency_symbol}0.00"
    try:
        # Simple formatting for now, can be enhanced for Indian grouping (e.g., 1,00,000)
        return f"{currency_symbol}{float(value):,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"

def format_dual_currency(value_inr, value_usd=None):
    """Formats a value in INR only (Removed USD support per user request)."""
    return format_currency(value_inr, "₹")

def calculate_days_until_expiry(expiry_date_str: str) -> int:
    """Calculates the number of days until a given expiry date."""
    if not expiry_date_str:
        return 9999
    try:
        if isinstance(expiry_date_str, datetime):
            expiry_date = expiry_date_str
        else:
            # Handle various date formats
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    expiry_date = datetime.strptime(expiry_date_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                return 9999
        
        delta = expiry_date - datetime.now()
        return delta.days
    except (ValueError, TypeError):
        return 9999

def calculate_stock_status(current_stock: int, minimum_stock: int) -> str:
    """Determines the stock status based on current and minimum levels."""
    if current_stock <= 0:
        return "Out of Stock"
    if current_stock <= minimum_stock:
        return "Low Stock"
    if current_stock <= minimum_stock * 1.5:
        return "Reorder"
    return "In Stock"

def get_stock_status_color(status: str) -> str:
    """Returns a color string based on the stock status."""
    color_map = {
        "Out of Stock": "#dc3545",  # Red
        "Low Stock": "#fd7e14",     # Orange
        "Reorder": "#ffc107",       # Yellow
        "In Stock": "#28a745",      # Green
    }
    return color_map.get(status, "#6c757d") # Grey

def generate_alerts(_db: Any) -> List[Dict]:
    """Generates a comprehensive list of alerts for various inventory conditions."""
    alerts = []

    # 1. Low Stock Alerts
    try:
        inventory = _db.get_inventory()
        low_stock = inventory[inventory["current_stock"] <= inventory["min_stock_level"]]
        for _, item in low_stock.head(5).iterrows():
            alerts.append({
                "type": "warning",
                "category": "stock",
                "message": f"Low stock: **{item['drug_name']}** has {int(item['current_stock'])} units (min: {int(item['min_stock_level'])}).",
                "id": item["id"]
            })
    except Exception:
        pass

    # 2. Expiry Alerts
    try:
        expiring = _db.get_expiring_items()
        for _, item in expiring.head(5).iterrows():
            days = item["days_until_expiry"]
            if days <= 0:
                msg = f"EXPIRED: **{item['drug_name']}** (Batch: {item['batch_number']}) expired on {item['expiry_date']}."
                alert_type = "error"
            elif days <= 30:
                msg = f"Expiring soon: **{item['drug_name']}** expires in {days} days."
                alert_type = "critical" if days <= 7 else "warning"
            else:
                continue
                
            alerts.append({
                "type": alert_type,
                "category": "expiry",
                "message": msg,
                "batch": item["batch_number"]
            })
    except Exception:
        pass

    # 3. Anomaly Alerts (Mocked for now as per database pattern)
    try:
        anomalies = _db.detect_anomalies()
        for anom in anomalies[:2]:
            alerts.append({
                "type": "info",
                "category": "anomaly",
                "message": anom["description"]
            })
    except Exception:
        pass

    return alerts

def get_low_stock_items(db: Any) -> pd.DataFrame:
    """Retrieves items that are low in stock."""
    inventory = db.get_inventory()
    return inventory[inventory["current_stock"] <= inventory["min_stock_level"]]

def get_expiring_items(db: Any, days_threshold: int = 30) -> pd.DataFrame:
    """Retrieves items that are expiring soon."""
    return db.get_expiring_drugs(days_ahead=days_threshold)

def get_high_value_expiring_items(db: Any, days_threshold: int = 60, value_threshold: int = 5000) -> pd.DataFrame:
    """Retrieves high-value items that are expiring soon."""
    expiring = db.get_expiring_drugs(days_ahead=days_threshold)
    # Calculate value
    expiring["value"] = expiring["current_stock"] * expiring.get("unit_price", 0)
    return expiring[expiring["value"] >= value_threshold]

def get_seasonal_adjustment_factor(date_obj: datetime, drug_category: str) -> float:
    """Get seasonal adjustment factor for demand forecasting."""
    month = date_obj.month
    
    # Example seasonal weights
    patterns = {
        "Antibiotics": {1: 1.2, 2: 1.2, 11: 1.1, 12: 1.3},
        "Respiratory": {1: 1.5, 2: 1.4, 11: 1.2, 12: 1.5},
        "Analgesics": {6: 1.1, 7: 1.2, 8: 1.1},
    }
    
    category_pattern = patterns.get(drug_category, {})
    return category_pattern.get(month, 1.0)

def get_reorder_alerts(_db: Any) -> List[Dict]:
    """Get reorder alerts based on current stock and consumption patterns."""
    try:
        data = _db.get_reorder_suggestions_data()
        alerts = data[data["current_stock"] <= data["minimum_stock"] * 1.5]
        return alerts.to_dict("records")
    except Exception:
        return []
