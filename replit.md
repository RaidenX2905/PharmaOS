# AI-Based Pharmaceutical Inventory Management System

## Overview
This project is an AI-powered pharmaceutical inventory management system designed to enhance efficiency in pharmacies and healthcare facilities. It integrates traditional inventory management with advanced AI capabilities such as demand forecasting, smart reordering, expiry prediction, and drug interaction checking. The system aims to optimize inventory, reduce waste, ensure patient safety, and provide comprehensive analytics for informed decision-making, offering significant market potential and serving as a robust solution for pharmaceutical inventory challenges.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system is built as a Streamlit web application with a Python-based core and a SQLite database, featuring a modular, object-oriented design.

### UI/UX Decisions
-   **Frontend Framework**: Streamlit for a modern, responsive web interface.
-   **Navigation**: Multi-page navigation for modules like Dashboard, Inventory, AI Assistant, Forecasting, and Analytics.
-   **Visualization**: Interactive data visualizations using Plotly and other advanced libraries for charts, graphs, 3D plots, Sankey diagrams, sunburst charts, heatmaps, and network graphs.
-   **Theming**: Custom theme with modern purple gradient primary colors, animations (fadeInUp, slideInRight, pulse, shimmer), and glassmorphism effects.

### Technical Implementations
-   **Backend Core**: Python with modular AI components, employing TensorFlow/Keras for deep learning.
-   **Database**: SQLite housing 700 pharmaceutical items, over 1.5 million transaction records, and more than 82,000 consumption pattern records spanning 2020-2025.
-   **AI/ML Components**:
    -   **Advanced Anomaly Detection**: Multi-algorithm ensemble (Z-score, Isolation Forest, DBSCAN) with severity scoring and confidence levels.
    -   **Automated Insights Generator**: Natural language explanations for trends and recommendations.
    -   **Demand Forecasting**: Multiple ML models (Linear Regression, Random Forest, ARIMA, LSTM neural networks) with seasonal decomposition and confidence intervals.
    -   **Smart Reordering**: AI-driven suggestions based on consumption patterns and Economic Order Quantity (EOQ) calculations.
    -   **Expiry Prediction**: Alerts for drugs nearing expiration.
    -   **Drug Interaction Checker**: Identifies dangerous drug combinations.
    -   **Drug Correlation Analysis**: Identifies strong positive/negative correlations between drug consumption.
    -   **Wastage Analysis & Prevention**: Predictive wastage detection with AI-powered recommendations.
    -   **Drug Utilization Review (DUR)**: Comprehensive usage pattern analysis.
    -   **Smart Recommendations**: AI-powered personalized inventory suggestions with priority scoring.
-   **Inventory Operations**: CRUD operations, intelligent duplicate handling, batch operations, and advanced filtering.
-   **Analytics & Reporting**: Multi-tab analytics dashboard, year-based filtering, CSV export, and professional PDF report generation.
-   **User Management**: User authentication with PBKDF2 hashing, session management, and role-based access control.
-   **Notifications**: Automated email/SMS alerts for low stock and expiring medications.
-   **Automated Purchase Orders**: AI-driven PO generation.
-   **Audit Trail**: Comprehensive logging of all system activities.
-   **Caching**: Streamlit caching for database and AI model initialization.

### Feature Specifications
-   **Dashboard**: Real-time metrics, alerts, and analytics.
-   **Inventory Management**: Comprehensive interface for viewing, adding, updating, and performing batch operations on 700 diverse pharmaceutical items.
-   **AI Assistant**: OpenAI GPT-5 powered chatbot for inventory queries.
-   **Analytics**: Year/month filtering, comprehensive reports, and consumption analysis from over 82,000 records.
-   **Anomaly Monitor**: Real-time auto-loading dashboard with multi-algorithm ML ensemble for anomaly detection, severity scoring, and automated insights.
-   **Drug Correlations**: Correlation matrix analysis for top drugs and visualization of relationships.
-   **Wastage Analysis**: Real-time tracking, predictive detection, and AI-powered prevention recommendations.
-   **Cost Optimization**: Automated identification of savings, EOQ analysis, and detection of overstocking/slow-moving inventory.
-   **Drug Utilization Review (DUR)**: Classification of utilization, department-wise analysis, and trend tracking.
-   **Advanced Predictive Analytics**: Consumption pattern analysis, demand clustering (K-Means), and seasonal pattern identification.
-   **Deep Learning Forecast**: LSTM neural network predictions with confidence intervals and a 7-90 day forecast horizon.
-   **Smart Recommendations**: AI-powered personalized suggestions for restocking, expiry alerts, and ROI optimization.
-   **Advanced Visualizations**: Includes 3D scatter plots, Sankey diagrams, sunburst charts, consumption heatmaps, network correlation graphs, and treemaps.
-   **Generate Reports**: Professional PDF generation for comprehensive inventory reports, analytics, and executive summaries.

## External Dependencies
-   **OpenAI API**: For AI chatbot functionality (GPT-5).
-   **Python Libraries**:
    -   `streamlit`, `pandas`, `numpy`, `scikit-learn`, `scipy`, `plotly`, `openai`, `prophet`, `tensorflow`, `seaborn`, `networkx`, `statsmodels`, `pillow`, `opencv-python`, `pytesseract`, `pyzbar`, `psutil`, `fpdf`, `reportlab`.
-   **Optional Services**:
    -   **SendGrid API**: For email notifications.
    -   **Twilio API**: For SMS notifications.

## Recent Changes

### October 29, 2025 - Major Feature Enhancements
**Performance Dashboard Removal & Feature Complexity Improvements**

**Removed:**
- Performance Dashboard feature and performance_monitor.py module

**Enhanced Features:**

1. **AI Chatbot** - Now with multi-module integration
   - Advanced context awareness with drug interactions, analytics, forecasting, and recommendations
   - Multi-turn conversation memory (30 messages)
   - Intelligent query routing to appropriate modules
   - Real-time data integration from all features
   - Enhanced fallback responses with status indicators

2. **Smart Reordering** - Advanced supply chain optimization
   - Multi-supplier optimization with composite scoring (reliability, cost, quality, speed)
   - Seasonal demand pattern recognition and forecasting adjustments
   - Economic Order Quantity (EOQ) calculations
   - Stockout risk probability calculations
   - Budget constraint management
   - Supplier performance grading (A+ to D)

3. **Deep Learning Forecasting** - Enhanced prediction capabilities
   - Ensemble model support (LSTM + Bidirectional LSTM + GRU)
   - 95% confidence intervals with uncertainty growth modeling
   - Automatic model selection
   - Trend analysis with strength indicators
   - Seasonality detection via autocorrelation
   - Actionable recommendations from predictions
   - Batch forecasting for top drugs

4. **Smart Recommendations** - Comprehensive AI-powered insights
   - Multi-criteria optimization (impact, urgency, ROI, time-sensitivity)
   - Seasonal opportunity detection
   - Supplier performance recommendations
   - Growth opportunity identification with revenue projections
   - ROI-based priority scoring
   - Days-until-impact tracking
   - Estimated cost and savings calculations

All features now provide significantly more complex analysis, deeper insights, and actionable recommendations for pharmaceutical inventory management.