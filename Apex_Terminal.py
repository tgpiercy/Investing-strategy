# FILE: apex_terminal.py
# ROLE: Master UI Dashboard
# ARCHITECTURE: Streamlit Convergence (Tactical UI V5.20 + RRG Restored + SLY/RSP)
# STATUS: ACTIVE (Uncompressed Master Build)

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import zipfile
import io
from datetime import datetime
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
st.set_page_config(page_title="TITAN APEX", layout="wide", initial_sidebar_state="collapsed")

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

st.markdown("<h1 style='text-align: center; color: #FFF; font-weight: 900; letter-spacing: 3px; margin-bottom: 20px;'>🦅 TITAN APEX COMMAND</h1>", unsafe_allow_html=True)

# ==============================================================================
# DATA ENGINES
# ==============================================================================
@st.cache_data(ttl=300)
def get_risk_engine():
    try:
        data = yf.download(["^VIX", "^VIX3M"], period="1d", progress=False)['Close']
        vix = data['^VIX'].iloc[-1]
        vix3m = data['^VIX3M'].iloc[-1]
        return {"vix": vix, "vix3m": vix3m, "ratio": vix / vix3m, "status": "online"}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=3600)
def get_macro_tide():
    url = f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{datetime.now().year}.zip"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with z.open(z.namelist()[0]) as f:
                df = pd.read_csv(f, low_memory=False)
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
                intensity = (abs(net) / oi) * 100
                results.append({"Asset": ticker, "Net Position": net, "Intensity (%)": intensity})
        return pd.DataFrame(results), latest_date
    except Exception as e: return pd.DataFrame(), str(e)

@st.cache_data(ttl=300)
def get_gamma_walls():
    results = []
    for ticker in ["SPY", "QQQ", "IWM", "NVDA", "AAPL", "TSLA"]:
        try:
            tk = yf.Ticker(ticker)
            px = tk.history(period="1d")['Close'].iloc[-1]
            expirations = tk.options
            if not expirations: continue
            chain = tk.option_chain(expirations[0])
            c_wall = chain.calls.loc[chain.calls['openInterest'].idxmax()]
            p_wall = chain.puts.loc[chain.puts['openInterest'].idxmax()]
            results.append({
                "Ticker": ticker, "Price": px, "Call Wall": c_wall['strike'], 
                "Dist to Call": ((c_wall['strike'] - px) / px) * 100, 
                "Put Wall": p_wall['strike'], "Dist to Put": ((px - p_wall['strike']) / px) * 100
            })
        except: pass
    return results

@st.cache_data(ttl=3600)
def run_credit_stress_engine():
    try:
        df = yf.download(["HYG", "IEF", "SPY"], period="6mo", progress=False)['Close']
        df = df.dropna()
        df['Credit_Ratio'] = df['HYG'] / df['IEF']
        df['Ratio_20SMA'] = df['Credit_Ratio'].rolling(20).mean()
        spy_bullish = df['SPY'].iloc[-1] > df['SPY'].rolling(20).mean().iloc[-1]
        credit_bearish = df['Credit_Ratio'].iloc[-1] < df['Ratio_20SMA'].iloc[-1]
        divergence = spy_bullish and credit_bearish
        return {"status": "online", "divergence": divergence, "ratio": df['Credit_Ratio'].iloc[-1], "sma": df['Ratio_20SMA'].iloc[-1]}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=900)
def get_options_skew(ticker="SPY"):
    try:
        tk = yf.Ticker(ticker)
        px = tk.history(period="1d")['Close'].iloc[-1]
        exps = tk.options
        if not exps: return {"status": "offline"}
        chain = tk.option_chain(exps[min(1, len(exps)-1)])
        calls, puts = chain.calls, chain.puts
        pcr = puts['openInterest'].sum() / calls['openInterest'].sum() if calls['openInterest'].sum() > 0 else 1
        c_strike = calls.iloc[(calls['strike'] - (px * 1.05)).abs().argsort()[:1]]
        p_strike = puts.iloc[(puts['strike'] - (px * 0.95)).abs().argsort()[:1]]
        c_iv = c_strike['impliedVolatility'].values[0] if not c_strike.empty else 0
        p_iv = p_strike['impliedVolatility'].values[0] if not p_strike.empty else 0
        skew = (p_iv - c_iv) * 100 
        return {"status": "online", "pcr": pcr, "put_iv": p_iv, "call_iv": c_iv, "skew": skew}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=86400)
def get_insider_signals():
    results = []
    scan_list = ["NVDA", "AMD", "PLTR", "SMCI", "TSLA", "COIN", "MSTR", "XOM"]
    for ticker in scan_list:
        try:
            tk = yf.Ticker(ticker)
            it = tk.insider_transactions
            if it is not None and not it.empty:
                buys = it[it.iloc[:, 0].astype(str).str.contains("Buy|Purchase", case=False, na=False)]
                if not buys.empty:
                    results.append({"Ticker": ticker, "Status": "Recent Accumulation Detected"})
        except: pass
    if not results: results.append({"Ticker": "SYSTEM", "Status": "No anomalous C-Suite blocks detected today."})
    return pd.DataFrame(results)

@st.cache_data(ttl=900)
def run_kinetic_radar():
    results = []
    for ticker in cfg.LIEUTENANTS:
        try:
            df = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            if df.empty or len(df) < 40: continue
            df = df.dropna()
            
            high = df['High'].rolling(40).max().iloc[-1]
            close = df['Close'].iloc[-1]
            vol = df['Volume'].iloc[-1]
            vol_20 = df['Volume'].rolling(20).mean().iloc[-1]
            
            dist = ((close - high) / high) * 100
            v_spike = vol / vol_20 if vol_20 > 0 else 0
            
            if dist >= cfg.MIN_DONCHIAN_PROX and v_spike >= cfg.MIN_VOLUME_SPIKE: 
                results.append({"Ticker": ticker, "Dist to High (%)": dist, "Vol Spike (x)": v_spike, "Price": close})
        except: pass
    return pd.DataFrame(results)

@st.cache_data(ttl=900)
def run_dark_pool_radar():
    results = []
    for ticker in cfg.LIEUTENANTS:
        try:
            df = yf.download(ticker, period="2mo", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            if df.empty or len(df) < 20: continue
            df = df.dropna()
            
            close = df['Close'].iloc[-1]
            vol = df['Volume'].iloc[-1]
            vol_20 = df['Volume'].rolling(20).mean().iloc[-1]
            
            df['Range'] = df['High'] - df['Low']
            atr_20 = df['Range'].rolling(20).mean().iloc[-1]
            current_range = df['Range'].iloc[-1]
            
            v_spike = vol / vol_20 if vol_20 > 0 else 0
            range_compression = current_range / atr_20 if atr_20 > 0 else 1
            
            if v_spike >= 1.5 and range_compression <= 0.75: 
                results.append({"Ticker": ticker, "Vol Spike (x)": v_spike, "Price Compression": range_compression, "Price": close})
        except: pass
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def run_rotation_engine(sym1="SPY", sym2="DBC"):
    try:
        df = yf.download([sym1, sym2], period="1y", progress=False)['Close']
        df = df.dropna()
        df['Ratio'] = df[sym1] / df[sym2]
        df['Ratio_50SMA'] = df['Ratio'].rolling(50).mean()
        current_ratio = df['Ratio'].iloc[-1]
        current_sma = df['Ratio_50SMA'].iloc[-1]
        is_favored = current_ratio > current_sma
        return {"status": "online", "favored": is_favored, "ratio": current_ratio, "sma": current_sma, "chart": df[['Ratio', 'Ratio_50SMA']].tail(90)}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=900)
def run_master_screener():
    results = []
    tickers = list(dict.fromkeys(cfg.LIEUTENANTS))
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="6mo", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            df = df.dropna()
            if len(df) < 50: continue
            
            c, v = float(df['Close'].iloc[-1]), float(df['Volume'].iloc[-1])
            sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
            ema_9, ema_21 = float(df['Close'].ewm(span=9, adjust=False).mean().iloc[-1]), float(df['Close'].ewm(span=21, adjust=False).mean().iloc[-1])
            vol_sma_9, vol_sma_20, vol_sma_50 = float(df['Volume'].rolling(9).mean().iloc[-1]), float(df['Volume'].rolling(20).mean().iloc[-1]), float(df['Volume'].rolling(50).mean().iloc[-1])
            atr_20 = float((df['High'] - df['Low']).rolling(20).mean().iloc[-1])
            rng = float(df['High'].iloc[-1] - df['Low'].iloc[-1])
            
            trend, mom, liq = c > sma_50, ema_9 > ema_21, vol_sma_9 > vol_sma_50
            dp_vol = (v / vol_sma_20) >= 1.5 if vol_sma_20 > 0 else False
            dp_comp = (rng / atr_20) <= 0.75 if atr_20 > 0 else False
            
            score = sum([trend, mom, liq, dp_vol, dp_comp])
            if score == 5: cat = "🔥 TIER 1: PERFECT SETUP"
            elif dp_vol and dp_comp and not trend: cat = "🦇 STEALTH ACCUMULATION"
            elif mom and liq: cat = "🚀 KINETIC BREAKOUT"
            else: cat = "STANDBY"
            
            if cat != "STANDBY":
                results.append({"Ticker": ticker, "Price": f"${c:.2f}", "Titan Score": f"{score}/5", "Category": cat, "Volume": f"{v/vol_sma_20:.1f}x", "Compression": f"{rng/atr_20:.2f}x"})
        except Exception: pass
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def run_rrg_engine(universe="Macro"):
    try:
        universes = {
            "Macro (Assets)": {"benchmark": "SPY", "tickers": ["QQQ", "IWM", "USO", "GLD", "COPX", "TLT"]},
            "Sectors (S&P 500)": {"benchmark": "SPY", "tickers": ["XLK", "XLF", "XLV", "XLE", "XLY", "XLI", "XLP", "XLU", "XLB", "XLRE"]},
            "Subsectors (Industry)": {"benchmark": "SPY", "tickers": ["XSD", "KRE", "ITB", "XOP", "XRT", "XBI", "JETS", "OIH"]},
            "AI & Tech Infra": {"benchmark": "SPY", "tickers": ["NVDA", "AMD", "AVGO", "SMCI", "ANET", "VRT", "PLTR", "TSM", "ARM"]},
            "Global Indices": {"benchmark": "SPY", "tickers": ["EFA", "EEM", "QQQ", "DIA", "IWM"]}
        }
        benchmark = universes[universe]["benchmark"]
        tickers = universes[universe]["tickers"]
        all_symbols = tickers + [benchmark]
        df = yf.download(all_symbols, period="6mo", progress=False)
        closes, volumes = df['Close'].dropna(), df['Volume'].dropna()
        results = []
        for ticker in tickers:
            if ticker not in closes.columns or benchmark not in closes.columns: continue
            rs = closes[ticker] / closes[benchmark]
            rs_ratio, rs_mom = (rs.rolling(10).mean() / rs.rolling(40).mean()) * 100, ((rs.rolling(10).mean() / rs.rolling(40).mean()) * 100 / (rs.rolling(10).mean() / rs.rolling(40).mean() * 100).rolling(10).mean()) * 100
            vol_ratio = volumes[ticker] / volumes[ticker].rolling(20).mean()
            rs_ratio, rs_mom, vol_ratio = rs_ratio.dropna(), rs_mom.dropna(), vol_ratio.dropna()
            if not rs_ratio.empty and not rs_mom.empty:
                current_vol_spike = vol_ratio.iloc[-1]
                results.append({
                    "Ticker": ticker, "RS_Ratio": rs_ratio.iloc[-1], "RS_Mom": rs_mom.iloc[-1],     
                    "Tail_X": rs_ratio.tail(5).tolist(), "Tail_Y": rs_mom.tail(5).tolist(),
                    "Bubble_Size": max(6, min(current_vol_spike * 8, 25)), "Vol_Spike_Text": f"{current_vol_spike:.2f}x Vol"
                })
        return {"status": "online", "data": results, "benchmark": benchmark}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=300)
def run_tactical_chart(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df = df.dropna()

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
            "Close": df['Close'].iloc[-1], "SMA_50": df['SMA_50'].iloc[-1], "EMA_9": df['EMA_9'].iloc[-1], "EMA_21": df['EMA_21'].iloc[-1],
            "Vol_SMA_9": df['Vol_SMA_9'].iloc[-1], "Vol_SMA_50": df['Vol_SMA_50'].iloc[-1], "Vol_Ratio": df['Vol_Ratio'].iloc[-1], "Range_Comp": df['Range_Comp'].iloc[-1], "ATR_20": df['ATR_20'].iloc[-1]
        }
        return fig, latest_data
    except Exception as e: return None, None

# ==============================================================================
# UI RENDERING: DEFCON SYSTEM
# ==============================================================================
with st.spinner("Calibrating Volatility Engines..."):
    risk = get_risk_engine()
    if risk['status'] == 'online':
        r = risk['ratio']
        if r >= 1.0: color, title, sub, b_bg = "#FF4444", "🚨 DEFCON 1: VOLATILITY INVERTED", "Market Makers pricing immediate crash. HALT LONGS.", "rgba(255, 68, 68, 0.1)"
        elif r >= 0.9: color, title, sub, b_bg = "#FFAA00", "⚠️ DEFCON 3: ELEVATED RISK", "Term Structure flattening. Reduce sizing.", "rgba(255, 170, 0, 0.1)"
        else: color, title, sub, b_bg = "#39FF14", "🟢 DEFCON 5: NORMAL CONTANGO", "Institutional fear low. High probability breakouts.", "rgba(57, 255, 20, 0.05)"
        st.markdown(f"<div class='defcon-banner' style='border-color: {color}; background-color: {b_bg};'><div class='defcon-title' style='color: {color};'>{title}</div><div class='defcon-sub' style='color: #c9d1d9;'>{sub} <span style='color:{color};'>(VIX/VIX3M: {r:.2f})</span></div></div>", unsafe_allow_html=True)

# ==============================================================================
# UI RENDERING: ROW 1 (MACRO & DEALER MATRIX)
# ==============================================================================
col1, col2 = st.columns([1, 1], gap="large")
with col1:
    st.markdown("<div class='apex-header'>🌊 MACRO TIDE (SMART MONEY)</div>", unsafe_allow_html=True)
    macro_df, date = get_macro_tide()
    if not macro_df.empty:
        for _, row in macro_df.iterrows():
            i, l = row['Intensity (%)'], row['Net Position'] > 0
            if l and i >= 10: cc, tc, m, mc = "card-bullish", "#39FF14", "PRIORITIZE LONGS", "mandate-buy"
            elif not l and i >= 20: cc, tc, m, mc = "card-bearish", "#FF4444", "AVOID LONGS / SEEK SHORTS", "mandate-sell"
            else: cc, tc, m, mc = "card-neutral", "#8b949e", "NEUTRAL TIDE", "mandate-warn"
            st.markdown(f"<div class='tactical-card {cc}'><div><div class='asset-title'>{row['Asset']}</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>BIAS:</span><span style='color:{tc}; font-weight:bold;'>{'NET LONG' if l else 'NET SHORT'} ({i:.1f}%)</span></div></div></div><div class='mandate-box {mc}'>[ {m} ]</div></div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='apex-header'>☢️ DEALER MATRIX (GAMMA WALLS)</div>", unsafe_allow_html=True)
    for g in get_gamma_walls():
        c_dist, p_dist = g['Dist to Call'], g['Dist to Put']
        if c_dist < 0: cc, mc, m, ct = "card-squeeze", "mandate-buy", "SHORT GAMMA - MAX LONGS", f"<span style='color:#39FF14;'>⚠️ BREACHED</span>"
        elif p_dist > 0: cc, mc, m, ct = "card-bearish", "mandate-sell", "LONG GAMMA - RESISTANCE", f"{c_dist:+.2f}%"
        else: cc, mc, m, ct = "card-neutral", "mandate-warn", "TRAPPED IN CHOP", f"{c_dist:+.2f}%"
        pt = f"<span style='color:#FF4444;'>⚠️ BREACHED</span>" if p_dist > 0 else f"{p_dist:+.2f}%"
        st.markdown(f"<div class='tactical-card {cc}'><div><div style='display:flex; justify-content:space-between;'><div class='asset-title'>{g['Ticker']}</div><div class='price-text'>${g['Price']:.2f}</div></div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>CALL WALL: <b style='color:#FFF;'>${g['Call Wall']:.2f}</b></span><span>[{ct}]</span></div><div class='data-row'><span>PUT FLOOR: <b style='color:#FFF;'>${g['Put Wall']:.2f}</b></span><span>[{pt}]</span></div></div></div><div class='mandate-box {mc}'>[ {m} ]</div></div>", unsafe_allow_html=True)

# ==============================================================================
# UI RENDERING: ROW 2 (CREDIT & SKEW)
# ==============================================================================
st.markdown("<div class='apex-header' style='margin-top: 40px;'>🏦 INSTITUTIONAL CREDIT & VOLATILITY</div>", unsafe_allow_html=True)
c_col1, c_col2 = st.columns([1, 1], gap="large")
with c_col1:
    credit = run_credit_stress_engine()
    if credit['status'] == 'online':
        cc, tc, cm = ("card-bearish", "#FF4444", "RISK-OFF DIVERGENCE") if credit['divergence'] else ("card-bullish", "#39FF14", "CREDIT ALIGNED (RISK-ON)")
        st.markdown(f"<div class='tactical-card {cc}'><div><div class='asset-title'>CREDIT STRESS RADAR</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>HYG/IEF RATIO:</span><span style='color:#FFF; font-weight:bold;'>{credit['ratio']:.3f}</span></div><div class='data-row'><span>TREND:</span><span style='color:{tc}; font-weight:bold;'>{'DIVERGING' if credit['divergence'] else 'SUPPORTIVE'}</span></div></div></div><div class='mandate-box {'mandate-sell' if credit['divergence'] else 'mandate-buy'}'>[ {cm} ]</div></div>", unsafe_allow_html=True)
with c_col2:
    skew = get_options_skew()
    if skew['status'] == 'online':
        is_fear = skew['skew'] > 5.0 or skew['pcr'] > 1.5
        sc, tc, sm = ("card-bearish", "#FF4444", "INSTITUTIONS HEDGING (FEAR)") if is_fear else ("card-bullish", "#39FF14", "VOL SKEW NORMAL")
        st.markdown(f"<div class='tactical-card {sc}'><div><div class='asset-title'>OPTIONS FLOW (SPY)</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>PUT/CALL RATIO:</span><span style='color:#FFF; font-weight:bold;'>{skew['pcr']:.2f}</span></div><div class='data-row'><span>SKEW (PUT IV - CALL IV):</span><span style='color:{tc}; font-weight:bold;'>{skew['skew']:+.2f}%</span></div></div></div><div class='mandate-box {'mandate-sell' if is_fear else 'mandate-buy'}'>[ {sm} ]</div></div>", unsafe_allow_html=True)

# ==============================================================================
# UI RENDERING: ROW 3 (RADARS & DARK POOLS/INSIDERS) - RESTORED
# ==============================================================================
r_col1, r_col2 = st.columns([1, 1], gap="large")
with r_col1:
    st.markdown("<div class='apex-header' style='margin-top: 20px;'>⚡ KINETIC RADAR (LIVE BREAKOUTS)</div>", unsafe_allow_html=True)
    with st.spinner("Scanning Lieutenants for volume ignition..."):
        radar_df = run_kinetic_radar()
        if not radar_df.empty: 
            st.dataframe(radar_df.sort_values(by="Vol Spike (x)", ascending=False).style.format({"Dist to High (%)": "{:+.2f}%", "Vol Spike (x)": "{:.2f}x", "Price": "${:.2f}"}), width="stretch", height=200)
        else: 
            st.info("No Lieutenants meeting kinetic volume thresholds today.")

with r_col2:
    st.markdown("<div class='apex-header' style='margin-top: 20px;'>🦇 DARK POOLS & INSIDER BLOCKS</div>", unsafe_allow_html=True)
    tabs = st.tabs(["Dark Pool Compression", "C-Suite Insider Matrix"])
    with tabs[0]:
        with st.spinner("Scanning Institutional Anomalies..."):
            dp_df = run_dark_pool_radar()
            if not dp_df.empty: 
                st.dataframe(dp_df.sort_values(by="Vol Spike (x)", ascending=False).style.format({"Vol Spike (x)": "{:.2f}x", "Price Compression": "{:.2f}x", "Price": "${:.2f}"}), width="stretch", height=200)
            else: 
                st.info("No Dark Pool signatures detected today.")
    with tabs[1]:
        with st.spinner("Scraping SEC Form 4 Proxies..."):
            insider_df = get_insider_signals()
            st.dataframe(insider_df, width="stretch", height=200)

# ==============================================================================
# UI RENDERING: ROW 4 (MACRO ROTATION & RRG) - RESTORED & UPGRADED WITH SLY/RSP
# ==============================================================================
st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔄 MACRO ROTATION & RRG (EQUITIES vs COMMODITIES vs BREADTH)</div>", unsafe_allow_html=True)
rot_col1, rot_col2 = st.columns([1, 1], gap="large")

with rot_col1:
    rot_tabs = st.tabs(["Macro Flow (SPY / DBC)", "Risk Breadth (SLY / RSP)"])
    
    with rot_tabs[0]:
        with st.spinner("Calculating Intermarket See-Saw..."):
            spy_dbc = run_rotation_engine("SPY", "DBC")
            if spy_dbc['status'] == 'online':
                eq_favored = spy_dbc['favored']
                box_color, box_bg = ("#39FF14", "rgba(57, 255, 20, 0.05)") if eq_favored else ("#FFAA00", "rgba(255, 170, 0, 0.05)")
                status_text = "EQUITIES DOMINATING" if eq_favored else "COMMODITIES DOMINATING"
                st.markdown(f"<div style='border: 2px solid {box_color}; background-color: {box_bg}; border-radius: 8px; padding: 20px; margin-bottom: 20px;'><h3 style='color: {box_color}; margin-top: 0;'>SYSTEM READOUT: {status_text}</h3></div>", unsafe_allow_html=True)
                st.line_chart(spy_dbc['chart'], color=["#58a6ff", "#8b949e"], width="stretch")

    with rot_tabs[1]:
        with st.spinner("Calculating Equal Weight Breadth..."):
            sly_rsp = run_rotation_engine("SLY", "RSP")
            if sly_rsp['status'] == 'online':
                sly_favored = sly_rsp['favored']
                box_color, box_bg = ("#39FF14", "rgba(57, 255, 20, 0.05)") if sly_favored else ("#8b949e", "rgba(139, 148, 158, 0.05)")
                status_text = "SMALL CAPS LEADING (RISK-ON BREADTH)" if sly_favored else "LARGE CAPS DEFENSIVE (NARROW MARKET)"
                st.markdown(f"<div style='border: 2px solid {box_color}; background-color: {box_bg}; border-radius: 8px; padding: 20px; margin-bottom: 20px;'><h3 style='color: {box_color}; margin-top: 0;'>SYSTEM READOUT: {status_text}</h3></div>", unsafe_allow_html=True)
                st.line_chart(sly_rsp['chart'], color=["#58a6ff", "#8b949e"], width="stretch")

with rot_col2:
    selected_universe = st.radio("Select RRG Universe:", ["Sectors (S&P 500)", "Subsectors (Industry)", "AI & Tech Infra", "Macro (Assets)", "Global Indices"], horizontal=True, label_visibility="collapsed")
    with st.spinner(f"Mapping {selected_universe}..."):
        rrg_engine = run_rrg_engine(selected_universe)
        if rrg_engine['status'] == 'online':
            fig = go.Figure()
            fig.add_hline(y=100, line_dash="dash", line_color="#30363d", layer="below")
            fig.add_vline(x=100, line_dash="dash", line_color="#30363d", layer="below")
            fig.add_annotation(x=101, y=101, text="LEADING", showarrow=False, font=dict(color="#39FF14", size=14), opacity=0.3)
            fig.add_annotation(x=101, y=99, text="WEAKENING", showarrow=False, font=dict(color="#FFAA00", size=14), opacity=0.3)
            fig.add_annotation(x=99, y=99, text="LAGGING", showarrow=False, font=dict(color="#FF4444", size=14), opacity=0.3)
            fig.add_annotation(x=99, y=101, text="IMPROVING", showarrow=False, font=dict(color="#58a6ff", size=14), opacity=0.3)

            for item in rrg_engine['data']:
                if item["RS_Ratio"] > 100 and item["RS_Mom"] > 100: color = "#39FF14"
                elif item["RS_Ratio"] > 100 and item["RS_Mom"] < 100: color = "#FFAA00"
                elif item["RS_Ratio"] < 100 and item["RS_Mom"] < 100: color = "#FF4444"
                else: color = "#58a6ff"
                
                fig.add_trace(go.Scatter(
                    x=item["Tail_X"], y=item["Tail_Y"], mode='lines+markers+text', name=item["Ticker"],
                    text=[None, None, None, None, item["Ticker"]], textposition="top center", hovertext=f"Vol: {item['Vol_Spike_Text']}",
                    marker=dict(size=[4, 4, 4, 4, item["Bubble_Size"]], color=color, line=dict(width=1, color="#FFF") if item["Bubble_Size"] > 10 else dict(width=0)),
                    line=dict(width=2, color=color)
                ))
            
            fig.update_layout(plot_bgcolor='#0d1117', paper_bgcolor='#0d1117', font=dict(color='#c9d1d9'), xaxis=dict(title='Relative Strength vs Benchmark', gridcolor='#30363d', zeroline=False), yaxis=dict(title='Momentum', gridcolor='#30363d', zeroline=False), margin=dict(l=20, r=20, t=20, b=20), showlegend=False, height=400)
            st.plotly_chart(fig, width="stretch")

# ==============================================================================
# UI RENDERING: ROW 5 (THE GLOBAL SCREENER)
# ==============================================================================
st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔍 TITAN MASTER SCREENER (ALL LIEUTENANTS)</div>", unsafe_allow_html=True)
st.markdown("<p style='color: #8b949e; font-size: 0.9rem;'>Vectorized scan of the entire configuration universe for algorithmic setup confirmation.</p>", unsafe_allow_html=True)

if st.button("EXECUTE GLOBAL SCAN"):
    with st.spinner("Compiling cross-asset vector data (Bypassing bulk-API limits)..."):
        screen_df = run_master_screener()
        if not screen_df.empty:
            st.dataframe(screen_df.sort_values(by="Titan Score", ascending=False), width="stretch", hide_index=True)
        else:
            st.info("No actionable Tier 1 or Stealth setups detected across the universe today.")

# ==============================================================================
# UI RENDERING: ROW 6 (TACTICAL RECON & DECODER)
# ==============================================================================
st.markdown("<div class='apex-header' style='margin-top: 40px;'>🎯 TACTICAL RECON & DECODER</div>", unsafe_allow_html=True)
recon_col1, recon_col2 = st.columns([1, 4], gap="medium")
with recon_col1:
    target_category = st.selectbox("Category Lens:", ["Lieutenants (Watchlist)", "Indices", "Sectors (Macro)", "Subsectors (Micro)", "Thematic (AI/Crypto)"])
    if target_category == "Indices": active_list = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM"]
    elif target_category == "Sectors (Macro)": active_list = ["XLK", "XLF", "XLV", "XLE", "XLY", "XLI", "XLP", "XLU", "XLB", "XLRE"]
    elif target_category == "Subsectors (Micro)": active_list = ["XSD", "KRE", "ITB", "XOP", "XRT", "XBI", "JETS", "OIH"]
    elif target_category == "Thematic (AI/Crypto)": active_list = ["NVDA", "AMD", "SMCI", "ANET", "VRT", "PLTR", "TSM", "MSTR", "COIN", "MARA"]
    else: active_list = list(dict.fromkeys(cfg.LIEUTENANTS))
    target_chart = st.selectbox("Select Target:", active_list)

with recon_col2:
    with st.spinner(f"Loading {target_chart}..."):
        chart_fig, last_data = run_tactical_chart(target_chart)
        if chart_fig: st.plotly_chart(chart_fig, width="stretch")

if last_data:
    c = last_data['Close']
    trend_bull = c > last_data['SMA_50']
    mom_bull = last_data['EMA_9'] > last_data['EMA_21']
    liq_bull = last_data['Vol_SMA_9'] > last_data['Vol_SMA_50']
    dp_active = (last_data['Vol_Ratio'] >= 1.5) and (last_data['Range_Comp'] <= 0.75)
    
    struct_dist = c - last_data['SMA_50']
    struct_pct = (struct_dist / c) * 100
    tact_dist = 2 * last_data['ATR_20']
    tact_pct = (tact_dist / c) * 100
    tact_stop_price = c - tact_dist

    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    d_col1.markdown(f"<div class='tactical-card {'card-bullish' if trend_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>TREND (>50 SMA)</div><div class='price-text' style='color: {'#39FF14' if trend_bull else '#FF4444'};'>{'BULLISH' if trend_bull else 'BEARISH'}</div></div></div>", unsafe_allow_html=True)
    d_col2.markdown(f"<div class='tactical-card {'card-bullish' if mom_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>MOMENTUM (9>21)</div><div class='price-text' style='color: {'#39FF14' if mom_bull else '#FF4444'};'>{'IGNITED' if mom_bull else 'LAGGING'}</div></div></div>", unsafe_allow_html=True)
    d_col3.markdown(f"<div class='tactical-card {'card-bullish' if liq_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>LIQUIDITY (9>50 VOL)</div><div class='price-text' style='color: {'#39FF14' if liq_bull else '#FF4444'};'>{'EXPANDING' if liq_bull else 'CONTRACTING'}</div></div></div>", unsafe_allow_html=True)
    d_col4.markdown(f"<div class='tactical-card {'card-squeeze' if dp_active else 'card-neutral'}' style='min-height: 100px;'><div><div class='metric-sub'>DARK POOL BLOCK</div><div class='price-text' style='color: {'#FFAA00' if dp_active else '#8b949e'};'>{'DETECTED' if dp_active else 'CLEAR'}</div></div></div>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin-top: 20px;'>
        <b style='color: #58a6ff;'>RISK DRAWDOWN MATRIX</b><br><br>
        <div style='display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(139, 148, 158, 0.2); padding-bottom: 10px; margin-bottom: 10px;'>
            <span style='color: #8b949e;'>Structural Risk (To 50 SMA):</span>
            <span style='color: #FFF; font-weight: bold;'>Stop: ${last_data['SMA_50']:.2f} | Risk: -${abs(struct_dist):.2f} / Share ({abs(struct_pct):.2f}%)</span>
        </div>
        <div style='display: flex; justify-content: space-between;'>
            <span style='color: #8b949e;'>Tactical Risk (2x ATR Trailing):</span>
            <span style='color: #FFF; font-weight: bold;'>Stop: ${tact_stop_price:.2f} | Risk: -${tact_dist:.2f} / Share ({tact_pct:.2f}%)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    journal_str = f"[{datetime.now().strftime('%Y-%m-%d')}] TARGET: {target_chart} @ ${c:.2f} | T: {'BULL' if trend_bull else 'BEAR'} | M: {'IGNITED' if mom_bull else 'LAGGING'} | L: {'EXPANDING' if liq_bull else 'CONTRACTING'} | DP: {'YES' if dp_active else 'NO'} | STRUC RSK: {abs(struct_pct):.2f}% | TACT RSK: {tact_pct:.2f}%"
    st.markdown("<p style='color: #8b949e; font-size: 0.9rem; margin-top: 20px;'>Auto-Journal Entry (Click to Copy):</p>", unsafe_allow_html=True)
    st.code(journal_str, language="text")
