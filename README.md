# 💊 PharmaOS

**High-Performance Pharmaceutical Operations & Inventory Operating System**

A modern, cloud-optimized pharmaceutical resource platform engineered for fast, lightweight deployment on Streamlit Community Cloud. Features deterministic demand forecasting, anomaly detection, smart procurement optimization, and an offline local operations assistant styled with the minimalist **Claude Amber** theme.

[![Tests](https://img.shields.io/badge/tests-12%20passed-success)](tests/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Theme](https://img.shields.io/badge/theme-Claude%20Amber-orange)](https://21st.dev/@serafimcloud/themes/claude-amber)
[![Live Demo](https://img.shields.io/badge/Streamlit%20Cloud-Live-brightgreen)](https://pharmaos.streamlit.app/)

**Live Application:** [https://pharmaos.streamlit.app/](https://pharmaos.streamlit.app/)

---

## 🚀 Key Features

*   **⚡ Ultra-Fast Cold Starts**: Heavy libraries (Scikit-Learn, Plotly) load lazily on-demand, reducing cold boot overhead to under 1 second.
*   **📊 Executive Inventory Dashboard**: Real-time aggregated inventory valuation, safety stock alerts, and 30-day expiry notifications.
*   **📈 Demand Forecasting (No Leakage)**: Chronological rolling holdouts (80/20 past-to-future) with Linear, Polynomial, Ridge, Lasso, ElasticNet, and Random Forest sequence regressors.
*   **🤖 Local Operations Assistant (100% Offline)**: Rule-based, parameterized SQL engine querying live stock levels, shortages, expiry risks, suppliers, and transaction ledgers without external cloud API dependencies.
*   **🔒 SQLite WAL & Concurrency**: Configured Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and busy timeouts (`10000ms`) eliminating database locks across concurrent readers/writers.
*   **🎨 Claude Amber Aesthetic**: Minimalist warm parchment surfaces (`#faf9f5`), rich charcoal typography (`#3d3929`), and terracotta semantic indicators (`#c96442`).

---

## 🛠️ Tech Stack & Requirements

*   **Runtime**: Python 3.9+
*   **UI Framework**: Streamlit (High-Performance UI)
*   **Database**: SQLite with WAL Mode
*   **Machine Learning**: Scikit-Learn (Random Forest, Regularized Regression)
*   **Data Processing**: Pandas, NumPy, SciPy
*   **Visualizations**: Plotly Express & Graph Objects

---

## ⚙️ Quick Start

### 1. Installation
```bash
git clone https://github.com/RaidenX2905/PharmaOS.git
cd PharmaOS
pip install -r requirements.txt
```

### 2. Run Application
```bash
streamlit run app.py
```
Access locally at `http://localhost:8501`.

### 3. Run Automated Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### 4. Reproduce Forecasting Benchmarks
```bash
python3 reproduce_benchmarks.py
```

---

## 🌐 Streamlit Community Cloud Deployment

1. Push your changes to GitHub:
   ```bash
   git push origin main
   git push origin v1.0.1
   ```
2. In [share.streamlit.io](https://share.streamlit.io), connect your repository:
   - **Repository**: `RaidenX2905/PharmaOS`
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. Click **Deploy**. The application runs natively on the 1GB RAM free tier.

---

## ⚠️ Limitations & Clinical Boundary

*   **Clinical Prototype**: Drug interaction and substitution features use a curated demonstration subset. Absence of an interaction warning does **not** establish combination safety. Professional pharmacist review is required.
*   **Capacity Limit**: Streamlit free tier supports ~20-50 concurrent active users on SQLite WAL. For higher concurrent traffic (>100 active writers), migrate SQLite persistence to managed PostgreSQL (e.g., Supabase or Neon).

---

## 📝 Changelog (v1.0.1)

*   **Full UI Redesign**: Integrated Claude Amber design system with GPU-accelerated page animations.
*   **Forecasting Hardening**: Fixed regression methods, removed target leakage, and enforced chronological holdouts.
*   **Offline Assistant**: Replaced cloud API requirement with deterministic local SQL query engine.
*   **Database Concurrency**: Enabled SQLite WAL mode and safe transaction rollbacks.
*   **Test Suite**: Added 12 comprehensive unit and regression tests.
