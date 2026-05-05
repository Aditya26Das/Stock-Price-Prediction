import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import timedelta, datetime
from requests.exceptions import ConnectionError, Timeout

API_URL = "http://127.0.0.1:8000/forecast"

st.set_page_config(page_title="Stock Forecasting", layout="wide")

# ===============================
# 🔥 PREMIUM UI STYLING
# ===============================
st.markdown("""
<style>
body {
    background-color: #020617;
}
.block-container {
    padding-top: 2rem;
}

.card {
    border-radius: 16px;
    height: 100px;
    padding: 18px;
    background: linear-gradient(145deg, #020617, #0f172a);
    border: 1px solid #1f2937;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

.metric-card {
    padding: 16px;
    border-radius: 14px;
    background: linear-gradient(145deg, #020617, #111827);
    border: 1px solid #1f2937;
}

.badge {
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 14px;
}

.pos { background: #064e3b; color: #34d399; }
.neu { background: #1f2937; color: #d1d5db; }
.neg { background: #3f0d0d; color: #f87171; }

.small { color:#9ca3af; font-size:12px; }

.title {
    font-size: 34px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# HEADER
# ===============================
st.markdown('<div class="title">📈 Multi-Day Stock Price Forecasting</div>', unsafe_allow_html=True)
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ===============================
# STOCK SELECTION
# ===============================
stocks = {
    "Apple (AAPL)": "AAPL",
    "Google (GOOGL)": "GOOGL",
    "Amazon (AMZN)": "AMZN",
    "Intel (INTC)": "INTC",
    "IBM": "IBM",
    "AMD": "AMD",
    "Microsoft (MSFT)": "MSFT"
}

ticker = stocks[st.sidebar.selectbox("Select Stock", list(stocks.keys()))]

# ===============================
# SETTINGS
# ===============================
horizon = st.sidebar.slider("Forecast Horizon (days)", 1, 30, 7)
use_ci = st.sidebar.checkbox("Confidence Interval", value=False)

mc_samples = None
if use_ci:
    mc_samples = st.sidebar.slider("Monte Carlo Samples", 10, 100, 30)

# ===============================
# LOAD DATA
# ===============================
@st.cache_data
def load_data(t):
    df = yf.Ticker(t).history(period="1mo")
    df.reset_index(inplace=True)
    return df

hist = load_data(ticker)

# ===============================
# API CALL
# ===============================
def fetch(params):
    try:
        r = requests.get(API_URL, params=params)
        if r.status_code != 200:
            return None
        return r.json()
    except (ConnectionError, Timeout):
        st.error("Backend not running")
        return None

with st.spinner("🔮 Generating forecast..."):
    params = {
        "ticker": ticker,
        "horizon": horizon,
        "model_type": "lstm-gru",
        "use_ci": use_ci
    }
    if use_ci:
        params["mc_samples"] = mc_samples

    result = fetch(params)

if not result:
    st.stop()

# ===============================
# DATA
# ===============================
preds = result.get("predictions", [])
sentiment = result.get("sentiment", {})
last_close = result.get("last_close", float(hist["Close"].iloc[-1]))

# ===============================
# KPI CARDS (🔥 NEW)
# ===============================
st.subheader("📊 Key Metrics")

c1, c2, c3 = st.columns(3)

c1.markdown(f'<div class="metric-card">Last Close<br><b>${last_close:.2f}</b></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card">Next Day<br><b>${preds[0]:.2f}</b></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card">End Forecast<br><b>${preds[-1]:.2f}</b></div>', unsafe_allow_html=True)

# ===============================
# SENTIMENT
# ===============================
def badge(label):
    cls = "neu"
    emoji = "➖"
    if label == "Positive":
        cls = "pos"; emoji = "📈"
    elif label == "Negative":
        cls = "neg"; emoji = "📉"
    return f'{emoji} <span class="badge {cls}">{label}</span>'

def confidence(score):
    s = abs(score)
    if s < 0.15: return "Low", 0.3
    elif s < 0.35: return "Medium", 0.6
    return "High", 0.9

if sentiment:
    st.subheader("🧠 Market Sentiment")

    label = sentiment.get("label", "Neutral")
    score = sentiment.get("score", 0)
    warning = sentiment.get("warning", False)

    conf_text, conf_val = confidence(score)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
        <div class="card">
            Overall Sentiment: {badge(label)}
            <div class="small">Based on recent financial news</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card">
            Confidence: <b>{conf_text}</b>
            <div style="width: 100%; margin-top: 8px;">
                <div style="width: {conf_val*100}%; background-color: #34d399; height: 6px; border-radius: 3px; transition: width 0.3s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if warning:
        st.warning("⚠️ Market conditions are volatile")

    insight = {
        "Positive": "📈 Bullish sentiment detected. Upward momentum possible.",
        "Neutral": "⚖️ Balanced sentiment. Sideways movement likely.",
        "Negative": "📉 Bearish sentiment detected. Downside risk present."
    }

    st.info(insight.get(label))

# ===============================
# FORECAST DATES
# ===============================
dates = pd.date_range(
    start=hist["Date"].iloc[-1] + timedelta(days=1),
    periods=horizon,
    freq="B"
)

# ===============================
# CHARTS
# ===============================
st.subheader("📊 Price Analysis")

col1, col2 = st.columns(2)

with col1:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist["Date"],
        open=hist["Open"],
        high=hist["High"],
        low=hist["Low"],
        close=hist["Close"]
    ))
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=preds,
        mode="lines+markers",
        line=dict(width=3)
    ))
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

# ===============================
# TABLE
# ===============================
st.subheader("📅 Forecast Breakdown")

df = pd.DataFrame({
    "Date": dates,
    "Predicted Price": preds
})

st.dataframe(df, use_container_width=True)