import streamlit as st
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd


class PharmaceuticalChatbot:
    """Local, deterministic, rule-based pharmaceutical inventory assistant.

    Zero external APIs, zero paid dependencies, fully offline.
    Uses parameterized SQL and real project database records.
    """

    def __init__(self, db, drug_checker=None, analytics=None, forecaster=None, recommendations=None):
        self.db = db
        self.drug_checker = drug_checker
        self.analytics = analytics
        self.forecaster = forecaster
        self.recommendations = recommendations

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        if "chat_context" not in st.session_state:
            st.session_state.chat_context = {
                "recent_queries": [],
                "conversation_topic": None,
            }

    def _make_card(self, title: str, content: str, accent_color: str = "#c96442", category: str = "Assistant") -> str:
        """Create a Claude Amber styled information card."""
        return f"""
        <div style="background-color: #ffffff; border: 1px solid #dad9d4; border-left: 3px solid {accent_color}; border-radius: 6px; padding: 1.15rem; margin: 0.65rem 0; box-shadow: 0 1px 2px rgba(61, 57, 41, 0.03);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; color: #83827d;">{category}</span>
            </div>
            <div style="font-size: 1.05rem; font-weight: 600; color: #3d3929; margin-bottom: 0.4rem;">{title}</div>
            <div style="font-size: 0.88rem; color: #3d3929; line-height: 1.5;">{content}</div>
        </div>
        """.strip()

    def generate_ai_response(self, user_message: str) -> str:
        """Process natural language questions and query real database tables."""
        if not user_message or not user_message.strip():
            return self._make_card("Empty Query", "Please provide a question about stock levels, expiry dates, suppliers, or purchase orders.", "#83827d")

        msg = user_message.lower().strip()
        conn = self.db.get_connection()

        try:
            # 1. Greetings
            if any(re.search(rf"\b{w}\b", msg) for w in ["hi", "hello", "hey", "greetings"]):
                content = """
                Welcome to the local pharmaceutical operations assistant. You can ask me:
                <ul style="margin: 0.5rem 0 0.5rem 1.25rem; padding: 0;">
                    <li><strong>Stock levels:</strong> e.g., <em>"How much Paracetamol is in stock?"</em></li>
                    <li><strong>Shortages:</strong> e.g., <em>"Which drugs are low in stock?"</em></li>
                    <li><strong>Expiry risk:</strong> e.g., <em>"What medications are expiring soon?"</em></li>
                    <li><strong>Suppliers & Vendors:</strong> e.g., <em>"List our suppliers"</em> or <em>"Who supplies Amoxicillin?"</em></li>
                    <li><strong>Orders & Movements:</strong> e.g., <em>"Show recent purchase orders"</em> or <em>"Recent transactions"</em></li>
                </ul>
                """
                return self._make_card("Pharmaceutical Operations Assistant", content, "#c96442", "Overview")

            # 2. Help / Capabilities
            if any(re.search(rf"\b{w}\b", msg) for w in ["help", "what can you do", "commands", "options"]):
                content = """
                I operate completely offline using parameterized SQL queries across your operational tables:
                <br/><br/>
                • <code>inventory</code>: Current quantities, minimum buffers, unit costs.<br/>
                • <code>purchase_orders</code>: Pending and delivered procurement records.<br/>
                • <code>suppliers</code>: Lead times, reliability scores, contact details.<br/>
                • <code>transactions</code>: Dispensation and receipt history.
                """
                return self._make_card("Capabilities & Data Access", content, "#c96442", "Help")

            # 3. Specific drug lookup
            drug_name_match = None
            cur = conn.cursor()
            drugs = [r[0] for r in cur.execute("SELECT DISTINCT drug_name FROM inventory").fetchall()]
            for d in sorted(drugs, key=len, reverse=True):
                # match if drug name tokens appear in query
                first_word = d.split()[0].lower()
                if first_word in msg or d.lower() in msg:
                    drug_name_match = d
                    break

            if drug_name_match:
                row = cur.execute("""
                    SELECT drug_name, category, manufacturer, batch_number, current_stock, minimum_stock, unit_price, expiry_date, supplier_name
                    FROM inventory
                    WHERE drug_name = ?
                    ORDER BY expiry_date ASC
                    LIMIT 1
                """, (drug_name_match,)).fetchone()

                if row:
                    is_low = row["current_stock"] <= row["minimum_stock"]
                    status_badge = "<span style='color: #c53030; font-weight: 600;'>Low Stock (Action Required)</span>" if is_low else "<span style='color: #2e7d32; font-weight: 600;'>Sufficient</span>"
                    content = f"""
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-top: 0.4rem;">
                        <div><strong>Category:</strong> {row['category']}</div>
                        <div><strong>Status:</strong> {status_badge}</div>
                        <div><strong>Current Stock:</strong> {row['current_stock']} units</div>
                        <div><strong>Safety Buffer:</strong> {row['minimum_stock']} units</div>
                        <div><strong>Earliest Expiry:</strong> {row['expiry_date']}</div>
                        <div><strong>Batch:</strong> {row['batch_number']}</div>
                        <div><strong>Unit Price:</strong> ₹{row['unit_price']:.2f}</div>
                        <div><strong>Supplier:</strong> {row['supplier_name']}</div>
                    </div>
                    """
                    accent = "#c53030" if is_low else "#2e7d32"
                    return self._make_card(f"Stock Record: {row['drug_name']}", content, accent, "Inventory Query")

            # 4. Low stock / Critical shortage query
            if any(w in msg for w in ["low stock", "shortage", "out of stock", "reorder", "running low", "depleted"]):
                cur.execute("""
                    SELECT drug_name, current_stock, minimum_stock, supplier_name
                    FROM inventory
                    WHERE current_stock <= minimum_stock
                    ORDER BY current_stock ASC
                    LIMIT 8
                """)
                rows = cur.fetchall()
                if rows:
                    items_html = "".join([
                        f"<li style='margin-bottom: 0.35rem;'><strong>{r['drug_name']}</strong>: "
                        f"{r['current_stock']} remaining (Min: {r['minimum_stock']}) — Vendor: {r['supplier_name']}</li>"
                        for r in rows
                    ])
                    content = f"""
                    Found <strong>{len(rows)}</strong> items currently at or below minimum threshold:
                    <ul style="margin: 0.5rem 0 0.5rem 1.25rem; padding: 0;">{items_html}</ul>
                    <em>Recommended action: Open Purchase Orders section to replenish low stock batches.</em>
                    """
                    return self._make_card("Low Stock Items Detected", content, "#c53030", "Inventory Alert")
                else:
                    return self._make_card("Stock Status Normal", "All catalog medicines are currently above minimum safety buffer levels.", "#2e7d32", "Inventory Alert")

            # 5. Expiry query
            if any(w in msg for w in ["expir", "outdated", "shelf life"]):
                days = 90 if "90" in msg else (60 if "60" in msg else 30)
                cur.execute("""
                    SELECT drug_name, batch_number, current_stock, expiry_date
                    FROM inventory
                    WHERE expiry_date <= date('now', ? || ' days')
                    ORDER BY expiry_date ASC
                    LIMIT 8
                """, (f"+{days}",))
                rows = cur.fetchall()
                if rows:
                    items_html = "".join([
                        f"<li style='margin-bottom: 0.35rem;'><strong>{r['drug_name']}</strong> (Batch: {r['batch_number']}): "
                        f"{r['current_stock']} units, expires on <strong>{r['expiry_date']}</strong></li>"
                        for r in rows
                    ])
                    content = f"""
                    Medications expiring within the next <strong>{days} days</strong>:
                    <ul style="margin: 0.5rem 0 0.5rem 1.25rem; padding: 0;">{items_html}</ul>
                    <em>Recommended action: Apply First-Expiry-First-Out (FEFO) dispensing or contact suppliers for returns.</em>
                    """
                    return self._make_card(f"Medications Expiring Within {days} Days", content, "#c96442", "Expiry Notice")
                else:
                    return self._make_card(f"No Expiry Risks Within {days} Days", f"No inventory batches are scheduled to expire in the next {days} days.", "#2e7d32", "Expiry Notice")

            # 6. Suppliers query
            if any(w in msg for w in ["supplier", "vendor", "distributor"]):
                cur.execute("""
                    SELECT name, contact_person, phone, lead_time_days, reliability_score
                    FROM suppliers
                    ORDER BY reliability_score DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                if rows:
                    items_html = "".join([
                        f"<li style='margin-bottom: 0.35rem;'><strong>{r['name']}</strong> — Lead time: {r['lead_time_days']}d | "
                        f"Reliability: {r['reliability_score']:.1f}/5.0 (Contact: {r['contact_person'] or 'N/A'}, Phone: {r['phone'] or 'N/A'})</li>"
                        for r in rows
                    ])
                    content = f"""
                    Registered suppliers on file:
                    <ul style="margin: 0.5rem 0 0.5rem 1.25rem; padding: 0;">{items_html}</ul>
                    """
                    return self._make_card("Supplier Records", content, "#c96442", "Procurement")

            # 7. Purchase orders query
            if any(w in msg for w in ["purchase order", "po", "orders", "procurement"]):
                cur.execute("""
                    SELECT po.order_number, i.drug_name, po.quantity, po.status, po.order_date, s.name as supplier
                    FROM purchase_orders po
                    LEFT JOIN inventory i ON po.drug_id = i.id
                    LEFT JOIN suppliers s ON po.supplier_id = s.id
                    ORDER BY po.order_date DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                if rows:
                    items_html = "".join([
                        f"<li style='margin-bottom: 0.35rem;'><strong>#{r['order_number']}</strong>: {r['drug_name']} ({r['quantity']} units) "
                        f"— Status: <em>{r['status']}</em> from {r['supplier']} on {r['order_date']}</li>"
                        for r in rows
                    ])
                    content = f"""
                    Recent purchase orders:
                    <ul style="margin: 0.5rem 0 0.5rem 1.25rem; padding: 0;">{items_html}</ul>
                    """
                    return self._make_card("Purchase Order Register", content, "#c96442", "Procurement")

            # 8. Transactions query
            if any(w in msg for w in ["transaction", "dispensed", "movement", "sales"]):
                cur.execute("""
                    SELECT t.transaction_type, i.drug_name, t.quantity, t.total_amount, t.created_at
                    FROM transactions t
                    LEFT JOIN inventory i ON t.drug_id = i.id
                    ORDER BY t.created_at DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                if rows:
                    items_html = "".join([
                        f"<li style='margin-bottom: 0.35rem;'><strong>{r['transaction_type']}</strong>: {r['drug_name']} "
                        f"({r['quantity']} units) — ₹{r['total_amount']:.2f} at {r['created_at']}</li>"
                        for r in rows
                    ])
                    content = f"""
                    Recent inventory transactions:
                    <ul style="margin: 0.5rem 0 0.5rem 1.25rem; padding: 0;">{items_html}</ul>
                    """
                    return self._make_card("Recent Transaction Ledger", content, "#c96442", "Audit")

            # 9. General valuation / summary
            if any(w in msg for w in ["total", "summary", "valuation", "stats", "overview"]):
                row = cur.execute("""
                    SELECT COUNT(*) as total_items, SUM(current_stock) as total_units, SUM(current_stock * unit_price) as total_value
                    FROM inventory
                """).fetchone()
                content = f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-top: 0.4rem;">
                    <div><strong>Catalog Items:</strong> {row['total_items']:,}</div>
                    <div><strong>Total Stock Units:</strong> {row['total_units']:,}</div>
                    <div><strong>Total Valuation:</strong> ₹{row['total_value']:,.2f}</div>
                    <div><strong>Mode:</strong> Local Deterministic Engine</div>
                </div>
                """
                return self._make_card("Inventory Summary Overview", content, "#c96442", "Analytics")

            # Fallback for unrecognized questions
            return self._make_card(
                "Local Query Limitation",
                "I am a lightweight local assistant with read-only access to inventory, purchase orders, suppliers, and transactions.<br/><br/>"
                "Try asking: <em>'Which drugs are low in stock?'</em>, <em>'What is expiring soon?'</em>, <em>'List suppliers'</em>, or ask for a specific drug name like <em>'Paracetamol'</em> or <em>'Amoxicillin'</em>.",
                "#83827d",
                "Unrecognized Intent"
            )

        except Exception as e:
            return self._make_card("Database Query Error", f"Failed to execute local query: {str(e)}", "#c53030", "System Error")
        finally:
            conn.close()

    def add_to_history(self, role: str, content: str):
        st.session_state.chat_history.append({"role": role, "content": content, "timestamp": datetime.now()})
        if len(st.session_state.chat_history) > 30:
            st.session_state.chat_history = st.session_state.chat_history[-30:]


def render_ai_chatbot_page(db):
    """Render local deterministic pharmaceutical assistant with Claude Amber aesthetic."""
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #dad9d4; border-radius: 6px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 2px rgba(61, 57, 41, 0.03);">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h2 style="font-size: 1.35rem; font-weight: 600; color: #3d3929; margin: 0; letter-spacing: -0.02em;">Pharmaceutical Operations Assistant</h2>
                <p style="font-size: 0.875rem; color: #83827d; margin-top: 0.25rem; margin-bottom: 0;">Local deterministic query engine with direct database verification (Zero external API dependencies)</p>
            </div>
            <span style="font-size: 0.72rem; padding: 0.25rem 0.6rem; border-radius: 4px; background: #fbeee8; color: #c96442; font-weight: 600; border: 1px solid #dad9d4;">OFFLINE ACTIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    chatbot = PharmaceuticalChatbot(db)

    # Quick action prompt pills
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Low Stock Items", use_container_width=True):
            prompt = "Which items are running low on stock?"
            chatbot.add_to_history("user", prompt)
            resp = chatbot.generate_ai_response(prompt)
            chatbot.add_to_history("assistant", resp)
            st.rerun()

    with col2:
        if st.button("Expiring Soon", use_container_width=True):
            prompt = "What medications are expiring soon?"
            chatbot.add_to_history("user", prompt)
            resp = chatbot.generate_ai_response(prompt)
            chatbot.add_to_history("assistant", resp)
            st.rerun()

    with col3:
        if st.button("Suppliers List", use_container_width=True):
            prompt = "List our suppliers and lead times"
            chatbot.add_to_history("user", prompt)
            resp = chatbot.generate_ai_response(prompt)
            chatbot.add_to_history("assistant", resp)
            st.rerun()

    with col4:
        if st.button("Inventory Summary", use_container_width=True):
            prompt = "What is the total valuation and inventory summary?"
            chatbot.add_to_history("user", prompt)
            resp = chatbot.generate_ai_response(prompt)
            chatbot.add_to_history("assistant", resp)
            st.rerun()

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # Chat history display
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"], unsafe_allow_html=True)

    # User input
    if prompt := st.chat_input("Ask about stock levels, expiry dates, suppliers, or purchase orders..."):
        chatbot.add_to_history("user", prompt)
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            resp = chatbot.generate_ai_response(prompt)
            st.markdown(resp, unsafe_allow_html=True)
            chatbot.add_to_history("assistant", resp)

    # Sidebar controls
    if st.sidebar.button("Clear Conversation"):
        st.session_state.chat_history = []
        st.rerun()
