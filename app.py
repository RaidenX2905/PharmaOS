import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import socket
from datetime import datetime, timedelta
import random
import sqlite3
from database import DatabaseManager
from utils import (
    format_currency,
    format_dual_currency,
    calculate_days_until_expiry,
    generate_alerts,
)

# Lazy imports - only load when needed
# Heavy libraries will be imported on-demand to reduce startup time

# Page configuration
st.set_page_config(
    page_title="AI Pharmaceutical Inventory Management",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Optimized lightweight CSS - minimal animations for faster rendering
st.markdown(
    """
<style>
    /* Simplified header - solid color instead of gradients */
    .main-header {
        background: #667eea;
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }

    /* Simplified metric cards - solid colors, minimal effects */
    .metric-card {
        background: #667eea;
        padding: 1.2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
    }

    /* Mobile-specific adjustments */
    @media (max-width: 640px) {
        .main-header {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .main-header h1 {
            font-size: 1.5rem;
        }
        .metric-card {
            padding: 0.8rem;
        }
        .metric-card h3 {
            font-size: 1rem;
        }
        .metric-card h2 {
            font-size: 1.4rem;
        }
    }

    /* Simplified alert cards */
    .alert-card, .success-card, .warning-card, .error-card {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    
    .alert-card { background: #f8f9fa; border-left-color: #007bff; }
    .success-card { background: #d4edda; border-left-color: #28a745; }
    .warning-card { background: #fff3cd; border-left-color: #ffc107; }
    .error-card { background: #f8d7da; border-left-color: #dc3545; }

    /* Simplified buttons */
    .stButton > button {
        background: #667eea;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
        width: 100%;
    }

    /* Simplified inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {
        border-radius: 6px;
        border: 1px solid #ddd;
    }
    
    /* Ensure charts are responsive */
    .chart-container {
        width: 100%;
        overflow-x: auto;
    }
    
    img {
        max-width: 100%;
        height: auto;
    }
    
    .metric-card h2 {
        word-wrap: break-word;
        overflow-wrap: break-word;
        font-size: 1.8rem;
    }
    
    /* Better table alignment on mobile */
    .stDataFrame {
        width: 100% !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Initialize database - lightweight, always needed
@st.cache_resource
def init_database():
    return DatabaseManager()


# Lazy load AI models - only when needed (not at startup)
@st.cache_resource
def init_ai_models():
    from ai_models import SmartReordering, ExpiryPredictor
    reordering = SmartReordering()
    expiry_predictor = ExpiryPredictor()
    return reordering, expiry_predictor


# Lazy import functions for heavy modules
def lazy_import_plotly():
    """Import plotly only when needed"""
    if 'plotly_loaded' not in st.session_state:
        import plotly.express as px
        import plotly.graph_objects as go
        st.session_state['plotly_loaded'] = True
        st.session_state['px'] = px
        st.session_state['go'] = go
    return st.session_state['px'], st.session_state['go']


def lazy_import_analytics():
    """Import advanced analytics only when needed"""
    if 'analytics_loaded' not in st.session_state:
        from advanced_analytics import (
            AdvancedAnalytics,
            WastageAnalyzer,
            CostOptimizer,
            DrugUtilizationReview,
            AutomatedInsightsGenerator,
        )
        st.session_state['analytics_loaded'] = True
        st.session_state['AdvancedAnalytics'] = AdvancedAnalytics
        st.session_state['WastageAnalyzer'] = WastageAnalyzer
        st.session_state['CostOptimizer'] = CostOptimizer
        st.session_state['DrugUtilizationReview'] = DrugUtilizationReview
        st.session_state['AutomatedInsightsGenerator'] = AutomatedInsightsGenerator
    return (
        st.session_state['AdvancedAnalytics'],
        st.session_state['WastageAnalyzer'],
        st.session_state['CostOptimizer'],
        st.session_state['DrugUtilizationReview'],
        st.session_state['AutomatedInsightsGenerator'],
    )




# Function to invalidate analytics cache when inventory changes
def invalidate_analytics_cache():
    """Clear cached analytics results to force refresh"""
    if "regression_results" in st.session_state:
        del st.session_state["regression_results"]
    if "lstm_results" in st.session_state:
        del st.session_state["lstm_results"]
    if "last_inventory_update" not in st.session_state:
        st.session_state["last_inventory_update"] = datetime.now()
    else:
        st.session_state["last_inventory_update"] = datetime.now()


# Add progress indicators and loading states
def show_loading_spinner():
    """Show a loading spinner with custom styling"""
    st.markdown(
        """
    <div style="text-align: center; padding: 2rem;">
        <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin-top: 1rem; color: #666;">Loading...</p>
    </div>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


def show_success_message(message):
    """Show a success message with animation"""
    st.markdown(
        f"""
    <div style="background: #d4edda; color: #155724; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745; margin: 1rem 0; animation: slideIn 0.5s ease;">
        <strong>✅ Success!</strong> {message}
    </div>
    <style>
        @keyframes slideIn {{
            from {{ transform: translateX(-100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
    </style>
    """,
        unsafe_allow_html=True,
    )


# Sidebar navigation with enhanced styling
st.sidebar.markdown(
    """
<div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
    <h2 style="color: white; margin: 0;">🏥 AI Pharma Manager</h2>
    <p style="color: white; margin: 0; font-size: 0.9rem;">Smart Inventory Management</p>
</div>
""",
    unsafe_allow_html=True,
)

# Add a welcome message
st.sidebar.markdown(
    """
<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
    <p style="margin: 0; font-size: 0.9rem; color: #666;">👋 Welcome to your AI-powered pharmaceutical inventory management system!</p>
</div>
""",
    unsafe_allow_html=True,
)

# Initialize database - lightweight, always needed
_db = init_database()

# PERFORMANCE: Global cached data loader
@st.cache_data(ttl=120, show_spinner=False)
def get_inventory_data(_db_instance):
    """Cached global inventory fetch for speed optimization"""
    return _db_instance.get_inventory()

@st.cache_data(ttl=300, show_spinner=False)
def get_dashboard_metrics(_db_instance):
    """Cache high-level metrics to speed up dashboard loads"""
    return {
        "total": _db_instance.get_total_inventory_count(),
        "low": _db_instance.get_low_stock_count(),
        "expiring": _db_instance.get_expiring_soon_count(),
        "value": _db_instance.get_total_inventory_value(),
        "category_data": _db_instance.get_inventory_by_category(),
        "stock_data": _db_instance.get_stock_levels()
    }

@st.cache_data(ttl=60, show_spinner=False)
def get_recent_transactions_cached(_db_instance, limit=50):
    """Cache recent transactions with a short TTL"""
    return _db_instance.get_recent_transactions(limit=limit)

# AI models will be loaded lazily when needed (not at startup)
reordering = None
expiry_predictor = None


st.sidebar.markdown("---")

# Navigation menu based on user role
menu_items = [
    "Dashboard",
    "Inventory Management",
    "Analytics",
    "📈 Regression & LSTM Analysis",
]

# Advanced Analytics Features - Now Available!
menu_items.extend(
    [
        "🚨 Anomaly Monitor",
        "💡 Wastage Analysis",
        "💰 Cost Optimization",
        "📊 Drug Utilization Review",
        "🔮 Advanced Predictive Analytics",
        "🔗 Drug Correlations",
    ]
)

# New Advanced Features
menu_items.extend(
    [
        "🤖 AI Assistant",
        "🎯 Smart Recommendations",
        "📄 Generate Reports",
    ]
)

menu_items.extend(["Smart Reordering", "Expiry Management"])


menu_items.append("Settings")

# Safe query params reading for Streamlit >= 1.30
query_params = st.query_params
default_index = 0
if "page" in query_params:
    requested_page = query_params["page"]
    if requested_page in menu_items:
        default_index = menu_items.index(requested_page)

page = st.sidebar.selectbox("📋 Navigation Menu", menu_items, index=default_index)

# Update query param when page changes
if query_params.get("page") != page:
    st.query_params["page"] = page

# Sidebar - Quick Actions
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ System Tools")
if st.sidebar.button("🧹 Clear AI & Database Cache"):
    st.cache_resource.clear()
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")


def dashboard_page():
    # Enhanced header
    st.markdown(
        """
    <div class="main-header">
        <h1>📊 AI Pharmaceutical Inventory Dashboard</h1>
        <p>Real-time insights and smart analytics for your pharmacy</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Add a quick stats row
    st.markdown("### 📈 Quick Overview")

    # Key metrics with enhanced styling
    col1, col2, col3, col4 = st.columns(4)

    metrics = get_dashboard_metrics(_db)
    total_items = metrics["total"]
    low_stock_items = metrics["low"]
    expiring_soon = metrics["expiring"]
    total_value = metrics["value"]

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>📦 Total Items</h3>
            <h2>{total_items}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>⚠️ Low Stock Items</h3>
            <h2>{low_stock_items}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>⏰ Expiring Soon</h3>
            <h2>{expiring_soon}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>💰 Total Value</h3>
            <h2>{format_dual_currency(total_value, 0)}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Enhanced alerts section
    st.markdown("### 🚨 Smart Alerts & Notifications")
    alerts = generate_alerts(_db)
    if alerts:
        for alert in alerts:
            if alert["type"] == "critical":
                st.markdown(
                    f"""
                <div class="error-card">
                    <strong>🚨 Critical Alert:</strong> {alert["message"]}
                </div>
                """,
                    unsafe_allow_html=True,
                )
            elif alert["type"] == "warning":
                st.markdown(
                    f"""
                <div class="warning-card">
                    <strong>⚠️ Warning:</strong> {alert["message"]}
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                <div class="alert-card">
                    <strong>ℹ️ Info:</strong> {alert["message"]}
                </div>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            """
        <div class="success-card">
            <strong>✅ All Good!</strong> No alerts at this time. Your inventory is well-managed.
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Enhanced charts section
    st.markdown("### 📊 Analytics & Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📈 Inventory by Category")
        category_data = metrics["category_data"]
        if not category_data.empty:
            px, _ = lazy_import_plotly()
            fig = px.pie(
                category_data,
                values="quantity",
                names="category",
                title="Inventory Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📉 Stock Levels")
        stock_data = metrics["stock_data"]
        if not stock_data.empty:
            px, _ = lazy_import_plotly()
            fig = px.bar(
                stock_data,
                x="drug_name",
                y="current_stock",
                title="Current Stock Levels",
                color="current_stock",
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Recent transactions with enhanced styling
    st.markdown("### 📋 Recent Transactions")
    recent_transactions = get_recent_transactions_cached(_db, limit=50)
    if not recent_transactions.empty:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)

        # Format the dataframe for better display
        display_df = recent_transactions.copy()

        # Format dates
        if "created_at" in display_df.columns:
            display_df["created_at"] = pd.to_datetime(
                display_df["created_at"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

        # Calculate amounts if missing - use quantity × unit_price
        if "total_amount" in display_df.columns:
            # Fill missing amounts by calculating from quantity × unit_price
            if "unit_price" in display_df.columns:
                mask = (display_df["total_amount"].isna()) | (
                    display_df["total_amount"] == 0
                )
                display_df.loc[mask, "total_amount"] = (
                    display_df.loc[mask, "quantity"]
                    * display_df.loc[mask, "unit_price"]
                ).fillna(0)

            # Format currency - ensure amount is always shown and calculated
            display_df["total_amount"] = display_df["total_amount"].fillna(0)
            display_df["total_amount"] = display_df["total_amount"].apply(
                lambda x: f"₹{float(x):,.2f}" if float(x) > 0 else "₹0.00"
            )
        else:
            # Calculate amount from quantity × unit_price if available
            if "quantity" in display_df.columns and "unit_price" in display_df.columns:
                display_df["total_amount"] = (
                    display_df["quantity"] * display_df["unit_price"]
                ).fillna(0)
                display_df["total_amount"] = display_df["total_amount"].apply(
                    lambda x: f"₹{float(x):,.2f}" if float(x) > 0 else "₹0.00"
                )
            else:
                display_df["total_amount"] = "N/A"

        # Reorder columns for better readability - exclude unit_price from display
        column_order = [
            "transaction_type",
            "drug_name",
            "quantity",
            "total_amount",
            "notes",
            "created_at",
        ]
        display_columns = [col for col in column_order if col in display_df.columns]
        # Remove unit_price from display if it exists (it was only used for calculation)
        if "unit_price" in display_df.columns and "unit_price" not in column_order:
            display_columns = [col for col in display_columns if col != "unit_price"]
        display_df = display_df[display_columns]

        # Rename columns for better display
        display_df = display_df.rename(
            columns={
                "transaction_type": "Type",
                "drug_name": "Drug Name",
                "quantity": "Quantity",
                "total_amount": "💰 Amount (₹)",
                "notes": "Details",
                "created_at": "Date & Time",
            }
        )

        st.dataframe(display_df, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Add summary statistics with total amounts
        if len(recent_transactions) > 0:
            # Calculate totals by transaction type
            add_items = recent_transactions[
                recent_transactions["transaction_type"] == "Add Item"
            ]
            update_items = recent_transactions[
                recent_transactions["transaction_type"] == "Update Item"
            ]
            delete_items = recent_transactions[
                recent_transactions["transaction_type"] == "Delete Item"
            ]
            csv_imports = recent_transactions[
                recent_transactions["transaction_type"] == "CSV Import"
            ]
            purchase_orders = recent_transactions[
                recent_transactions["transaction_type"] == "Purchase Order"
            ]

            # Calculate totals - convert formatted strings back to numbers if needed
            def extract_amount(value):
                """Extract numeric amount from formatted string or number"""
                if pd.isna(value):
                    return 0
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    # Remove ₹ and commas, convert to float
                    cleaned = value.replace("₹", "").replace(",", "").strip()
                    try:
                        return float(cleaned)
                    except:
                        return 0
                return 0

            # Use original dataframe (recent_transactions) for accurate totals, not formatted display_df
            add_total = (
                add_items["total_amount"].apply(extract_amount).sum()
                if "total_amount" in add_items.columns
                else 0
            )
            update_total = (
                update_items["total_amount"].apply(extract_amount).sum()
                if "total_amount" in update_items.columns
                else 0
            )
            delete_total = (
                delete_items["total_amount"].apply(extract_amount).sum()
                if "total_amount" in delete_items.columns
                else 0
            )
            import_total = (
                csv_imports["total_amount"].apply(extract_amount).sum()
                if "total_amount" in csv_imports.columns
                else 0
            )
            order_total = (
                purchase_orders["total_amount"].apply(extract_amount).sum()
                if "total_amount" in purchase_orders.columns
                else 0
            )

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("➕ Items Added", len(add_items), f"₹{add_total:,.2f}")
            with col2:
                st.metric("✏️ Items Updated", len(update_items), f"₹{update_total:,.2f}")
            with col3:
                st.metric("🗑️ Items Deleted", len(delete_items), f"₹{delete_total:,.2f}")
            with col4:
                st.metric("📥 CSV Imports", len(csv_imports), f"₹{import_total:,.2f}")
            with col5:
                st.metric(
                    "📋 Purchase Orders", len(purchase_orders), f"₹{order_total:,.2f}"
                )

            # Grand total - calculate from numeric values
            if "total_amount" in recent_transactions.columns:
                grand_total = (
                    recent_transactions["total_amount"]
                    .apply(lambda x: float(x) if isinstance(x, (int, float)) else 0)
                    .sum()
                )
                st.markdown(f"**💰 Total Transaction Value: ₹{grand_total:,.2f}**")
            else:
                st.markdown("**💰 Total Transaction Value: ₹0.00**")
    else:
        st.markdown(
            """
        <div class="alert-card">
            <strong>ℹ️ No recent transactions found.</strong>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Add helpful footer
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 8px; margin-top: 2rem;">
        <p style="margin: 0; color: #666; font-size: 0.9rem;">
            💡 <strong>Tip:</strong> Use the sidebar to navigate between different features. Each section provides specialized tools for managing your pharmaceutical inventory.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Duplicate 'Recent Transactions' section removed to avoid double rendering


def inventory_management_page():
    st.title("📦 Inventory Management")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "View Inventory",
            "Add New Item",
            "Update Stock",
            "Edit/Delete Item",
            "Batch Operations",
        ]
    )

    with tab1:
        st.subheader("Current Inventory")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            all_categories = _db.get_categories()
            category_filter = st.selectbox(
                "Filter by Category",
                ["All", "Drugs", "Baby Care Products", "Surgical Items"]
                + [
                    c
                    for c in all_categories
                    if c not in ["Drugs", "Baby Care Products", "Surgical Items"]
                ],
            )
        with col2:
            stock_filter = st.selectbox(
                "Stock Status", ["All", "Low Stock", "Out of Stock", "Normal"]
            )
        with col3:
            search_term = st.text_input("Search Drug Name")

        # Get filtered inventory
        inventory_data = _db.get_filtered_inventory(
            category_filter, stock_filter, search_term
        )

        if not inventory_data.empty:
            # Add color coding for stock levels
            def color_stock_level(val):
                if val <= 10:
                    return "background-color: #ffcccc"  # Red for low stock
                elif val <= 50:
                    return "background-color: #fff3cd"  # Yellow for medium stock
                else:
                    return "background-color: #d4edda"  # Green for good stock

            styled_df = inventory_data.style.map(
                color_stock_level, subset=["current_stock"]
            )
            st.dataframe(styled_df, use_container_width=True)

            # Export and Import functionality
            col_export, col_import = st.columns(2)
            with col_export:
                csv = inventory_data.to_csv(index=False)
                st.download_button(
                    label="📥 Export to CSV",
                    data=csv,
                    file_name=f"inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
            with col_import:
                uploaded_file = st.file_uploader("📥 Import from CSV", type="csv")
                if uploaded_file is not None:
                    try:
                        df = pd.read_csv(uploaded_file)
                        # Required columns
                        required_cols = {
                            "drug_name",
                            "category",
                            "batch_number",
                            "current_stock",
                            "minimum_stock",
                            "unit_price",
                            "expiry_date",
                        }
                        if not required_cols.issubset(df.columns):
                            st.error(
                                f"CSV must contain the following columns: {', '.join(required_cols)}"
                            )
                        else:
                            # Clean and validate data before importing
                            def clean_and_validate_data(df):
                                """Clean and validate CSV data before importing to inventory"""
                                original_count = len(df)
                                cleaned_df = df.copy()
                                invalid_rows = []
                                errors = []

                                # Define invalid values patterns
                                invalid_patterns = [
                                    "#",
                                    "0",
                                    "N/A",
                                    "n/a",
                                    "NULL",
                                    "null",
                                    "None",
                                    "none",
                                    "-",
                                    "--",
                                    "---",
                                    "",
                                    " ",
                                    "NA",
                                    "na",
                                    "NAN",
                                    "nan",
                                ]

                                def is_invalid_value(value):
                                    """Check if a value is considered invalid"""
                                    if pd.isna(value):
                                        return True
                                    str_value = str(value).strip()
                                    return (
                                        str_value in invalid_patterns
                                        or str_value == ""
                                        or str_value == "0"
                                    )

                                def is_invalid_batch_number(batch_num):
                                    """Check if batch number is invalid"""
                                    if pd.isna(batch_num):
                                        return True
                                    str_batch = str(batch_num).strip()
                                    # Check for common invalid patterns
                                    if str_batch in invalid_patterns:
                                        return True
                                    # Check if it's just "0" or starts with invalid chars
                                    if str_batch == "0" or str_batch.startswith("#"):
                                        return True
                                    # Check if it contains only special characters
                                    if all(
                                        c in "#-./\\"
                                        for c in str_batch.replace(" ", "")
                                    ):
                                        return True
                                    return False

                                # Remove rows with completely empty values
                                cleaned_df = cleaned_df.dropna(how="all")

                                # Trim whitespace from string columns
                                string_cols = [
                                    "drug_name",
                                    "category",
                                    "batch_number",
                                    "expiry_date",
                                    "manufacturer",
                                    "supplier_name",
                                    "description",
                                    "id",
                                ]
                                for col in string_cols:
                                    if col in cleaned_df.columns:
                                        cleaned_df[col] = (
                                            cleaned_df[col].astype(str).str.strip()
                                        )

                                # Validate required fields
                                for idx, row in cleaned_df.iterrows():
                                    row_errors = []

                                    # Check for missing or empty required fields
                                    if pd.isna(
                                        row.get("drug_name")
                                    ) or is_invalid_value(row.get("drug_name")):
                                        row_errors.append("Missing or empty drug_name")

                                    if pd.isna(row.get("category")) or is_invalid_value(
                                        row.get("category")
                                    ):
                                        row_errors.append("Missing or empty category")

                                    # Validate batch_number - check for invalid values like 0, #, etc.
                                    batch_number = row.get("batch_number", "")
                                    if is_invalid_batch_number(batch_number):
                                        row_errors.append(
                                            f"Invalid batch_number: '{batch_number}' (cannot be 0, #, or placeholder)"
                                        )

                                    # Validate id field if present
                                    if "id" in cleaned_df.columns:
                                        id_value = row.get("id", "")
                                        if is_invalid_value(id_value) or str(
                                            id_value
                                        ).strip() in ["0", "#"]:
                                            row_errors.append(
                                                f"Invalid id: '{id_value}' (cannot be 0, #, or placeholder)"
                                            )

                                    # Validate numeric fields
                                    try:
                                        current_stock = float(
                                            row.get("current_stock", 0)
                                        )
                                        if pd.isna(current_stock) or current_stock < 0:
                                            row_errors.append(
                                                "Invalid current_stock (must be >= 0)"
                                            )
                                    except (ValueError, TypeError):
                                        row_errors.append(
                                            "Invalid current_stock (not a number)"
                                        )

                                    try:
                                        minimum_stock = float(
                                            row.get("minimum_stock", 0)
                                        )
                                        if pd.isna(minimum_stock) or minimum_stock < 0:
                                            row_errors.append(
                                                "Invalid minimum_stock (must be >= 0)"
                                            )
                                    except (ValueError, TypeError):
                                        row_errors.append(
                                            "Invalid minimum_stock (not a number)"
                                        )

                                    # Validate unit_price - must not be 0 or invalid
                                    try:
                                        unit_price_str = str(
                                            row.get("unit_price", "0")
                                        ).strip()
                                        # Check if price contains invalid characters like #
                                        if (
                                            "#" in unit_price_str
                                            or unit_price_str in invalid_patterns
                                        ):
                                            row_errors.append(
                                                f"Invalid unit_price: '{unit_price_str}' (contains invalid characters or placeholder)"
                                            )
                                        else:
                                            unit_price = float(row.get("unit_price", 0))
                                            if pd.isna(unit_price) or unit_price <= 0:
                                                row_errors.append(
                                                    f"Invalid unit_price: {unit_price} (must be > 0)"
                                                )
                                    except (ValueError, TypeError) as e:
                                        row_errors.append(
                                            f"Invalid unit_price (not a number): {str(row.get('unit_price', ''))}"
                                        )

                                    # Validate expiry_date format (should be YYYY-MM-DD or similar)
                                    expiry_date = row.get("expiry_date", "")
                                    if pd.isna(expiry_date) or is_invalid_value(
                                        expiry_date
                                    ):
                                        row_errors.append(
                                            "Missing or empty expiry_date"
                                        )
                                    else:
                                        try:
                                            # Try to parse the date to ensure it's valid
                                            pd.to_datetime(
                                                str(expiry_date).strip(), errors="raise"
                                            )
                                        except (ValueError, TypeError):
                                            row_errors.append(
                                                f"Invalid expiry_date format: {expiry_date}"
                                            )

                                    if row_errors:
                                        invalid_rows.append(idx)
                                        errors.append(
                                            {
                                                "row": idx
                                                + 2,  # +2 because of header and 0-indexing
                                                "drug_name": str(
                                                    row.get("drug_name", "Unknown")
                                                ),
                                                "errors": row_errors,
                                            }
                                        )

                                # Remove invalid rows
                                cleaned_df = cleaned_df.drop(invalid_rows)

                                return cleaned_df, invalid_rows, errors, original_count

                            # Clean the data
                            (
                                cleaned_df,
                                invalid_rows,
                                validation_errors,
                                original_count,
                            ) = clean_and_validate_data(df)

                            # Show validation results
                            if validation_errors:
                                st.warning(
                                    f"⚠️ Found {len(validation_errors)} row(s) with invalid data. These will be skipped."
                                )
                                with st.expander("📋 View Invalid Rows Details"):
                                    for error in validation_errors:
                                        st.write(
                                            f"**Row {error['row']} ({error['drug_name']}):**"
                                        )
                                        for err_msg in error["errors"]:
                                            st.write(f"  - {err_msg}")

                            if len(cleaned_df) == 0:
                                st.error(
                                    "❌ No valid rows found after cleaning. Please check your CSV file and try again."
                                )
                            else:
                                st.info(
                                    f"📊 {len(cleaned_df)} valid row(s) out of {original_count} total row(s) will be imported."
                                )

                                with st.spinner("Processing import... Please wait."):
                                    success_count = 0
                                    error_count = 0
                                    updated_count = 0

                                    for _, row in cleaned_df.iterrows():
                                        try:
                                            drug_name = row["drug_name"]
                                            batch_number = row["batch_number"]
                                            quantity = int(row["current_stock"])
                                            expiry_date = row.get("expiry_date", "")
                                            supplier_name = row.get("supplier_name", "")

                                            # Check if this drug already exists
                                            existing_item = _db.find_item_by_drug_name(
                                                drug_name
                                            )

                                            if existing_item:
                                                # Add stock to existing item (merge with current data)
                                                notes = "New batch medicine arrived"
                                                success = (
                                                    _db.add_stock_to_existing_item(
                                                        item_id=existing_item["id"],
                                                        quantity_to_add=quantity,
                                                        batch_number=batch_number,
                                                        expiry_date=expiry_date,
                                                        supplier_name=supplier_name,
                                                        notes=notes,
                                                    )
                                                )
                                                if success:
                                                    updated_count += 1
                                                else:
                                                    error_count += 1
                                            else:
                                                # Add as new item (will appear at end of table)
                                                success = _db.add_inventory_item(
                                                    row["drug_name"],
                                                    row["category"],
                                                    row.get("manufacturer", ""),
                                                    row["batch_number"],
                                                    int(row["current_stock"]),
                                                    int(row["minimum_stock"]),
                                                    float(row["unit_price"]),
                                                    row["expiry_date"],
                                                    row.get("supplier_name", ""),
                                                    row.get("description", ""),
                                                )
                                                if success:
                                                    success_count += 1
                                                    # Transaction is already logged in add_inventory_item method
                                                else:
                                                    error_count += 1
                                        except Exception as e:
                                            error_count += 1
                                            st.error(
                                                f"Error processing {row.get('drug_name', 'unknown')}: {str(e)}"
                                            )

                                    # Log CSV import transaction if items were imported
                                    if success_count > 0 or updated_count > 0:
                                        try:
                                            conn = _db.get_connection()
                                            cursor = conn.cursor()

                                            # Calculate total amount for imported items
                                            total_import_amount = 0
                                            for _, row in cleaned_df.iterrows():
                                                try:
                                                    quantity = int(
                                                        row.get("current_stock", 0)
                                                    )
                                                    price = float(
                                                        row.get("unit_price", 0)
                                                    )
                                                    total_import_amount += (
                                                        quantity * price
                                                    )
                                                except:
                                                    pass

                                            cursor.execute(
                                                """
                                                INSERT INTO transactions (drug_id, transaction_type, quantity, total_amount, notes, created_at)
                                                VALUES (NULL, 'CSV Import', ?, ?, ?, CURRENT_TIMESTAMP)
                                            """,
                                                (
                                                    success_count + updated_count,
                                                    total_import_amount,
                                                    f"CSV Import: {success_count} new items added, {updated_count} items updated | Total rows processed: {len(cleaned_df)} | Invalid rows skipped: {len(validation_errors)} | Total Value: ₹{total_import_amount:.2f}",
                                                ),
                                            )
                                            conn.commit()
                                            conn.close()
                                        except Exception as e:
                                            print(
                                                f"Error logging CSV import transaction: {e}"
                                            )

                                    # Show results summary
                                    if success_count > 0:
                                        st.success(
                                            f"✅ Successfully added {success_count} new items to inventory"
                                        )
                                    if updated_count > 0:
                                        st.info(
                                            f"📦 Updated stock for {updated_count} existing items (merged with current data)"
                                        )
                                    if error_count > 0:
                                        st.warning(
                                            f"⚠️ Failed to process {error_count} items"
                                        )

                                    if success_count > 0 or updated_count > 0:
                                        invalidate_analytics_cache()
                                        st.cache_data.clear()
                                        st.success(f"Successfully processed {success_count + updated_count} items!")
                                        st.rerun()

                    except Exception as e:
                        st.error(f"Error importing CSV file: {e}")
        else:
            st.info("No inventory items found matching your criteria.")

    with tab2:
        st.subheader("Add New Pharmaceutical Item")

        with st.form("add_item_form"):
            col1, col2 = st.columns(2)

            with col1:
                drug_name = st.text_input("Drug Name*")
                category = st.selectbox(
                    "Category",
                    [
                        "Drugs",
                        "Baby Care Products",
                        "Surgical Items",
                    ],
                )
                manufacturer = st.text_input("Manufacturer")
                batch_number = st.text_input("Batch Number*")
                current_stock = st.number_input("Current Stock", min_value=0, value=0)
                minimum_stock = st.number_input(
                    "Minimum Stock Level", min_value=0, value=10
                )

            with col2:
                per_tablet_price = st.number_input(
                    "Per Tablet/Unit Price (₹)", min_value=0.0, value=0.0, step=0.01
                )
                tablets_per_sheet = st.number_input(
                    "Tablets Per Sheet", min_value=1, value=10
                )
                per_sheet_price = st.number_input(
                    "Per Sheet Price (₹) - Auto Calculated",
                    min_value=0.0,
                    value=per_tablet_price * tablets_per_sheet,
                    step=0.01,
                    disabled=False,
                )
                expiry_date = st.date_input("Expiry Date")

            supplier_name = st.text_input("Supplier Name")
            description = st.text_area("Description")

            submitted = st.form_submit_button("Add Item")

            if submitted:
                if drug_name and batch_number:
                    success = _db.add_inventory_item(
                        drug_name,
                        category,
                        manufacturer,
                        batch_number,
                        current_stock,
                        minimum_stock,
                        per_tablet_price,
                        expiry_date,
                        supplier_name,
                        description,
                        per_tablet_price=per_tablet_price,
                        per_sheet_price=per_sheet_price,
                        tablets_per_sheet=tablets_per_sheet,
                    )
                    if success:
                        invalidate_analytics_cache()
                        st.success("Item added successfully!")
                        st.rerun()
                    else:
                        st.error(
                            "Failed to add item. Please check if batch number already exists."
                        )
                else:
                    st.error("Please fill in all required fields (marked with *).")

    with tab3:
        st.subheader("Update Stock Levels")

        # Select item to update
        items = _db.get_all_items_for_dropdown()
        if items:
            selected_item = st.selectbox("Select Item to Update", items)

            if selected_item:
                item_id = selected_item.split(" - ")[0]
                current_item = _db.get_item_details(item_id)

                if current_item:
                    st.write(f"**Current Stock:** {current_item['current_stock']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        transaction_type = st.selectbox(
                            "Transaction Type", ["Add Stock", "Remove Stock"]
                        )
                        quantity = st.number_input("Quantity", min_value=1, value=1)

                    with col2:
                        reason = st.text_input("Reason/Notes")

                    if st.button("Update Stock"):
                        if transaction_type == "Add Stock":
                            new_stock = current_item["current_stock"] + quantity
                        else:
                            new_stock = max(0, current_item["current_stock"] - quantity)

                        success = _db.update_stock_level(
                            item_id, new_stock, transaction_type, quantity, reason
                        )
                        if success:
                            invalidate_analytics_cache()
                            st.success(
                                f"Stock updated successfully! New stock level: {new_stock}"
                            )
                            st.rerun()
                        else:
                            st.error("Failed to update stock.")
        else:
            st.info("No items available for update.")

    with tab4:
        st.subheader("✏️ Edit or Delete Inventory Item")

        # Select item to edit
        items = _db.get_all_items_for_dropdown()
        if items:
            selected_item = st.selectbox(
                "Select Item to Edit/Delete", items, key="edit_item_select"
            )

            if selected_item:
                item_id = selected_item.split(" - ")[0]

                # Clear session state when selected item changes
                if (
                    "last_edited_item_id" not in st.session_state
                    or st.session_state.last_edited_item_id != item_id
                ):
                    st.session_state.last_edited_item_id = item_id
                    # Clear all edit-related session state
                    for key in [
                        "edit_per_tablet_price",
                        "edit_tablets_per_sheet",
                        "edit_per_sheet_price",
                    ]:
                        if key in st.session_state:
                            del st.session_state[key]
                current_item = _db.get_item_details(item_id)

                if current_item:
                    # Create two columns for Edit and Delete
                    col_edit, col_delete = st.columns([3, 1])

                    with col_edit:
                        st.markdown("### Edit Item Details")

                        with st.form("edit_item_form"):
                            col1, col2 = st.columns(2)

                            with col1:
                                edit_drug_name = st.text_input(
                                    "Drug Name*",
                                    value=current_item.get("drug_name", ""),
                                )
                                edit_category = st.selectbox(
                                    "Category",
                                    ["Drugs", "Baby Care Products", "Surgical Items"],
                                    index=[
                                        "Drugs",
                                        "Baby Care Products",
                                        "Surgical Items",
                                    ].index(current_item.get("category", "Drugs"))
                                    if current_item.get("category")
                                    in ["Drugs", "Baby Care Products", "Surgical Items"]
                                    else 0,
                                )
                                edit_manufacturer = st.text_input(
                                    "Manufacturer",
                                    value=current_item.get("manufacturer", ""),
                                )
                                edit_batch_number = st.text_input(
                                    "Batch Number*",
                                    value=current_item.get("batch_number", ""),
                                )
                                edit_current_stock = st.number_input(
                                    "Current Stock",
                                    min_value=0,
                                    value=int(current_item.get("current_stock", 0)),
                                )
                                edit_minimum_stock = st.number_input(
                                    "Minimum Stock Level",
                                    min_value=0,
                                    value=int(current_item.get("minimum_stock", 10)),
                                )

                            with col2:
                                # Price editing with auto-calculation
                                edit_per_tablet_price = st.number_input(
                                    "Per Tablet/Unit Price (₹)*",
                                    min_value=0.0,
                                    value=float(
                                        current_item.get("per_tablet_price", 0)
                                    ),
                                    step=0.01,
                                    key="edit_tablet_price_input",
                                )

                                edit_tablets_per_sheet = st.number_input(
                                    "Tablets Per Sheet*",
                                    min_value=1,
                                    value=int(
                                        current_item.get("tablets_per_sheet", 10)
                                    ),
                                    key="edit_tablets_input",
                                )

                                # Auto-calculate sheet price
                                calculated_sheet_price = (
                                    edit_per_tablet_price * edit_tablets_per_sheet
                                )

                                edit_per_sheet_price = st.number_input(
                                    "Per Sheet Price (₹) - Auto Calculated",
                                    min_value=0.0,
                                    value=calculated_sheet_price,
                                    step=0.01,
                                    disabled=True,
                                    key="edit_sheet_price_input",
                                )

                                # Handle expiry date
                                if current_item.get("expiry_date"):
                                    try:
                                        expiry_date_value = datetime.strptime(
                                            str(current_item["expiry_date"]), "%Y-%m-%d"
                                        ).date()
                                    except:
                                        expiry_date_value = datetime.now().date()
                                else:
                                    expiry_date_value = datetime.now().date()

                                edit_expiry_date = st.date_input(
                                    "Expiry Date", value=expiry_date_value
                                )

                            edit_supplier_name = st.text_input(
                                "Supplier Name",
                                value=current_item.get("supplier_name", ""),
                            )
                            edit_description = st.text_area(
                                "Description", value=current_item.get("description", "")
                            )

                            submitted = st.form_submit_button("💾 Save Changes")

                            if submitted:
                                if edit_drug_name and edit_batch_number:
                                    success = _db.update_inventory_item(
                                        item_id,
                                        edit_drug_name,
                                        edit_category,
                                        edit_manufacturer,
                                        edit_batch_number,
                                        edit_current_stock,
                                        edit_minimum_stock,
                                        edit_per_tablet_price,
                                        calculated_sheet_price,  # Use calculated price
                                        edit_tablets_per_sheet,
                                        edit_expiry_date,
                                        edit_supplier_name,
                                        edit_description,
                                    )
                                    if success:
                                        invalidate_analytics_cache()
                                        st.success("✅ Item updated successfully!")
                                        # Clear session state
                                        for key in [
                                            "edit_per_tablet_price",
                                            "edit_tablets_per_sheet",
                                            "edit_per_sheet_price",
                                        ]:
                                            if key in st.session_state:
                                                del st.session_state[key]
                                        st.rerun()
                                    else:
                                        st.error(
                                            "❌ Failed to update item. Please check if the batch number is unique."
                                        )
                                else:
                                    st.error(
                                        "Please fill in all required fields (marked with *)."
                                    )

                    with col_delete:
                        st.markdown("### Delete Item")
                        st.warning("⚠️ This action cannot be undone!")

                        if st.button(
                            "🗑️ Delete Item", type="primary", key="delete_item_btn"
                        ):
                            if _db.delete_inventory_item(item_id):
                                invalidate_analytics_cache()
                                st.success("Item deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete item.")
        else:
            st.info("No items available to edit.")

    with tab5:
        st.subheader("🔄 Batch Operations")

        operation_type = st.selectbox(
            "Select Batch Operation",
            [
                "Batch Update Prices",
                "Batch Delete Expired Items",
                "Batch Stock Alert Update",
                "Generate Batch Report",
            ],
        )

        if operation_type == "Batch Update Prices":
            st.write("**Update prices for multiple items at once**")

            category_for_update = st.selectbox(
                "Select Category", ["All Categories"] + _db.get_categories()
            )

            price_adjustment = st.radio(
                "Price Adjustment Type",
                ["Percentage Increase", "Percentage Decrease", "Fixed Amount"],
            )

            if price_adjustment in ["Percentage Increase", "Percentage Decrease"]:
                adjustment_value = st.number_input(
                    "Percentage (%)", min_value=0.0, max_value=100.0, value=5.0
                )
            else:
                adjustment_value = st.number_input(
                    "Amount (₹)", min_value=0.0, value=10.0
                )

            if st.button("Preview Changes"):
                items_to_update = _db.get_filtered_inventory(
                    category_for_update, "All", ""
                )
                if not items_to_update.empty:
                    preview_df = items_to_update[
                        ["id", "drug_name", "batch_number", "category", "unit_price"]
                    ].copy()

                    if price_adjustment == "Percentage Increase":
                        preview_df["new_price"] = preview_df["unit_price"] * (
                            1 + adjustment_value / 100
                        )
                    elif price_adjustment == "Percentage Decrease":
                        preview_df["new_price"] = preview_df["unit_price"] * (
                            1 - adjustment_value / 100
                        )
                    else:
                        preview_df["new_price"] = (
                            preview_df["unit_price"] + adjustment_value
                        )

                    preview_df["new_price"] = preview_df["new_price"].round(2)
                    st.dataframe(
                        preview_df[
                            [
                                "drug_name",
                                "batch_number",
                                "category",
                                "unit_price",
                                "new_price",
                            ]
                        ],
                        use_container_width=True,
                    )

                    if st.button("Apply Price Changes"):
                        for _, row in preview_df.iterrows():
                            _db.update_item_price_by_id(row["id"], row["new_price"])
                        st.success(f"Updated prices for {len(preview_df)} items!")
                        st.rerun()
                else:
                    st.info("No items found in selected category.")

        elif operation_type == "Batch Delete Expired Items":
            st.write("**Remove all expired items from inventory**")
            st.warning(
                "⚠️ This action will permanently delete expired items from the database."
            )

            expiring_items = _db.get_expiring_drugs(days_ahead=0)
            if not expiring_items.empty:
                st.write(f"Found {len(expiring_items)} expired items:")
                st.dataframe(expiring_items, use_container_width=True)

                if st.button("Delete All Expired Items", type="primary"):
                    deleted_count = 0
                    for _, item in expiring_items.iterrows():
                        if _db.delete_inventory_item(item["id"]):
                            deleted_count += 1
                    st.success(f"Successfully deleted {deleted_count} expired items!")
                    st.rerun()
            else:
                st.success("✅ No expired items found in inventory.")

        elif operation_type == "Batch Stock Alert Update":
            st.write("**Update minimum stock levels for multiple items**")

            category_for_alert = st.selectbox(
                "Select Category",
                ["All Categories"] + _db.get_categories(),
                key="alert_category",
            )

            new_min_stock = st.number_input(
                "New Minimum Stock Level", min_value=1, value=10
            )

            if st.button("Update Minimum Stock Levels"):
                items_to_update = _db.get_filtered_inventory(
                    category_for_alert, "All", ""
                )
                update_count = 0
                for _, item in items_to_update.iterrows():
                    if _db.update_minimum_stock(item["id"], new_min_stock):
                        update_count += 1
                st.success(f"Updated minimum stock levels for {update_count} items!")
                st.rerun()

        elif operation_type == "Generate Batch Report":
            st.write("**Generate comprehensive inventory report**")

            report_type = st.selectbox(
                "Report Type",
                [
                    "Full Inventory",
                    "Low Stock Items",
                    "High Value Items",
                    "Expiring Soon",
                ],
            )

            if st.button("Generate Report"):
                if report_type == "Full Inventory":
                    report_data = _db.get_inventory()
                elif report_type == "Low Stock Items":
                    report_data = _db.get_filtered_inventory("All", "Low Stock", "")
                elif report_type == "High Value Items":
                    all_items = _db.get_inventory()
                    report_data = all_items[all_items["unit_price"] > 100]
                else:
                    report_data = _db.get_expiring_drugs(days_ahead=30)

                if not report_data.empty:
                    st.dataframe(report_data, use_container_width=True)

                    csv = report_data.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Report",
                        data=csv,
                        file_name=f"{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No data available for selected report type.")



def smart_reordering_page():
    st.title("🤖 Smart Reordering System")

    st.write(
        "AI-powered automatic reordering suggestions based on consumption patterns and forecasts."
    )

    # Auto-reorder recommendations
    st.subheader("📋 Reorder Recommendations")

    # Lazy load AI models if not already loaded
    global reordering
    if reordering is None:
        reordering, _ = init_ai_models()
    reorder_suggestions = reordering.get_reorder_suggestions(_db)

    if reorder_suggestions:
        # Display all items without pagination as requested
        page_items = reorder_suggestions


        st.markdown(
            """
        <div style="max-height: 480px; overflow-y: auto; border: 1px solid #e0e3eb; border-radius: 10px; padding: 8px; margin-bottom: 16px;">
        """,
            unsafe_allow_html=True,
        )
        for suggestion in page_items:
            with st.expander(
                f"🔄 {suggestion['drug_name']} - Priority: {suggestion['priority'].upper()}"
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Current Stock:** {suggestion['current_stock']}")
                    st.write(f"**Minimum Level:** {suggestion['minimum_stock']}")
                    st.write(f"**Suggested Order:** {suggestion['suggested_quantity']}")

                with col2:
                    st.write(
                        f"**Days Until Stockout:** {suggestion['days_until_stockout']}"
                    )
                    st.write(
                        f"**Average Daily Usage:** {suggestion['avg_daily_usage']:.1f}"
                    )
                    st.write(f"**Supplier:** {suggestion['supplier']}")

                with col3:
                    st.write(
                        f"**Estimated Cost:** {format_dual_currency(suggestion['estimated_cost'], 0)}"
                    )
                    st.write(f"**Lead Time:** {suggestion['lead_time']} days")

                st.write(f"**Reason:** {suggestion['reason']}")

                # Action buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(
                        f"✅ Approve Order", key=f"approve_{suggestion['id']}"
                    ):
                        success = _db.create_purchase_order(suggestion)
                        if success:
                            st.success("Purchase order created!")
                        else:
                            st.error("Failed to create purchase order.")

                with col2:
                    if st.button(
                        f"⏰ Snooze (1 day)", key=f"snooze_{suggestion['id']}"
                    ):
                        _db.snooze_reorder_suggestion(suggestion["id"], 1)
                        st.info("Suggestion snoozed for 1 day.")

                with col3:
                    if st.button(f"❌ Dismiss", key=f"dismiss_{suggestion['id']}"):
                        _db.dismiss_reorder_suggestion(suggestion["id"])
                        st.info("Suggestion dismissed.")
        st.markdown(
            """
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.success("No reorder recommendations at this time!")

    # Supplier optimization
    st.subheader("🏪 Supplier Optimization")

    supplier_analysis = reordering.analyze_suppliers(_db)
    if supplier_analysis:
        suppliers_df = pd.DataFrame(supplier_analysis)
        px, _ = lazy_import_plotly()
        fig = px.scatter(
            suppliers_df,
            x="avg_delivery_time",
            y="avg_unit_cost",
            size="reliability_score",
            color="supplier_name",
            title="Supplier Performance Analysis",
            hover_data=["total_orders"],
        )
        fig.update_layout(
            xaxis_title="Average Delivery Time (days)",
            yaxis_title="Average Cost per Unit (₹)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Manual reorder
    st.subheader("📝 Manual Reorder")

    with st.form("manual_reorder"):
        col1, col2 = st.columns(2)

        with col1:
            drugs = _db.get_all_drugs()
            selected_drug = st.selectbox("Select Drug", drugs)
            quantity = st.number_input("Quantity to Order", min_value=1, value=1)

        with col2:
            suppliers = _db.get_suppliers()
            selected_supplier = st.selectbox("Select Supplier", suppliers)
            notes = st.text_area("Notes")

        if st.form_submit_button("Create Manual Order"):
            order_data = {
                "drug_name": selected_drug,
                "quantity": quantity,
                "supplier": selected_supplier,
                "notes": notes,
                "manual": True,
            }

            success = _db.create_purchase_order(order_data)
            if success:
                st.success("Manual purchase order created successfully!")
            else:
                st.error("Failed to create purchase order.")


def expiry_management_page():
    st.title("⏰ Expiry & Wastage Management")

    st.write("AI-powered expiry monitoring and wastage prevention system.")

    # Expiry alerts
    st.subheader("🚨 Expiry Alerts")

    tab1, tab2 = st.tabs(
        ["Expiring Soon", "Wastage Analysis"]
    )

    with tab1:
        expiring_items = _db.get_expiring_items()

        if not expiring_items.empty:
            # Color code by urgency
            def get_urgency_color(days):
                if days <= 7:
                    return "🔴"
                elif days <= 30:
                    return "🟡"
                else:
                    return "🟢"

            expiring_items["urgency"] = expiring_items["days_until_expiry"].apply(
                get_urgency_color
            )

            st.dataframe(expiring_items, use_container_width=True)

            # Bulk actions
            st.subheader("Bulk Actions")
            selected_items = st.multiselect(
                "Select items for bulk action:",
                options=expiring_items["drug_name"].tolist(),
            )

            if selected_items:
                action = st.selectbox(
                    "Action", ["Mark as Used", "Return to Supplier", "Dispose"]
                )

                if st.button(f"Apply {action}"):
                    for item in selected_items:
                        _db.apply_expiry_action(item, action)
                    st.success(f"{action} applied to selected items!")
                    st.rerun()
        else:
            st.success("No items expiring soon!")

    with tab2:
        st.subheader("Wastage Analysis")

        # Time period selection
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date", datetime.now() - timedelta(days=90)
            )
        with col2:
            end_date = st.date_input("End Date", datetime.now())

        wastage_data = _db.get_wastage_analysis(start_date, end_date)

        if not wastage_data.empty:
            px, _ = lazy_import_plotly()
            # Wastage by category
            fig1 = px.bar(
                wastage_data,
                x="category",
                y="wasted_value",
                title="Wastage by Category",
                color="category",
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Top wasted drugs
            fig2 = px.pie(
                wastage_data.head(10),
                values="wasted_quantity",
                names="drug_name",
                title="Top 10 Wasted Drugs by Quantity",
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Wastage trends
            wastage_trends = _db.get_wastage_trends(start_date, end_date)
            if not wastage_trends.empty:
                fig3 = px.line(
                    wastage_trends,
                    x="date",
                    y="daily_wastage",
                    title="Daily Wastage Trend",
                )
                st.plotly_chart(fig3, use_container_width=True)

            # Summary metrics
            total_wastage = wastage_data["wasted_value"].sum()
            total_quantity = wastage_data["wasted_quantity"].sum()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Wastage Value", format_currency(total_wastage))
            with col2:
                st.metric("Total Wastage Quantity", f"{total_quantity:.0f} units")
            with col3:
                avg_daily_wastage = total_wastage / ((end_date - start_date).days + 1)
                st.metric("Avg Daily Wastage", format_currency(avg_daily_wastage))
        else:
            st.info("No wastage data found for the selected period.")


def analytics_page():
    st.title("📈 Analytics & Reports")

    st.write(
        "Comprehensive analytics and insights for pharmaceutical inventory management."
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        available_years = list(range(2020, datetime.now().year + 1))
        selected_year = st.selectbox(
            "📅 Filter by Year", ["All Years"] + available_years, key="analytics_year"
        )
    with col2:
        if selected_year != "All Years":
            selected_month = st.selectbox(
                "📆 Filter by Month",
                ["All Months"] + list(range(1, 13)),
                key="analytics_month",
            )
        else:
            selected_month = "All Months"
    with col3:
        st.write("")

    if selected_year != "All Years":
        if selected_month != "All Months":
            start_date = datetime(int(selected_year), int(selected_month), 1)
            if int(selected_month) == 12:
                end_date = datetime(int(selected_year) + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(
                    int(selected_year), int(selected_month) + 1, 1
                ) - timedelta(days=1)
        else:
            start_date = datetime(int(selected_year), 1, 1)
            end_date = datetime(int(selected_year), 12, 31)
    else:
        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Consumption Analytics",
            "Financial Reports",
            "Supplier Performance",
            "Predictive Analytics",
        ]
    )

    with tab1:
        st.subheader("📊 Consumption Analytics")

        col_period1, col_period2, col_export = st.columns([2, 2, 1])
        with col_period1:
            custom_start_date = st.date_input(
                "Custom Start Date",
                start_date,
                key="consumption_start",
            )
        with col_period2:
            custom_end_date = st.date_input(
                "Custom End Date", end_date, key="consumption_end"
            )

        start_date = custom_start_date
        end_date = custom_end_date

        consumption_data = _db.get_consumption_analytics(start_date, end_date)

        if not consumption_data.empty:
            with col_export:
                st.write("")
                st.write("")
                excel_data = consumption_data.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Export to Excel",
                    data=excel_data,
                    file_name=f"consumption_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )

            px, _ = lazy_import_plotly()
            # Top consumed drugs
            fig1 = px.bar(
                consumption_data.head(15),
                x="drug_name",
                y="total_consumed",
                title=f"Top 15 Consumed Drugs ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
                color="total_consumed",
                color_continuous_scale="Blues",
            )
            fig1.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig1, use_container_width=True)

            # Consumption by category
            category_consumption = (
                consumption_data.groupby("category")["total_consumed"]
                .sum()
                .reset_index()
            )
            fig2 = px.pie(
                category_consumption,
                values="total_consumed",
                names="category",
                title="Consumption by Drug Category",
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Daily consumption trends
            daily_trends = _db.get_daily_consumption_trends(start_date, end_date)
            if not daily_trends.empty:
                fig3 = px.line(
                    daily_trends,
                    x="date",
                    y="daily_consumption",
                    title="Daily Consumption Trends",
                )
                st.plotly_chart(fig3, use_container_width=True)

            # Department-wise consumption (if department data available)
            dept_consumption = _db.get_department_consumption(start_date, end_date)
            if not dept_consumption.empty:
                fig4 = px.treemap(
                    dept_consumption,
                    path=["department"],
                    values="consumption",
                    title="Consumption by Department",
                )
                st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No consumption data available for the selected period.")

    with tab2:
        st.subheader("💰 Financial Reports")

        # Financial overview
        financial_data = _db.get_financial_overview()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Total Inventory Value",
                format_dual_currency(financial_data["total_value"], 0),
            )
        with col2:
            st.metric(
                "Monthly Spend",
                format_dual_currency(financial_data["monthly_spend"], 0),
            )
        with col3:
            st.metric(
                "Cost Savings", format_dual_currency(financial_data["cost_savings"], 0)
            )
        with col4:
            st.metric("ROI", f"{financial_data['roi']:.1%}")

        # Cost analysis
        cost_data = _db.get_cost_analysis()
        if not cost_data.empty:
            px, go = lazy_import_plotly()
            # Cost by category
            fig1 = px.bar(
                cost_data,
                x="category",
                y="total_cost",
                title="Cost by Drug Category",
                color="total_cost",
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Cost trends
            cost_trends = _db.get_cost_trends()
            if not cost_trends.empty:
                fig2 = px.line(
                    cost_trends,
                    x="month",
                    y="monthly_cost",
                    title="Monthly Cost Trends",
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Budget vs actual
        budget_data = _db.get_budget_analysis()
        if budget_data:
            fig3 = go.Figure()

            categories = list(budget_data.keys())
            budgeted = [budget_data[cat]["budgeted"] for cat in categories]
            actual = [budget_data[cat]["actual"] for cat in categories]

            fig3.add_trace(go.Bar(name="Budgeted", x=categories, y=budgeted))
            fig3.add_trace(go.Bar(name="Actual", x=categories, y=actual))

            fig3.update_layout(
                title="Budget vs Actual Spending",
                barmode="group",
                yaxis_title="Amount (₹)",
            )
            st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.subheader("🏪 Supplier Performance Analysis")

        supplier_metrics = _db.get_supplier_metrics()

        if not supplier_metrics.empty:
            px, _ = lazy_import_plotly()
            # Supplier scorecard
            fig1 = px.scatter(
                supplier_metrics,
                x="avg_delivery_time",
                y="quality_score",
                size="total_orders",
                color="cost_rating",
                hover_name="supplier_name",
                title="Supplier Performance Matrix",
                labels={
                    "avg_delivery_time": "Average Delivery Time (days)",
                    "quality_score": "Quality Score (/10)",
                },
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Delivery performance
            fig2 = px.bar(
                supplier_metrics,
                x="supplier_name",
                y="on_time_delivery_rate",
                title="On-Time Delivery Rate by Supplier",
                color="on_time_delivery_rate",
                color_continuous_scale="RdYlGn",
            )
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

            # Cost comparison
            fig3 = px.box(
                supplier_metrics,
                y="avg_unit_cost",
                x="supplier_name",
                title="Cost Distribution by Supplier",
            )
            fig3.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig3, use_container_width=True)

            # Supplier recommendations
            st.subheader("🎯 Supplier Recommendations")
            recommendations = _db.get_supplier_recommendations()
            for rec in recommendations:
                if rec["type"] == "best_performer":
                    st.success(
                        f"⭐ **Best Performer**: {rec['supplier']} - {rec['reason']}"
                    )
                elif rec["type"] == "needs_improvement":
                    st.warning(
                        f"⚠️ **Needs Improvement**: {rec['supplier']} - {rec['reason']}"
                    )
                elif rec["type"] == "cost_optimization":
                    st.info(f"💰 **Cost Optimization**: {rec['message']}")
        else:
            st.info("No supplier performance data available.")

    with tab4:
        st.subheader("🔮 Predictive Analytics")

        # Anomaly detection
        st.write("**Anomaly Detection Results**")
        anomalies = _db.detect_anomalies()

        if anomalies:
            for anomaly in anomalies:
                severity = anomaly["severity"].lower()
                if severity == "high":
                    st.error(f"🔴 **High Priority**: {anomaly['description']}")
                elif severity == "medium":
                    st.warning(f"🟡 **Medium Priority**: {anomaly['description']}")
                else:
                    st.info(f"🔵 **Low Priority**: {anomaly['description']}")
        else:
            st.success("✅ No anomalies detected in recent data.")

        # Predictive insights
        st.write("**Predictive Insights**")
        insights = _db.get_predictive_insights()

        for insight in insights:
            with st.expander(f"📊 {insight['title']}"):
                st.write(insight["description"])

                if (
                    insight.get("chart_data") is not None
                    and not insight["chart_data"].empty
                ):
                    px, _ = lazy_import_plotly()
                    # Create chart based on insight type
                    if insight["chart_type"] == "line":
                        fig = px.line(
                            insight["chart_data"], x="x", y="y", title=insight["title"]
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    elif insight["chart_type"] == "bar":
                        fig = px.bar(
                            insight["chart_data"], x="x", y="y", title=insight["title"]
                        )
                        st.plotly_chart(fig, use_container_width=True)

                if insight.get("recommendations"):
                    st.write("**Recommendations:**")
                    for rec in insight["recommendations"]:
                        st.write(f"• {rec}")


def settings_page():
    st.title("⚙️ Settings & Configuration")

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "General Settings",
            "Alert Configuration",
            "Data Management",
            "AI Model Settings",
        ]
    )

    with tab1:
        st.subheader("General Settings")

        with st.form("general_settings"):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Inventory Settings**")
                default_min_stock = st.number_input(
                    "Default Minimum Stock Level", min_value=0, value=10
                )
                low_stock_threshold = st.number_input(
                    "Low Stock Alert Threshold", min_value=0, value=20
                )
                auto_reorder = st.checkbox("Enable Auto-Reordering", value=True)

            with col2:
                st.write("**System Settings**")
                currency = st.selectbox("Currency", ["₹ (Rupees)"])
                date_format = st.selectbox(
                    "Date Format", ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]
                )
                timezone = st.selectbox("Timezone", ["UTC", "EST", "PST", "GMT"])

                # Currency converter removed - INR only

            if st.form_submit_button("Save General Settings"):
                settings = {
                    "default_min_stock": default_min_stock,
                    "low_stock_threshold": low_stock_threshold,
                    "auto_reorder": auto_reorder,
                    "currency": currency,
                    "date_format": date_format,
                    "timezone": timezone,
                }
                _db.update_settings(settings)
                st.success("Settings saved successfully!")

    with tab2:
        st.subheader("Alert Configuration")

        with st.form("alert_settings"):
            st.write("**Expiry Alerts**")
            expiry_warning_days = st.slider("Days before expiry to alert", 1, 90, 30)
            expiry_critical_days = st.slider(
                "Days before expiry for critical alert", 1, 30, 7
            )

            st.write("**Stock Alerts**")
            stock_alert_threshold = st.slider(
                "Stock level percentage for alerts", 1, 50, 20
            )

            st.write("**Financial Alerts**")
            budget_alert_threshold = st.slider(
                "Budget usage percentage for alerts", 50, 100, 80
            )

            if st.form_submit_button("Save Alert Settings"):
                alert_settings = {
                    "expiry_warning_days": expiry_warning_days,
                    "expiry_critical_days": expiry_critical_days,
                    "stock_alert_threshold": stock_alert_threshold,
                    "budget_alert_threshold": budget_alert_threshold,
                }
                _db.update_alert_settings(alert_settings)
                st.success("Alert settings saved successfully!")

    with tab3:
        st.subheader("Data Management")

        st.write("**Export Data**")
        export_format = st.selectbox("Export Format", ["CSV", "Excel", "JSON"])
        export_data_type = st.selectbox(
            "Data Type",
            ["All Data", "Inventory Only", "Transactions Only", "Reports Only"],
        )

        if st.button("Export Data"):
            if export_data_type == "All Data":
                data = _db.export_all_data()
            elif export_data_type == "Inventory Only":
                data = _db.export_inventory_data()
            elif export_data_type == "Transactions Only":
                data = _db.export_transaction_data()
            else:
                data = _db.export_report_data()

            if export_format == "CSV":
                st.download_button(
                    label="📥 Download CSV",
                    data=data.to_csv(index=False),
                    file_name=f"pharma_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
            elif export_format == "JSON":
                st.download_button(
                    label="📥 Download JSON",
                    data=data.to_json(orient="records"),
                    file_name=f"pharma_data_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                )

        # Database maintenance
        st.write("**Database Maintenance**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🧹 Clean Old Data"):
                cleaned_records = _db.clean_old_data()
                st.success(f"Cleaned {cleaned_records} old records!")

        with col2:
            if st.button("📊 Optimize Database"):
                _db.optimize_database()
                st.success("Database optimized!")

        with col3:
            if st.button("💾 Backup Database"):
                backup_file = _db.backup_database()
                st.success(f"Database backed up to: {backup_file}")

    with tab4:
        st.subheader("AI Model Settings")

        with st.form("ai_settings"):
            st.write("**Forecasting Models**")
            default_forecast_model = st.selectbox(
                "Default Forecasting Model",
                ["Random Forest", "Linear Regression", "ARIMA"],
            )
            forecast_accuracy_threshold = st.slider(
                "Minimum Accuracy Threshold", 0.1, 1.0, 0.7
            )

            st.write("**Reordering AI**")
            reorder_safety_factor = st.slider("Safety Stock Factor", 1.0, 3.0, 1.5)
            lead_time_variance = st.slider("Lead Time Variance Factor", 0.1, 1.0, 0.2)

            st.write("**Anomaly Detection**")
            anomaly_sensitivity = st.slider(
                "Anomaly Detection Sensitivity", 0.1, 1.0, 0.5
            )

            if st.form_submit_button("Save AI Settings"):
                ai_settings = {
                    "default_forecast_model": default_forecast_model,
                    "forecast_accuracy_threshold": forecast_accuracy_threshold,
                    "reorder_safety_factor": reorder_safety_factor,
                    "lead_time_variance": lead_time_variance,
                    "anomaly_sensitivity": anomaly_sensitivity,
                }
                _db.update_ai_settings(ai_settings)
                st.success("AI settings saved successfully!")

        # Model performance monitoring
        st.subheader("Model Performance Monitoring")

        model_performance = _db.get_model_performance()
        if model_performance:
            px, _ = lazy_import_plotly()
            performance_df = pd.DataFrame(model_performance)

            fig = px.bar(
                performance_df,
                x="model_name",
                y="accuracy",
                title="AI Model Performance",
                color="accuracy",
                color_continuous_scale="RdYlGn",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Model recommendations
            st.write("**Model Recommendations:**")
            for model in model_performance:
                if model["accuracy"] < 0.7:
                    st.warning(
                        f"⚠️ {model['model_name']} accuracy is below threshold. Consider retraining."
                    )
                else:
                    st.success(f"✅ {model['model_name']} is performing well.")


def wastage_analysis_page():
    """Advanced wastage analysis and prevention"""
    st.title("💡 Wastage Analysis & Prevention")
    st.write(
        "Comprehensive analysis of drug wastage with AI-powered prevention recommendations"
    )

    _, WastageAnalyzer, _, _, _ = lazy_import_analytics()
    analyzer = WastageAnalyzer(_db)

    # Current Wastage Summary
    st.subheader("📊 Current Wastage Summary")
    wastage_data = analyzer.calculate_wastage()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Wastage Value",
            format_dual_currency(wastage_data["total_wastage_value"], 0),
            help="Total value of expired inventory",
        )
    with col2:
        st.metric(
            "Total Wastage Units",
            f"{wastage_data['total_wastage_units']:,}",
            help="Total units of expired drugs",
        )
    with col3:
        wastage_percent = (
            wastage_data["total_wastage_value"]
            / max(_db.get_total_inventory_value(), 1)
        ) * 100
        st.metric(
            "Wastage Percentage",
            f"{wastage_percent:.2f}%",
            help="Percentage of total inventory value wasted",
        )

    # Wastage by Category
    if wastage_data["wastage_by_category"]:
        px, _ = lazy_import_plotly()
        st.subheader("📈 Wastage by Category")
        category_df = pd.DataFrame.from_dict(
            wastage_data["wastage_by_category"], orient="index"
        ).reset_index()
        category_df.columns = ["Category", "Value", "Units"]

        fig = px.bar(
            category_df,
            x="Category",
            y="Value",
            title="Wastage Value by Category",
            color="Value",
            color_continuous_scale="Reds",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Potential Future Wastage
    st.subheader("⚠️ Potential Future Wastage (Next 90 Days)")
    potential_wastage = analyzer.predict_potential_wastage(90)

    if potential_wastage:
        total_potential_loss = sum(
            item.get("potential_wastage_value", 0) for item in potential_wastage
        )
        st.warning(
            f"**Potential Loss:** {format_dual_currency(total_potential_loss, 0)}"
        )

        wastage_df = pd.DataFrame(potential_wastage)
        st.dataframe(
            wastage_df[
                [
                    "drug_name",
                    "category",
                    "days_to_expiry",
                    "current_stock",
                    "wastage_risk",
                    "potential_wastage_value",
                ]
            ].head(20),
            use_container_width=True,
        )
    else:
        st.success("✅ No significant wastage risk identified for the next 90 days!")

    # Prevention Recommendations
    st.subheader("💡 Wastage Prevention Recommendations")
    recommendations = analyzer.get_wastage_prevention_recommendations()

    if recommendations:
        for rec in recommendations:
            if rec["priority"] == "High":
                st.error(
                    f"🔴 **{rec['drug_name']}**: {rec['action']}\n\n{rec['reason']}\n\nPotential Loss: {rec['potential_loss']}"
                )
            else:
                st.warning(
                    f"🟡 **{rec['drug_name']}**: {rec['action']}\n\n{rec['reason']}\n\nPotential Loss: {rec['potential_loss']}"
                )
    else:
        st.info("No specific recommendations at this time.")


def cost_optimization_page():
    """Cost optimization and savings opportunities"""
    st.title("💰 Cost Optimization Engine")
    st.write("AI-powered cost savings opportunities and inventory optimization")

    _, _, CostOptimizer, _, _ = lazy_import_analytics()
    optimizer = CostOptimizer(_db)

    # Cost Savings Overview
    st.subheader("💵 Cost Savings Opportunities")
    opportunities = optimizer.identify_cost_saving_opportunities()

    if opportunities:
        total_potential_savings = sum(opp["potential_savings"] for opp in opportunities)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Potential Savings",
                format_dual_currency(total_potential_savings, 0),
            )
        with col2:
            st.metric("Number of Opportunities", len(opportunities))
        with col3:
            high_priority = sum(1 for opp in opportunities if opp["priority"] == "High")
            st.metric("High Priority Items", high_priority)

        # Opportunities by Type
        st.subheader("📊 Opportunities Breakdown")
        px, _ = lazy_import_plotly()
        opp_df = pd.DataFrame(opportunities)

        fig = px.bar(
            opp_df.groupby("type")["potential_savings"].sum().reset_index(),
            x="type",
            y="potential_savings",
            title="Savings by Opportunity Type",
            color="potential_savings",
            color_continuous_scale="Greens",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed Opportunities
        st.subheader("🔍 Detailed Opportunities")
        for opp in opportunities[:15]:
            priority_color = "🔴" if opp["priority"] == "High" else "🟡"
            with st.expander(
                f"{priority_color} {opp['type']}: {opp['drug_name']} - Potential Savings: {format_dual_currency(opp['potential_savings'], 0)}"
            ):
                st.write(f"**Issue:** {opp['issue']}")
                st.write(f"**Recommendation:** {opp['recommendation']}")
                st.write(f"**Priority:** {opp['priority']}")
    else:
        st.success(
            "✅ No major cost optimization opportunities identified. Your inventory is well-optimized!"
        )

def drug_utilization_review_page():
    """Drug utilization review and analysis"""
    st.title("📊 Drug Utilization Review (DUR)")
    st.write("Comprehensive analysis of drug usage patterns and utilization rates")

    _, _, _, DrugUtilizationReview, _ = lazy_import_analytics()
    dur = DrugUtilizationReview(_db)

    # Utilization Analysis
    st.subheader("📈 Utilization Analysis (Last 90 Days)")
    utilization = dur.analyze_utilization()

    tab1, tab2, tab3 = st.tabs(
        ["High Utilization", "Low Utilization", "Moderate Utilization"]
    )

    with tab1:
        st.write("### High Utilization Drugs")
        st.write(
            "These drugs are heavily used and require close monitoring for stock levels"
        )

        if utilization["high_utilization"]:
            high_df = pd.DataFrame(utilization["high_utilization"])
            st.dataframe(
                high_df[
                    [
                        "drug_name",
                        "category",
                        "total_consumed",
                        "avg_daily_usage",
                        "departments_using",
                    ]
                ].head(15),
                use_container_width=True,
            )

            # Chart
            px, _ = lazy_import_plotly()
            fig = px.bar(
                high_df.head(10),
                x="drug_name",
                y="total_consumed",
                title="Top 10 High Utilization Drugs",
                color="category",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No high utilization drugs identified.")

    with tab2:
        st.write("### Low Utilization Drugs")
        st.write(
            "These drugs have low usage - consider reducing stock levels or discontinuing"
        )

        if utilization["low_utilization"]:
            low_df = pd.DataFrame(utilization["low_utilization"])
            st.dataframe(
                low_df[
                    [
                        "drug_name",
                        "category",
                        "total_consumed",
                        "avg_daily_usage",
                        "departments_using",
                    ]
                ].head(15),
                use_container_width=True,
            )

            st.warning(
                "💡 **Recommendation:** Review these drugs for potential stock reduction or discontinuation"
            )
        else:
            st.info("No low utilization drugs identified.")

    with tab3:
        st.write("### Moderate Utilization Drugs")
        st.write("These drugs have steady, moderate usage")

        if utilization["moderate_utilization"]:
            mod_df = pd.DataFrame(utilization["moderate_utilization"])
            st.dataframe(
                mod_df[
                    [
                        "drug_name",
                        "category",
                        "total_consumed",
                        "avg_daily_usage",
                        "departments_using",
                    ]
                ].head(15),
                use_container_width=True,
            )
        else:
            st.info("No moderate utilization drugs identified.")

    # Department Utilization
    st.subheader("🏥 Department Utilization Analysis")
    dept_util = dur.get_department_utilization()

    if dept_util:
        px, _ = lazy_import_plotly()
        dept_df = pd.DataFrame(dept_util)

        # Department comparison
        fig = px.treemap(
            dept_df,
            path=["department", "category"],
            values="total_consumed",
            title="Drug Consumption by Department and Category",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Top departments
        top_depts = (
            dept_df.groupby("department")["total_consumed"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        fig2 = px.bar(top_depts, x="department", y="total_consumed", title="Top 10 Departments by Drug Consumption")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No department utilization data available.")


def anomaly_monitor_page():
    """Real-time anomaly monitoring dashboard with auto-detection"""
    st.markdown(
        """
    <div class="main-header">
        <h1>🚨 Real-Time Anomaly Monitor</h1>
        <p>AI-powered consumption anomaly detection and alerting system</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    AdvancedAnalytics, _, _, _, _ = lazy_import_analytics()
    analytics = AdvancedAnalytics(_db)

    with st.spinner("🔍 Scanning for anomalies..."):
        anomaly_summary = analytics.get_anomaly_summary()
        anomalies = anomaly_summary.get("recent_anomalies", [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;">
            <h2 style="margin: 0; font-size: 2.5rem;">{anomaly_summary["total_anomalies"]}</h2>
            <p style="margin: 0;">Total Anomalies</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;">
            <h2 style="margin: 0; font-size: 2.5rem;">{anomaly_summary["high_severity"]}</h2>
            <p style="margin: 0;">High Severity</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;">
            <h2 style="margin: 0; font-size: 2.5rem;">{anomaly_summary["medium_severity"]}</h2>
            <p style="margin: 0;">Medium Severity</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
        <div style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center;">
            <h2 style="margin: 0; font-size: 2.5rem;">{anomaly_summary["low_severity"]}</h2>
            <p style="margin: 0;">Low Severity</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if anomalies and len(anomalies) > 0:
        px, _ = lazy_import_plotly()
        st.subheader("📊 Anomaly Visualizations")

        anomaly_df = pd.DataFrame(anomalies)

        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.scatter(
                anomaly_df,
                x="date",
                y="consumption",
                color="type",
                size="severity_score",
                hover_data=["drug_name", "expected", "confidence"],
                title="Consumption Anomalies Timeline",
                color_discrete_map={
                    "High Consumption": "#f5576c",
                    "Low Consumption": "#4facfe",
                },
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            severity_counts = (
                anomaly_df.groupby(["type", "confidence"])
                .size()
                .reset_index(name="count")
            )
            fig2 = px.bar(
                severity_counts,
                x="confidence",
                y="count",
                color="type",
                title="Anomalies by Confidence Level",
                barmode="group",
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)

        category_counts = anomaly_df["category"].value_counts().reset_index()
        category_counts.columns = ["category", "count"]
        fig3 = px.pie(
            category_counts,
            values="count",
            names="category",
            title="Anomalies by Drug Category",
            hole=0.4,
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("🔍 Detailed Anomaly Report")

        severity_filter = st.selectbox(
            "Filter by Severity", ["All", "High (70+)", "Medium (40-70)", "Low (<40)"]
        )

        if severity_filter == "High (70+)":
            filtered_anomalies = [a for a in anomalies if a["severity_score"] >= 70]
        elif severity_filter == "Medium (40-70)":
            filtered_anomalies = [
                a for a in anomalies if 40 <= a["severity_score"] < 70
            ]
        elif severity_filter == "Low (<40)":
            filtered_anomalies = [a for a in anomalies if a["severity_score"] < 40]
        else:
            filtered_anomalies = anomalies

        for idx, anomaly in enumerate(filtered_anomalies[:15]):
            severity = anomaly["severity_score"]

            if severity >= 70:
                color = "#f8d7da"
                border_color = "#dc3545"
                icon = "🔴"
            elif severity >= 40:
                color = "#fff3cd"
                border_color = "#ffc107"
                icon = "🟡"
            else:
                color = "#d1ecf1"
                border_color = "#17a2b8"
                icon = "🔵"

            st.markdown(
                f"""
            <div style="background: {color}; padding: 1rem; border-radius: 8px; border-left: 4px solid {border_color}; margin: 0.5rem 0;">
                <strong>{icon} {anomaly["drug_name"]}</strong> - {anomaly["category"]}<br/>
                <small>Date: {anomaly["date"]} | Method: {anomaly["detection_method"]} | Confidence: {anomaly["confidence"]}</small><br/>
                <strong>Consumption:</strong> {anomaly["consumption"]} units (Expected: ~{anomaly["expected"]} units)<br/>
                <strong>Deviation:</strong> {abs(anomaly["deviation"]):.2f}σ | <strong>Type:</strong> {anomaly["type"]}<br/>
                <strong>Severity Score:</strong> {severity:.1f}/100
            </div>
            """,
                unsafe_allow_html=True,
            )

        if st.button("📥 Export Anomaly Report"):
            csv = anomaly_df.to_csv(index=False)
            st.download_button(
                label="Download CSV Report",
                data=csv,
                file_name=f"anomaly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
    else:
        st.success(
            "✅ No significant anomalies detected! Your inventory consumption patterns are normal."
        )
        st.balloons()

    st.markdown("---")

    _, _, _, _, AutomatedInsightsGenerator = lazy_import_analytics()
    insights_gen = AutomatedInsightsGenerator(_db)
    daily_insights = insights_gen.generate_daily_insights()

    if daily_insights:
        st.subheader("💡 Automated Insights")
        for insight in daily_insights:
            if insight["priority"] == "high":
                st.error(
                    f"**{insight['title']}**\n\n{insight['description']}\n\n💡 **Recommendation:** {insight['recommendation']}"
                )
            elif insight["priority"] == "medium":
                st.warning(
                    f"**{insight['title']}**\n\n{insight['description']}\n\n💡 **Recommendation:** {insight['recommendation']}"
                )
            else:
                st.info(
                    f"**{insight['title']}**\n\n{insight['description']}\n\n💡 **Recommendation:** {insight['recommendation']}"
                )


def drug_correlations_page():
    """Drug correlation analysis and network visualization"""
    st.title("🔗 Drug Correlation Analysis")
    st.write("Discover relationships between drug consumption patterns")

    AdvancedAnalytics, _, _, _, _ = lazy_import_analytics()
    analytics = AdvancedAnalytics(_db)

    # Drug Selection Filter
    all_drugs = _db.get_all_drug_names()
    selected_drugs = st.multiselect(
        "🎯 Select Drugs to Analyze",
        options=all_drugs,
        default=all_drugs[:10] if len(all_drugs) >= 10 else all_drugs,
        help="Select at least 2 drugs to analyze correlations between them",
    )

    with st.spinner("Analyzing drug correlations..."):
        correlation_data = analytics.analyze_drug_correlations(selected_drugs=selected_drugs)

    correlations = correlation_data.get("correlations", [])

    if correlations:
        px, _ = lazy_import_plotly()
        st.success(f"Found {len(correlations)} strong correlations")

        corr_df = pd.DataFrame(correlations)

        fig1 = px.scatter(
            corr_df,
            x=list(range(len(corr_df))),
            y="correlation",
            color="relationship",
            hover_data=["drug1", "drug2"],
            title="Drug Consumption Correlations",
            labels={"x": "Correlation Pair", "y": "Correlation Coefficient"},
        )
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("🔍 Strong Correlations Details")

        for idx, corr in enumerate(correlations[:15]):
            relationship_color = (
                "#d4edda" if corr["relationship"] == "Positive" else "#f8d7da"
            )
            relationship_icon = "📈" if corr["relationship"] == "Positive" else "📉"

            st.markdown(
                f"""
            <div style="background: {relationship_color}; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>{relationship_icon} {corr["drug1"]}</strong> ↔️ <strong>{corr["drug2"]}</strong><br/>
                <strong>Correlation:</strong> {corr["correlation"]:.3f} | <strong>Type:</strong> {corr["relationship"]}<br/>
                <small>These drugs show {corr["relationship"].lower()} consumption patterns - they tend to be used {"together" if corr["relationship"] == "Positive" else "inversely"}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if st.button("📥 Export Correlation Data"):
            csv = corr_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"drug_correlations_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
    else:
        st.info(
            "🔎 **No strong correlations found for the selected drugs.**\n\n"
            "This indicates that the consumption patterns of these drugs are independent of each other.\n"
            "**Try selecting different drugs or adding more items to the selection to find relationships.**"
        )


def advanced_predictive_analytics_page():
    """Advanced predictive analytics with ML"""
    st.title("🔮 Advanced Predictive Analytics")
    st.write("Machine learning-powered insights and predictions")

    AdvancedAnalytics, _, _, _, _ = lazy_import_analytics()
    analytics = AdvancedAnalytics(_db)

    # Consumption Pattern Analysis
    st.subheader("📊 Consumption Pattern Analysis")

    col1, col2 = st.columns([2, 1])
    with col1:
        analysis_period = st.slider("Analysis Period (Days)", 30, 180, 90)
    with col2:
        st.write("")

    if st.button("Analyze Patterns"):
        with st.spinner("Analyzing consumption patterns..."):
            trends = analytics.analyze_consumption_patterns(analysis_period)

            if trends:
                st.success(f"Analyzed {len(trends)} drugs")

                # Trend Summary
                increasing = sum(
                    1 for t in trends.values() if t["trend"] == "Increasing"
                )
                decreasing = sum(
                    1 for t in trends.values() if t["trend"] == "Decreasing"
                )
                stable = sum(1 for t in trends.values() if t["trend"] == "Stable")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "📈 Increasing Demand",
                        increasing,
                        help="Drugs with increasing consumption",
                    )
                with col2:
                    st.metric(
                        "📉 Decreasing Demand",
                        decreasing,
                        help="Drugs with decreasing consumption",
                    )
                with col3:
                    st.metric(
                        "➡️ Stable Demand", stable, help="Drugs with stable consumption"
                    )

                # Detailed Trends
                trend_df = pd.DataFrame.from_dict(trends, orient="index").reset_index()
                trend_df.columns = [
                    "Drug",
                    "Trend",
                    "Slope",
                    "R²",
                    "Avg Consumption",
                    "Std Dev",
                    "Category",
                ]

                # Filter options
                trend_filter = st.selectbox(
                    "Filter by Trend", ["All", "Increasing", "Decreasing", "Stable"]
                )

                if trend_filter != "All":
                    filtered_df = trend_df[trend_df["Trend"] == trend_filter]
                else:
                    filtered_df = trend_df

                st.dataframe(filtered_df.head(20), use_container_width=True)
            else:
                st.warning("Insufficient data for pattern analysis.")

    # Anomaly Detection - Auto-loading
    st.subheader("🚨 Quick Anomaly Check")
    st.write("Real-time anomaly detection using ensemble ML algorithms")

    col1, col2 = st.columns([3, 1])
    with col1:
        auto_detect = st.checkbox("Auto-detect on load", value=True)
    with col2:
        manual_detect = st.button("🔍 Detect Now")

    if auto_detect or manual_detect:
        with st.spinner("Detecting anomalies using ML ensemble..."):
            anomalies = analytics.detect_anomalies(threshold=2.5, use_ensemble=True)

            if anomalies:
                px, _ = lazy_import_plotly()
                st.warning(
                    f"⚠️ Detected {len(anomalies)} anomalies using advanced ML algorithms"
                )

                anomaly_df = pd.DataFrame(anomalies)

                fig = px.scatter(
                    anomaly_df,
                    x="date",
                    y="consumption",
                    color="type",
                    size="severity_score",
                    hover_data=[
                        "drug_name",
                        "expected",
                        "confidence",
                        "detection_method",
                    ],
                    title="Consumption Anomalies Over Time (ML-Detected)",
                    color_discrete_map={
                        "High Consumption": "#ff6b6b",
                        "Low Consumption": "#4ecdc4",
                    },
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

                st.write("### Top 10 Critical Anomalies")
                for anomaly in anomalies[:10]:
                    severity = anomaly.get("severity_score", 0)
                    if severity >= 70:
                        icon = "🔴"
                        alert_type = "High Priority"
                    elif severity >= 40:
                        icon = "🟡"
                        alert_type = "Medium Priority"
                    else:
                        icon = "🔵"
                        alert_type = "Low Priority"

                    st.write(
                        f"{icon} **{alert_type}** - {anomaly['drug_name']} ({anomaly['category']}) on {anomaly['date']}"
                    )
                    st.write(
                        f"  • Consumed: {anomaly['consumption']} (Expected: ~{anomaly['expected']})"
                    )
                    st.write(
                        f"  • Deviation: {abs(anomaly['deviation']):.2f}σ | Severity: {severity:.1f}/100 | Confidence: {anomaly.get('confidence', 'N/A')}"
                    )
                    st.write(
                        f"  • Detection: {anomaly.get('detection_method', 'Ensemble ML')}"
                    )

                st.info(
                    "💡 **Tip:** Visit the '🚨 Anomaly Monitor' page for detailed analysis and real-time monitoring"
                )
            else:
                st.success(
                    "✅ No significant anomalies detected! Consumption patterns are normal."
                )

    # Demand Clustering
    st.subheader("🔬 Demand Clustering Analysis")
    st.write("Group drugs by similar demand patterns using machine learning")

    n_clusters = st.slider("Number of Clusters", 3, 8, 5)

    if st.button("Cluster Drugs"):
        with st.spinner("Clustering drugs by demand patterns..."):
            clusters = analytics.cluster_drugs_by_demand(n_clusters)

            if clusters:
                st.success(f"Drugs clustered into {len(clusters)} groups")

                for cluster_name, cluster_data in clusters.items():
                    with st.expander(
                        f"{cluster_name} - {cluster_data['description']} ({cluster_data['count']} drugs)"
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "Avg Consumption",
                                f"{cluster_data['avg_consumption']:.1f}",
                            )
                        with col2:
                            st.metric(
                                "Total Consumption",
                                f"{cluster_data['total_consumption']:,.0f}",
                            )

                        st.write("**Sample Drugs:**")
                        for drug in cluster_data["drugs"][:10]:
                            st.write(f"• {drug}")
            else:
                st.warning("Insufficient data for clustering analysis.")

    # Seasonal Analysis
    st.subheader("🌡️ Seasonal Pattern Analysis")
    st.write("Identify drugs with seasonal demand variations")

    if st.button("Analyze Seasonal Patterns"):
        with st.spinner("Analyzing seasonal patterns..."):
            seasonal_drugs = analytics.calculate_seasonal_indices()

            if seasonal_drugs:
                st.success(f"Found {len(seasonal_drugs)} drugs with seasonal patterns")

                seasonal_df = pd.DataFrame.from_dict(
                    seasonal_drugs, orient="index"
                ).reset_index()
                seasonal_df.columns = [
                    "Drug",
                    "Peak Month",
                    "Peak Index",
                    "Low Month",
                    "Low Index",
                    "Seasonality",
                    "Category",
                ]

                # Month names
                month_names = {
                    1: "Jan",
                    2: "Feb",
                    3: "Mar",
                    4: "Apr",
                    5: "May",
                    6: "Jun",
                    7: "Jul",
                    8: "Aug",
                    9: "Sep",
                    10: "Oct",
                    11: "Nov",
                    12: "Dec",
                }
                seasonal_df["Peak Month"] = seasonal_df["Peak Month"].map(month_names)
                seasonal_df["Low Month"] = seasonal_df["Low Month"].map(month_names)

                st.dataframe(seasonal_df.head(20), use_container_width=True)

                # Seasonal heatmap
                st.write("**Seasonal Variation:**")
                for _, row in seasonal_df.head(10).iterrows():
                    st.write(
                        f"**{row['Drug']}**: Peaks in {row['Peak Month']} ({row['Seasonality']} seasonality)"
                    )
            else:
                st.info("No significant seasonal patterns detected.")




def smart_recommendations_page():
    """Smart AI Recommendations"""
    st.markdown(
        """
    <div class="main-header">
        <h1>🎯 Smart Recommendation Engine</h1>
        <p>AI-Powered Inventory Optimization Recommendations</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    from smart_recommendations import SmartRecommendationEngine
    engine = SmartRecommendationEngine(_db)

    st.markdown("### 💡 Personalized Recommendations")

    if st.button("🔮 Generate Smart Recommendations", type="primary"):
        with st.spinner(
            "Analyzing inventory and generating personalized recommendations..."
        ):
            recommendations = engine.get_personalized_recommendations()

            if recommendations:
                st.success(f"✅ Generated {len(recommendations)} recommendations")

                # Filter options
                rec_types = list(set([r["type"] for r in recommendations]))
                selected_type = st.multiselect(
                    "Filter by Type", rec_types, default=rec_types
                )

                filtered_recs = [
                    r for r in recommendations if r["type"] in selected_type
                ]

                # Display recommendations
                for i, rec in enumerate(filtered_recs[:20], 1):
                    with st.expander(
                        f"#{i} - {rec['title']} (Priority: {rec['priority_score']:.0f})"
                    ):
                        st.write(f"**Category:** {rec['category']}")
                        st.write(f"**Description:** {rec['description']}")
                        st.write(f"**Recommended Action:** {rec['action']}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            impact_color = (
                                "🟢"
                                if rec["impact"] == "High"
                                else "🟡"
                                if rec["impact"] == "Medium"
                                else "🔵"
                            )
                            st.write(f"{impact_color} **Impact:** {rec['impact']}")
                        with col2:
                            urgency_color = (
                                "🔴"
                                if rec["urgency"] == "Critical"
                                else "🟠"
                                if rec["urgency"] == "High"
                                else "🟡"
                            )
                            st.write(f"{urgency_color} **Urgency:** {rec['urgency']}")
                        with col3:
                            if rec["estimated_cost"] < 0:
                                st.write(
                                    f"💰 **Potential Savings:** {format_currency(abs(rec['estimated_cost']))}"
                                )
                            else:
                                st.write(
                                    f"💵 **Estimated Cost:** {format_currency(rec['estimated_cost'])}"
                                )
            else:
                st.info(
                    "No recommendations at this time. Your inventory is well-optimized!"
                )

    # Optimization Opportunities
    st.markdown("### 💰 Top Optimization Opportunities")

    if st.button("🔍 Find Optimization Opportunities"):
        opportunities = engine.get_optimization_opportunities()

        if opportunities:
            for opp in opportunities:
                with st.expander(
                    f"{opp['type']} - {opp['drug_name']} - ROI: {opp['roi_percentage']:.1f}%"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Potential Savings",
                            format_currency(opp["potential_savings"]),
                        )
                        st.metric(
                            "Implementation Cost",
                            format_currency(opp["implementation_cost"]),
                        )
                    with col2:
                        st.metric("ROI %", f"{opp['roi_percentage']:.1f}%")
                        st.metric("Timeframe", opp["timeframe"])
        else:
            st.info("No major optimization opportunities identified.")


def generate_reports_page():
    """PDF Report Generation"""
    st.markdown(
        """
    <div class="main-header">
        <h1>📄 Professional Report Generation</h1>
        <p>Generate Comprehensive PDF Reports</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    from pdf_report_generator import InventoryReportGenerator
    report_gen = InventoryReportGenerator(_db)

    st.markdown("### 📋 Available Reports")

    report_type = st.radio(
        "Select Report Type",
        ["Comprehensive Inventory Report", "Analytics Report (Date Range)"],
    )

    if report_type == "Comprehensive Inventory Report":
        st.markdown("#### 📊 Comprehensive Inventory Report")
        st.info(
            "Includes: Executive Summary, Stock Alerts, Expiry Analysis, Financial Overview, High-Value Items, and Recommendations"
        )

        if st.button("📥 Generate Comprehensive Report", type="primary"):
            with st.spinner("Generating professional PDF report..."):
                try:
                    filename = report_gen.generate_comprehensive_report(
                        "comprehensive_inventory_report.pdf"
                    )
                    st.success(f"✅ Report generated successfully: {filename}")

                    with open(filename, "rb") as file:
                        st.download_button(
                            label="⬇️ Download PDF Report",
                            data=file,
                            file_name=filename,
                            mime="application/pdf",
                        )
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")

    else:
        st.markdown("#### 📅 Analytics Report (Custom Date Range)")
        st.info("Generate analytics report for a specific time period")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date", value=datetime.now() - timedelta(days=90)
            )
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())

        if st.button("📥 Generate Analytics Report", type="primary"):
            with st.spinner("Generating analytics report..."):
                try:
                    filename = report_gen.generate_analytics_report(
                        str(start_date),
                        str(end_date),
                        f"analytics_report_{start_date}_to_{end_date}.pdf",
                    )
                    st.success(f"✅ Report generated successfully: {filename}")

                    with open(filename, "rb") as file:
                        st.download_button(
                            label="⬇️ Download Analytics Report",
                            data=file,
                            file_name=filename,
                            mime="application/pdf",
                        )
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")


# QR Code Scan/Details Page - Check for item_id in query params


if page == "Dashboard":
    dashboard_page()
elif page == "Inventory Management":
    inventory_management_page()
elif page == "🚨 Anomaly Monitor":
    anomaly_monitor_page()
elif page == "Smart Reordering":
    smart_reordering_page()
elif page == "Expiry Management":
    expiry_management_page()
elif page == "Analytics":
    analytics_page()
elif page == "📈 Regression & LSTM Analysis":
    from regression_lstm_page import regression_lstm_analysis_page
    regression_lstm_analysis_page(_db)
elif page == "🤖 AI Assistant":
    from ai_chatbot import render_ai_chatbot_page
    render_ai_chatbot_page(_db)
elif page == "💡 Wastage Analysis":
    wastage_analysis_page()
elif page == "💰 Cost Optimization":
    cost_optimization_page()
elif page == "📊 Drug Utilization Review":
    drug_utilization_review_page()
elif page == "🔗 Drug Correlations":
    drug_correlations_page()
elif page == "🔮 Advanced Predictive Analytics":
    advanced_predictive_analytics_page()
elif page == "🎯 Smart Recommendations":
    smart_recommendations_page()
elif page == "📄 Generate Reports":
    generate_reports_page()
elif page == "Settings":
    settings_page()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**AI Pharmaceutical Inventory Management System**")
st.sidebar.markdown("Version 1.0.0")
st.sidebar.markdown("© 2025 AI Pharma Systems")
