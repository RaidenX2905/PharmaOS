<p align="center">
  <img src="static/pharmaos-mark-parchment-512.png" alt="PharmaOS Brand Mark" width="128" height="128">
</p>

<div align="center">

# PharmaOS

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](#) [![Streamlit](https://img.shields.io/badge/Streamlit-Cloud%20Optimized-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](#) [![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)](#) [![scikit--learn](https://img.shields.io/badge/scikit--learn-Regressors-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)](#) [![Theme](https://img.shields.io/badge/Theme-Claude%20Amber-E07A5F?style=flat-square)](#) [![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](#)

<p align="center">
  High-performance pharmaceutical operations platform featuring demand forecasting, FEFO expiry tracking, SQLite WAL persistence, and an offline clinical assistant.
</p>

</div>

---

**Live Demo**: [https://pharmaos.streamlit.app/](https://pharmaos.streamlit.app/)

---

## Features

- **Sub-Second Boot Time**: Lazy-loaded dependency architecture reduces cold boot latency to under 1 second on free-tier cloud containers.
- **Executive Operations Dashboard**: Live valuation metrics, critical stock shortages, and 30-day expiry notifications.
- **Non-Leaking Demand Forecasting**: Chronological past-to-future rolling holdouts benchmarked across Linear, Ridge, Lasso, and Random Forest sequence regressors.
- **Offline Operations Assistant**: Parameterized SQL query parser for local inventory auditing without external LLM API costs.
- **High Concurrency SQLite WAL**: Configured Write-Ahead Logging (`PRAGMA journal_mode = WAL`) preventing database lockups under concurrent sessions.
- **Claude Amber Styling**: Warm parchment aesthetic (`#faf9f5`) with terracotta status indicators.

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Run Tests

```bash
pytest tests/ -v
```

---

## License

MIT License
