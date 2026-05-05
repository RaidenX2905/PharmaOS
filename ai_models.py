import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import streamlit as st

warnings.filterwarnings("ignore")


class SmartReordering:
    def __init__(self):
        self.safety_factor = 1.5
        self.lead_time_variance = 0.2
        self.seasonal_weights = {}

    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def _get_all_seasonal_factors(_self, _db):
        """Pre-calculate seasonal demand factors for all drugs."""
        conn = _db.get_connection()
        query = """
            SELECT i.drug_name, strftime('%m', cp.date) as month,
                   AVG(cp.quantity_consumed) as avg_consumption
            FROM inventory i
            JOIN consumption_patterns cp ON i.id = cp.drug_id
            WHERE cp.date >= date('now', '-365 days')
            GROUP BY i.drug_name, month
        """
        seasonal_data = pd.read_sql_query(query, conn)
        conn.close()

        factors = {}
        for drug_name in seasonal_data["drug_name"].unique():
            drug_df = seasonal_data[seasonal_data["drug_name"] == drug_name]
            if len(drug_df) >= 3:
                current_month = datetime.now().month
                current_month_str = str(current_month).zfill(2)
                overall_avg = drug_df["avg_consumption"].mean()
                current_month_data = drug_df[drug_df["month"] == current_month_str]

                if not current_month_data.empty and overall_avg > 0:
                    current_avg = current_month_data["avg_consumption"].iloc[0]
                    seasonal_factor = current_avg / overall_avg
                    factors[drug_name] = max(0.5, min(2.0, seasonal_factor))
                else:
                    factors[drug_name] = 1.0
            else:
                factors[drug_name] = 1.0
        return factors

    @staticmethod
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def _get_all_supplier_performance(_db):
        """Pre-fetch all supplier performance metrics."""
        supplier_metrics = _db.get_supplier_metrics()

        if supplier_metrics.empty:
            return {}

        suppliers_data = supplier_metrics.to_dict("records")

        for supplier in suppliers_data:
            reliability_weight = 0.3
            cost_weight = 0.3
            quality_weight = 0.4

            norm_reliability = supplier["reliability_score"] / 5.0
            norm_cost = (6 - supplier["cost_rating"]) / 5.0
            norm_quality = supplier["quality_score"] / 5.0

            supplier["composite_score"] = (
                norm_reliability * reliability_weight
                + norm_cost * cost_weight
                + norm_quality * quality_weight
            )
            supplier["performance_grade"] = SmartReordering._get_performance_grade(
                supplier["composite_score"]
            )

        return {s["supplier_name"]: s for s in suppliers_data}

    def get_reorder_suggestions(self, _db, budget_limit=None):
        """Get intelligent reorder suggestions with budget constraints and supplier optimization"""
        data = _db.get_reorder_suggestions_data()

        # Pre-fetch and cache seasonal factors and supplier performance
        seasonal_factors = self._get_all_seasonal_factors(_db)
        all_supplier_performance = SmartReordering._get_all_supplier_performance(_db)

        suggestions = []
        total_cost = 0

        for _, row in data.iterrows():
            suggestion = self.analyze_item_for_reorder(
                row, seasonal_factors, all_supplier_performance
            )
            if suggestion:
                if (
                    budget_limit
                    and (total_cost + suggestion["estimated_cost"]) > budget_limit
                ):
                    suggestion["budget_constrained"] = True
                    suggestion["priority"] = "deferred"
                else:
                    total_cost += suggestion["estimated_cost"]
                    suggestion["budget_constrained"] = False
                suggestions.append(suggestion)

        priority_order = {"high": 3, "medium": 2, "low": 1, "deferred": 0}
        suggestions.sort(
            key=lambda x: (priority_order[x["priority"]], -x["estimated_cost"]),
            reverse=True,
        )

        return suggestions

    def analyze_item_for_reorder(
        self, item, seasonal_factors, all_supplier_performance
    ):
        """Enhanced analysis with seasonal patterns and multi-supplier optimization"""
        current_stock = item["current_stock"]
        minimum_stock = item["minimum_stock"]
        avg_daily_usage = item["avg_daily_usage"] or 0
        lead_time = item["lead_time_days"] or 7
        unit_price = item["unit_price"] or 0
        drug_name = item["drug_name"]

        seasonal_factor = seasonal_factors.get(drug_name, 1.0)
        adjusted_usage = avg_daily_usage * seasonal_factor

        safety_stock = adjusted_usage * lead_time * self.safety_factor
        reorder_point = minimum_stock + safety_stock

        if current_stock <= reorder_point:
            eoq = self.calculate_economic_order_quantity(
                adjusted_usage, unit_price, lead_time
            )

            suggested_quantity = max(
                eoq,
                self.calculate_order_quantity(
                    current_stock, adjusted_usage, lead_time, minimum_stock
                ),
            )

            stockout_risk = self.calculate_stockout_risk(
                current_stock,
                adjusted_usage,
                lead_time,
                item.get("demand_variability", 0.2),
            )

            if current_stock <= minimum_stock or stockout_risk > 0.7:
                priority = "high"
                reason = f"Critical: Stock below minimum ({current_stock} <= {minimum_stock}), Stockout risk: {stockout_risk:.1%}"
            elif current_stock <= minimum_stock * 1.5 or stockout_risk > 0.4:
                priority = "medium"
                reason = (
                    f"Stock approaching minimum, Stockout risk: {stockout_risk:.1%}"
                )
            else:
                priority = "low"
                reason = f"Preventive reorder recommended (Seasonal factor: {seasonal_factor:.2f})"

            days_until_stockout = (
                current_stock / adjusted_usage if adjusted_usage > 0 else float("inf")
            )

            optimal_supplier = self.select_optimal_supplier(
                item,
                required_quantity=suggested_quantity,
                all_supplier_performance=all_supplier_performance,
            )

            return {
                "id": item["id"],
                "drug_name": drug_name,
                "current_stock": current_stock,
                "minimum_stock": minimum_stock,
                "suggested_quantity": int(suggested_quantity),
                "eoq": int(eoq),
                "priority": priority,
                "reason": reason,
                "days_until_stockout": int(days_until_stockout)
                if days_until_stockout != float("inf")
                else 999,
                "avg_daily_usage": avg_daily_usage,
                "adjusted_usage": adjusted_usage,
                "seasonal_factor": seasonal_factor,
                "stockout_risk": stockout_risk,
                "supplier": optimal_supplier.get("name", item["supplier_name"])
                if optimal_supplier
                else item["supplier_name"],
                "supplier_score": optimal_supplier.get("composite_score", 0.5)
                if optimal_supplier
                else 0.5,
                "lead_time": optimal_supplier.get("lead_time_days", lead_time)
                if optimal_supplier
                else lead_time,
                "estimated_cost": suggested_quantity * unit_price,
                "cost_per_day": (suggested_quantity * unit_price)
                / (suggested_quantity / adjusted_usage)
                if adjusted_usage > 0
                else 0,
            }

        return None

    def get_seasonal_factor(self, drug_name, _db):
        """Calculate seasonal demand factor for the drug"""
        # This method is now effectively replaced by _get_all_seasonal_factors
        # but kept for potential direct use or testing.
        # It should ideally use the pre-calculated factors if available.
        # For this exercise, we'll assume the pre-calculated factors are always used.
        return 1.0  # Fallback, should not be reached if pre-calculation works

    def calculate_economic_order_quantity(self, annual_demand, unit_price, lead_time):
        """Calculate Economic Order Quantity (EOQ) with advanced parameters"""
        if annual_demand <= 0 or unit_price <= 0:
            return 50

        ordering_cost = 100
        holding_cost_rate = 0.25
        annual_demand_units = annual_demand * 365

        eoq = np.sqrt(
            (2 * annual_demand_units * ordering_cost) / (unit_price * holding_cost_rate)
        )

        eoq = max(annual_demand * lead_time, eoq)

        return max(10, eoq)

    def calculate_order_quantity(
        self, current_stock, avg_daily_usage, lead_time, minimum_stock
    ):
        """Calculate optimal order quantity with safety considerations"""
        if avg_daily_usage <= 0:
            return minimum_stock * 2

        target_stock = avg_daily_usage * lead_time * 2.5 + minimum_stock
        order_quantity = max(0, target_stock - current_stock)

        min_order = avg_daily_usage * 7
        order_quantity = max(order_quantity, min_order)

        return order_quantity

    def calculate_stockout_risk(
        self, current_stock, avg_daily_usage, lead_time, demand_variability
    ):
        """Calculate probability of stockout during lead time"""
        if avg_daily_usage <= 0:
            return 0.0

        expected_demand = avg_daily_usage * lead_time
        demand_std = avg_daily_usage * lead_time * demand_variability

        if demand_std <= 0:
            return 0.0 if current_stock >= expected_demand else 1.0

        z_score = (current_stock - expected_demand) / demand_std

        stockout_probability = 0.5 * (1 - np.tanh(z_score))

        return max(0.0, min(1.0, stockout_probability))

    def select_optimal_supplier(
        self, item, required_quantity, all_supplier_performance
    ):
        """Select optimal supplier using multi-criteria optimization"""
        try:
            # Filter suppliers relevant to the current item's original supplier
            # or consider top performing suppliers if item's supplier is not found
            item_supplier_name = item.get("supplier_name")
            relevant_suppliers = []
            if item_supplier_name and item_supplier_name in all_supplier_performance:
                relevant_suppliers.append(all_supplier_performance[item_supplier_name])

            # Add top 2-3 overall performing suppliers if no specific supplier or for wider choice
            sorted_suppliers = sorted(
                all_supplier_performance.values(),
                key=lambda x: x["composite_score"],
                reverse=True,
            )
            for s in sorted_suppliers:
                if s not in relevant_suppliers:
                    relevant_suppliers.append(s)
                if (
                    len(relevant_suppliers) >= 3
                ):  # Limit to 3 relevant suppliers for consideration
                    break

            if not relevant_suppliers:
                return None

            best_supplier = None
            best_score = -1

            for supplier in relevant_suppliers:
                reliability_weight = 0.35
                cost_weight = 0.30
                quality_weight = 0.25
                speed_weight = 0.10

                norm_reliability = supplier.get("reliability_score", 3) / 5.0
                norm_cost = (6 - supplier.get("cost_rating", 3)) / 5.0
                norm_quality = supplier.get("quality_score", 3) / 5.0

                lead_time = supplier.get("lead_time_days", 7)
                norm_speed = max(0, (14 - lead_time)) / 14.0

                composite_score = (
                    norm_reliability * reliability_weight
                    + norm_cost * cost_weight
                    + norm_quality * quality_weight
                    + norm_speed * speed_weight
                )

                supplier["composite_score"] = composite_score

                if composite_score > best_score:
                    best_score = composite_score
                    best_supplier = supplier

            return best_supplier
        except Exception as e:
            # Log the error for debugging, but return None to not break the app
            print(f"Error selecting optimal supplier: {e}")
            return None

    def analyze_suppliers(self, _db):
        """Analyze supplier performance with enhanced metrics"""
        # This method is now effectively replaced by _get_all_supplier_performance
        # and should not be called directly in the reordering flow.
        # It's kept for potential other uses.
        supplier_metrics = _db.get_supplier_metrics()

        if supplier_metrics.empty:
            return []

        suppliers = supplier_metrics.to_dict("records")

        for supplier in suppliers:
            reliability_weight = 0.3
            cost_weight = 0.3
            quality_weight = 0.4

            norm_reliability = supplier["reliability_score"] / 5.0
            norm_cost = (6 - supplier["cost_rating"]) / 5.0
            norm_quality = supplier["quality_score"] / 5.0

            supplier["composite_score"] = (
                norm_reliability * reliability_weight
                + norm_cost * cost_weight
                + norm_quality * quality_weight
            )

            supplier["performance_grade"] = self._get_performance_grade(
                supplier["composite_score"]
            )

        return sorted(suppliers, key=lambda x: x["composite_score"], reverse=True)

    @staticmethod
    def _get_performance_grade(score):
        """Convert composite score to a letter grade."""
        if score > 0.85:
            return "A+"
        elif score > 0.75:
            return "A"
        elif score > 0.6:
            return "B"
        elif score > 0.45:
            return "C"
        else:
            return "D"


class ExpiryPredictor:
    def __init__(self):
        self.risk_thresholds = {"low": 0.3, "medium": 0.6, "high": 0.8}

    def predict_expiry_risk(self, drug_name, db):
        """Predict expiry risk for a specific drug with enhanced analytics"""
        try:
            consumption_data = db.get_historical_consumption(drug_name)
            current_stock = db.get_current_stock(drug_name)

            if consumption_data.empty or current_stock == 0:
                return None

            daily_consumption = consumption_data["consumption"].values
            avg_consumption = np.mean(daily_consumption)
            std_consumption = np.std(daily_consumption)

            if len(daily_consumption) > 7:
                recent_avg = np.mean(daily_consumption[-7:])
                older_avg = np.mean(daily_consumption[:-7])
                trend = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            else:
                trend = 0

            if avg_consumption > 0:
                days_to_use = current_stock / avg_consumption
            else:
                days_to_use = float("inf")

            risk_score = self.calculate_risk_score(
                days_to_use, trend, std_consumption, avg_consumption
            )

            if risk_score >= self.risk_thresholds["high"]:
                risk_level = "high"
            elif risk_score >= self.risk_thresholds["medium"]:
                risk_level = "medium"
            else:
                risk_level = "low"

            predicted_wastage = self.predict_wastage(
                current_stock, avg_consumption, trend, days_to_use
            )

            recommendations = self.generate_expiry_recommendations(
                drug_name, risk_level, days_to_use, predicted_wastage, trend
            )

            trend_data = self.generate_trend_data(
                consumption_data, avg_consumption, trend
            )

            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "days_to_use": days_to_use,
                "predicted_wastage": predicted_wastage,
                "recommendations": recommendations,
                "trend_data": trend_data,
                "consumption_volatility": std_consumption / avg_consumption
                if avg_consumption > 0
                else 0,
                "trend_direction": "Increasing"
                if trend > 0.1
                else "Decreasing"
                if trend < -0.1
                else "Stable",
            }

        except Exception as e:
            return None

    def calculate_risk_score(
        self, days_to_use, trend, std_consumption, avg_consumption
    ):
        """Calculate expiry risk score (0-1) with enhanced factors"""
        risk_score = 0

        if days_to_use < 30:
            risk_score += 0.5
        elif days_to_use < 60:
            risk_score += 0.3
        elif days_to_use < 90:
            risk_score += 0.2
        else:
            risk_score += 0.1

        if trend < -0.2:
            risk_score += 0.3
        elif trend < -0.1:
            risk_score += 0.2
        elif trend < 0:
            risk_score += 0.1

        if avg_consumption > 0:
            cv = std_consumption / avg_consumption
            if cv > 1:
                risk_score += 0.2
            elif cv > 0.5:
                risk_score += 0.1

        return min(1.0, risk_score)

    def predict_wastage(self, current_stock, avg_consumption, trend, days_to_use):
        """Predict potential wastage with trend-based adjustments"""
        if days_to_use > 365:
            wastage_rate = 0.0
        elif days_to_use > 180:
            wastage_rate = 0.01
        elif days_to_use > 90:
            wastage_rate = 0.03
        elif days_to_use > 30:
            wastage_rate = 0.06
        else:
            wastage_rate = 0.02

        if trend < -0.2:
            wastage_rate *= 2.0
        elif trend < -0.1:
            wastage_rate *= 1.5
        elif trend > 0.1:
            wastage_rate *= 0.6

        predicted_wastage = current_stock * wastage_rate
        return max(0, predicted_wastage)

    def generate_expiry_recommendations(
        self, drug_name, risk_level, days_to_use, predicted_wastage, trend
    ):
        """Generate comprehensive recommendations based on expiry risk"""
        recommendations = []

        if risk_level == "high":
            recommendations.append(
                f"🚨 HIGH RISK: {drug_name} - Immediate action required"
            )
            recommendations.append(
                "• Implement aggressive promotional pricing (20-30% discount)"
            )
            recommendations.append(
                "• Transfer stock to high-demand departments/branches"
            )
            recommendations.append(
                "• Contact supplier for possible returns or exchanges"
            )
            recommendations.append("• Consider donation to charitable organizations")
            if trend < -0.1:
                recommendations.append("• Address declining demand - investigate cause")

        elif risk_level == "medium":
            recommendations.append(f"⚠️ MEDIUM RISK: {drug_name} - Monitor closely")
            recommendations.append(
                "• Implement moderate promotional activities (10-15% discount)"
            )
            recommendations.append("• Review and adjust minimum stock levels")
            recommendations.append("• Consider inter-departmental transfers")
            recommendations.append("• Pause new orders until stock normalizes")

        else:
            recommendations.append(f"✅ LOW RISK: {drug_name} - Normal operations")
            recommendations.append("• Continue regular monitoring")
            recommendations.append("• Maintain current inventory practices")

        if predicted_wastage > 10:
            recommendations.append(
                f"💰 Potential loss: ~{predicted_wastage:.0f} units (₹{predicted_wastage * 10:.2f} estimated)"
            )

        if days_to_use < 30:
            recommendations.append("⏰ URGENT: Less than 30 days to use current stock!")
        elif days_to_use < 60:
            recommendations.append("⏰ ATTENTION: 30-60 days to use current stock")

        return recommendations

    def generate_trend_data(self, consumption_data, avg_consumption, trend):
        """Generate data for trend visualization with predictions"""
        dates = consumption_data["date"].tolist()
        consumption = consumption_data["consumption"].tolist()

        future_dates = pd.date_range(
            start=dates[-1] + timedelta(days=1), periods=30, freq="D"
        ).tolist()

        predicted_consumption = []
        for i in range(30):
            predicted_value = avg_consumption + (trend * avg_consumption * i / 30)
            noise = np.random.normal(0, avg_consumption * 0.1)
            predicted_value += noise
            predicted_consumption.append(max(0, predicted_value))

        return {
            "dates": dates,
            "consumption": consumption,
            "future_dates": future_dates,
            "predicted_consumption": predicted_consumption,
            "avg_consumption": avg_consumption,
            "trend_slope": trend,
        }
