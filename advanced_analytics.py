import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict
import sqlite3
import warnings
import os

warnings.filterwarnings("ignore")

# Check for heavy features flag
DISABLE_HEAVY = os.environ.get("DISABLE_HEAVY_FEATURES", "false").lower() == "true"



class AdvancedAnalytics:
    """Advanced analytics for pharmaceutical inventory with ML-powered anomaly detection"""

    def __init__(self, db_manager):
        self.db = db_manager

    def analyze_consumption_patterns(self, days=90):
        """Analyze consumption patterns and identify trends"""
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, i.category, cp.date, cp.quantity_consumed, cp.department
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', ? || ' days')
            ORDER BY cp.date
        """
        df = pd.read_sql_query(query, conn, params=(f"-{days}",))
        conn.close()

        if df.empty:
            return {}

        df["date"] = pd.to_datetime(df["date"])

        trends = {}
        for drug in df["drug_name"].unique()[:50]:
            drug_data = df[df["drug_name"] == drug].copy()
            drug_data = drug_data.sort_values("date")

            if len(drug_data) >= 7:
                from scipy import stats
                x = np.arange(len(drug_data))
                y = drug_data["quantity_consumed"].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

                if slope > 0.5:
                    trend = "Increasing"
                elif slope < -0.5:
                    trend = "Decreasing"
                else:
                    trend = "Stable"

                trends[drug] = {
                    "trend": trend,
                    "slope": float(slope),
                    "r_squared": float(r_value**2),
                    "avg_consumption": float(drug_data["quantity_consumed"].mean()),
                    "std_dev": float(drug_data["quantity_consumed"].std()),
                    "category": drug_data["category"].iloc[0],
                }

        return trends

    def detect_anomalies(self, threshold=2.5, use_ensemble=True):
        """
        Advanced multi-algorithm anomaly detection system
        Uses Z-score, Isolation Forest, and DBSCAN for comprehensive anomaly detection
        """
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, i.category, cp.date, cp.quantity_consumed, cp.department
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', '-180 days')
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return []

        df["date"] = pd.to_datetime(df["date"])
        all_anomalies = []

        for drug in df["drug_name"].unique()[:150]:
            drug_data = df[df["drug_name"] == drug].copy()

            if len(drug_data) >= 15:
                drug_data = drug_data.sort_values("date").reset_index(drop=True)

                anomalies = self._detect_drug_anomalies_ensemble(
                    drug_data, threshold, use_ensemble
                )
                all_anomalies.extend(anomalies)

        all_anomalies = sorted(
            all_anomalies, key=lambda x: x["severity_score"], reverse=True
        )[:50]
        return all_anomalies

    def _detect_drug_anomalies_ensemble(self, drug_data, threshold, use_ensemble):
        """Detect anomalies using ensemble of multiple ML algorithms"""
        anomalies = []
        drug_name = drug_data["drug_name"].iloc[0]
        category = drug_data["category"].iloc[0]

        consumption = drug_data["quantity_consumed"].values
        dates = drug_data["date"].values

        if use_ensemble:
            anomaly_scores = self._calculate_ensemble_anomaly_scores(drug_data)
        else:
            anomaly_scores = self._calculate_zscore_anomalies(consumption)

        for idx, score in enumerate(anomaly_scores):
            if abs(score) > threshold:
                severity = self._calculate_severity(
                    score, consumption[idx], consumption
                )
                anomaly_type = "High Consumption" if score > 0 else "Low Consumption"

                anomalies.append(
                    {
                        "drug_name": drug_name,
                        "category": category,
                        "date": pd.Timestamp(dates[idx]).strftime("%Y-%m-%d"),
                        "consumption": int(consumption[idx]),
                        "expected": int(np.mean(consumption)),
                        "deviation": float(score),
                        "severity_score": severity,
                        "type": anomaly_type,
                        "detection_method": "Ensemble ML"
                        if use_ensemble
                        else "Z-Score",
                        "confidence": self._calculate_confidence(score),
                    }
                )

        return anomalies

    def _calculate_ensemble_anomaly_scores(self, drug_data):
        """
        Use ensemble of Z-score, Isolation Forest, and DBSCAN
        Z-score provides direction (sign), auxiliary models provide magnitude weighting
        """
        consumption = drug_data["quantity_consumed"].values.reshape(-1, 1)
        n_samples = len(consumption)

        z_scores = self._calculate_zscore_anomalies(consumption.flatten())

        magnitude_weights = np.ones(n_samples)

        if n_samples >= 20:
            try:
                from sklearn.ensemble import IsolationForest
                iso_forest = IsolationForest(
                    contamination=0.1, random_state=42, n_estimators=100
                )
                iso_forest.fit(consumption)
                iso_anomaly_scores = -iso_forest.score_samples(consumption)
                iso_normalized = (iso_anomaly_scores - np.mean(iso_anomaly_scores)) / (
                    np.std(iso_anomaly_scores) + 1e-6
                )
                magnitude_weights += np.abs(iso_normalized)
            except:
                pass

        if n_samples >= 10:
            try:
                from sklearn.preprocessing import StandardScaler
                from sklearn.cluster import DBSCAN
                scaler = StandardScaler()
                consumption_scaled = scaler.fit_transform(consumption)

                dbscan = DBSCAN(eps=0.5, min_samples=max(2, n_samples // 10))
                clusters = dbscan.fit_predict(consumption_scaled)

                for idx, cluster in enumerate(clusters):
                    if cluster == -1:
                        magnitude_weights[idx] += 1.0
            except:
                pass

        ensemble_scores = z_scores * (magnitude_weights / 2.0)

        return ensemble_scores

    def _calculate_zscore_anomalies(self, consumption):
        """Calculate Z-score based anomalies"""
        mean = np.mean(consumption)
        std = np.std(consumption)

        if std > 0:
            z_scores = (consumption - mean) / std
        else:
            z_scores = np.zeros(len(consumption))

        return z_scores

    def _calculate_severity(self, deviation, actual, all_consumption):
        """Calculate severity score (0-100) for anomaly"""
        abs_deviation = abs(deviation)
        max_deviation = max(
            abs(all_consumption - np.mean(all_consumption))
            / (np.std(all_consumption) + 1e-6)
        )

        normalized_deviation = min(abs_deviation / (max_deviation + 1e-6), 1.0) * 100

        impact = abs(actual - np.mean(all_consumption)) / (np.mean(all_consumption) + 1)
        impact_score = min(impact * 50, 50)

        severity = normalized_deviation * 0.6 + impact_score * 0.4

        return float(min(severity, 100))

    def _calculate_confidence(self, deviation):
        """Calculate confidence level for anomaly detection"""
        abs_dev = abs(deviation)
        if abs_dev > 5:
            return "Very High"
        elif abs_dev > 4:
            return "High"
        elif abs_dev > 3:
            return "Medium"
        elif abs_dev > 2:
            return "Low"
        else:
            return "Very Low"

    def get_anomaly_summary(self):
        """Get comprehensive anomaly summary with statistics"""
        anomalies = self.detect_anomalies()

        if not anomalies:
            return {
                "total_anomalies": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "affected_categories": [],
                "top_drugs": [],
            }

        df = pd.DataFrame(anomalies)

        high_severity = len(df[df["severity_score"] >= 70])
        medium_severity = len(
            df[(df["severity_score"] >= 40) & (df["severity_score"] < 70)]
        )
        low_severity = len(df[df["severity_score"] < 40])

        affected_categories = df["category"].unique().tolist()
        top_drugs = df.groupby("drug_name").size().nlargest(10).to_dict()

        return {
            "total_anomalies": len(anomalies),
            "high_severity": high_severity,
            "medium_severity": medium_severity,
            "low_severity": low_severity,
            "affected_categories": affected_categories,
            "top_drugs": top_drugs,
            "recent_anomalies": anomalies[:10],
        }

    def cluster_drugs_by_demand(self, n_clusters=5):
        """Cluster drugs by demand patterns using K-Means"""
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, i.category,
                   AVG(cp.quantity_consumed) as avg_consumption,
                   SUM(cp.quantity_consumed) as total_consumption,
                   COUNT(cp.id) as frequency
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', '-90 days')
            GROUP BY i.drug_name, i.category
            HAVING COUNT(cp.id) >= 10
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if len(df) < n_clusters:
            return {}

        X = df[["avg_consumption", "total_consumption", "frequency"]].values
        X_normalized = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-6)

        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["cluster"] = kmeans.fit_predict(X_normalized)

        clusters = {}
        for cluster_id in range(n_clusters):
            cluster_drugs = df[df["cluster"] == cluster_id]
            clusters[f"Cluster {cluster_id + 1}"] = {
                "drugs": cluster_drugs["drug_name"].tolist()[:10],
                "count": len(cluster_drugs),
                "avg_consumption": float(cluster_drugs["avg_consumption"].mean()),
                "total_consumption": float(cluster_drugs["total_consumption"].sum()),
                "description": self._get_cluster_description(cluster_drugs),
            }

        return clusters

    def _get_cluster_description(self, cluster_df):
        """Generate description for a cluster"""
        avg_cons = cluster_df["avg_consumption"].mean()

        if avg_cons > 50:
            return "High-demand drugs requiring frequent restocking"
        elif avg_cons > 20:
            return "Medium-demand drugs with regular usage"
        elif avg_cons > 5:
            return "Low-to-medium demand drugs"
        else:
            return "Low-demand drugs for specific cases"

    def calculate_seasonal_indices(self):
        """Calculate seasonal indices for drugs"""
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, i.category,
                   CAST(strftime('%m', cp.date) AS INTEGER) as month,
                   AVG(cp.quantity_consumed) as avg_consumption
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', '-365 days')
            GROUP BY i.drug_name, i.category, month
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return {}

        seasonal_drugs = {}

        for drug in df["drug_name"].unique()[:50]:
            drug_data = df[df["drug_name"] == drug].copy()

            if len(drug_data) >= 6:
                overall_avg = drug_data["avg_consumption"].mean()

                if overall_avg > 0:
                    drug_data["seasonal_index"] = (
                        drug_data["avg_consumption"] / overall_avg
                    )

                    peak_month = drug_data.loc[
                        drug_data["seasonal_index"].idxmax(), "month"
                    ]
                    low_month = drug_data.loc[
                        drug_data["seasonal_index"].idxmin(), "month"
                    ]
                    peak_index = drug_data["seasonal_index"].max()
                    low_index = drug_data["seasonal_index"].min()

                    if peak_index > 1.2 or low_index < 0.8:
                        seasonal_drugs[drug] = {
                            "peak_month": int(peak_month),
                            "peak_index": float(peak_index),
                            "low_month": int(low_month),
                            "low_index": float(low_index),
                            "seasonality": "High" if peak_index > 1.5 else "Moderate",
                            "category": drug_data["category"].iloc[0],
                        }

        return seasonal_drugs

    def analyze_drug_correlations(self, selected_drugs=None):
        """Analyze correlations between drug consumption patterns"""
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, cp.date, SUM(cp.quantity_consumed) as daily_consumption
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', '-180 days')
            GROUP BY i.drug_name, cp.date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return {}

        pivot_df = df.pivot(
            index="date", columns="drug_name", values="daily_consumption"
        ).fillna(0)

        if selected_drugs and len(selected_drugs) >= 2:
            # Filter for selected drugs that exist in the pivot table
            available_drugs = [d for d in selected_drugs if d in pivot_df.columns]
            if len(available_drugs) < 2:
                # If less than 2 selected drugs found, fall back to top drugs or return empty
                top_drugs = pivot_df.sum().nlargest(30).index.tolist()
                pivot_df = pivot_df[top_drugs]
            else:
                pivot_df = pivot_df[available_drugs]
        else:
            top_drugs = pivot_df.sum().nlargest(30).index.tolist()
            pivot_df = pivot_df[top_drugs]

        correlation_matrix = pivot_df.corr()

        strong_correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i + 1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.5:  # Lowered from 0.7 for better visibility
                    strong_correlations.append(
                        {
                            "drug1": correlation_matrix.columns[i],
                            "drug2": correlation_matrix.columns[j],
                            "correlation": float(corr_value),
                            "relationship": "Positive"
                            if corr_value > 0
                            else "Negative",
                        }
                    )

        strong_correlations = sorted(
            strong_correlations, key=lambda x: abs(x["correlation"]), reverse=True
        )[:20]

        return {
            "correlations": strong_correlations,
            "correlation_matrix": correlation_matrix.to_dict()
            if len(correlation_matrix) > 0
            else {},
        }


class WastageAnalyzer:
    """Analyze and prevent drug wastage"""

    def __init__(self, db_manager):
        self.db = db_manager

    def calculate_wastage(self):
        """Calculate wastage from expired drugs"""
        conn = self.db.get_connection()

        query = """
            SELECT drug_name, category, batch_number, current_stock, unit_price,
                   expiry_date, current_stock * unit_price as wastage_value
            FROM inventory
            WHERE expiry_date < date('now')
            ORDER BY wastage_value DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return {
                "total_wastage_value": 0,
                "total_wastage_units": 0,
                "wastage_by_category": {},
                "expired_items": [],
            }

        total_value = df["wastage_value"].sum()
        total_units = df["current_stock"].sum()

        category_wastage = (
            df.groupby("category")
            .agg({"wastage_value": "sum", "current_stock": "sum"})
            .to_dict("index")
        )

        expired_items = df.to_dict("records")[:20]

        return {
            "total_wastage_value": float(total_value),
            "total_wastage_units": int(total_units),
            "wastage_by_category": category_wastage,
            "expired_items": expired_items,
        }

    def predict_potential_wastage(self, days_ahead=90):
        """Predict potential wastage in next N days"""
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, i.category, i.batch_number, i.current_stock,
                   i.unit_price, i.expiry_date,
                   CAST(julianday(i.expiry_date) - julianday('now') AS INTEGER) as days_to_expiry,
                   AVG(cp.quantity_consumed) as avg_daily_usage,
                   i.current_stock * i.unit_price as potential_loss
            FROM inventory i
            LEFT JOIN consumption_patterns cp ON i.id = cp.drug_id
                AND cp.date >= date('now', '-30 days')
            WHERE i.expiry_date BETWEEN date('now') AND date('now', '+' || ? || ' days')
            GROUP BY i.id, i.drug_name, i.category, i.batch_number, i.current_stock,
                     i.unit_price, i.expiry_date
        """
        df = pd.read_sql_query(query, conn, params=(days_ahead,))
        conn.close()

        if df.empty:
            return []

        df["avg_daily_usage"] = df["avg_daily_usage"].fillna(0)
        df["expected_usage"] = df["avg_daily_usage"] * df["days_to_expiry"]
        df["excess_stock"] = df["current_stock"] - df["expected_usage"]
        df["wastage_risk"] = df.apply(
            lambda row: "High"
            if row["excess_stock"] > row["current_stock"] * 0.5
            else "Medium"
            if row["excess_stock"] > 0
            else "Low",
            axis=1,
        )

        at_risk = df[df["wastage_risk"].isin(["High", "Medium"])].copy()
        at_risk["potential_wastage_value"] = (
            at_risk["excess_stock"] * at_risk["unit_price"]
        )

        return at_risk.sort_values("potential_wastage_value", ascending=False).to_dict(
            "records"
        )[:30]

    def get_wastage_prevention_recommendations(self):
        """Get recommendations to prevent wastage"""
        potential_wastage = self.predict_potential_wastage()

        recommendations = []

        for item in potential_wastage[:15]:
            if item["wastage_risk"] == "High":
                recommendations.append(
                    {
                        "drug_name": item["drug_name"],
                        "action": "URGENT: Promote usage or transfer",
                        "reason": f"High wastage risk: {int(item['excess_stock'])} units may expire in {int(item['days_to_expiry'])} days",
                        "potential_loss": f"₹{item['potential_wastage_value']:.2f}",
                        "priority": "High",
                    }
                )
            elif item["wastage_risk"] == "Medium":
                recommendations.append(
                    {
                        "drug_name": item["drug_name"],
                        "action": "Monitor and reduce orders",
                        "reason": f"Moderate wastage risk: {int(item['excess_stock'])} excess units",
                        "potential_loss": f"₹{item['potential_wastage_value']:.2f}",
                        "priority": "Medium",
                    }
                )

        return recommendations


class CostOptimizer:
    """Optimize inventory costs"""

    def __init__(self, db_manager):
        self.db = db_manager

    def identify_cost_saving_opportunities(self):
        """Identify opportunities to reduce costs"""
        conn = self.db.get_connection()

        query = """
            SELECT i.drug_name, i.category, i.current_stock, i.minimum_stock,
                   i.unit_price, i.supplier_name,
                   AVG(cp.quantity_consumed) as avg_daily_usage,
                   i.current_stock * i.unit_price as inventory_value
            FROM inventory i
            LEFT JOIN consumption_patterns cp ON i.id = cp.drug_id
                AND cp.date >= date('now', '-30 days')
            GROUP BY i.id, i.drug_name, i.category, i.current_stock, i.minimum_stock,
                     i.unit_price, i.supplier_name
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return []

        df["avg_daily_usage"] = df["avg_daily_usage"].fillna(0)
        df["days_of_stock"] = df.apply(
            lambda row: row["current_stock"] / row["avg_daily_usage"]
            if row["avg_daily_usage"] > 0
            else 999,
            axis=1,
        )
        df["excess_stock"] = df.apply(
            lambda row: max(0, row["current_stock"] - (row["minimum_stock"] * 2)),
            axis=1,
        )
        df["potential_savings"] = df["excess_stock"] * df["unit_price"]

        opportunities = []

        overstocked = df[df["days_of_stock"] > 60].sort_values(
            "potential_savings", ascending=False
        )
        for _, row in overstocked.head(10).iterrows():
            opportunities.append(
                {
                    "type": "Overstocking",
                    "drug_name": row["drug_name"],
                    "issue": f"Has {int(row['days_of_stock'])} days of stock",
                    "recommendation": f"Reduce stock by {int(row['excess_stock'])} units",
                    "potential_savings": float(row["potential_savings"]),
                    "priority": "High" if row["potential_savings"] > 1000 else "Medium",
                }
            )

        slow_moving = df[df["avg_daily_usage"] < 1].sort_values(
            "inventory_value", ascending=False
        )
        for _, row in slow_moving.head(10).iterrows():
            if row["current_stock"] > row["minimum_stock"]:
                opportunities.append(
                    {
                        "type": "Slow-Moving",
                        "drug_name": row["drug_name"],
                        "issue": f"Low usage ({row['avg_daily_usage']:.1f} units/day)",
                        "recommendation": "Reduce minimum stock level or discontinue",
                        "potential_savings": float(row["inventory_value"] * 0.2),
                        "priority": "Medium",
                    }
                )

        return sorted(
            opportunities, key=lambda x: x["potential_savings"], reverse=True
        )[:20]

    def calculate_economic_order_quantity(self, drug_name):
        """Calculate optimal order quantity (EOQ)"""
        conn = self.db.get_connection()

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT unit_price, current_stock FROM inventory
            WHERE drug_name = ? LIMIT 1
        """,
            (drug_name,),
        )
        drug_data = cursor.fetchone()

        if not drug_data:
            conn.close()
            return None

        unit_price = drug_data[0]

        cursor.execute(
            """
            SELECT SUM(quantity_consumed) as annual_demand
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE i.drug_name = ? AND cp.date >= date('now', '-365 days')
        """,
            (drug_name,),
        )
        demand_data = cursor.fetchone()
        conn.close()

        if not demand_data or not demand_data[0]:
            return None

        annual_demand = demand_data[0]

        ordering_cost = 100
        holding_cost_rate = 0.25
        holding_cost = unit_price * holding_cost_rate

        if holding_cost > 0:
            eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)

            return {
                "drug_name": drug_name,
                "optimal_order_quantity": int(eoq),
                "annual_demand": int(annual_demand),
                "order_frequency": int(annual_demand / eoq) if eoq > 0 else 0,
                "total_annual_cost": float(
                    (annual_demand / eoq) * ordering_cost + (eoq / 2) * holding_cost
                )
                if eoq > 0
                else 0,
            }

        return None


class DrugUtilizationReview:
    """Perform drug utilization review"""

    def __init__(self, _db_manager):
        self._db = _db_manager

    def analyze_utilization(self):
        """Analyze drug utilization patterns"""
        conn = self._db.get_connection()

        query = """
            SELECT i.drug_name, i.category,
                   SUM(cp.quantity_consumed) as total_consumed,
                   COUNT(DISTINCT cp.date) as days_used,
                   COUNT(DISTINCT cp.department) as departments_using,
                   AVG(cp.quantity_consumed) as avg_daily_usage
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', '-90 days')
            GROUP BY i.drug_name, i.category
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return {
                "high_utilization": [],
                "low_utilization": [],
                "moderate_utilization": [],
            }

        df["utilization_score"] = df["total_consumed"] / df["days_used"]

        high_threshold = df["utilization_score"].quantile(0.75)
        low_threshold = df["utilization_score"].quantile(0.25)

        high_util = df[df["utilization_score"] >= high_threshold].to_dict("records")[
            :15
        ]
        low_util = df[df["utilization_score"] <= low_threshold].to_dict("records")[:15]
        moderate_util = df[
            (df["utilization_score"] > low_threshold)
            & (df["utilization_score"] < high_threshold)
        ].to_dict("records")[:15]

        return {
            "high_utilization": high_util,
            "low_utilization": low_util,
            "moderate_utilization": moderate_util,
        }

    def get_department_utilization(self):
        """Analyze utilization by department"""
        conn = self._db.get_connection()

        query = """
            SELECT department, i.category,
                   SUM(cp.quantity_consumed) as total_consumed,
                   COUNT(DISTINCT i.drug_name) as unique_drugs
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE cp.date >= date('now', '-90 days') AND department IS NOT NULL
            GROUP BY department, i.category
            ORDER BY total_consumed DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        return df.to_dict("records") if not df.empty else []

    @staticmethod
    def perform_dur(drug_name: str, _db) -> Optional[Dict]:
        """
        Performs a Drug Utilization Review for a specific drug.
        This is a simplified example and can be expanded with more complex logic.
        """
        try:
            conn = _db.get_connection()

            # Get basic drug info and recent consumption
            drug_info_query = """
                SELECT id, drug_name, category, current_stock, minimum_stock, unit_price
                FROM inventory WHERE drug_name = ?
            """
            drug_info = pd.read_sql_query(drug_info_query, conn, params=(drug_name,))

            consumption_query = """
                SELECT SUM(quantity_consumed) as total_consumed_90_days,
                       AVG(quantity_consumed) as avg_daily_consumed_90_days
                FROM consumption_patterns cp
                JOIN inventory i ON cp.drug_id = i.id
                WHERE i.drug_name = ? AND cp.date >= date('now', '-90 days')
            """
            consumption_data = pd.read_sql_query(
                consumption_query, conn, params=(drug_name,)
            )
            conn.close()

            if drug_info.empty:
                return None

            drug_info = drug_info.iloc[0].to_dict()
            total_consumed = (
                consumption_data["total_consumed_90_days"].iloc[0]
                if not consumption_data.empty
                else 0
            )
            avg_daily_consumed = (
                consumption_data["avg_daily_consumed_90_days"].iloc[0]
                if not consumption_data.empty
                else 0
            )

            # Generate a simple DUR report
            report = {
                "drug_name": drug_name,
                "category": drug_info["category"],
                "current_stock": drug_info["current_stock"],
                "total_consumed_90_days": total_consumed,
                "avg_daily_consumed_90_days": avg_daily_consumed,
                "recommendations": [],
            }

            if total_consumed == 0 and drug_info["current_stock"] > 0:
                report["recommendations"].append(
                    f"Consider promoting {drug_name} as there has been no consumption in the last 90 days despite having stock."
                )

            return report

        except Exception as e:
            print(f"Error during DUR for {drug_name}: {e}")
            return None


class AutomatedInsightsGenerator:
    """Generate automated insights with natural language explanations"""

    def __init__(self, _db_manager):
        self._db = _db_manager
        self.analytics = AdvancedAnalytics(self._db)

    def generate_daily_insights(self):
        """Generate comprehensive daily insights"""
        insights = []

        anomaly_summary = self.analytics.get_anomaly_summary()
        if anomaly_summary["total_anomalies"] > 0:
            insights.append(
                {
                    "type": "anomaly_alert",
                    "priority": "high"
                    if anomaly_summary["high_severity"] > 0
                    else "medium",
                    "title": f"🚨 {anomaly_summary['total_anomalies']} Consumption Anomalies Detected",
                    "description": f"Found {anomaly_summary['high_severity']} high-severity and {anomaly_summary['medium_severity']} medium-severity anomalies across {len(anomaly_summary['affected_categories'])} categories.",
                    "recommendation": "Review the anomalies immediately to identify potential issues like stockouts, ordering errors, or unusual demand spikes.",
                    "data": anomaly_summary,
                }
            )

        trends = self.analytics.analyze_consumption_patterns(30)
        if trends:
            increasing = sum(1 for t in trends.values() if t["trend"] == "Increasing")
            if increasing > 5:
                insights.append(
                    {
                        "type": "trend_alert",
                        "priority": "medium",
                        "title": f"📈 {increasing} Drugs Showing Increasing Demand",
                        "description": f"Multiple drugs are showing upward consumption trends over the past 30 days.",
                        "recommendation": "Consider increasing stock levels and review reorder points to prevent stockouts.",
                        "data": {
                            "increasing_drugs": [
                                drug
                                for drug, data in trends.items()
                                if data["trend"] == "Increasing"
                            ][:10]
                        },
                    }
                )

        correlations = self.analytics.analyze_drug_correlations()
        if correlations["correlations"]:
            strong_positive = [
                c for c in correlations["correlations"] if c["correlation"] > 0.8
            ]
            if strong_positive:
                insights.append(
                    {
                        "type": "correlation_insight",
                        "priority": "low",
                        "title": f"🔗 {len(strong_positive)} Strong Drug Correlations Found",
                        "description": f"Identified drugs with highly correlated consumption patterns.",
                        "recommendation": "Use these correlations for better demand forecasting and bundle ordering.",
                        "data": {"correlations": strong_positive[:5]},
                    }
                )

        return insights
