# 💊 AI-Powered Pharmaceutical Inventory Management System

A high-performance, cloud-optimized pharmaceutical inventory system. This application is specifically engineered for fast deployment on free tiers (Streamlit Cloud, Vercel) while maintaining sophisticated AI capabilities like demand forecasting, anomaly detection, and automated stock optimization.

## 🚀 Key Features

*   **⚡ Ultra-Fast Startup**: Implements "Invisible Lazy Loading" for heavy ML libraries (Scikit-learn), allowing the app to boot instantly on restricted hardware.
*   **🤖 Advanced AI Forecasting**: Predict future stock consumption using **Random Forest** and regression models with automatic seasonal decomposition.
*   **📊 Comprehensive Analytics**:
    *   **Consumption Trends**: Visualize historical usage and projected needs.
    *   **Wastage Analysis**: Track expired items and potential financial losses.
    *   **Cost Optimization**: Automated EOQ (Economic Order Quantity) calculations to reduce holding costs.
    *   **Anomaly Monitor**: Real-time detection of unusual inventory fluctuations.
*   **💬 Pharma AI Assistant**: An intelligent chatbot integrated with your inventory data for instant queries and recommendations.
*   **⏰ Expiry & Alerts**: Proactive monitoring of stock levels and approaching expiry dates with customizable urgency levels.
*   **📄 Professional Reporting**: Generate detailed PDF and CSV reports for inventory audits and financial reviews.
*   **📱 QR Code Integration**: Quick scanning and generation of QR codes for efficient product tracking.

## 🛠️ Optimized Tech Stack

*   **Frontend**: Streamlit (High-Performance UI)
*   **Database**: SQLite (Relational Storage)
*   **Machine Learning**: Scikit-learn (Random Forest, Regression)
*   **Data Science**: Pandas, NumPy, SciPy
*   **Visualizations**: Plotly (Interactive Charts)
*   **Security**: Self-signed SSL support for local development

**Live:** https://ai-powered-pharmaceutical-inventory-management-system-by-jsh.streamlit.app/?page=Dashboard

## 📋 Prerequisites

*   Python 3.9+
*   pip (Python package manager)

## ⚙️ Quick Start

1.  **Clone and Install**:
    ```bash
    git clone https://github.com/RaidenX2905/AI-Powered-Pharmaceutical-Inventory-Management-System.git
    cd AI-Powered-Pharmaceutical-Inventory-Management-System
    pip install -r requirements.txt
    ```

2.  **Launch the System**:
    ```bash
    streamlit run app.py
    ```
    The application will be accessible at `http://localhost:8501`.

## 📂 Project Structure

- `app.py`: Main application controller and UI layout.
- `database.py`: Core database logic and SQL transaction management.
- `ai_models.py`: AI recommendation and reordering logic.
- `inventory_forecasting.py`: Regression and Random Forest models.
- `advanced_analytics.py`: Data-driven insights for wastage and costs.
- `utils.py`: Formatting and calculation utilities.

## 🌐 Deployment Note

This version is **Production-Ready** for platforms like Streamlit Community Cloud. It uses deferred loading to stay within the 1GB RAM limit of free tiers without compromising on AI functionality.

---
Developed with ❤️ for Pharmaceutical Excellence.
