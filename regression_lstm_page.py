import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from inventory_forecasting import InventoryForecaster

def regression_lstm_analysis_page(db):
    """Page for regression and LSTM analysis"""
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #dad9d4; border-radius: 6px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.35rem; font-weight: 600; color: #3d3929; margin: 0; letter-spacing: -0.02em;">Demand Forecasting & Regression Analysis</h2>
        <p style="font-size: 0.875rem; color: #83827d; margin-top: 0.25rem; margin-bottom: 0;">Empirical validation across statistical baselines and sequential ensemble forecasters</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if inventory was updated and show notification
    if 'last_inventory_update' in st.session_state:
        if 'regression_results' not in st.session_state and 'lstm_results' not in st.session_state:
            st.info("Inventory dataset has been updated. Recalculate models to refresh metrics.")
    
    forecaster = InventoryForecaster(db)
    
    # Tabs for different analyses
    tab1, tab2 = st.tabs(["Regression Benchmarks", "Sequential Sequence Forecast"])
    
    with tab1:
        st.subheader("Multi-Model Regression Comparison")
        st.markdown("""
        Compare **Linear Regression**, **Polynomial Regression**, and **Ridge Regression** models side-by-side.
        Each model predicts inventory stock levels based on consumption patterns and pricing data.
        """)
        
        # Auto-display cached results if available
        if 'regression_results' in st.session_state and st.session_state['regression_results'] is not None:
            results = st.session_state['regression_results']
            st.info("📊 **Showing cached results.** Click 'Train & Compare' button to refresh with latest data.")
        else:
            results = None
        
        if st.button("🔄 Train & Compare All Regression Models", key="train_regression"):
            with st.spinner("Training all regression models on complete dataset..."):
                try:
                    results = forecaster.train_regression_models()
                    
                    if results is None:
                        st.warning("⚠️ Insufficient data for regression analysis. Need at least 10 items with consumption history.")
                        if 'regression_results' in st.session_state:
                            del st.session_state['regression_results']
                    else:
                        # Cache results in session state
                        st.session_state['regression_results'] = results
                except Exception as e:
                    st.error(f"Error during regression analysis: {str(e)}")
                    results = None
        
        # Display results if available
        if results is not None:
            try:
                # Display best model
                best_model = results['best_model']
                st.success(f"✅ **Best Model:** {best_model.upper()} (Highest R² Score)")
                
                # Metrics comparison
                st.markdown("### 📊 Model Performance Metrics")
                
                cols = st.columns(5)
                model_names = ["linear", "polynomial", "ridge", "lasso", "elasticnet"]
                display_names = ["Linear", "Poly", "Ridge", "Lasso", "ElasticNet"]
                
                for i, (m_key, d_name) in enumerate(zip(model_names, display_names)):
                    with cols[i]:
                        st.metric(
                            f"{d_name} R²",
                            f"{results[m_key]['r2']:.4f}",
                            delta=f"MAE: {results[m_key]['mae']:.2f}"
                        )
                        st.metric(f"{d_name} RMSE", f"{results[m_key]['rmse']:.2f}")
                
                # Display plots
                st.markdown("### 📈 Visual Comparison: Actual vs Predicted")
                fig = forecaster.create_regression_plots(results)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Model recommendation
                st.markdown("### 💡 Model Recommendation")
                
                best_r2 = results[best_model]['r2']
                best_mae = results[best_model]['mae']
                best_rmse = results[best_model]['rmse']
                
                if best_r2 > 0.8:
                    quality = "Optimal Fit"
                    color = "#2e7d32"
                elif best_r2 > 0.6:
                    quality = "Acceptable"
                    color = "#c96442"
                elif best_r2 > 0.4:
                    quality = "Moderate"
                    color = "#b85434"
                else:
                    quality = "Low Fit"
                    color = "#c53030"
                
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #dad9d4; border-left: 3px solid {color}; padding: 1rem; border-radius: 6px; margin: 1rem 0;">
                    <div style="font-weight: 600; font-size: 0.95rem; color: #3d3929;">Recommended Model: {best_model.upper()} ({quality})</div>
                    <div style="font-size: 0.85rem; color: #83827d; margin-top: 0.35rem;">
                        R² Score: <strong>{best_r2:.4f}</strong> | MAE: <strong>{best_mae:.2f}</strong> | RMSE: <strong>{best_rmse:.2f}</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error displaying regression results: {str(e)}")
        
        st.markdown("---")
        st.markdown("""
        **Model Explanations:**
        - **Linear Regression**: Simple linear relationship between features and stock levels
        - **Polynomial Regression**: Captures non-linear patterns (degree 2)
        - **Ridge Regression**: Regularized model that prevents overfitting
        
        **Metrics Explained:**
        - **R² Score**: Proportion of variance explained (0-1, higher is better). *Note: Negative R² means the model is performing worse than a horizontal line (the mean), often due to small datasets or lack of correlation.*
        - **MAE**: Average absolute difference between predicted and actual values
        - **RMSE**: Square root of average squared differences (penalizes large errors more)
        """)
    
    with tab2:
        st.subheader("LSTM Neural Network Forecasting")
        st.markdown("""
        Use Long Short-Term Memory (LSTM) deep learning to forecast future stock consumption.
        The model learns from historical patterns to predict future trends.
        """)
        
        forecast_days = st.slider("Forecast Horizon (days)", min_value=7, max_value=90, value=30, step=7)
        
        # Auto-display cached results if available
        if 'lstm_results' in st.session_state and st.session_state['lstm_results'] is not None:
            lstm_results = st.session_state['lstm_results']
            st.info("📊 **Showing cached results.** Click 'Train LSTM' button to refresh with latest data.")
        else:
            lstm_results = None
        
        if st.button("🚀 Train LSTM & Generate Forecast", key="train_lstm"):
            with st.spinner(f"Training LSTM model and forecasting next {forecast_days} days..."):
                try:
                    lstm_results = forecaster.train_lstm_model(forecast_days=forecast_days)
                    
                    if lstm_results is None:
                        st.warning("⚠️ Insufficient data for LSTM forecasting. Need at least 30 days of consumption history.")
                        if 'lstm_results' in st.session_state:
                            del st.session_state['lstm_results']
                    else:
                        # Cache results in session state
                        st.session_state['lstm_results'] = lstm_results
                except Exception as e:
                    st.error(f"Error during LSTM forecasting: {str(e)}")
                    lstm_results = None
        
        # Display results if available
        if lstm_results is not None:
            try:
                results = lstm_results
                # Display metrics
                st.markdown(f"### 🎯 Forecast Performance (Best Model: **{results['best_model_name']}**)")
                
                # Show all model metrics in a table for comparison
                st.markdown("#### 🔬 All Tested Time-Series Models")
                metrics_df = pd.DataFrame(results['all_metrics']).T
                st.table(metrics_df.style.highlight_min(axis=0, subset=['MAE', 'RMSE'], color='#d4edda'))
                
                st.markdown("---")
                st.markdown("### 🎯 Best Model Detailed Metrics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Mean Absolute Error (MAE)",
                        f"{results['mae']:.2f} units"
                    )
                
                with col2:
                    st.metric(
                        "Root Mean Squared Error (RMSE)",
                        f"{results['rmse']:.2f} units"
                    )
                
                with col3:
                    st.metric(
                        "Mean Absolute Percentage Error (MAPE)",
                        f"{results['mape']:.2f}%"
                    )
                
                # Display plot
                st.markdown("### 📈 LSTM Forecast Visualization")
                fig = forecaster.create_lstm_plot(results)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Forecast summary
                st.markdown("### 📋 Forecast Summary")
                
                avg_forecast = results['future_pred'].mean()
                max_forecast = results['future_pred'].max()
                min_forecast = results['future_pred'].min()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Average Daily Forecast", f"{avg_forecast:.1f} units")
                with col2:
                    st.metric("Peak Forecast", f"{max_forecast:.1f} units")
                with col3:
                    st.metric("Minimum Forecast", f"{min_forecast:.1f} units")
                
                # Recommendations
                st.markdown("### 💡 Insights & Recommendations")
                
                if results['mape'] < 10:
                    accuracy = "High Precision"
                    color = "#2e7d32"
                elif results['mape'] < 20:
                    accuracy = "Acceptable"
                    color = "#c96442"
                elif results['mape'] < 30:
                    accuracy = "Moderate"
                    color = "#b85434"
                else:
                    accuracy = "Low Precision"
                    color = "#c53030"
                
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #dad9d4; border-left: 3px solid {color}; padding: 1rem; border-radius: 6px; margin: 1rem 0;">
                    <div style="font-weight: 600; font-size: 0.95rem; color: #3d3929;">Evaluation Summary: {accuracy}</div>
                    <div style="font-size: 0.85rem; color: #83827d; margin-top: 0.35rem;">
                        Projected Average Demand: <strong>{avg_forecast:.1f} units/day</strong> | WAPE/MAPE: <strong>{results['mape']:.2f}%</strong> | Test MAE: <strong>±{results['mae']:.2f} units</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error displaying LSTM results: {str(e)}")
        
        st.markdown("---")
        st.markdown("""
        **How LSTM Works:**
        - LSTM is a type of recurrent neural network designed for time series data
        - It learns patterns from 180 days of historical consumption
        - The model can capture seasonal trends and complex patterns
        - Future forecasts help with proactive inventory management
        
        **Metrics Explained:**
        - **MAE**: Average prediction error in units
        - **RMSE**: Error metric that penalizes large deviations
        - **MAPE**: Percentage error (easier to interpret accuracy)
        """)
