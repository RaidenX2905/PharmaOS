import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from utils import format_currency, format_dual_currency
from advanced_analytics import AdvancedAnalytics, WastageAnalyzer, CostOptimizer

class SmartRecommendationEngine:
    """Generates smart inventory recommendations and optimization opportunities using advanced analytics."""

    def __init__(self, database_manager: Optional[Any] = None) -> None:
        self.db = database_manager
        self.analytics = AdvancedAnalytics(database_manager) if database_manager else None
        self.wastage = WastageAnalyzer(database_manager) if database_manager else None
        self.cost = CostOptimizer(database_manager) if database_manager else None

    def get_personalized_recommendations(self) -> List[Dict[str, Any]]:
        """Generates a list of personalized recommendations based on inventory state."""
        if not self.db:
            return []
            
        recommendations = []
        
        # 1. Wastage Prevention Recommendations
        if self.wastage:
            wastage_recs = self.wastage.get_wastage_prevention_recommendations()
            for rec in wastage_recs:
                recommendations.append({
                    "type": "Wastage Prevention",
                    "title": f"Prevent wastage for {rec['drug_name']}",
                    "category": "Expiry Risk",
                    "description": rec["reason"],
                    "action": rec["action"],
                    "priority_score": 90 if rec["priority"] == "High" else 60,
                    "impact": "High" if rec["priority"] == "High" else "Medium",
                    "urgency": "Critical" if rec["priority"] == "High" else "High",
                    "estimated_cost": -float(rec["potential_loss"].replace('₹', '').replace(',', '')) if isinstance(rec["potential_loss"], str) else 0
                })

        # 2. Reorder Recommendations
        inventory = self.db.get_inventory()
        low_stock = inventory[inventory["current_stock"] <= inventory["min_stock_level"]]
        for _, item in low_stock.iterrows():
            recommendations.append({
                "type": "Restocking",
                "title": f"Reorder {item['drug_name']}",
                "category": "Stock Level",
                "description": f"Current stock ({int(item['current_stock'])}) is below minimum level ({int(item['min_stock_level'])}).",
                "action": f"Order at least {int(item['min_stock_level'] * 2)} units from {item['supplier_name']}.",
                "priority_score": 85 if item["current_stock"] == 0 else 70,
                "impact": "High",
                "urgency": "Critical" if item["current_stock"] == 0 else "High",
                "estimated_cost": item["current_stock"] * item["unit_price"]
            })

        # 3. Consumption Trend Insights
        if self.analytics:
            trends = self.analytics.analyze_consumption_patterns(30)
            for drug, data in trends.items():
                if data["trend"] == "Increasing":
                    recommendations.append({
                        "type": "Trend Adjustment",
                        "title": f"Adjust stock for {drug}",
                        "category": "Demand Pattern",
                        "description": f"Consumption for {drug} is increasing (slope: {data['slope']:.2f}).",
                        "action": "Consider increasing minimum stock levels to prevent stockouts.",
                        "priority_score": 50,
                        "impact": "Medium",
                        "urgency": "Medium",
                        "estimated_cost": 0
                    })

        # Sort by priority
        recommendations.sort(key=lambda x: x["priority_score"], reverse=True)
        return recommendations

    def get_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Identifies opportunities for cost and inventory optimization."""
        if not self.cost:
            return []
            
        cost_opps = self.cost.identify_cost_saving_opportunities()
        opportunities = []
        
        for opp in cost_opps:
            opportunities.append({
                "type": opp["type"],
                "drug_name": opp["drug_name"],
                "issue": opp["issue"],
                "recommendation": opp["recommendation"],
                "potential_savings": opp["potential_savings"],
                "implementation_cost": 0, # Assuming low implementation cost for data changes
                "roi_percentage": 100.0,
                "timeframe": "Immediate",
                "priority": opp["priority"]
            })
            
        return opportunities

def render_smart_recommendations(engine: SmartRecommendationEngine) -> None:
    st.markdown("### 💡 Personalized Recommendations")

    if st.button("🔮 Generate Smart Recommendations", type="primary"):
        with st.spinner("Analyzing inventory and generating personalized recommendations..."):
            recommendations = engine.get_personalized_recommendations()

            if recommendations:
                st.success(f"✅ Generated {len(recommendations)} recommendations")

                rec_types = list(set([r["type"] for r in recommendations]))
                selected_type = st.multiselect("Filter by Type", rec_types, default=rec_types)

                filtered_recs = [r for r in recommendations if r["type"] in selected_type]

                for i, rec in enumerate(filtered_recs, 1):
                    with st.expander(f"#{i} - {rec['title']} (Priority: {rec['priority_score']:.0f})"):
                        st.write(f"**Category:** {rec['category']}")
                        st.write(f"**Description:** {rec['description']}")
                        st.write(f"**Recommended Action:** {rec['action']}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            impact_color = "🟢" if rec["impact"] == "High" else "🟡" if rec["impact"] == "Medium" else "🔵"
                            st.write(f"{impact_color} **Impact:** {rec['impact']}")
                        with col2:
                            urgency_color = "🔴" if rec["urgency"] == "Critical" else "🟠" if rec["urgency"] == "High" else "🟡"
                            st.write(f"{urgency_color} **Urgency:** {rec['urgency']}")
                        with col3:
                            if rec["estimated_cost"] < 0:
                                st.write(f"💰 **Potential Savings:** {format_currency(abs(rec['estimated_cost']))}")
                            else:
                                st.write(f"💵 **Estimated Cost:** {format_currency(rec['estimated_cost'])}")
            else:
                st.info("No recommendations at this time. Your inventory is well-optimized!")

    st.markdown("### 💰 Top Optimization Opportunities")

    if st.button("🔍 Find Optimization Opportunities"):
        opportunities = engine.get_optimization_opportunities()

        if opportunities:
            for opp in opportunities:
                priority_color = "🔴" if opp.get("priority") == "High" else "🟡"
                with st.expander(f"{priority_color} {opp['type']}: {opp['drug_name']} - Potential Savings: {format_currency(opp['potential_savings'])}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Potential Savings", format_currency(opp["potential_savings"]))
                        st.metric("Implementation Cost", format_currency(opp["implementation_cost"]))
                    with col2:
                        st.metric("ROI %", f"{opp['roi_percentage']:.1f}%")
                        st.metric("Timeframe", opp["timeframe"])
        else:
            st.info("No major optimization opportunities identified.")
