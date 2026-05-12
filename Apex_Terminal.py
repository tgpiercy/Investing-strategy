# FILE: apex_terminal.py
# ROLE: Master UI Dashboard
# ARCHITECTURE: Streamlit Convergence (Tactical UI V5.44 + Full Restoration)
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
st.sidebar.markdown("<p style='font-size: 0.8rem; color: #8b949e; text-align: center;'>TITAN OMEGA V5.44<br>System Online.</p>", unsafe_allow_html=True)

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
        data = yf.download(["^VIX", "^VIX3M"], period="5d", progress=False)['Close'].dropna()
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
def get_options_flow_chart_data(live_pcr, ticker="SPY"):
    try:
        df = yf.download([ticker, "^VIX"], period="6mo", progress=False)['Close'].dropna()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        vix = df['^VIX']
        sim_pcr = 0.6 + ((vix - vix.min()) / (vix.max() - vix.min()) * 1.0)
        df['PCR_Proxy'] = sim_pcr + (live_pcr - float(sim_pcr.iloc[-1]))
        return df.tail(120)
    except: return None

@st.cache_data(ttl=3600)
def run_rotation_engine(sym1="SPY", sym2="DBC"):
    try:
        df1, df2 = yf.download(sym1, period="1y", progress=False).dropna(), yf.download(sym2, period="1y", progress=False).dropna()
        if isinstance(df1.columns, pd.MultiIndex): df1.columns, df2.columns = df1.columns.droplevel(1), df2.columns.droplevel(1)
        c1, c2 = df1['Close'], df2['Close']
        if c1.index.tz is not None: c1.index, c2.index = c1.index.tz_localize(None), c2.index.tz_localize(None)
        df = pd.concat([c1, c2], axis=1, keys=[sym1, sym2]).dropna()
        df['Ratio'], df['Ratio_50SMA'] = df[sym1] / df[sym2], (df[sym1] / df[sym2]).rolling(50).mean()
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

@st.cache_data(ttl=300)
def run_tactical_chart(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False).dropna()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        if df.empty or len(df) < 50: return None, None
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['Vol_SMA_9'], df['Vol_SMA_20'], df['Vol_SMA_50'] = df['Volume'].rolling(window=9).mean(), df['Volume'].rolling(window=20).mean(), df['Volume'].rolling(window=50).mean()
        df['ATR_20'] = (df['High'] - df['Low']).rolling(window=20).mean()
        df['Vol_Ratio'] = np.where(df['Vol_SMA_20'] > 0, df['Volume'] / df['Vol_SMA_20'], 0)
        df['Range_Comp'] = np.where(df['ATR_20'] > 0, (df['High'] - df['Low']) / df['ATR_20'], 1)
        dp_mask = (df['Vol_Ratio'] >= 1.5) & (df['Range_Comp'] <= 0.75)
        dp_signals = df[dp_mask]

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="PriceAction"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#8b949e', width=2, dash='dot'), name='50 SMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], line=dict(color='#39FF14', width=1.5), name='9 EMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], line=dict(color='#FFAA00', width=1.5), name='21 EMA'), row=1, col=1)

        if not dp_signals.empty:
            bubble_sizes = np.clip(dp_signals['Vol_Ratio'] * 15, 25, 75)
            fig.add_trace(go.Scatter(
                x=dp_signals.index, y=dp_signals['Close'], mode='markers',
                marker=dict(color='rgba(138, 43, 226, 0.75)', size=bubble_sizes, line=dict(color='#FFFFFF', width=2)),
                name='Dark Pool Block', hovertext=[f"Vol Spike: {r:.2f}x<br>Compression: {c:.2f}x" for r, c in zip(dp_signals['Vol_Ratio'], dp_signals['Range_Comp'])], hoverinfo="text+x+y"
            ), row=1, col=1)

        colors = ['rgba(57, 255, 20, 0.6)' if row['Close'] >= row['Open'] else 'rgba(255, 68, 68, 0.6)' for idx, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Vol_SMA_50'], line=dict(color='#8b949e', width=1.5, dash='dot'), name='50 Vol SMA'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Vol_SMA_20'], line=dict(color='#58a6ff', width=2), name='20 Vol SMA'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Vol_SMA_9'], line=dict(color='#39FF14', width=1.5), name='9 Vol SMA'), row=2, col=1)

        fig.update_layout(plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', font=dict(color='#c9d1d9'), margin=dict(l=20, r=20, t=20, b=20), height=650, xaxis_rangeslider_visible=False, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(gridcolor='#30363d', zeroline=False)
        fig.update_xaxes(gridcolor='#30363d', zeroline=False)

        latest_data = {
            "Close": float(df['Close'].iloc[-1]), "SMA_50": float(df['SMA_50'].iloc[-1]), "EMA_9": float(df['EMA_9'].iloc[-1]), "EMA_21": float(df['EMA_21'].iloc[-1]),
            "Vol_SMA_9": float(df['Vol_SMA_9'].iloc[-1]), "Vol_SMA_50": float(df['Vol_SMA_50'].iloc[-1]), "Vol_Ratio": float(df['Vol_Ratio'].iloc[-1]), "Range_Comp": float(df['Range_Comp'].iloc[-1]), "ATR_20": float(df['ATR_20'].iloc[-1])
        }
        return fig, latest_data
    except: return None, None

def run_fast_backtest(df: pd.DataFrame, vol_thresh: float, atr_mult: float):
    signal = (df['Close'] > df['SMA_50']) & (df['EMA_9'] > df['EMA_21']) & (df['EMA_9'].shift(1) <= df['EMA_21'].shift(1)) & (df['Volume'] > (df['Vol_SMA_20'] * vol_thresh))
    closes, opens, lows = df['Close'].values, df['Open'].values, df['Low'].values
    sma50s, atrs, signals = df['SMA_50'].values, df['ATR_20'].values, signal.values
    trades, in_pos, entry_px, stop_px = [], False, 0.0, 0.0
    
    for i in range(1, len(df) - 1):
        if not in_pos:
            if signals[i-1]:
                in_pos, entry_px, stop_px = True, opens[i], closes[i-1] - (atr_mult * atrs[i-1])
                if entry_px < stop_px: stop_px = entry_px
        else:
            if lows[i] <= stop_px:
                trades.append(((stop_px if opens[i] >= stop_px else opens[i]) - entry_px) / entry_px)
                in_pos = False
            elif closes[i] < sma50s[i]:
                trades.append((opens[i+1] - entry_px) / entry_px)
                in_pos = False
            else:
                new_stop = closes[i] - (atr_mult * atrs[i])
                if new_stop > stop_px: stop_px = new_stop
                
    if in_pos: trades.append((closes[-1] - entry_px) / entry_px)
    if not trades: return None
    
    trades_arr = np.array(trades)
    wins, losses = trades_arr[trades_arr > 0], trades_arr[trades_arr <= 0]
    wr = len(wins) / len(trades_arr)
    lr = 1 - wr
    avg_w = wins.mean() if len(wins) > 0 else 0.0
    avg_l = losses.mean() if len(losses) > 0 else 0.0
    exp = (wr * avg_w) / abs(lr * avg_l) if lr > 0 and avg_l != 0 else 0.0
    
    return {"Vol Thresh": vol_thresh, "ATR Multiplier": atr_mult, "Trades": len(trades_arr), "Win Rate (%)": wr * 100, "Expectancy": exp, "Total ROI (%)": (np.prod(1 + trades_arr) - 1) * 100}

@st.cache_data(ttl=3600)
def run_global_optimizer(period="5y"):
    tickers = list(dict.fromkeys(cfg.LIEUTENANTS))
    df_raw = yf.download(tickers, period=period, progress=False)
    results = []
    vol_ranges, atr_ranges = [1.2, 1.5, 1.8, 2.0], [1.5, 2.0, 2.5, 3.0]
    
    for ticker in tickers:
        try:
            df = df_raw.xs(ticker, level=1, axis=1).dropna() if len(tickers) > 1 else df_raw.dropna()
            if df.empty or len(df) < 100: continue
            
            df['SMA_50'], df['EMA_9'], df['EMA_21'] = df['Close'].rolling(50).mean(), df['Close'].ewm(span=9, adjust=False).mean(), df['Close'].ewm(span=21, adjust=False).mean()
            df['Range'] = df['High'] - df['Low']
            df['ATR_20'], df['Vol_SMA_20'] = df['Range'].rolling(20).mean(), df['Volume'].rolling(20).mean()
            df = df.dropna()
            
            best_exp, best_res = -1, None
            for vt in vol_ranges:
                for am in atr_ranges:
                    res = run_fast_backtest(df, vt, am)
                    if res and res['Expectancy'] > best_exp:
                        best_exp, best_res = res['Expectancy'], res
            
            if best_res and best_exp > 0.2:
                results.append({"Ticker": ticker, "Optimal Vol Spike": f"{best_res['Vol Thresh']}x", "Optimal ATR Stop": f"{best_res['ATR Multiplier']}x", "Win Rate": f"{best_res['Win Rate (%)']:.1f}%", "Expectancy": f"{best_res['Expectancy']:.2f}", "Total ROI": f"{best_res['Total ROI (%)']:+.1f}%", "Total Trades": best_res['Trades']})
        except: pass
    return pd.DataFrame(results)

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

    st.markdown("<div class='apex-header' style='margin-top: 20px;'>🏛️ FOMC LIQUIDITY & YIELD CURVE (MACRO PLUMBING)</div>", unsafe_allow_html=True)
    with st.spinner("Fetching FRED Macro Data..."):
        fomc = get_fomc_data()
        if fomc['status'] == 'online':
            df_fomc, yc_val, ff_val = fomc['data'], fomc['current_yc'], fomc['current_ff']
            yc_color = "#FF4444" if yc_val < 0 else "#39FF14"
            st.markdown(f"<div style='display: flex; gap: 20px; margin-bottom: 20px;'><div class='tactical-card' style='flex: 1; min-height: 100px; border-left: 5px solid {yc_color};'><div class='metric-sub'>10Y-2Y YIELD CURVE</div><div class='price-text' style='color: {yc_color};'>{yc_val:+.2f}% ({fomc['curve_status']})</div></div><div class='tactical-card' style='flex: 1; min-height: 100px; border-left: 5px solid #58a6ff;'><div class='metric-sub'>FED FUNDS RATE (COST OF CAPITAL)</div><div class='price-text' style='color: #58a6ff;'>{ff_val:.2f}%</div></div></div>", unsafe_allow_html=True)
            fig_fomc = make_subplots(specs=[[{"secondary_y": True}]])
            fig_fomc.add_trace(go.Scatter(x=df_fomc.index, y=df_fomc['Yield_Curve'], name="10Y-2Y Spread", line=dict(color=yc_color, width=2), fill='tozeroy', fillcolor=f'rgba({255 if yc_val < 0 else 57}, {68 if yc_val < 0 else 255}, {68 if yc_val < 0 else 20}, 0.1)'), secondary_y=False)
            fig_fomc.add_trace(go.Scatter(x=df_fomc.index, y=df_fomc['Fed_Funds'], name="Fed Funds Rate", line=dict(color='#58a6ff', width=2, dash='dot')), secondary_y=True)
            fig_fomc.add_hline(y=0, line_dash="dash", line_color="#FFF", secondary_y=False)
            fig_fomc.update_layout(plot_bgcolor='#161b22', paper_bgcolor='#161b22', font=dict(color='#c9d1d9'), margin=dict(l=10, r=10, t=10, b=10), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
            fig_fomc.update_yaxes(title_text="Yield Curve Spread (%)", secondary_y=False, showgrid=False)
            fig_fomc.update_yaxes(title_text="Fed Funds Rate (%)", secondary_y=True, showgrid=False)
            fig_fomc.update_xaxes(showgrid=False)
            st.plotly_chart(fig_fomc, width="stretch", key="fomc_chart")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🌐 GLOBAL LIQUIDITY PHYSICS (CROSS-ASSET PEARSON MATRIX)</div>", unsafe_allow_html=True)
    with st.spinner("Calculating 90-Day Rolling Cross-Asset Correlations..."):
        matrix_res = get_cross_asset_matrix()
        if matrix_res['status'] == 'online':
            corr_df = matrix_res['data']
            fig_hm = go.Figure(data=go.Heatmap(z=corr_df.values, x=corr_df.columns, y=corr_df.index, colorscale=[[0.0, '#FF4444'], [0.5, '#161b22'], [1.0, '#39FF14']], zmin=-1, zmax=1, text=corr_df.values, texttemplate="%{text}", showscale=False, hoverinfo="x+y+z"))
            fig_hm.update_layout(plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', font=dict(color='#c9d1d9', size=14), margin=dict(l=20, r=20, t=20, b=20), height=450, xaxis=dict(side="bottom", showgrid=False), yaxis=dict(autorange="reversed", showgrid=False))
            st.plotly_chart(fig_hm, width="stretch", key="heatmap_chart")

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown("<div class='apex-header' style='margin-top: 20px;'>🌊 MACRO TIDE (SMART MONEY)</div>", unsafe_allow_html=True)
        macro_df, date = get_macro_tide()
        if not macro_df.empty:
            for _, row in macro_df.iterrows():
                i, l = row['Intensity (%)'], row['Net Position'] > 0
                if l and i >= 10: cc, tc, m, mc = "card-bullish", "#39FF14", "PRIORITIZE LONGS", "mandate-buy"
                elif not l and i >= 20: cc, tc, m, mc = "card-bearish", "#FF4444", "AVOID LONGS / SEEK SHORTS", "mandate-sell"
                else: cc, tc, m, mc = "card-neutral", "#8b949e", "NEUTRAL TIDE", "mandate-warn"
                st.markdown(f"<div class='tactical-card {cc}'><div><div class='asset-title'>{row['Asset']}</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>BIAS:</span><span style='color:{tc}; font-weight:bold;'>{'NET LONG' if l else 'NET SHORT'} ({i:.1f}%)</span></div></div></div><div class='mandate-box {mc}'>[ {m} ]</div></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='apex-header' style='margin-top: 20px;'>☢️ DEALER MATRIX (LIVE GAMMA FLOW)</div>", unsafe_allow_html=True)
        with st.spinner("Scanning Institutional Options Chains & Kinetic Flow..."):
            gamma_data = get_gamma_walls()
            if gamma_data:
                for g in gamma_data:
                    zg, c1, c2, p1, p2, px, pcr = g['Zero Gamma'], g['Call Wall 1'], g['Call Wall 2'], g['Put Wall 1'], g['Put Wall 2'], g['Price'], g['PCR']
                    vol_state, cc_main = ("<span style='color:#39FF14;'>+GEX (CHOP/MEAN-REVERT)</span>", "card-neutral") if px >= zg else ("<span style='color:#FF4444;'>-GEX (TREND/HIGH-VOL)</span>", "card-bearish")
                    c1_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('CW1_Active') else ""
                    c2_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('CW2_Active') else ""
                    p1_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('PW1_Active') else ""
                    p2_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('PW2_Active') else ""
                    pcr_color = "#FF4444" if pcr > 1.2 else "#39FF14" if pcr < 0.8 else "#8b949e"
                    st.markdown(f"<div class='tactical-card {cc_main}'><div style='display:flex; justify-content:space-between; align-items:center;'><div class='asset-title'>{g['Ticker']} <span style='font-size:0.8rem; color:#8b949e;'>${px:.2f}</span></div><div style='font-size:0.85rem; font-weight:bold;'>{vol_state} <span style='color:{pcr_color}; margin-left:10px;'>| PCR: {pcr:.2f}</span></div></div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>T2 Call (Squeeze Target): <b style='color:#FFAA00;'>${c2:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['CW2_OI']):,})</span>{c2_tag}</span><span>{g['Dist CW2']:+.1f}%</span></div><div class='data-row'><span>T1 Call (Primary Ceiling): <b style='color:#FFF;'>${c1:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['CW1_OI']):,})</span>{c1_tag}</span><span>{g['Dist CW1']:+.1f}%</span></div><div class='data-row' style='background:rgba(255,255,255,0.05); padding:2px 5px;'><span>Zero-Gamma (Volatility Flip): <b style='color:#58a6ff;'>${zg:.2f}</b></span><span>{((zg-px)/px)*100:+.1f}%</span></div><div class='data-row'><span>T1 Put (Primary Floor): <b style='color:#FFF;'>${p1:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['PW1_OI']):,})</span>{p1_tag}</span><span>{g['Dist PW1']:+.1f}%</span></div><div class='data-row'><span>T2 Put (The Abyss): <b style='color:#FF4444;'>${p2:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['PW2_OI']):,})</span>{p2_tag}</span><span>{g['Dist PW2']:+.1f}%</span></div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🏦 INSTITUTIONAL CREDIT & VOLATILITY</div>", unsafe_allow_html=True)
    c_col1, c_col2 = st.columns([1, 1], gap="large")
    with c_col1:
        with st.spinner("Pulling High Yield Spreads..."):
            credit_data = run_credit_stress_engine()
            if credit_data['status'] == 'online':
                cc, tc, cm = ("card-bearish", "#FF4444", "RISK-OFF DIVERGENCE") if credit_data['divergence'] else ("card-bullish", "#39FF14", "CREDIT ALIGNED (RISK-ON)")
                st.markdown(f"<div class='tactical-card {cc}'><div><div class='asset-title'>CREDIT STRESS RADAR</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>HYG/IEF RATIO:</span><span style='color:#FFF; font-weight:bold;'>{credit_data['ratio']:.3f}</span></div><div class='data-row'><span>TREND:</span><span style='color:{tc}; font-weight:bold;'>{'DIVERGING' if credit_data['divergence'] else 'SUPPORTIVE'}</span></div></div></div><div class='mandate-box {'mandate-sell' if credit_data['divergence'] else 'mandate-buy'}'>[ {cm} ]</div></div>", unsafe_allow_html=True)
                df_c = credit_data['history']
                fig_c = make_subplots(specs=[[{"secondary_y": True}]])
                fig_c.add_trace(go.Scatter(x=df_c.index, y=df_c['SPY'], name="SPY Price", line=dict(color='#58a6ff', width=2)), secondary_y=False)
                fig_c.add_trace(go.Scatter(x=df_c.index, y=df_c['Credit_Ratio'], name="HYG/IEF Ratio", line=dict(color='#FF4444' if credit_data['divergence'] else '#39FF14', width=2)), secondary_y=True)
                fig_c.update_layout(plot_bgcolor='#161b22', paper_bgcolor='#161b22', font=dict(color='#c9d1d9'), margin=dict(l=10, r=10, t=10, b=10), height=280, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
                fig_c.update_yaxes(showgrid=False, zeroline=False); fig_c.update_xaxes(showgrid=False, zeroline=False)
                st.plotly_chart(fig_c, width="stretch", key="credit_chart")
    with c_col2:
        with st.spinner("Parsing Option Volatility Skew..."):
            skew_data = get_options_skew()
            if skew_data['status'] == 'online':
                is_fear = skew_data['skew'] > 5.0 or skew_data['pcr'] > 1.5
                sc, tc, sm = ("card-bearish", "#FF4444", "INSTITUTIONS HEDGING (FEAR)") if is_fear else ("card-bullish", "#39FF14", "VOL SKEW NORMAL")
                st.markdown(f"<div class='tactical-card {sc}'><div><div class='asset-title'>OPTIONS FLOW (SPY)</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>PUT/CALL RATIO:</span><span style='color:#FFF; font-weight:bold;'>{skew_data['pcr']:.2f}</span></div><div class='data-row'><span>SKEW (PUT IV - CALL IV):</span><span style='color:{tc}; font-weight:bold;'>{skew_data['skew']:+.2f}%</span></div></div></div><div class='mandate-box {'mandate-sell' if is_fear else 'mandate-buy'}'>[ {sm} ]</div></div>", unsafe_allow_html=True)
                df_o = get_options_flow_chart_data(skew_data['pcr'])
                if df_o is not None:
                    fig_o = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_o.add_trace(go.Scatter(x=df_o.index, y=df_o['SPY'], name="SPY Price", line=dict(color='#58a6ff', width=2)), secondary_y=False)
                    fig_o.add_trace(go.Scatter(x=df_o.index, y=df_o['PCR_Proxy'], name="Put/Call Ratio (Synthetic Proxy)", line=dict(color='#FF4444' if is_fear else '#FFAA00', width=2)), secondary_y=True)
                    fig_o.update_layout(plot_bgcolor='#161b22', paper_bgcolor='#161b22', font=dict(color='#c9d1d9'), margin=dict(l=10, r=10, t=10, b=10), height=280, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
                    fig_o.update_yaxes(showgrid=False, zeroline=False); fig_o.update_xaxes(showgrid=False, zeroline=False)
                    st.plotly_chart(fig_o, width="stretch", key="options_chart")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔄 MACRO ROTATION & RRG</div>", unsafe_allow_html=True)
    rot_col1, rot_col2 = st.columns([1, 1], gap="large")
    with rot_col1:
        rot_tabs = st.tabs(["Macro Flow (SPY / DBC)", "Risk Breadth (IJR / SPY)"])
        with rot_tabs[0]:
            spy_dbc = run_rotation_engine("SPY", "DBC")
            if spy_dbc['status'] == 'online':
                eq_favored = spy_dbc['favored']
                box_color, box_bg = ("#39FF14", "rgba(57, 255, 20, 0.05)") if eq_favored else ("#FFAA00", "rgba(255, 170, 0, 0.05)")
                st.markdown(f"<div style='border: 2px solid {box_color}; background-color: {box_bg}; border-radius: 8px; padding: 20px; margin-bottom: 20px;'><h3 style='color: {box_color}; margin-top: 0;'>SYSTEM READOUT: {'EQUITIES DOMINATING' if eq_favored else 'COMMODITIES DOMINATING'}</h3></div>", unsafe_allow_html=True)
                st.line_chart(spy_dbc['chart'], color=["#58a6ff", "#8b949e"], width="stretch")
        with rot_tabs[1]:
            breadth_engine = run_rotation_engine("IJR", "SPY")
            if breadth_engine['status'] == 'online':
                breadth_favored = breadth_engine['favored']
                box_color, box_bg = ("#39FF14", "rgba(57, 255, 20, 0.05)") if breadth_favored else ("#8b949e", "rgba(139, 148, 158, 0.05)")
                st.markdown(f"<div style='border: 2px solid {box_color}; background-color: {box_bg}; border-radius: 8px; padding: 20px; margin-bottom: 20px;'><h3 style='color: {box_color}; margin-top: 0;'>SYSTEM READOUT: {'SMALL CAPS LEADING (RISK-ON BREADTH)' if breadth_favored else 'LARGE CAPS DEFENSIVE (NARROW MARKET)'}</h3></div>", unsafe_allow_html=True)
                st.line_chart(breadth_engine['chart'], color=["#58a6ff", "#8b949e"], width="stretch")
    with rot_col2:
        selected_universe = st.radio("Select RRG Universe:", ["Sectors (S&P 500)", "Subsectors (Industry)", "AI & Tech Infra", "Macro (Assets)", "Crypto Proxy"], horizontal=True, label_visibility="collapsed")
        rrg_engine = run_rrg_engine(selected_universe)
        if rrg_engine['status'] == 'online':
            fig = go.Figure()
            fig.add_hline(y=100, line_dash="dash", line_color="#30363d", layer="below"); fig.add_vline(x=100, line_dash="dash", line_color="#30363d", layer="below")
            fig.add_annotation(x=101, y=101, text="LEADING", showarrow=False, font=dict(color="#39FF14", size=14), opacity=0.3)
            fig.add_annotation(x=101, y=99, text="WEAKENING", showarrow=False, font=dict(color="#FFAA00", size=14), opacity=0.3)
            fig.add_annotation(x=99, y=99, text="LAGGING", showarrow=False, font=dict(color="#FF4444", size=14), opacity=0.3)
            fig.add_annotation(x=99, y=101, text="IMPROVING", showarrow=False, font=dict(color="#58a6ff", size=14), opacity=0.3)
            for item in rrg_engine['data']:
                color = "#39FF14" if item["RS_Ratio"] > 100 and item["RS_Mom"] > 100 else "#FFAA00" if item["RS_Ratio"] > 100 and item["RS_Mom"] < 100 else "#FF4444" if item["RS_Ratio"] < 100 and item["RS_Mom"] < 100 else "#58a6ff"
                fig.add_trace(go.Scatter(x=item["Tail_X"], y=item["Tail_Y"], mode='lines+markers+text', name=item["Ticker"], text=[None, None, None, None, item["Ticker"]], textposition="top center", hovertext=f"Vol: {item['Vol_Spike_Text']}", marker=dict(size=[4, 4, 4, 4, item["Bubble_Size"]], color=color, line=dict(width=1, color="#FFF") if item["Bubble_Size"] > 10 else dict(width=0)), line=dict(width=2, color=color)))
            fig.update_layout(plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', font=dict(color='#c9d1d9'), xaxis=dict(title='Relative Strength vs Benchmark', gridcolor='#30363d', zeroline=False), yaxis=dict(title='Momentum', gridcolor='#30363d', zeroline=False), margin=dict(l=20, r=20, t=20, b=20), showlegend=False, height=400)
            st.plotly_chart(fig, width="stretch")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔍 TITAN MASTER SCREENER (UNIFIED GLOBAL SCAN)</div>", unsafe_allow_html=True)
    if st.button("EXECUTE GLOBAL SCAN"):
        with st.spinner("Compiling cross-asset vector data & institutional footprints..."):
            screen_df = run_master_screener()
            if not screen_df.empty: st.dataframe(screen_df.sort_values(by="Vol Spike (x)", ascending=False), width="stretch", hide_index=True)
            else: st.info("No actionable setups detected.")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🎯 TACTICAL RECON & DECODER</div>", unsafe_allow_html=True)
    recon_col1, recon_col2 = st.columns([1, 4], gap="medium")
    with recon_col1:
        target_category = st.selectbox("Category Lens:", ["Lieutenants (Watchlist)", "Indices", "Sectors (Macro)", "Subsectors (Micro)", "Thematic (AI/Crypto)"])
        active_list = cfg.MACRO_ASSETS if target_category == "Indices" else cfg.SECTORS if target_category == "Sectors (Macro)" else cfg.SUBSECTORS if target_category == "Subsectors (Micro)" else cfg.AI_THEMATIC + cfg.CRYPTO_THEMATIC if target_category == "Thematic (AI/Crypto)" else cfg.LIEUTENANTS
        target_chart = st.selectbox("Select Target:", active_list)
    with recon_col2:
        with st.spinner(f"Loading {target_chart}..."):
            chart_fig, last_data = run_tactical_chart(target_chart)
            if chart_fig: st.plotly_chart(chart_fig, width="stretch")
            else: st.error("Chart Engine Offline.")
    
    if last_data:
        c = last_data['Close']
        trend_bull, mom_bull, liq_bull = c > last_data['SMA_50'], last_data['EMA_9'] > last_data['EMA_21'], last_data['Vol_SMA_9'] > last_data['Vol_SMA_50']
        dp_active = (last_data['Vol_Ratio'] >= 1.5) and (last_data['Range_Comp'] <= 0.75)
        struct_dist, struct_pct = c - last_data['SMA_50'], ((c - last_data['SMA_50']) / c) * 100
        tact_dist, tact_pct = 2 * last_data['ATR_20'], ((2 * last_data['ATR_20']) / c) * 100
        tact_stop_price = c - tact_dist

        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        d_col1.markdown(f"<div class='tactical-card {'card-bullish' if trend_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>TREND (>50 SMA)</div><div class='price-text' style='color: {'#39FF14' if trend_bull else '#FF4444'};'>{'BULLISH' if trend_bull else 'BEARISH'}</div></div></div>", unsafe_allow_html=True)
        d_col2.markdown(f"<div class='tactical-card {'card-bullish' if mom_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>MOMENTUM (9>21)</div><div class='price-text' style='color: {'#39FF14' if mom_bull else '#FF4444'};'>{'IGNITED' if mom_bull else 'LAGGING'}</div></div></div>", unsafe_allow_html=True)
        d_col3.markdown(f"<div class='tactical-card {'card-bullish' if liq_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>LIQUIDITY (9>50 VOL)</div><div class='price-text' style='color: {'#39FF14' if liq_bull else '#FF4444'};'>{'EXPANDING' if liq_bull else 'CONTRACTING'}</div></div></div>", unsafe_allow_html=True)
        d_col4.markdown(f"<div class='tactical-card {'card-squeeze' if dp_active else 'card-neutral'}' style='min-height: 100px;'><div><div class='metric-sub'>DARK POOL BLOCK</div><div class='price-text' style='color: {'#FFAA00' if dp_active else '#8b949e'};'>{'DETECTED' if dp_active else 'CLEAR'}</div></div></div>", unsafe_allow_html=True)
        
        st.markdown(f"<div style='background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin-top: 20px;'><b style='color: #58a6ff;'>RISK DRAWDOWN MATRIX</b><br><br><div style='display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(139, 148, 158, 0.2); padding-bottom: 10px; margin-bottom: 10px;'><span style='color: #8b949e;'>Structural Risk (To 50 SMA):</span><span style='color: #FFF; font-weight: bold;'>Stop: ${last_data['SMA_50']:.2f} | Risk: -${abs(struct_dist):.2f} / Share ({abs(struct_pct):.2f}%)</span></div><div style='display: flex; justify-content: space-between;'><span style='color: #8b949e;'>Tactical Risk (2x ATR Trailing):</span><span style='color: #FFF; font-weight: bold;'>Stop: ${tact_stop_price:.2f} | Risk: -${tact_dist:.2f} / Share ({tact_pct:.2f}%)</span></div></div>", unsafe_allow_html=True)
        st.code(f"[{datetime.now().strftime('%Y-%m-%d')}] TARGET: {target_chart} @ ${c:.2f} | T: {'BULL' if trend_bull else 'BEAR'} | M: {'IGNITED' if mom_bull else 'LAGGING'} | L: {'EXPANDING' if liq_bull else 'CONTRACTING'} | DP: {'YES' if dp_active else 'NO'} | STRUC RSK: {abs(struct_pct):.2f}% | TACT RSK: {tact_pct:.2f}%", language="text")

# ==============================================================================
# ROUTING LOGIC: LIVE PORTFOLIO MANAGER
# ==============================================================================
elif app_mode == "💼 LIVE PORTFOLIO MANAGER":
    st.markdown("<div class='apex-header'>💼 ACTIVE BOOK & RISK LEDGER</div>", unsafe_allow_html=True)
    db = load_portfolio()
    portfolio_data, total_open_pnl_dollars, total_invested = [], 0.0, 0.0
    
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
                    entry_date, current_px = pd.to_datetime(pos["entry_date"]), float(df['Close'].iloc[-1])
                    shares, entry_px, user_stop = float(pos["shares"]), float(pos["entry_price"]), float(pos["current_stop"])
                    invested, current_value = entry_px * shares, current_px * shares
                    pnl_dollars, pnl_pct = current_value - invested, ((current_value - invested) / invested) * 100
                    days_held = (datetime.now() - entry_date).days
                    total_open_pnl_dollars += pnl_dollars
                    total_invested += invested
                    
                    df_since_entry = df[df.index >= entry_date]
                    highest_high = float(df_since_entry['High'].max()) if not df_since_entry.empty else current_px
                    atr_20, sma_50 = float((df['High'] - df['Low']).rolling(20).mean().iloc[-1]), float(df['Close'].rolling(50).mean().iloc[-1])
                    optimal_stop = highest_high - (2 * atr_20)
                    
                    if current_px < user_stop: action, action_color = "🚨 STOP HIT - LIQUIDATE", "#FF4444"
                    elif pnl_pct > 20.0 and current_px < float(df['Close'].ewm(span=9).mean().iloc[-1]): action, action_color = "✂️ TRIM POSITION", "#FFAA00"
                    elif user_stop < (optimal_stop * 0.99): action, action_color = f"⚠️ RAISE STOP TO ${optimal_stop:.2f}", "#FFAA00"
                    elif current_px < sma_50: action, action_color = "⚠️ STRUCTURAL RISK (< 50 SMA)", "#FF4444"
                    else: action, action_color = "✅ HOLD", "#39FF14"
                        
                    portfolio_data.append({"ID": pos["id"], "Ticker": t, "Entry Date": pos["entry_date"], "Days Held": days_held, "Shares": shares, "Entry Px": entry_px, "Current Px": current_px, "$ PnL": pnl_dollars, "% PnL": pnl_pct, "User Stop": user_stop, "Optimal Stop": optimal_stop, "Action": action, "Action Color": action_color})
                except: pass

    total_realized_pnl = sum([t["pnl_dollars"] for t in db["closed_trades"]])
    total_open_pct = (total_open_pnl_dollars / total_invested * 100) if total_invested > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Open Positions", len(db["open_positions"]))
    m2.metric("Open Unrealized P&L ($)", f"${total_open_pnl_dollars:,.2f}")
    m3.metric("Open Portfolio ROI (%)", f"{total_open_pct:+.2f}%")
    m4.metric("Accumulated Realized P&L ($)", f"${total_realized_pnl:,.2f}")
    
    st.markdown("---")
    st.markdown("<h3 style='color:#FFF;'>Active Engagement Board</h3>", unsafe_allow_html=True)
    
    if not portfolio_data: st.info("No active trades logged.")
    else:
        for p in portfolio_data:
            pnl_color = "#39FF14" if p["% PnL"] > 0 else "#FF4444"
            st.markdown(f"<div style='background: #161b22; border: 1px solid #30363d; border-left: 5px solid {pnl_color}; border-radius: 6px; padding: 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;'><div style='width: 15%;'><div style='font-size: 1.4rem; font-weight: 900; color: #FFF;'>{p['Ticker']}</div><div style='font-size: 0.8rem; color: #8b949e;'>{p['Shares']} shrs @ ${p['Entry Px']:.2f}</div></div><div style='width: 15%; text-align: right;'><div style='font-size: 1.2rem; font-weight: bold; color: {pnl_color};'>{p['% PnL']:+.2f}%</div><div style='font-size: 0.9rem; color: {pnl_color};'>${p['$ PnL']:+.2f}</div></div><div style='width: 25%; text-align: center; border-left: 1px dashed #30363d; border-right: 1px dashed #30363d; padding: 0 15px;'><div style='font-size: 0.8rem; color: #8b949e;'>Logged Stop: <b style='color:#FFF;'>${p['User Stop']:.2f}</b></div><div style='font-size: 0.8rem; color: #8b949e;'>Math Optimal: <b style='color:#58a6ff;'>${p['Optimal Stop']:.2f}</b></div><div style='font-size: 0.8rem; color: #8b949e; margin-top: 5px;'>Days Held: {p['Days Held']}</div></div><div style='width: 35%; text-align: center; font-weight: 800; font-size: 1.1rem; color: {p['Action Color']};'>[ {p['Action']} ]</div></div>", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#FFF; margin-top:40px;'>Control Panel</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown("<h4 style='color:#58a6ff;'>Log New Entry</h4>", unsafe_allow_html=True)
        with st.form("new_trade_form", clear_on_submit=True):
            f_ticker, f_date = st.text_input("Ticker Symbol").upper(), st.date_input("Purchase Date")
            f_px, f_shrs, f_stop = st.number_input("Fill Price ($)", min_value=0.01, format="%.2f"), st.number_input("Shares", min_value=0.01, format="%.4f"), st.number_input("Initial Stop Loss ($)", min_value=0.01, format="%.2f")
            if st.form_submit_button("LOCK POSITION") and f_ticker:
                db["open_positions"].append({"id": str(int(datetime.now().timestamp())), "ticker": f_ticker, "entry_date": f_date.strftime('%Y-%m-%d'), "entry_price": f_px, "shares": f_shrs, "current_stop": f_stop})
                save_portfolio(db); st.success(f"Logged {f_ticker} successfully."); st.rerun()

    with c2:
        st.markdown("<h4 style='color:#FFAA00;'>Update or Close Position</h4>", unsafe_allow_html=True)
        if db["open_positions"]:
            with st.form("manage_trade_form"):
                target_ticker = st.selectbox("Select Active Position", [p["ticker"] for p in db["open_positions"]])
                new_stop_val = st.number_input("Update Stop Price To ($)", min_value=0.0)
                is_close, close_px = st.checkbox("LIQUIDATE POSITION"), st.number_input("Actual Exit Price ($)", min_value=0.0)
                if st.form_submit_button("EXECUTE"):
                    target_idx = next(i for i, p in enumerate(db["open_positions"]) if p["ticker"] == target_ticker)
                    pos = db["open_positions"][target_idx]
                    if is_close and close_px > 0:
                        pnl = (close_px - pos["entry_price"]) * pos["shares"]
                        db["closed_trades"].append({"ticker": pos["ticker"], "entry_date": pos["entry_date"], "close_date": datetime.now().strftime('%Y-%m-%d'), "entry_price": pos["entry_price"], "close_price": close_px, "shares": pos["shares"], "pnl_dollars": pnl})
                        db["open_positions"].pop(target_idx)
                        save_portfolio(db); st.success(f"Position Closed. Realized P&L: ${pnl:.2f}"); st.rerun()
                    elif new_stop_val > 0 and not is_close:
                        db["open_positions"][target_idx]["current_stop"] = new_stop_val
                        save_portfolio(db); st.success(f"Stop updated for {target_ticker}"); st.rerun()

# ==============================================================================
# ROUTING LOGIC: QUANT OPTIMIZER LAB
# ==============================================================================
elif app_mode == "🧪 QUANT OPTIMIZER LAB":
    st.markdown("<div class='apex-header'>🔬 GLOBAL QUANTITATIVE OPTIMIZER (UNIVERSE SWEEP)</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 3])
    with c1: test_period = st.selectbox("Historical Horizon:", ["1y", "2y", "5y", "10y"], index=2)
    with c2: run_opt = st.button("EXECUTE GLOBAL PARAMETER SWEEP", use_container_width=True)

    if run_opt:
        with st.spinner(f"Ingesting {test_period} dataset across all Lieutenants..."):
            res_df = run_global_optimizer(test_period)
            if res_df.empty: st.warning("Zero robust mathematical edges detected.")
            else:
                st.markdown("<h3 style='color: #FFF; margin-top: 20px;'>🗺️ OPTIMAL SYSTEM RANGES (SORTED BY EXPECTANCY)</h3>", unsafe_allow_html=True)
                st.dataframe(res_df.sort_values(by="Expectancy", ascending=False).reset_index(drop=True), width="stretch")
