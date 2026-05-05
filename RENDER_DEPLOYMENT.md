# Render Free Tier Deployment Guide (512MB RAM)

This guide helps you deploy the pharmaceutical inventory system on Render's free tier.

## Quick Start

1. **Use the lightweight requirements file**:
   ```bash
   pip install -r requirements-lite.txt
   ```

2. **Set environment variable**:
   - In Render dashboard, add: `DISABLE_HEAVY_FEATURES=true`
   - This disables TensorFlow (saves ~200MB RAM)

3. **Start command**:
   ```bash
   streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

## Memory Optimization Features

### ✅ Enabled by Default (Lightweight)
- Core inventory management
- Analytics (using scikit-learn instead of TensorFlow)
- Dashboard and reports
- QR code generation
- Basic forecasting (regression-based)

### ⚠️ Disabled by Default (Heavy)
- Deep Learning forecasting (TensorFlow)
- Advanced OCR (pytesseract + opencv)
- Prophet time series forecasting

## Memory Usage Estimate

With `DISABLE_HEAVY_FEATURES=true`:
- Streamlit: ~100MB
- Pandas/Numpy: ~50MB
- App code: ~50MB
- Database: ~10MB
- Available buffer: ~300MB

**Total: ~210MB / 512MB (41% usage)**

## To Enable Heavy Features

1. Set `DISABLE_HEAVY_FEATURES=false` in Render
2. Install full requirements: `pip install -r requirements.txt`
3. **Note**: May cause memory issues on free tier

## Database Optimization

The app uses SQLite with:
- Query limits (1000-5000 rows max)
- Caching (5-minute TTL)
- Indexed queries

## Monitoring

Check Render logs if you see:
- Memory limit errors → Enable `DISABLE_HEAVY_FEATURES=true`
- Slow loading → Check database size
- Timeouts → Reduce query limits

## Recommended Settings for 512MB

```env
DISABLE_HEAVY_FEATURES=true
PYTHON_VERSION=3.11.0
```


