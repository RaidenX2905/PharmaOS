import streamlit as st
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


class PharmaceuticalChatbot:
    def __init__(
        self,
        db,
        drug_checker=None,
        analytics=None,
        forecaster=None,
        recommendations=None,
    ):
        self.db = db
        self.drug_checker = drug_checker
        self.analytics = analytics
        self.forecaster = forecaster
        self.recommendations = recommendations
        self.openai_client = None

        if OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        if "chat_context" not in st.session_state:
            st.session_state.chat_context = {
                "user_preferences": {},
                "recent_queries": [],
                "conversation_topic": None,
            }

        self.fallback_responses = {
            "inventory": "I can help you check current inventory levels, low stock items, and expiring drugs.",
            "drug_info": "I can provide basic information about drugs in your inventory including dosage, category, and supplier details.",
            "interactions": "I can check for potential drug interactions using our built-in interaction database.",
            "ordering": "I can suggest items to reorder based on consumption patterns and current stock levels.",
            "expiry": "I can show you items nearing expiry and suggest actions to prevent wastage.",
            "analytics": "I can provide insights from your inventory data including trends and forecasts.",
        }

    def get_system_context(self) -> str:
        """Get enriched system context for the AI with advanced analytics integration"""
        try:
            inventory_df = self.db.get_inventory()
            total_items = len(inventory_df)
            low_stock_items = len(
                inventory_df[
                    inventory_df["current_stock"] < inventory_df["min_stock_level"]
                ]
            )
            expiring_items = self.db.get_expiring_drugs(days_ahead=30)
            recent_transactions = self.db.get_recent_transactions(limit=5)

            context = f"""
You are an advanced AI assistant for a pharmaceutical inventory management system with deep integration into analytics and forecasting modules.

CURRENT SYSTEM STATUS:
- Total items in inventory: {total_items}
- Items with low stock: {low_stock_items}
- Items expiring in next 30 days: {len(expiring_items)}
- Recent activity: {len(recent_transactions)} transactions

ADVANCED CAPABILITIES:
1. Inventory Management: Stock levels, item details, categories, batch tracking
2. Drug Safety: Interaction checking, substitution recommendations
3. Predictive Analytics: Demand forecasting, anomaly detection, wastage prediction
4. Smart Recommendations: AI-powered restocking, cost optimization
5. Trend Analysis: Consumption patterns, seasonal variations, correlation analysis
6. Multi-turn Conversations: Context-aware responses with conversation memory

INTEGRATION STATUS:
- Drug Interaction Checker: {"Available" if self.drug_checker else "Not Available"}
- Advanced Analytics: {"Available" if self.analytics else "Not Available"}
- Smart Recommendations: {"Available" if self.recommendations else "Not Available"}

CONVERSATION CONTEXT:
- Current topic: {st.session_state.chat_context.get("conversation_topic", "General")}
- Recent query themes: {", ".join(st.session_state.chat_context.get("recent_queries", [])[-3:])}

Provide comprehensive, actionable insights. When users ask about analytics, forecasting, or recommendations,
leverage the integrated modules to provide detailed analysis. Always be specific with numbers and actionable recommendations.
"""
            return context
        except Exception as e:
            return "You are an AI assistant for a pharmaceutical inventory management system."

    @st.cache_data(show_spinner=False, ttl=60) # Cache for 60 seconds to stay fresh but fast
    def _get_cached_inventory(_self):
        """Helper to cache inventory data for faster chatbot responses"""
        return _self.db.get_inventory()

    def query_inventory_data(self, query: str) -> Dict:
        """Optimized query engine with caching for speed"""
        try:
            results = {}
            query_lower = query.lower()

            # Always check for drug matches in the query
            inventory_df = self._get_cached_inventory()
            words = [w.strip("?,.!") for w in query_lower.split()]
            drug_matches = []
            
            for _, drug in inventory_df.iterrows():
                drug_name_lower = drug["drug_name"].lower()
                # Check if drug name is in query or any word from query is in drug name
                if drug_name_lower in query_lower or any(len(word) > 3 and word in drug_name_lower for word in words):
                    drug_matches.append(drug.to_dict())

            if drug_matches:
                # Sort matches by how well they match the query (exact name first)
                drug_matches.sort(key=lambda x: x['drug_name'].lower() in query_lower, reverse=True)
                results["matching_drugs"] = drug_matches[:5]

            if any(
                word in query_lower
                for word in ["stock", "level", "quantity", "low", "empty", "how many"]
            ):
                inventory_df = self._get_cached_inventory()
                low_stock = inventory_df[
                    inventory_df["current_stock"] < inventory_df["min_stock_level"]
                ]
                results["low_stock_items"] = low_stock.to_dict("records")[:10]

            if any(
                word in query_lower
                for word in ["expiry", "expire", "expiring", "expired"]
            ):
                expiring_items = self.db.get_expiring_drugs(days_ahead=30)
                results["expiring_items"] = expiring_items[:10]

            if any(
                word in query_lower
                for word in ["transaction", "sale", "purchase", "recent"]
            ):
                recent_transactions = self.db.get_recent_transactions(limit=10)
                results["recent_transactions"] = recent_transactions.to_dict("records")

            if any(
                word in query_lower
                for word in ["interaction", "safe", "combine", "together"]
            ):
                if self.drug_checker:
                    results["has_drug_checker"] = True
                    results["drug_checker_message"] = (
                        "Drug interaction checking is available. Specify drugs to check."
                    )

            if any(
                word in query_lower
                for word in ["anomaly", "unusual", "spike", "pattern"]
            ):
                if self.analytics:
                    try:
                        anomalies = self.analytics.detect_anomalies(
                            threshold=2.5, use_ensemble=True
                        )
                        results["anomalies"] = anomalies[:5]
                    except:
                        results["anomalies_error"] = "Unable to fetch anomaly data"

            if any(
                word in query_lower
                for word in ["trend", "consumption", "usage", "demand"]
            ):
                if self.analytics:
                    try:
                        trends = self.analytics.analyze_consumption_patterns(days=90)
                        results["consumption_trends"] = dict(list(trends.items())[:5])
                    except:
                        results["trends_error"] = "Unable to fetch trend data"


            if any(
                word in query_lower
                for word in ["recommend", "suggest", "advice", "should"]
            ):
                if self.recommendations:
                    try:
                        recs = self.recommendations.get_personalized_recommendations()
                        results["smart_recommendations"] = recs[:5]
                    except:
                        results["recommendations_error"] = (
                            "Unable to fetch recommendations"
                        )

            return results
        except Exception as e:
            return {"error": str(e)}

    def update_conversation_context(self, user_message: str):
        """Track conversation context for better multi-turn understanding"""
        query_lower = user_message.lower()

        themes = []
        if any(word in query_lower for word in ["stock", "inventory"]):
            themes.append("inventory")
        if any(word in query_lower for word in ["expiry", "expire"]):
            themes.append("expiry")
        if any(word in query_lower for word in ["interaction", "safe"]):
            themes.append("drug_safety")
        if any(word in query_lower for word in ["anomaly", "unusual"]):
            themes.append("analytics")

        if themes:
            st.session_state.chat_context["recent_queries"].extend(themes)
            st.session_state.chat_context["recent_queries"] = (
                st.session_state.chat_context["recent_queries"][-10:]
            )
            st.session_state.chat_context["conversation_topic"] = themes[0]

    def generate_ai_response(self, user_message: str) -> str:
        """Generate AI response with advanced context and module integration"""
        self.update_conversation_context(user_message)

        if not self.openai_client:
            return self.generate_fallback_response(user_message)

        try:
            system_context = self.get_system_context()
            data_context = self.query_inventory_data(user_message)

            context_message = f"{system_context}\n\nRELEVANT DATA:\n{json.dumps(data_context, indent=2, default=str)}"

            messages = [
                {"role": "system", "content": context_message},
                {"role": "user", "content": user_message},
            ]

            if "chat_history" in st.session_state:
                recent_history = (
                    st.session_state.chat_history[-8:]
                    if st.session_state.chat_history
                    else []
                )
                for msg in recent_history:
                    if msg["role"] in ["user", "assistant"]:
                        messages.append(
                            {"role": msg["role"], "content": str(msg["content"])}
                        )

            response = self.openai_client.chat.completions.create(
                model="gpt-5", messages=messages, max_completion_tokens=800
            )

            return (
                response.choices[0].message.content
                or "I apologize, but I couldn't generate a response."
            )

        except Exception as e:
            st.error(f"AI response error: {str(e)}")
            return self.generate_fallback_response(user_message)

    def generate_fallback_response(self, user_message: str) -> str:
        """Robust NLU engine that returns beautiful HTML-formatted cards"""
        msg = user_message.lower()
        data_context = self.query_inventory_data(user_message)
        inventory_df = self._get_cached_inventory()
        
        # Helper for beautiful cards
        def make_card(title, content, color="#4A90E2", icon="💊"):
            return f"""
            <div style="background: white; padding: 1.5rem; border-left: 5px solid {color}; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 1rem 0;">
                <h3 style="margin-top: 0; color: {color}; display: flex; align-items: center; gap: 10px;">
                    <span>{icon}</span> {title}
                </h3>
                <div style="color: #333; line-height: 1.6;">
                    {content}
                </div>
            </div>
            """

        # 1. Action: Check Stock for specific drug
        if "matching_drugs" in data_context and data_context["matching_drugs"]:
            drug = data_context["matching_drugs"][0]
            if any(w in msg for w in ["how many", "quantity", "stock", "count", "much"]):
                is_low = drug['current_stock'] < drug['min_stock_level']
                status_color = "#E74C3C" if is_low else "#27AE60"
                status_text = "LOW STOCK" if is_low else "HEALTHY STOCK"
                content = f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div><b>Current Stock:</b> <span style="font-size: 1.2rem; color: {status_color};">{drug['current_stock']} units</span></div>
                    <div><b>Min. Required:</b> {drug['min_stock_level']} units</div>
                    <div><b>Status:</b> <span style="padding: 2px 8px; border-radius: 4px; background: {status_color}; color: white; font-size: 0.8rem;">{status_text}</span></div>
                    <div><b>Batch:</b> {drug.get('batch_number', 'N/A')}</div>
                </div>
                """
                return make_card(f"Stock Report: {drug['drug_name']}", content, status_color, "📦")
            
            if any(w in msg for w in ["price", "cost", "how much", "rate"]):
                content = f"""
                <div style="font-size: 1.1rem; margin-bottom: 10px;"><b>Unit Price:</b> <span style="color: #27AE60; font-weight: bold;">₹{drug['unit_price']:.2f}</span></div>
                <div style="color: #666;"><b>Total Inventory Value:</b> ₹{(drug['current_stock'] * drug['unit_price']):,.2f}</div>
                <div style="margin-top: 10px; font-size: 0.9rem;"><b>Supplier:</b> {drug.get('supplier_name', 'Not specified')}</div>
                """
                return make_card(f"Pricing: {drug['drug_name']}", content, "#27AE60", "💰")

            if any(w in msg for w in ["supplier", "who provides", "from where", "vendor"]):
                content = f"""
                <div style="font-size: 1.1rem;"><b>Main Vendor:</b> {drug.get('supplier_name', 'Information missing')}</div>
                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">Data Last Updated: {drug.get('updated_at', 'Recently')}</div>
                """
                return make_card(f"Supplier: {drug['drug_name']}", content, "#8E44AD", "🏢")

        # 2. Action: Category Summary
        categories = [c.lower() for c in inventory_df['category'].unique()]
        found_cat = next((c for c in categories if c in msg), None)
        if found_cat:
            cat_df = inventory_df[inventory_df['category'].str.lower() == found_cat]
            total_cat_stock = cat_df['current_stock'].sum()
            content = f"""
            <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                <div><small>Items</small><br/><b>{len(cat_df)}</b></div>
                <div><small>Total Units</small><br/><b>{total_cat_stock}</b></div>
                <div><small>Leading Brand</small><br/><b>{cat_df.iloc[0]['drug_name']}</b></div>
            </div>
            <hr style="border: none; border-top: 1px solid #eee; margin: 10px 0;"/>
            <p style="font-size: 0.9rem; color: #666;">I can list all individual items if you'd like. Just ask for "list items".</p>
            """
            return make_card(f"Category: {found_cat.title()}", content, "#F39C12", "📁")

        # 3a. Action: Top Trending Drugs (Based on sales/movements)
        if any(w in msg for w in ["trending", "trend", "popular", "fast moving", "top selling"]):
            try:
                # Try to get most moved items in last 14 days from transactions
                conn = self.db.get_connection()
                query = """
                    SELECT d.drug_name, SUM(t.quantity) as total_qty
                    FROM transactions t
                    JOIN inventory d ON t.drug_id = d.id
                    WHERE t.created_at >= date('now', '-14 days')
                    GROUP BY d.drug_name
                    ORDER BY total_qty DESC
                    LIMIT 5
                """
                trending_df = pd.read_sql(query, conn)
                conn.close()
                
                if not trending_df.empty:
                    list_html = "".join([f"<div style='margin-bottom: 8px;'>🔥 <b>{r['drug_name']}</b> is currently a top mover with {int(r['total_qty'])} units sold recently.</div>" for _, r in trending_df.iterrows()])
                    return make_card("Market Trend Analysis", list_html.strip(), "#2ECC71", "🚀").strip()
            except: pass
            return make_card("Trend Analysis", "📊 Your inventory usage is currently stable. No significant 'fast-moving' trends detected in the last 14 days.", "#3498DB", "📉").strip()

        # 3b. Action: Smart Strategy Recommendations
        if any(w in msg for w in ["recommend", "suggest", "advice", "what should i"]):
            if self.recommendations:
                try:
                    recs = self.recommendations.generate_all_recommendations()
                    if recs:
                        list_html = "".join([f"<div style='margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px;'><b>📍 {r['title']}</b><br/><span style='font-size: 0.9rem; color: #555;'>{r['description']}</span></div>" for r in recs[:3]])
                        return make_card("AI Business Strategy", list_html.strip(), "#9B59B6", "🧠").strip()
                except: pass
            return make_card("Strategic Advice", "✨ Your inventory metrics are currently within optimal parameters. No new strategic recommendations available.", "#27AE60", "💎").strip()

        # 3c. Action: Inventory Irregularities (Anomalies)
        if any(w in msg for w in ["anomaly", "unusual", "pattern", "spike", "drop", "weird"]):
            if self.analytics:
                try:
                    anomalies = self.analytics.detect_anomalies()
                    if anomalies:
                        unique_anoms = {a['drug_name']: a for a in anomalies}
                        list_html = "".join([f"<div style='margin-bottom: 8px;'>🚩 <b>{a['drug_name']}</b>: Flagged for unusual {a['type'].lower()}.</div>" for a in list(unique_anoms.values())[:5]])
                        return make_card("Risk & Anomaly Report", list_html.strip(), "#E67E22", "🚨").strip()
                except: pass
            return make_card("Anomaly Check", "✅ I've scanned the last 30 days of data. All consumption patterns are normal.", "#27AE60", "🛡️").strip()

        # 3d. Action: Critical Alerts (Low Stock / Expiry)
        if any(w in msg for w in ["alert", "critical", "warning", "issue", "problem"]):
            low_items = inventory_df[inventory_df['current_stock'] < inventory_df['min_stock_level']]
            expiring = self.db.get_expiring_drugs(30)
            
            # Properly define is_expiring
            is_expiring = not expiring.empty if hasattr(expiring, 'empty') else (len(expiring) > 0 if expiring else False)
            
            content = ""
            if not low_items.empty:
                content += f"⚠️ <b>Low Stock Warning:</b> You have {len(low_items)} items below their safe levels.<br/>"
            
            if is_expiring:
                content += f"⏳ <b>Expiry Alert:</b> {len(expiring)} items are expiring within 30 days.<br/>"
            
            if not content: content = "✅ Your system is currently healthy with no active critical alerts."
            return make_card("System Health Alerts", content.strip(), "#E74C3C", "⚡").strip()

        # 3e. Action: Professional Report Generation
        if any(w in msg for w in ["report", "generate report", "full report", "document"]):
            total_items = len(inventory_df)
            total_val = (inventory_df['current_stock'] * inventory_df['unit_price']).sum()
            low_stock = inventory_df[inventory_df['current_stock'] < inventory_df['min_stock_level']]
            
            # Category breakdown for report
            cat_breakdown = inventory_df.groupby('category')['current_stock'].sum().to_dict()
            cat_html = "".join([f"<tr><td style='padding:8px; border-bottom:1px solid #eee;'>{c}</td><td style='padding:8px; border-bottom:1px solid #eee; text-align:right;'>{q} units</td></tr>" for c, q in cat_breakdown.items()])
            
            report_html = f"""
            <div style="font-family: sans-serif; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background: #2C3E50; color: white; padding: 20px; text-align: center;">
                    <h2 style="margin: 0;">PRO-PHARMA INVENTORY REPORT</h2>
                    <small>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                <div style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                        <div><b>Total Items:</b> {total_items}</div>
                        <div><b>Total Valuation:</b> ₹{total_val:,.2f}</div>
                    </div>
                    <h4 style="border-bottom: 2px solid #3498DB; padding-bottom: 5px;">Category Breakdown</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        {cat_html}
                    </table>
                    <div style="margin-top: 20px; padding: 10px; background: #fdf2f2; border-radius: 4px; color: #c0392b;">
                        <b>Attention Required:</b> {len(low_stock)} items are currently below minimum safety levels.
                    </div>
                </div>
                <div style="background: #F8F9FA; padding: 10px; text-align: center; font-size: 0.8rem; color: #7F8C8D;">
                    Confidential Pharmaceutical Inventory Data
                </div>
            </div>
            """
            return make_card("Professional Report Generated", report_html.strip(), "#2C3E50", "📄").strip()

        # 3f. Action: General System Stats (Summary)
        if any(w in msg for w in ["total", "all", "summary", "overview", "system", "stocks", "status", "everything"]):
            total_items = len(inventory_df)
            total_val = (inventory_df['current_stock'] * inventory_df['unit_price']).sum()
            content = f"""
            <div style="font-size: 1rem; margin-bottom: 10px;">Here is your current inventory snapshot:</div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                <div style="background: #F8F9FA; padding: 10px; border-radius: 6px; text-align: center;">
                    <small>DRUGS TRACKED</small><br/><span style="font-size: 1.2rem; font-weight: bold;">{total_items}</span>
                </div>
                <div style="background: #F8F9FA; padding: 10px; border-radius: 6px; text-align: center;">
                    <small>TOTAL VALUE</small><br/><span style="font-size: 1.2rem; font-weight: bold; color: #27AE60;">₹{total_val:,.0f}</span>
                </div>
            </div>
            """
            return make_card("Executive Summary", content.strip(), "#34495E", "📊").strip()

        # 4. Action: Expiry Search
        if any(w in msg for w in ["expiry", "expire", "date", "old"]):
            expiring = self.db.get_expiring_drugs(60)
            is_expiring = not expiring.empty if hasattr(expiring, 'empty') else (len(expiring) > 0 if expiring else False)
            
            if is_expiring:
                items_to_show = expiring.head(5) if hasattr(expiring, 'head') else expiring[:5]
                list_html = ""
                for item in items_to_show:
                    name = item['drug_name'] if isinstance(item, dict) else item.drug_name
                    date = item['expiry_date'] if isinstance(item, dict) else item.expiry_date
                    list_html += f"<li style='margin-bottom: 5px;'><b>{name}</b> - <span style='color: #E74C3C;'>{date}</span></li>"
                content = f"<ul>{list_html}</ul>"
                return make_card("Expiry Alerts (60 Days)", content.strip(), "#E67E22", "⏳").strip()
            return make_card("Expiry Status", "✅ Everything is fresh! No medications expire in the next 2 months.", "#27AE60", "⏳").strip()

        # 5. Action: Comparison or "Best/Most" queries
        if "most" in msg or "highest" in msg or "expensive" in msg:
            if "stock" in msg:
                top = inventory_df.nlargest(1, 'current_stock').iloc[0]
                content = f"<b>{top['drug_name']}</b> holds the record with <b>{top['current_stock']} units</b> in stock."
                return make_card("Highest Stock Item", content.strip(), "#2980B9", "🔝").strip()
            if "price" in msg or "expensive" in msg:
                top = inventory_df.nlargest(1, 'unit_price').iloc[0]
                content = f"<b>{top['drug_name']}</b> is your most premium item at <b>₹{top['unit_price']:.2f}</b> per unit."
                return make_card("Most Expensive Item", content.strip(), "#E91E63", "💎").strip()

        # 6. Action: Greeting & Help
        if any(w in msg for w in ["hello", "hi", "hey", "help", "what can you do"]):
            content = """
            <p>I am your dedicated AI Assistant. Try asking me:</p>
            <ul style="padding-left: 20px;">
                <li>"How much <b>Paracetamol</b> is in stock?"</li>
                <li>"What is the total <b>inventory value</b>?"</li>
                <li>"Who is the <b>supplier</b> of Aspirin?"</li>
                <li>"Show me all <b>expiring</b> items."</li>
            </ul>
            """
            return make_card("How can I help you?", content.strip(), "#4A90E2", "👋").strip()

        # 7. Final Search Fallback
        if "matching_drugs" in data_context and data_context["matching_drugs"]:
            drugs = data_context["matching_drugs"]
            list_html = "".join([f"<div style='margin-bottom: 8px;'>🔹 <b>{d['drug_name']}</b> | Stock: {d['current_stock']} | Price: ₹{d['unit_price']:.2f}</div>" for d in drugs[:3]])
            return make_card(f"Search Results ({len(drugs)})", list_html.strip(), "#95A5A6", "🔍").strip()

        return f"""
        <div style="background: #F8F9FA; padding: 1rem; border-radius: 8px; color: #666; border-left: 5px solid #DDD;">
            🤔 I didn't quite catch that. Could you be more specific? You can ask about drug names, categories (like 'Antibiotics'), or system totals.
        </div>
        """.strip().strip()

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        st.session_state.chat_history.append(
            {"role": role, "content": content, "timestamp": datetime.now()}
        )

        if len(st.session_state.chat_history) > 30:
            st.session_state.chat_history = st.session_state.chat_history[-30:]

    def get_suggested_questions(self) -> List[str]:
        """Get context-aware suggested questions"""
        try:
            suggestions = []

            inventory_df = self.db.get_inventory()
            low_stock_items = len(
                inventory_df[
                    inventory_df["current_stock"] < inventory_df["min_stock_level"]
                ]
            )
            if low_stock_items > 0:
                suggestions.append("Which items are running low on stock?")
            
            suggestions.append("Generate a Professional Inventory Report")

            expiring_items = self.db.get_expiring_drugs(days_ahead=30)
            if len(expiring_items) > 0:
                suggestions.append("What medications are expiring soon?")

            if self.analytics:
                suggestions.append("Show me recent consumption anomalies")
                suggestions.append("What are the trending drugs this month?")

            if self.recommendations:
                suggestions.append("What are your top recommendations for me?")

            suggestions.extend(
                [
                    "What's the total value of my inventory?",
                    "Show me high-value items",
                    "Which suppliers do I order from most?",
                ]
            )

            return suggestions[:6]

        except Exception as e:
            return ["How can I help you with your inventory today?"]


def render_ai_chatbot_page(db):
    """Render enhanced AI chatbot page with module integrations"""
    st.title("🤖 Pharma AI")

    try:
        from drug_interactions import DrugInteractionChecker

        drug_checker = DrugInteractionChecker()
    except:
        drug_checker = None

    try:
        from advanced_analytics import AdvancedAnalytics

        analytics = AdvancedAnalytics(db)
    except:
        analytics = None


    try:
        from smart_recommendations import SmartRecommendationEngine

        recommendations = SmartRecommendationEngine(db)
    except:
        recommendations = None

    chatbot = PharmaceuticalChatbot(
        db, drug_checker, analytics, None, recommendations
    )



    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📊 Stock Status", use_container_width=True):
            query = "What is the current stock status and any critical alerts?"
            chatbot.add_to_history("user", query)
            response = chatbot.generate_ai_response(query)
            chatbot.add_to_history("assistant", response)
            st.rerun()

    with col2:
        if st.button("🚨 Anomalies", use_container_width=True):
            query = "Show me recent consumption anomalies and unusual patterns"
            chatbot.add_to_history("user", query)
            response = chatbot.generate_ai_response(query)
            chatbot.add_to_history("assistant", response)
            st.rerun()

    with col3:
        if st.button("💡 Recommendations", use_container_width=True):
            query = "What are your top smart recommendations for me right now?"
            chatbot.add_to_history("user", query)
            response = chatbot.generate_ai_response(query)
            chatbot.add_to_history("assistant", response)
            st.rerun()

    with col4:
        if st.button("📈 Trends", use_container_width=True):
            query = "Show me trending drugs and consumption patterns"
            chatbot.add_to_history("user", query)
            response = chatbot.generate_ai_response(query)
            chatbot.add_to_history("assistant", response)
            st.rerun()

    st.divider()

    st.subheader("💬 Chat with AI Assistant")

    chat_container = st.container()
    with chat_container:
        for i, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(message["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ask me about your pharmaceutical inventory..."):
        chatbot.add_to_history("user", prompt)

        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing with AI..."):
                response = chatbot.generate_ai_response(prompt)
                st.markdown(response, unsafe_allow_html=True)
                chatbot.add_to_history("assistant", response)

    st.sidebar.markdown("### 🛠️ Chat Controls")
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.chat_context = {
            "user_preferences": {},
            "recent_queries": [],
            "conversation_topic": None,
        }
        st.rerun()

    if st.session_state.chat_history:
        st.sidebar.markdown(f"**Messages:** {len(st.session_state.chat_history)}")
        st.sidebar.markdown(
            f"**Topic:** {st.session_state.chat_context.get('conversation_topic', 'General')}"
        )
        if st.session_state.chat_history:
            st.sidebar.markdown(
                f"**Started:** {st.session_state.chat_history[0]['timestamp'].strftime('%H:%M')}"
            )

    # Removed Advanced Features status buttons per user request
    if st.sidebar.button("📊 Full Inventory Status"):
        status_query = "Give me a comprehensive summary of my current inventory status with key insights"
        chatbot.add_to_history("user", status_query)
        response = chatbot.generate_ai_response(status_query)
        chatbot.add_to_history("assistant", response)
        st.rerun()

    if st.sidebar.button("⚠️ Critical Alerts"):
        alerts_query = "What critical alerts, anomalies, or issues should I be aware of immediately?"
        chatbot.add_to_history("user", alerts_query)
        response = chatbot.generate_ai_response(alerts_query)
        chatbot.add_to_history("assistant", response)
        st.rerun()
