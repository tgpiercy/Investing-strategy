# FILE: apex_terminal.py
# ROLE: Master UI Dashboard
# ARCHITECTURE: Streamlit Convergence (Tactical UI V5.16 + Stabilized Screener)
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
def run_master_screener():
    results = []
    tickers = list(dict.fromkeys(cfg.LIEUTENANTS))
    try:
        # Standardized download (no group_by) to prevent Streamlit cache multi-index failures
        data = yf.download(tickers, period="6mo", progress=False)
        for ticker in tickers:
            try:
                # Isolate the data per ticker safely
                if len(tickers) == 1:
                    df = data.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(1)
                else:
                    df = pd.DataFrame({
                        'Close': data['Close'][ticker],
                        'High': data['High'][ticker],
                        'Low': data['Low'][ticker],
                        'Volume': data['Volume'][ticker]
                    })
                
                df = df.dropna()
                if len(df) < 50: continue
                
                # Force standard Python float typing to ensure Streamlit cache compatibility
                c = float(df['Close'].iloc[-1])
                v = float(df['Volume'].iloc[-1])
                
                sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
                ema_9 = float(df['Close'].ewm(span=9, adjust=False).mean().iloc[-1])
                ema_21 = float(df['Close'].ewm(span=21, adjust=False).mean().iloc[-1])
                
                vol_sma_9 = float(df['Volume'].rolling(9).mean().iloc[-1])
                vol_sma_20 = float(df['Volume'].rolling(20).mean().iloc[-1])
                vol_sma_50 = float(df['Volume'].rolling(50).mean().iloc[-1])
                
                atr_20 = float((df['High'] - df['Low']).rolling(20).mean().iloc[-1])
                rng = float(df['High'].iloc[-1] - df['Low'].iloc[-1])
                
                # Logic Gates
                trend = c > sma_50
                mom = ema_9 > ema_21
                liq = vol_sma_9 > vol_sma_50
                dp_vol = (v / vol_sma_20) >= 1.5 if vol_sma_20 > 0 else False
                dp_comp = (rng / atr_20) <= 0.75 if atr_20 > 0 else False
                
                # Scoring
                score = sum([trend, mom, liq, dp_vol, dp_comp])
                
                # Categorization
                if score == 5: cat = "🔥 TIER 1: PERFECT SETUP"
                elif dp_vol and dp_comp and not trend: cat = "🦇 STEALTH ACCUMULATION"
                elif mom and liq: cat = "🚀 KINETIC BREAKOUT"
                else: cat = "STANDBY"
                
                if cat != "STANDBY":
                    results.append({
                        "Ticker": ticker, 
                        "Price": f"${c:.2f}", 
                        "Titan Score": f"{score}/5",
                        "Category": cat, 
                        "Volume": f"{v/vol_sma_20:.1f}x", 
                        "Compression": f"{rng/atr_20:.2f}x"
                    })
            except Exception as e: pass
    except Exception as e: pass
    
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def run_rotation_engine():
    try:
        df = yf.download(["SPY", "DBC"], period="1y", progress=False)['Close']
        df = df.dropna()
        df['Ratio'] = df['SPY'] / df['DBC']
        df['Ratio_50SMA'] = df['Ratio'].rolling(50).mean()
        current_ratio = df['Ratio'].iloc[-1]
        current_sma = df['Ratio_50SMA'].iloc[-1]
        is_equity_favored = current_ratio > current_sma
        return {"status": "online", "equity_favored": is_equity_favored, "ratio": current_ratio, "sma": current_sma, "chart": df[['Ratio', 'Ratio_50SMA']].tail(90)}
    except Exception as e: return {"status": "offline", "error": str(e)}

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
        closes = df['Close'].dropna()
        volumes = df['Volume'].dropna()
        results = []
        for ticker in tickers:
            if ticker not in closes.columns or benchmark not in closes.columns: continue
            rs = closes[ticker] / closes[benchmark]
            rs_ratio = (rs.rolling(10).mean() / rs.rolling(40).mean()) * 100
            rs_mom = (rs_ratio / rs_ratio.rolling(10).mean()) * 100
            vol_20sma = volumes[ticker].rolling(20).mean()
            vol_ratio = volumes[ticker] / vol_20sma
            rs_ratio = rs_ratio.dropna()
            rs_mom = rs_mom.dropna()
            vol_ratio = vol_ratio.dropna()
            if not rs_ratio.empty and not rs_mom.empty:
                current_vol_spike = vol_ratio.iloc[-1]
                dynamic_size = max(6, min(current_vol_spike * 8, 25))
                results.append({
                    "Ticker": ticker, "RS_Ratio": rs_ratio.iloc[-1], "RS_Mom": rs_mom.iloc[-1],     
                    "Tail_X": rs_ratio.tail(5).tolist(), "Tail_Y": rs_mom.tail(5).tolist(),
                    "Bubble_Size": dynamic_size, "Vol_Spike_Text": f"{current_vol_spike:.2f}x Vol"
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
        df['Vol_SMA_9'] = df['Volume'].rolling(window=9).mean()
        df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
        df['Vol_SMA_50'] = df['Volume'].rolling(window=50).mean()

        df['Range'] = df['High'] - df['Low']
        df['ATR_20'] = df['Range'].rolling(window=20).mean()
        
        df['Vol_Ratio'] = np.where(df['Vol_SMA_20'] > 0, df['Volume'] / df['Vol_SMA_20'], 0)
        df['Range_Comp'] = np.where(df['ATR_20'] > 0, df['Range'] / df['ATR_20'], 1)
        
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
                name='Dark Pool Block',
                hovertext=[f"Vol Spike: {r:.2f}x<br>Compression: {c:.2f}x" for r, c in zip(dp_signals['Vol_Ratio'], dp_signals['Range_Comp'])],
                hoverinfo="text+x+y"
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
# UI RENDERING: MACRO & DEALER MATRIX
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
        cd, pd = g['Dist to Call'], g['Dist to Put']
        if cd < 0: cc, mc, m, ct = "card-squeeze", "mandate-buy", "SHORT GAMMA - MAX LONGS", f"<span style='color:#39FF14;'>⚠️ BREACHED</span>"
        elif pd > 0: cc, mc, m, ct = "card-bearish", "mandate-sell", "LONG GAMMA - RESISTANCE", f"{cd:+.2f}%"
        else: cc, mc, m, ct = "card-neutral", "mandate-warn", "TRAPPED IN CHOP", f"{cd:+.2f}%"
        pt = f"<span style='color:#FF4444;'>⚠️ BREACHED</span>" if pd > 0 else f"{pd:+.2f}%"
        st.markdown(f"<div class='tactical-card {cc}'><div><div style='display:flex; justify-content:space-between;'><div class='asset-title'>{g['Ticker']}</div><div class='price-text'>${g['Price']:.2f}</div></div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>CALL WALL: <b style='color:#FFF;'>${g['Call Wall']:.2f}</b></span><span>[{ct}]</span></div><div class='data-row'><span>PUT FLOOR: <b style='color:#FFF;'>${g['Put Wall']:.2f}</b></span><span>[{pt}]</span></div></div></div><div class='mandate-box {mc}'>[ {m} ]</div></div>", unsafe_allow_html=True)

# ==============================================================================
# UI RENDERING: CREDIT & SKEW
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
# UI RENDERING: ROW 5 (THE GLOBAL SCREENER)
# ==============================================================================
st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔍 TITAN MASTER SCREENER (ALL LIEUTENANTS)</div>", unsafe_allow_html=True)
st.markdown("<p style='color: #8b949e; font-size: 0.9rem;'>Vectorized scan of the entire configuration universe for algorithmic setup confirmation.</p>", unsafe_allow_html=True)

if st.button("EXECUTE GLOBAL SCAN"):
    with st.spinner("Compiling cross-asset vector data..."):
        screen_df = run_master_screener()
        if not screen_df.empty:
            st.dataframe(screen_df.sort_values(by="Titan Score", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No actionable Tier 1 or Stealth setups detected across the universe today.")

# ==============================================================================
# UI RENDERING: RECON & DECODER
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
        if chart_fig: st.plotly_chart(chart_fig, use_container_width=True)

if last_data:
    c = last_data['Close']
    trend_bull, mom_bull, liq_bull = c > last_data['SMA_50'], last_data['EMA_9'] > last_data['EMA_21'], last_data['Vol_SMA_9'] > last_data['Vol_SMA_50']
    dp_active = (last_data['Vol_Ratio'] >= 1.5) and (last_data['Range_Comp'] <= 0.75)
    struct_pct, tact_pct = ((c - last_data['SMA_50']) / c) * 100, ((2 * last_data['ATR_20']) / c) * 100

    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    d_col1.markdown(f"<div class='tactical-card {'card-bullish' if trend_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>TREND (>50 SMA)</div><div class='price-text' style='color: {'#39FF14' if trend_bull else '#FF4444'};'>{'BULLISH' if trend_bull else 'BEARISH'}</div></div></div>", unsafe_allow_html=True)
    d_col2.markdown(f"<div class='tactical-card {'card-bullish' if mom_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>MOMENTUM (9>21)</div><div class='price-text' style='color: {'#39FF14' if mom_bull else '#FF4444'};'>{'IGNITED' if mom_bull else 'LAGGING'}</div></div></div>", unsafe_allow_html=True)
    d_col3.markdown(f"<div class='tactical-card {'card-bullish' if liq_bull else 'card-bearish'}' style='min-height: 100px;'><div><div class='metric-sub'>LIQUIDITY (9>50 VOL)</div><div class='price-text' style='color: {'#39FF14' if liq_bull else '#FF4444'};'>{'EXPANDING' if liq_bull else 'CONTRACTING'}</div></div></div>", unsafe_allow_html=True)
    d_col4.markdown(f"<div class='tactical-card {'card-squeeze' if dp_active else 'card-neutral'}' style='min-height: 100px;'><div><div class='metric-sub'>DARK POOL BLOCK</div><div class='price-text' style='color: {'#FFAA00' if dp_active else '#8b949e'};'>{'DETECTED' if dp_active else 'CLEAR'}</div></div></div>", unsafe_allow_html=True)
    
    st.code(f"[{datetime.now().strftime('%Y-%m-%d')}] {target_chart} @ ${c:.2f} | T: {'BULL' if trend_bull else 'BEAR'} | M: {'IGNITED' if mom_bull else 'LAGGING'} | L: {'EXPANDING' if liq_bull else 'CONTRACTING'} | DP: {'YES' if dp_active else 'NO'} | STRUC RSK: {abs(struct_pct):.2f}% | TACT RSK: {tact_pct:.2f}%", language="text")
