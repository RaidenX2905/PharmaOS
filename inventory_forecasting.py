import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os

from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import PolynomialFeatures
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class InventoryForecaster:
    """Time-series demand forecasting with leakage-safe chronological evaluation.

    Primary task: predict FUTURE consumption over a specified horizon.
    Secondary: expose baseline comparisons and evaluation metadata without leakage.
    """

    FORECAST_HORIZON_DAYS = 30
    MIN_HISTORY_DAYS = 30

    def __init__(self, _db_manager):
        self._db = _db_manager

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------
    def get_drugs_for_forecasting(self):
        """Return drugs with at least MIN_HISTORY_DAYS of consumption data."""
        conn = self._db.get_connection()
        query = """
            SELECT DISTINCT i.drug_name
            FROM inventory i
            JOIN consumption_patterns cp ON i.id = cp.drug_id
            GROUP BY i.drug_name
            HAVING COUNT(DISTINCT cp.date) >= ?
            ORDER BY i.drug_name
        """
        df = pd.read_sql_query(query, conn, params=(self.MIN_HISTORY_DAYS,))
        conn.close()
        return df["drug_name"].tolist()

    def get_historical_consumption(self, drug_name):
        """Daily consumption time series for one drug, indexed by date."""
        conn = self._db.get_connection()
        query = """
            SELECT cp.date, SUM(cp.quantity_consumed) AS consumption
            FROM consumption_patterns cp
            JOIN inventory i ON cp.drug_id = i.id
            WHERE i.drug_name = ?
            GROUP BY cp.date
            ORDER BY cp.date
        """
        df = pd.read_sql_query(query, conn, params=(drug_name,))
        conn.close()
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        # Fill missing daily dates with 0 (causally valid)
        full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
        df = df.reindex(full_range, fill_value=0)
        df.index.name = "date"
        return df

    # ------------------------------------------------------------------
    # Feature engineering (strictly historical, no leakage)
    # ------------------------------------------------------------------
    def _build_features(self, series: pd.Series, horizon: int = 1) -> pd.DataFrame:
        """Create lag/rolling features from historical series only."""
        df = series.to_frame(name="y")

        # Lags from the past
        for lag in [1, 2, 3, 7, 14]:
            df[f"lag_{lag}"] = df["y"].shift(lag)

        # Rolling statistics strictly on shifted past data (shift 1 avoids contemporaneous leakage)
        df["roll_mean_7"] = df["y"].shift(1).rolling(7, min_periods=1).mean()
        df["roll_std_7"] = df["y"].shift(1).rolling(7, min_periods=1).std().fillna(0)
        df["roll_mean_14"] = df["y"].shift(1).rolling(14, min_periods=1).mean()
        df["roll_mean_30"] = df["y"].shift(1).rolling(30, min_periods=1).mean()

        # Calendar features (known in advance)
        df["dayofweek"] = getattr(df.index, "day_of_week", df.index.dayofweek)
        df["month"] = df.index.month

        # Target: future consumption (shifted backwards by horizon)
        if horizon <= 1:
            df["target"] = df["y"]
        else:
            df["target"] = df["y"].shift(-horizon)

        df = df.dropna()
        return df

    # ------------------------------------------------------------------
    # Multi-Model Regression
    # ------------------------------------------------------------------
    def train_regression_models(self) -> Optional[Dict[str, Any]]:
        """Train and chronologically evaluate multiple regression models on aggregated consumption."""
        conn = self._db.get_connection()
        query = """
            SELECT cp.date, SUM(cp.quantity_consumed) AS consumption
            FROM consumption_patterns cp
            GROUP BY cp.date
            ORDER BY cp.date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty or len(df) < self.MIN_HISTORY_DAYS:
            return None

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
        df = df.reindex(full_range, fill_value=0)
        df.index.name = "date"

        feat_df = self._build_features(df["consumption"], horizon=1)
        if len(feat_df) < 20:
            return None

        feature_cols = [c for c in feat_df.columns if c not in ("y", "target")]
        X = feat_df[feature_cols].values
        y = feat_df["target"].values

        # Chronological train/test split: past 80% train, last 20% test (NO random shuffle)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        if len(y_test) < 3:
            return None

        # Polynomial features generator (fitted strictly on train)
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_train_poly = poly.fit_transform(X_train)
        X_test_poly = poly.transform(X_test)

        models = {
            "linear": LinearRegression(),
            "ridge": Ridge(alpha=1.0),
            "lasso": Lasso(alpha=0.1, max_iter=2000),
            "elasticnet": ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=2000),
        }

        results: Dict[str, Any] = {
            "dates_test": feat_df.index[split_idx:],
            "y_test": y_test,
        }

        # Train linear-type models
        for name, model in models.items():
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            pred = np.clip(pred, 0, None)  # consumption cannot be negative
            mae = float(mean_absolute_error(y_test, pred))
            rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
            r2 = float(r2_score(y_test, pred))
            results[name] = {"pred": pred, "mae": mae, "rmse": rmse, "r2": r2}

        # Train polynomial model
        poly_model = Ridge(alpha=10.0)
        poly_model.fit(X_train_poly, y_train)
        pred_poly = np.clip(poly_model.predict(X_test_poly), 0, None)
        mae_poly = float(mean_absolute_error(y_test, pred_poly))
        rmse_poly = float(np.sqrt(mean_squared_error(y_test, pred_poly)))
        r2_poly = float(r2_score(y_test, pred_poly))
        results["polynomial"] = {"pred": pred_poly, "mae": mae_poly, "rmse": rmse_poly, "r2": r2_poly}

        # Select best model by highest R2 score on test set
        model_names = ["linear", "polynomial", "ridge", "lasso", "elasticnet"]
        best_model = max(model_names, key=lambda m: results[m]["r2"])
        results["best_model"] = best_model
        return results

    def create_regression_plots(self, results: Dict[str, Any]):
        """Plot actual vs predicted for regression models."""
        if not results:
            return None
        dates = results["dates_test"]
        y_test = results["y_test"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=y_test, mode="lines", name="Actual Demand", line=dict(color="black", width=2)))

        colors = {"linear": "blue", "polynomial": "purple", "ridge": "green", "lasso": "orange", "elasticnet": "red"}
        for name, col in colors.items():
            if name in results:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=results[name]["pred"],
                    mode="lines",
                    name=f"{name.capitalize()} (R²={results[name]['r2']:.2f})",
                    line=dict(color=col, dash="dash" if name != results.get("best_model") else "solid")
                ))

        fig.update_layout(
            title="Regression Models Comparison: Actual vs Predicted Demand",
            xaxis_title="Date",
            yaxis_title="Consumption Units",
            template="plotly_white",
            height=450
        )
        return fig

    # ------------------------------------------------------------------
    # Time-series (Random Forest & baseline rolling models)
    # ------------------------------------------------------------------
    def train_lstm_model(self, forecast_days: int = 30) -> Optional[Dict[str, Any]]:
        """Lightweight, reliable time-series forecasting.

        Uses Naive baseline, Seasonal Moving Average, and Random Forest
        (as a robust, lightweight tree-based sequence model without heavy TensorFlow dependency).
        """
        conn = self._db.get_connection()
        query = """
            SELECT cp.date, SUM(cp.quantity_consumed) AS consumption
            FROM consumption_patterns cp
            GROUP BY cp.date
            ORDER BY cp.date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty or len(df) < self.MIN_HISTORY_DAYS:
            return None

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
        df = df.reindex(full_range, fill_value=0)
        series = df["consumption"]

        feat_df = self._build_features(series, horizon=1)
        if len(feat_df) < 20:
            return None

        feature_cols = [c for c in feat_df.columns if c not in ("y", "target")]
        X = feat_df[feature_cols].values
        y = feat_df["target"].values

        # Chronological 80/20 split
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Random Forest Regressor (deterministic seed)
        rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        rf.fit(X_train, y_train)
        pred_rf = np.clip(rf.predict(X_test), 0, None)

        # Baseline: 7-day rolling mean
        baseline_pred = feat_df["roll_mean_7"].iloc[split_idx:].values
        # Naive baseline: yesterday's demand
        naive_pred = feat_df["lag_1"].iloc[split_idx:].values

        def calc_metrics(y_true, y_p):
            mae = float(mean_absolute_error(y_true, y_p))
            rmse = float(np.sqrt(mean_squared_error(y_true, y_p)))
            # Scale-aware MAPE / WAPE to prevent division by zero
            denom = np.sum(np.abs(y_true))
            wape = float(np.sum(np.abs(y_true - y_p)) / denom * 100) if denom > 0 else 0.0
            return mae, rmse, wape

        rf_mae, rf_rmse, rf_mape = calc_metrics(y_test, pred_rf)
        b_mae, b_rmse, b_mape = calc_metrics(y_test, baseline_pred)
        n_mae, n_rmse, n_mape = calc_metrics(y_test, naive_pred)

        all_metrics = {
            "RandomForest (Ensemble)": {"MAE": rf_mae, "RMSE": rf_rmse, "MAPE": rf_mape},
            "7-Day Rolling Baseline": {"MAE": b_mae, "RMSE": b_rmse, "MAPE": b_mape},
            "Naive (Lag-1) Baseline": {"MAE": n_mae, "RMSE": n_rmse, "MAPE": n_mape},
        }

        # Multi-step iterative forward forecast for forecast_days
        history = list(series.values)
        future_preds = []
        for step in range(forecast_days):
            recent = history[-30:] if len(history) >= 30 else history
            lag_1 = recent[-1]
            lag_2 = recent[-2] if len(recent) >= 2 else lag_1
            lag_3 = recent[-3] if len(recent) >= 3 else lag_2
            lag_7 = recent[-7] if len(recent) >= 7 else lag_1
            lag_14 = recent[-14] if len(recent) >= 14 else lag_1
            roll_m7 = float(np.mean(recent[-7:]))
            roll_std7 = float(np.std(recent[-7:]))
            roll_m14 = float(np.mean(recent[-14:]))
            roll_m30 = float(np.mean(recent[-30:]))
            target_date = series.index[-1] + timedelta(days=step + 1)
            dow = getattr(target_date, "day_of_week", target_date.dayofweek)
            month = target_date.month

            vec = np.array([[lag_1, lag_2, lag_3, lag_7, lag_14, roll_m7, roll_std7, roll_m14, roll_m30, dow, month]])
            pred_step = float(np.clip(rf.predict(vec)[0], 0, None))
            future_preds.append(pred_step)
            history.append(pred_step)

        future_dates = [series.index[-1] + timedelta(days=i + 1) for i in range(forecast_days)]

        return {
            "best_model_name": "RandomForest Sequence Regressor",
            "all_metrics": all_metrics,
            "mae": rf_mae,
            "rmse": rf_rmse,
            "mape": rf_mape,
            "dates_test": feat_df.index[split_idx:],
            "y_test": y_test,
            "pred_test": pred_rf,
            "future_dates": future_dates,
            "future_pred": np.array(future_preds),
            "historical_dates": series.index[-60:],
            "historical_values": series.values[-60:],
        }

    def create_lstm_plot(self, results: Dict[str, Any]):
        """Plot historical consumption and forward-forecast trajectory."""
        if not results:
            return None

        fig = go.Figure()
        # Historical
        fig.add_trace(go.Scatter(
            x=results["historical_dates"],
            y=results["historical_values"],
            mode="lines",
            name="Recent History",
            line=dict(color="#2b5c8f", width=2)
        ))
        # Test Actual
        fig.add_trace(go.Scatter(
            x=results["dates_test"],
            y=results["y_test"],
            mode="markers",
            name="Test Observations",
            marker=dict(color="#4a5568", size=4)
        ))
        # Test Prediction
        fig.add_trace(go.Scatter(
            x=results["dates_test"],
            y=results["pred_test"],
            mode="lines",
            name="Validation Prediction",
            line=dict(color="#319795", dash="dot")
        ))
        # Future Forecast
        fig.add_trace(go.Scatter(
            x=results["future_dates"],
            y=results["future_pred"],
            mode="lines+markers",
            name="Future Forecast",
            line=dict(color="#e53e3e", width=2.5)
        ))

        fig.update_layout(
            title=f"Demand Forecast ({results.get('best_model_name', 'Forecaster')})",
            xaxis_title="Date",
            yaxis_title="Quantity Consumed",
            template="plotly_white",
            height=450
        )
        return fig
