# FILE: apex_terminal.py
# ROLE: Master UI Dashboard
# ARCHITECTURE: Streamlit Convergence (Tactical UI V5.43 + Live Portfolio Ledger)
# STATUS: ACTIVE (Uncompressed Master Build)

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import zipfile
import io
import json
import os
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    import apex_config as cfg
except ImportError:
    st.error("⚠️ apex_config.py not found. Please ensure it is in the same directory.")
    st.stop()

# ==============================================================================
# UI CONFIGURATION & CUSTOM CSS 
# ==============================================================================
st.set_page_config(page_title="TITAN APEX", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Inter', 'Roboto', sans-serif; }
    .apex-header { color: #58a6ff; font-weight: 800; letter-spacing: 1px; border-bottom: 1px solid rgba(88, 166, 255, 0.3); padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; font-size: 1.2rem;}
    .defcon-banner { padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: center; border: 2px solid; }
    .defcon-title { font-size: 1.8rem; font-weight: 900; letter-spacing: 2px; margin-bottom: 5px; }
    .defcon-sub { font-size: 1rem; font-family: 'Roboto Mono', monospace; font-weight: 700; }
    .tactical-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; flex-direction: column; justify-content: space-between; min-height: 170px; }
    .card-bullish { border-left: 5px solid #39FF14; background: linear-gradient(90deg, rgba(57,255,20,0.05) 0%, rgba(22,27,34,1) 40%); }
    .card-bearish { border-left: 5px solid #FF4444; background: linear-gradient(90deg, rgba(255,68,68,0.05) 0%, rgba(22,27,34,1) 40%); }
    .card-neutral { border-left: 5px solid #8b949e; }
    .card-squeeze { border: 1px solid #FFAA00; box-shadow: 0 0 15px rgba(255, 170, 0, 0.15); border-left: 5px solid #FFAA00; }
    .asset-title { font-size: 1.4rem; font-weight: 900; color: #ffffff; letter-spacing: 0.5px; }
    .price-text { font-size: 1.3rem; font-weight: 700; color: #58a6ff; font-family: 'Roboto Mono', monospace; }
    .metric-sub { font-size: 0.9rem; color: #8b949e; font-family: 'Roboto Mono', monospace; line-height: 1.6; }
    .data-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(139, 148, 158, 0.2); padding: 4px 0; }
    .data-row:last-child { border-bottom: none; }
    .mandate-box { margin-top: 15px; padding: 10px; border-radius: 4px; font-size: 0.85rem; font-weight: 800; letter-spacing: 0.5px; text-align: center; width: 100%; }
    .mandate-buy { background: rgba(57, 255, 20, 0.08); color: #39FF14; border: 1px solid rgba(57, 255, 20, 0.3); }
    .mandate-sell { background: rgba(255, 68, 68, 0.08); color: #FF4444; border: 1px solid rgba(255, 68, 68, 0.3); }
    .mandate-warn { background: rgba(255, 170, 0, 0.08); color: #FFAA00; border: 1px solid rgba(255, 170, 0, 0.3); }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR NAVIGATION
st.sidebar.markdown("<h2 style='text-align: center; color: #58a6ff;'>SYSTEM MENU</h2>", unsafe_allow_html=True)
app_mode = st.sidebar.radio("Select Module:", ["🚀 LIVE COMMAND CENTER", "💼 LIVE PORTFOLIO MANAGER", "🧪 QUANT OPTIMIZER LAB"])
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 0.8rem; color: #8b949e; text-align: center;'>TITAN OMEGA V5.43<br>System Online.</p>", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFF; font-weight: 900; letter-spacing: 3px; margin-bottom: 20px;'>🦅 TITAN APEX COMMAND</h1>", unsafe_allow_html=True)

# ==============================================================================
# LOCAL DATABASE ENGINE (JSON)
# ==============================================================================
DB_FILE = "titan_portfolio.json"

def load_portfolio():
    if not os.path.exists(DB_FILE):
        default_db = {"open_positions": [], "closed_trades": []}
        with open(DB_FILE, 'w') as f:
            json.dump(default_db, f, indent=4)
        return default_db
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {"open_positions": [], "closed_trades": []}

def save_portfolio(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

# ==============================================================================
# DATA ENGINES (HYBRID API PROTOCOL)
# ==============================================================================
@st.cache_data(ttl=300)
def get_risk_engine():
    try:
        data = yf.download(["^VIX", "^VIX3M"], period="5d", progress=False)['Close']
        data = data.dropna()
        if data.empty: return {"status": "offline"}
        vix, vix3m = float(data['^VIX'].iloc[-1]), float(data['^VIX3M'].iloc[-1])
        return {"vix": vix, "vix3m": vix3m, "ratio": vix / vix3m, "status": "online"}
    except: return {"status": "offline"}

@st.cache_data(ttl=86400)
def get_fomc_data():
    try:
        if not hasattr(cfg, 'FRED_API_KEY') or cfg.FRED_API_KEY == "PASTE_YOUR_32_CHARACTER_KEY_HERE" or cfg.FRED_API_KEY == "": return {"status": "offline"}
        api_key = cfg.FRED_API_KEY
        yc_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=T10Y2Y&api_key={api_key}&file_type=json"
        res_yc = requests.get(yc_url, timeout=10)
        df_yc = pd.DataFrame(res_yc.json()['observations'])
        df_yc['date'], df_yc['value'] = pd.to_datetime(df_yc['date']), pd.to_numeric(df_yc['value'], errors='coerce')
        df_yc = df_yc[['date', 'value']].rename(columns={'value': 'Yield_Curve'}).set_index('date')

        ff_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key={api_key}&file_type=json"
        res_ff = requests.get(ff_url, timeout=10)
        df_ff = pd.DataFrame(res_ff.json()['observations'])
        df_ff['date'], df_ff['value'] = pd.to_datetime(df_ff['date']), pd.to_numeric(df_ff['value'], errors='coerce')
        df_ff = df_ff[['date', 'value']].rename(columns={'value': 'Fed_Funds'}).set_index('date')

        df = df_yc.join(df_ff, how='inner').dropna()
        df = df[df.index > (datetime.now() - pd.DateOffset(years=5))]
        status = "INVERTED (RECESSION WARNING)" if df['Yield_Curve'].iloc[-1] < 0 else "NORMAL (CONTANGO)"
        return {"status": "online", "data": df, "curve_status": status, "current_yc": float(df['Yield_Curve'].iloc[-1]), "current_ff": float(df['Fed_Funds'].iloc[-1])}
    except: return {"status": "offline"}

@st.cache_data(ttl=3600)
def get_cross_asset_matrix():
    tickers = ["SPY", "QQQ", "TLT", "GLD", "USO", "UUP", "BTC-USD"]
    try:
        df = yf.download(tickers, period="3mo", progress=False)['Close'].dropna(how='all')
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
        returns = df.pct_change().dropna()
        corr_matrix = returns.corr().round(2)
        valid_tickers = [t for t in tickers if t in corr_matrix.columns]
        return {"status": "online", "data": corr_matrix.reindex(index=valid_tickers, columns=valid_tickers)}
    except: return {"status": "offline"}

@st.cache_data(ttl=3600)
def get_macro_tide():
    url = f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{datetime.now().year}.zip"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with z.open(z.namelist()[0]) as f: df = pd.read_csv(f, low_memory=False)
        df.columns = df.columns.str.strip().str.upper()
        date_col = next(c for c in df.columns if 'REPORT_DATE' in c)
        market_col = next(c for c in df.columns if 'MARKET_AND_EXCHANGE' in c)
        latest_date = df[date_col].max()
        latest_df = df[df[date_col] == latest_date]
        results = []
        cftc_map = {"GLD": "GOLD", "SLV": "SILVER", "USO": "CRUDE OIL", "UNG": "NAT GAS", "COPX": "COPPER"}
        for ticker, name in cftc_map.items():
            asset_df = latest_df[latest_df[market_col].str.contains(name, case=False, na=False)]
            if not asset_df.empty:
                row = asset_df.iloc[0]
                long_pos = int(row[next(c for c in df.columns if 'PROD_MERC_POSITIONS_LONG' in c)])
                short_pos = int(row[next(c for c in df.columns if 'PROD_MERC_POSITIONS_SHORT' in c)])
                oi = int(row[next(c for c in df.columns if 'OPEN_INTEREST_ALL' in c)])
                net = long_pos - short_pos
                results.append({"Asset": ticker, "Net Position": net, "Intensity (%)": (abs(net) / oi) * 100})
        return pd.DataFrame(results), latest_date
    except: return pd.DataFrame(), ""

@st.cache_data(ttl=300)
def get_gamma_walls():
    results = []
    for ticker in ["SPY", "QQQ", "IWM", "NVDA", "AAPL", "TSLA", "SMH", "XLE"]:
        try:
            df = yf.download(ticker, period="5d", progress=False).dropna()
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            px = float(df['Close'].iloc[-1])
            tk = yf.Ticker(ticker)
            expirations = tk.options
            if not expirations: continue
            chain = tk.option_chain(expirations[0])
            calls, puts = chain.calls, chain.puts
            if calls.empty or puts.empty: continue
            
            total_call_oi, total_put_oi = calls['openInterest'].sum(), puts['openInterest'].sum()
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

            calls_sorted = calls.sort_values(by='openInterest', ascending=False)
            puts_sorted = puts.sort_values(by='openInterest', ascending=False)
                
            c1, c1_oi, c1_vol = calls_sorted.iloc[0]['strike'], calls_sorted.iloc[0]['openInterest'], calls_sorted.iloc[0]['volume']
            c2 = calls_sorted.iloc[1]['strike'] if len(calls_sorted) > 1 else c1
            c2_oi = calls_sorted.iloc[1]['openInterest'] if len(calls_sorted) > 1 else c1_oi
            c2_vol = calls_sorted.iloc[1]['volume'] if len(calls_sorted) > 1 else c1_vol
            
            p1, p1_oi, p1_vol = puts_sorted.iloc[0]['strike'], puts_sorted.iloc[0]['openInterest'], puts_sorted.iloc[0]['volume']
            p2 = puts_sorted.iloc[1]['strike'] if len(puts_sorted) > 1 else p1
            p2_oi = puts_sorted.iloc[1]['openInterest'] if len(puts_sorted) > 1 else p1_oi
            p2_vol = puts_sorted.iloc[1]['volume'] if len(puts_sorted) > 1 else p1_vol
            
            merged = pd.merge(calls[['strike', 'openInterest']], puts[['strike', 'openInterest']], on='strike', how='outer').fillna(0)
            zg = float(merged.assign(total_oi=merged['openInterest_x'] + merged['openInterest_y']).sort_values(by='total_oi', ascending=False).iloc[0]['strike'])

            if c1 > c2: c1, c2, c1_oi, c2_oi, c1_vol, c2_vol = c2, c1, c2_oi, c1_oi, c2_vol, c1_vol
            if p1 < p2: p1, p2, p1_oi, p2_oi, p1_vol, p2_vol = p2, p1, p2_oi, p1_oi, p2_vol, p1_vol

            results.append({
                "Ticker": ticker, "Price": px, "Zero Gamma": zg, "PCR": pcr,
                "Call Wall 1": c1, "Dist CW1": ((c1 - px) / px) * 100, "CW1_OI": c1_oi, "CW1_Active": c1_vol > c1_oi,
                "Call Wall 2": c2, "Dist CW2": ((c2 - px) / px) * 100, "CW2_OI": c2_oi, "CW2_Active": c2_vol > c2_oi,
                "Put Wall 1": p1, "Dist PW1": ((px - p1) / px) * 100, "PW1_OI": p1_oi, "PW1_Active": p1_vol > p1_oi,
                "Put Wall 2": p2, "Dist PW2": ((px - p2) / px) * 100, "PW2_OI": p2_oi, "PW2_Active": p2_vol > p2_oi
            })
        except: pass
    return results

@st.cache_data(ttl=3600)
def run_credit_stress_engine():
    try:
        df_hyg, df_ief, df_spy = yf.download("HYG", period="6mo", progress=False), yf.download("IEF", period="6mo", progress=False), yf.download("SPY", period="6mo", progress=False)
        if isinstance(df_hyg.columns, pd.MultiIndex): df_hyg.columns, df_ief.columns, df_spy.columns = df_hyg.columns.droplevel(1), df_ief.columns.droplevel(1), df_spy.columns.droplevel(1)
        c_hyg, c_ief, c_spy = df_hyg['Close'].dropna(), df_ief['Close'].dropna(), df_spy['Close'].dropna()
        if c_hyg.index.tz is not None: c_hyg.index, c_ief.index, c_spy.index = c_hyg.index.tz_localize(None), c_ief.index.tz_localize(None), c_spy.index.tz_localize(None)
        df = pd.concat([c_hyg, c_ief, c_spy], axis=1, keys=['HYG', 'IEF', 'SPY']).dropna()
        df['Credit_Ratio'] = df['HYG'] / df['IEF']
        df['Ratio_20SMA'] = df['Credit_Ratio'].rolling(20).mean()
        return {
            "status": "online", "divergence": (float(df['SPY'].iloc[-1]) > float(df['SPY'].rolling(20).mean().iloc[-1])) and (float(df['Credit_Ratio'].iloc[-1]) < float(df['Ratio_20SMA'].iloc[-1])), 
            "ratio": float(df['Credit_Ratio'].iloc[-1]), "sma": float(df['Ratio_20SMA'].iloc[-1]), "history": df[['SPY', 'Credit_Ratio', 'Ratio_20SMA']].tail(120)
        }
    except: return {"status": "offline"}

@st.cache_data(ttl=900)
def get_options_skew(ticker="SPY"):
    try:
        df = yf.download(ticker, period="5d", progress=False).dropna()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        px = float(df['Close'].iloc[-1])
        chain = yf.Ticker(ticker).option_chain(yf.Ticker(ticker).options[1])
        calls, puts = chain.calls, chain.puts
        c_strike = calls.iloc[(calls['strike'] - (px * 1.05)).abs().argsort()[:1]]
        p_strike = puts.iloc[(puts['strike'] - (px * 0.95)).abs().argsort()[:1]]
        c_iv = c_strike['impliedVolatility'].values[0] if not c_strike.empty else 0
        p_iv = p_strike['impliedVolatility'].values[0] if not p_strike.empty else 0
        return {"status": "online", "pcr": puts['openInterest'].sum() / calls['openInterest'].sum() if calls['openInterest'].sum() > 0 else 1, "skew": (p_iv - c_iv) * 100}
    except: return {"status": "offline"}

@st.cache_data(ttl=3600)
def run_rotation_engine(sym1="SPY", sym2="DBC"):
    try:
        df1, df2 = yf.download(sym1, period="1y", progress=False).dropna(), yf.download(sym2, period="1y", progress=False).dropna()
        if isinstance(df1.columns, pd.MultiIndex): df1.columns, df2.columns = df1.columns.droplevel(1), df2.columns.droplevel(1)
        c1, c2 = df1['Close'], df2['Close']
        if c1.index.tz is not None: c1.index, c2.index = c1.index.tz_localize(None), c2.index.tz_localize(None)
        df = pd.concat([c1, c2], axis=1, keys=[sym1, sym2]).dropna()
        df['Ratio'] = df[sym1] / df[sym2]
        df['Ratio_50SMA'] = df['Ratio'].rolling(50).mean()
        return {"status": "online", "favored": float(df['Ratio'].iloc[-1]) > float(df['Ratio_50SMA'].iloc[-1]), "chart": df[['Ratio', 'Ratio_50SMA']].tail(90)}
    except: return {"status": "offline"}

@st.cache_data(ttl=900)
def run_master_screener():
    results = []
    tickers = list(dict.fromkeys(cfg.LIEUTENANTS))
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="6mo", progress=False).dropna()
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            if df.empty or len(df) < 50: continue
            c, v = float(df['Close'].iloc[-1]), float(df['Volume'].iloc[-1])
            sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
            ema_9, ema_21 = float(df['Close'].ewm(span=9, adjust=False).mean().iloc[-1]), float(df['Close'].ewm(span=21, adjust=False).mean().iloc[-1])
            df['Vol_SMA_20'] = df['Volume'].rolling(20).mean()
            vol_sma_9, vol_sma_20, vol_sma_50 = float(df['Volume'].rolling(9).mean().iloc[-1]), float(df['Vol_SMA_20'].iloc[-1]), float(df['Volume'].rolling(50).mean().iloc[-1])
            df['Range'] = df['High'] - df['Low']
            df['ATR_20'] = df['Range'].rolling(20).mean()
            atr_20, rng = float(df['ATR_20'].iloc[-1]), float(df['Range'].iloc[-1])
            
            df['Rel_Vol'] = df['Volume'] / (df['Vol_SMA_20'] + 1)
            df['Up_Day'] = df['Close'] > df['Open']
            df['Close_Pos'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'] + 0.0001) 
            
            score = sum([c > sma_50, ema_9 > ema_21, vol_sma_9 > vol_sma_50, (v / vol_sma_20) >= 1.5 if vol_sma_20 > 0 else False, (rng / atr_20) <= 0.75 if atr_20 > 0 else False])
            last_2 = df.tail(2)
            whale_block = any((row['Rel_Vol'] >= 2.5 and row['Up_Day'] and row['Close_Pos'] >= 0.7) for _, row in last_2.iterrows())
            acc_days = len(df.tail(10)[(df.tail(10)['Rel_Vol'] > 1.2) & (df.tail(10)['Up_Day'])])
            dist_days = len(df.tail(10)[(df.tail(10)['Rel_Vol'] > 1.2) & (~df.tail(10)['Up_Day'])])
            cluster_acc = acc_days >= 3 and dist_days <= 1
            
            if whale_block and cluster_acc: cat = "☢️ WHALE + CLUSTER"
            elif whale_block: cat = "🐋 WHALE BLOCK"
            elif cluster_acc: cat = "🔥 CLUSTER ACCUMULATION"
            elif score == 5: cat = "🔥 PERFECT TIER 1"
            elif ((v / vol_sma_20) >= 1.5) and ((rng / atr_20) <= 0.75) and not (c > sma_50): cat = "🦇 STEALTH (DARK POOL)"
            elif (ema_9 > ema_21) and (vol_sma_9 > vol_sma_50): cat = "🚀 KINETIC BREAKOUT"
            else: cat = "STANDBY"
            
            if cat != "STANDBY":
                results.append({"Ticker": ticker, "Price": f"${c:.2f}", "Category": cat, "Vol Spike (x)": f"{v/vol_sma_20:.1f}x" if vol_sma_20 > 0 else "0.0x", "Acc Days (10d)": f"{acc_days}", "Compression (x)": f"{rng/atr_20:.2f}x" if atr_20 > 0 else "0.00x", "Titan Score": f"{score}/5"})
        except Exception: pass
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def run_rrg_engine(universe_key="Macro (Assets)"):
    try:
        universes = {"Macro (Assets)": {"benchmark": "SPY", "tickers": cfg.MACRO_ASSETS}, "Sectors (S&P 500)": {"benchmark": "SPY", "tickers": cfg.SECTORS}, "Subsectors (Industry)": {"benchmark": "SPY", "tickers": cfg.SUBSECTORS}, "AI & Tech Infra": {"benchmark": "SPY", "tickers": cfg.AI_THEMATIC}, "Crypto Proxy": {"benchmark": "SPY", "tickers": cfg.CRYPTO_THEMATIC}}
        benchmark, tickers = universes[universe_key]["benchmark"], universes[universe_key]["tickers"]
        closes, volumes = pd.DataFrame(), pd.DataFrame()
        for t in tickers + [benchmark]:
            try:
                d = yf.download(t, period="6mo", progress=False).dropna()
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.droplevel(1)
                if not d.empty:
                    closes[t], volumes[t] = d['Close'], d['Volume']
                    if closes[t].index.tz is not None: closes[t].index, volumes[t].index = closes[t].index.tz_localize(None), volumes[t].index.tz_localize(None)
            except: pass
        if closes.empty or benchmark not in closes.columns: return {"status": "offline"}
        
        results = []
        for ticker in tickers:
            if ticker not in closes.columns: continue
            rs = closes[ticker] / closes[benchmark]
            rs_ratio = (rs.rolling(10).mean() / rs.rolling(40).mean()) * 100
            rs_mom = (rs_ratio / rs_ratio.rolling(10).mean()) * 100
            vol_ratio = volumes[ticker] / volumes[ticker].rolling(20).mean()
            rs_ratio, rs_mom, vol_ratio = rs_ratio.dropna(), rs_mom.dropna(), vol_ratio.dropna()
            if not rs_ratio.empty and not rs_mom.empty:
                results.append({"Ticker": ticker, "RS_Ratio": float(rs_ratio.iloc[-1]), "RS_Mom": float(rs_mom.iloc[-1]), "Tail_X": rs_ratio.tail(5).tolist(), "Tail_Y": rs_mom.tail(5).tolist(), "Bubble_Size": max(6, min(float(vol_ratio.iloc[-1]) * 8, 25)), "Vol_Spike_Text": f"{float(vol_ratio.iloc[-1]):.2f}x Vol"})
        return {"status": "online", "data": results, "benchmark": benchmark}
    except: return {"status": "offline"}

# ==============================================================================
# ROUTING LOGIC: LIVE COMMAND CENTER
# ==============================================================================
if app_mode == "🚀 LIVE COMMAND CENTER":
    with st.spinner("Calibrating Volatility Engines..."):
        risk = get_risk_engine()
        if risk['status'] == 'online':
            r = risk['ratio']
            if r >= 1.0: color, title, sub, b_bg = "#FF4444", "🚨 DEFCON 1: VOLATILITY INVERTED", "Market Makers pricing immediate crash. HALT LONGS.", "rgba(255, 68, 68, 0.1)"
            elif r >= 0.9: color, title, sub, b_bg = "#FFAA00", "⚠️ DEFCON 3: ELEVATED RISK", "Term Structure flattening. Reduce sizing.", "rgba(255, 170, 0, 0.1)"
            else: color, title, sub, b_bg = "#39FF14", "🟢 DEFCON 5: NORMAL CONTANGO", "Institutional fear low. High probability breakouts.", "rgba(57, 255, 20, 0.05)"
            st.markdown(f"<div class='defcon-banner' style='border-color: {color}; background-color: {b_bg};'><div class='defcon-title' style='color: {color};'>{title}</div><div class='defcon-sub' style='color: #c9d1d9;'>{sub} <span style='color:{color};'>(VIX/VIX3M: {r:.2f})</span></div></div>", unsafe_allow_html=True)
        else: st.error("DEFCON Engine Offline.")

    st.markdown("<div class='apex-header'>🌐 MACRO TIDE & DEALER MATRIX</div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        macro_df, date = get_macro_tide()
        if not macro_df.empty:
            for _, row in macro_df.iterrows():
                i, l = row['Intensity (%)'], row['Net Position'] > 0
                if l and i >= 10: cc, tc, m, mc = "card-bullish", "#39FF14", "PRIORITIZE LONGS", "mandate-buy"
                elif not l and i >= 20: cc, tc, m, mc = "card-bearish", "#FF4444", "AVOID LONGS / SEEK SHORTS", "mandate-sell"
                else: cc, tc, m, mc = "card-neutral", "#8b949e", "NEUTRAL TIDE", "mandate-warn"
                st.markdown(f"<div class='tactical-card {cc}' style='min-height:120px;'><div><div class='asset-title'>{row['Asset']}</div><div class='data-row'><span>BIAS:</span><span style='color:{tc}; font-weight:bold;'>{'NET LONG' if l else 'NET SHORT'} ({i:.1f}%)</span></div></div></div>", unsafe_allow_html=True)
    with col2:
        gamma_data = get_gamma_walls()
        if gamma_data:
            for g in gamma_data[:4]: # Show top 4 for space
                px, zg, pcr = g['Price'], g['Zero Gamma'], g['PCR']
                vol_state = "<span style='color:#39FF14;'>+GEX (CHOP)</span>" if px >= zg else "<span style='color:#FF4444;'>-GEX (TREND)</span>"
                pcr_color = "#FF4444" if pcr > 1.2 else "#39FF14" if pcr < 0.8 else "#8b949e"
                st.markdown(f"<div class='tactical-card {'card-neutral' if px >= zg else 'card-bearish'}' style='min-height:120px;'><div style='display:flex; justify-content:space-between;'><div class='asset-title'>{g['Ticker']} <span style='font-size:0.8rem; color:#8b949e;'>${px:.2f}</span></div><div style='font-size:0.85rem; font-weight:bold;'>{vol_state} <span style='color:{pcr_color};'>| PCR: {pcr:.2f}</span></div></div><div class='metric-sub'><div class='data-row'><span>T1 Call Wall: <b style='color:#FFF;'>${g['Call Wall 1']:.2f}</b></span><span>T1 Put Wall: <b style='color:#FFF;'>${g['Put Wall 1']:.2f}</b></span></div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔍 TITAN MASTER SCREENER</div>", unsafe_allow_html=True)
    if st.button("EXECUTE GLOBAL SCAN"):
        with st.spinner("Compiling cross-asset vectors..."):
            screen_df = run_master_screener()
            if not screen_df.empty: st.dataframe(screen_df.sort_values(by="Vol Spike (x)", ascending=False), width="stretch", hide_index=True)
            else: st.info("No actionable setups detected.")

# ==============================================================================
# ROUTING LOGIC: LIVE PORTFOLIO MANAGER
# ==============================================================================
elif app_mode == "💼 LIVE PORTFOLIO MANAGER":
    st.markdown("<div class='apex-header'>💼 ACTIVE BOOK & RISK LEDGER</div>", unsafe_allow_html=True)
    
    db = load_portfolio()
    
    # 1. LIVE DATA FETCHING & MATH ENGINE
    portfolio_data = []
    total_open_pnl_dollars = 0.0
    total_invested = 0.0
    
    if db["open_positions"]:
        with st.spinner("Syncing Active Book to Live Market Data..."):
            tickers = [p["ticker"] for p in db["open_positions"]]
            live_data = yf.download(tickers, period="6mo", progress=False)
            if isinstance(live_data.columns, pd.MultiIndex): live_data.columns = live_data.columns.droplevel(1)
            
            for pos in db["open_positions"]:
                t = pos["ticker"]
                try:
                    df = live_data.xs(t, level=1, axis=1).dropna() if len(tickers) > 1 else live_data.dropna()
                    if df.empty: continue
                    
                    entry_date = pd.to_datetime(pos["entry_date"])
                    current_px = float(df['Close'].iloc[-1])
                    shares = float(pos["shares"])
                    entry_px = float(pos["entry_price"])
                    user_stop = float(pos["current_stop"])
                    
                    # Core Math
                    invested = entry_px * shares
                    current_value = current_px * shares
                    pnl_dollars = current_value - invested
                    pnl_pct = (pnl_dollars / invested) * 100
                    days_held = (datetime.now() - entry_date).days
                    
                    total_open_pnl_dollars += pnl_dollars
                    total_invested += invested
                    
                    # Risk Math (Optimal Trailing Stop)
                    df_since_entry = df[df.index >= entry_date]
                    highest_high = float(df_since_entry['High'].max()) if not df_since_entry.empty else current_px
                    atr_20 = float((df['High'] - df['Low']).rolling(20).mean().iloc[-1])
                    sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
                    
                    optimal_stop = highest_high - (2 * atr_20)
                    
                    # Logic Tree for Mandates
                    if current_px < user_stop:
                        action, action_color = "🚨 STOP HIT - LIQUIDATE", "#FF4444"
                    elif pnl_pct > 20.0 and current_px < float(df['Close'].ewm(span=9).mean().iloc[-1]):
                        action, action_color = "✂️ TRIM POSITION (LOCK PROFIT)", "#FFAA00"
                    elif user_stop < (optimal_stop * 0.99): # 1% buffer to prevent constant nagging
                        action, action_color = f"⚠️ RAISE STOP TO ${optimal_stop:.2f}", "#FFAA00"
                    elif current_px < sma_50:
                        action, action_color = "⚠️ STRUCTURAL RISK (< 50 SMA)", "#FF4444"
                    else:
                        action, action_color = "✅ HOLD", "#39FF14"
                        
                    portfolio_data.append({
                        "ID": pos["id"], "Ticker": t, "Entry Date": pos["entry_date"], "Days Held": days_held,
                        "Shares": shares, "Entry Px": entry_px, "Current Px": current_px,
                        "$ PnL": pnl_dollars, "% PnL": pnl_pct,
                        "User Stop": user_stop, "Optimal Stop": optimal_stop, "Action": action, "Action Color": action_color
                    })
                except Exception: pass

    # 2. PORTFOLIO SUMMARY WIDGET
    total_realized_pnl = sum([t["pnl_dollars"] for t in db["closed_trades"]])
    total_open_pct = (total_open_pnl_dollars / total_invested * 100) if total_invested > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Open Positions", len(db["open_positions"]))
    m2.metric("Open Unrealized P&L ($)", f"${total_open_pnl_dollars:,.2f}")
    m3.metric("Open Portfolio ROI (%)", f"{total_open_pct:+.2f}%")
    m4.metric("Accumulated Realized P&L ($)", f"${total_realized_pnl:,.2f}")
    
    st.markdown("---")
    
    # 3. ACTIVE POSITIONS DASHBOARD (TACTICAL CARDS)
    st.markdown("<h3 style='color:#FFF;'>Active Engagement Board</h3>", unsafe_allow_html=True)
    
    if not portfolio_data:
        st.info("No active trades logged. Use the control panel below to initiate tracking.")
    else:
        for p in portfolio_data:
            pnl_color = "#39FF14" if p["% PnL"] > 0 else "#FF4444"
            st.markdown(f"""
            <div style='background: #161b22; border: 1px solid #30363d; border-left: 5px solid {pnl_color}; border-radius: 6px; padding: 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;'>
                <div style='width: 15%;'>
                    <div style='font-size: 1.4rem; font-weight: 900; color: #FFF;'>{p["Ticker"]}</div>
                    <div style='font-size: 0.8rem; color: #8b949e;'>{p["Shares"]} shrs @ ${p["Entry Px"]:.2f}</div>
                </div>
                <div style='width: 15%; text-align: right;'>
                    <div style='font-size: 1.2rem; font-weight: bold; color: {pnl_color};'>{p["% PnL"]:+.2f}%</div>
                    <div style='font-size: 0.9rem; color: {pnl_color};'>${p["$ PnL"]:+.2f}</div>
                </div>
                <div style='width: 25%; text-align: center; border-left: 1px dashed #30363d; border-right: 1px dashed #30363d; padding: 0 15px;'>
                    <div style='font-size: 0.8rem; color: #8b949e;'>Logged Stop: <b style='color:#FFF;'>${p["User Stop"]:.2f}</b></div>
                    <div style='font-size: 0.8rem; color: #8b949e;'>Math Optimal: <b style='color:#58a6ff;'>${p["Optimal Stop"]:.2f}</b></div>
                    <div style='font-size: 0.8rem; color: #8b949e; margin-top: 5px;'>Days Held: {p["Days Held"]}</div>
                </div>
                <div style='width: 35%; text-align: center; font-weight: 800; font-size: 1.1rem; color: {p["Action Color"]};'>
                    [ {p["Action"]} ]
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 4. TRADE MANAGEMENT CONTROL PANEL
    st.markdown("<h3 style='color:#FFF; margin-top:40px;'>Control Panel</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    
    with c1:
        st.markdown("<h4 style='color:#58a6ff;'>Log New Entry</h4>", unsafe_allow_html=True)
        with st.form("new_trade_form", clear_on_submit=True):
            f_ticker = st.text_input("Ticker Symbol").upper()
            f_date = st.date_input("Purchase Date")
            f_px = st.number_input("Fill Price ($)", min_value=0.01, format="%.2f")
            f_shrs = st.number_input("Shares", min_value=0.01, format="%.4f")
            f_stop = st.number_input("Initial Stop Loss ($)", min_value=0.01, format="%.2f")
            
            if st.form_submit_button("LOCK POSITION"):
                if f_ticker:
                    new_id = str(int(datetime.now().timestamp()))
                    db["open_positions"].append({
                        "id": new_id, "ticker": f_ticker, "entry_date": f_date.strftime('%Y-%m-%d'),
                        "entry_price": f_px, "shares": f_shrs, "current_stop": f_stop
                    })
                    save_portfolio(db)
                    st.success(f"Logged {f_ticker} successfully.")
                    st.rerun()

    with c2:
        st.markdown("<h4 style='color:#FFAA00;'>Update or Close Position</h4>", unsafe_allow_html=True)
        if db["open_positions"]:
            with st.form("manage_trade_form"):
                target_ticker = st.selectbox("Select Active Position", [p["ticker"] for p in db["open_positions"]])
                new_stop_val = st.number_input("Update Stop Price To ($)", min_value=0.0)
                is_close = st.checkbox("LIQUIDATE POSITION (Close Trade)")
                close_px = st.number_input("Actual Exit Price ($)", min_value=0.0) if is_close else 0.0
                
                if st.form_submit_button("EXECUTE"):
                    target_idx = next(i for i, p in enumerate(db["open_positions"]) if p["ticker"] == target_ticker)
                    pos = db["open_positions"][target_idx]
                    
                    if is_close and close_px > 0:
                        # Move to closed ledger
                        pnl = (close_px - pos["entry_price"]) * pos["shares"]
                        db["closed_trades"].append({
                            "ticker": pos["ticker"], "entry_date": pos["entry_date"], "close_date": datetime.now().strftime('%Y-%m-%d'),
                            "entry_price": pos["entry_price"], "close_price": close_px, "shares": pos["shares"], "pnl_dollars": pnl
                        })
                        db["open_positions"].pop(target_idx)
                        save_portfolio(db)
                        st.success(f"Position Closed. Realized P&L: ${pnl:.2f}")
                        st.rerun()
                    elif new_stop_val > 0:
                        # Update stop
                        db["open_positions"][target_idx]["current_stop"] = new_stop_val
                        save_portfolio(db)
                        st.success(f"Stop updated for {target_ticker}")
                        st.rerun()

# ==============================================================================
# ROUTING LOGIC: QUANT OPTIMIZER LAB
# ==============================================================================
elif app_mode == "🧪 QUANT OPTIMIZER LAB":
    st.markdown("<div class='apex-header'>🔬 GLOBAL QUANTITATIVE OPTIMIZER</div>", unsafe_allow_html=True)
    st.info("Optimizer Engine logic remains active in this module.")
