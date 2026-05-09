# FILE: apex_terminal.py
# ROLE: Master UI Dashboard
# ARCHITECTURE: Streamlit Convergence (Tactical UI V5.40 + Kinetic Gamma Flow)
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
app_mode = st.sidebar.radio("Select Module:", ["🚀 LIVE COMMAND CENTER", "🧪 BACKTESTER LAB"])
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 0.8rem; color: #8b949e; text-align: center;'>TITAN OMEGA V5.40<br>System Online.</p>", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFF; font-weight: 900; letter-spacing: 3px; margin-bottom: 20px;'>🦅 TITAN APEX COMMAND</h1>", unsafe_allow_html=True)

# ==============================================================================
# DATA ENGINES (HYBRID API PROTOCOL)
# ==============================================================================
@st.cache_data(ttl=300)
def get_risk_engine():
    try:
        data = yf.download(["^VIX", "^VIX3M"], period="5d", progress=False)['Close']
        data = data.dropna()
        if data.empty: return {"status": "offline", "error": "API returned empty dataset"}
        vix = float(data['^VIX'].iloc[-1])
        vix3m = float(data['^VIX3M'].iloc[-1])
        return {"vix": vix, "vix3m": vix3m, "ratio": vix / vix3m, "status": "online"}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=86400)
def get_fomc_data():
    try:
        if not hasattr(cfg, 'FRED_API_KEY') or cfg.FRED_API_KEY == "PASTE_YOUR_32_CHARACTER_KEY_HERE" or cfg.FRED_API_KEY == "":
            return {"status": "offline", "error": "Missing FRED_API_KEY in apex_config.py"}

        api_key = cfg.FRED_API_KEY
        
        yc_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=T10Y2Y&api_key={api_key}&file_type=json"
        res_yc = requests.get(yc_url, timeout=10)
        if res_yc.status_code != 200: return {"status": "offline", "error": f"FRED API Rejected T10Y2Y: {res_yc.status_code}"}
        
        df_yc = pd.DataFrame(res_yc.json()['observations'])
        df_yc['date'] = pd.to_datetime(df_yc['date'])
        df_yc['value'] = pd.to_numeric(df_yc['value'], errors='coerce')
        df_yc = df_yc[['date', 'value']].rename(columns={'value': 'Yield_Curve'}).set_index('date')

        ff_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key={api_key}&file_type=json"
        res_ff = requests.get(ff_url, timeout=10)
        if res_ff.status_code != 200: return {"status": "offline", "error": f"FRED API Rejected DFF: {res_ff.status_code}"}
        
        df_ff = pd.DataFrame(res_ff.json()['observations'])
        df_ff['date'] = pd.to_datetime(df_ff['date'])
        df_ff['value'] = pd.to_numeric(df_ff['value'], errors='coerce')
        df_ff = df_ff[['date', 'value']].rename(columns={'value': 'Fed_Funds'}).set_index('date')

        df = df_yc.join(df_ff, how='inner').dropna()
        df = df[df.index > (datetime.now() - pd.DateOffset(years=5))]
        
        if df.empty: return {"status": "offline", "error": "FRED API Returned Empty Dataset"}
        
        status = "INVERTED (RECESSION WARNING)" if df['Yield_Curve'].iloc[-1] < 0 else "NORMAL (CONTANGO)"
        return {"status": "online", "data": df, "curve_status": status, "current_yc": float(df['Yield_Curve'].iloc[-1]), "current_ff": float(df['Fed_Funds'].iloc[-1])}
        
    except Exception as e:
        return {"status": "offline", "error": f"API Architecture Failure: {str(e)}"}

@st.cache_data(ttl=3600)
def get_cross_asset_matrix():
    tickers = ["SPY", "QQQ", "TLT", "GLD", "USO", "UUP", "BTC-USD"]
    try:
        df = yf.download(tickers, period="3mo", progress=False)['Close']
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
        df = df.dropna(how='all')
        
        returns = df.pct_change().dropna()
        if returns.empty: return {"status": "offline", "error": "Insufficient data for correlation matrix"}
        
        corr_matrix = returns.corr().round(2)
        valid_tickers = [t for t in tickers if t in corr_matrix.columns]
        corr_matrix = corr_matrix.reindex(index=valid_tickers, columns=valid_tickers)
        
        return {"status": "online", "data": corr_matrix}
    except Exception as e:
        return {"status": "offline", "error": str(e)}

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
    """V5.40 KINETIC GAMMA ENGINE: Scans Volume vs OI and localized PCR"""
    results = []
    target_tickers = ["SPY", "QQQ", "IWM", "NVDA", "AAPL", "TSLA", "SMH", "XLE"]
    for ticker in target_tickers:
        try:
            df = yf.download(ticker, period="5d", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            df = df.dropna()
            if df.empty: continue
            px = float(df['Close'].iloc[-1])
            
            tk = yf.Ticker(ticker)
            expirations = tk.options
            if not expirations: continue
            chain = tk.option_chain(expirations[0])
            
            calls = chain.calls
            puts = chain.puts
            if calls.empty or puts.empty: continue
            
            # Ticker-Specific PCR
            total_call_oi = calls['openInterest'].sum()
            total_put_oi = puts['openInterest'].sum()
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

            calls_sorted = calls.sort_values(by='openInterest', ascending=False)
            puts_sorted = puts.sort_values(by='openInterest', ascending=False)
                
            c_wall_1 = calls_sorted.iloc[0]['strike']
            c_wall_1_oi = calls_sorted.iloc[0]['openInterest']
            c_wall_1_vol = calls_sorted.iloc[0]['volume']
            c1_active = c_wall_1_vol > c_wall_1_oi
            
            c_wall_2 = calls_sorted.iloc[1]['strike'] if len(calls_sorted) > 1 else c_wall_1
            c_wall_2_oi = calls_sorted.iloc[1]['openInterest'] if len(calls_sorted) > 1 else c_wall_1_oi
            c_wall_2_vol = calls_sorted.iloc[1]['volume'] if len(calls_sorted) > 1 else c_wall_1_vol
            c2_active = c_wall_2_vol > c_wall_2_oi
            
            p_wall_1 = puts_sorted.iloc[0]['strike']
            p_wall_1_oi = puts_sorted.iloc[0]['openInterest']
            p_wall_1_vol = puts_sorted.iloc[0]['volume']
            p1_active = p_wall_1_vol > p_wall_1_oi
            
            p_wall_2 = puts_sorted.iloc[1]['strike'] if len(puts_sorted) > 1 else p_wall_1
            p_wall_2_oi = puts_sorted.iloc[1]['openInterest'] if len(puts_sorted) > 1 else p_wall_1_oi
            p_wall_2_vol = puts_sorted.iloc[1]['volume'] if len(puts_sorted) > 1 else p_wall_1_vol
            p2_active = p_wall_2_vol > p_wall_2_oi
            
            merged = pd.merge(calls[['strike', 'openInterest']], puts[['strike', 'openInterest']], on='strike', how='outer').fillna(0)
            merged['total_oi'] = merged['openInterest_x'] + merged['openInterest_y']
            zero_gamma = float(merged.sort_values(by='total_oi', ascending=False).iloc[0]['strike'])

            if c_wall_1 > c_wall_2: 
                c_wall_1, c_wall_2 = c_wall_2, c_wall_1
                c_wall_1_oi, c_wall_2_oi = c_wall_2_oi, c_wall_1_oi
                c1_active, c2_active = c2_active, c1_active
            if p_wall_1 < p_wall_2: 
                p_wall_1, p_wall_2 = p_wall_2, p_wall_1
                p_wall_1_oi, p_wall_2_oi = p_wall_2_oi, p_wall_1_oi
                p1_active, p2_active = p2_active, p1_active

            results.append({
                "Ticker": ticker, "Price": px, "Zero Gamma": zero_gamma, "PCR": pcr,
                "Call Wall 1": c_wall_1, "Dist CW1": ((c_wall_1 - px) / px) * 100, "CW1_OI": c_wall_1_oi, "CW1_Active": c1_active,
                "Call Wall 2": c_wall_2, "Dist CW2": ((c_wall_2 - px) / px) * 100, "CW2_OI": c_wall_2_oi, "CW2_Active": c2_active,
                "Put Wall 1": p_wall_1, "Dist PW1": ((px - p_wall_1) / px) * 100, "PW1_OI": p_wall_1_oi, "PW1_Active": p1_active,
                "Put Wall 2": p_wall_2, "Dist PW2": ((px - p_wall_2) / px) * 100, "PW2_OI": p_wall_2_oi, "PW2_Active": p2_active
            })
        except: pass
    return results

@st.cache_data(ttl=3600)
def run_credit_stress_engine():
    try:
        df_hyg = yf.download("HYG", period="6mo", progress=False)
        df_ief = yf.download("IEF", period="6mo", progress=False)
        df_spy = yf.download("SPY", period="6mo", progress=False)
        
        if isinstance(df_hyg.columns, pd.MultiIndex): df_hyg.columns = df_hyg.columns.droplevel(1)
        if isinstance(df_ief.columns, pd.MultiIndex): df_ief.columns = df_ief.columns.droplevel(1)
        if isinstance(df_spy.columns, pd.MultiIndex): df_spy.columns = df_spy.columns.droplevel(1)
        
        c_hyg, c_ief, c_spy = df_hyg['Close'].dropna(), df_ief['Close'].dropna(), df_spy['Close'].dropna()
        if c_hyg.empty or c_ief.empty or c_spy.empty: return {"status": "offline", "error": "API returned empty dataset"}
        
        if c_hyg.index.tz is not None: c_hyg.index = c_hyg.index.tz_localize(None)
        if c_ief.index.tz is not None: c_ief.index = c_ief.index.tz_localize(None)
        if c_spy.index.tz is not None: c_spy.index = c_spy.index.tz_localize(None)
        
        df = pd.concat([c_hyg, c_ief, c_spy], axis=1, keys=['HYG', 'IEF', 'SPY']).dropna()
        if df.empty: return {"status": "offline", "error": "Index Alignment Failed"}

        df['Credit_Ratio'] = df['HYG'] / df['IEF']
        df['Ratio_20SMA'] = df['Credit_Ratio'].rolling(20).mean()
        spy_bullish = float(df['SPY'].iloc[-1]) > float(df['SPY'].rolling(20).mean().iloc[-1])
        credit_bearish = float(df['Credit_Ratio'].iloc[-1]) < float(df['Ratio_20SMA'].iloc[-1])
        divergence = spy_bullish and credit_bearish
        
        return {
            "status": "online", "divergence": divergence, 
            "ratio": float(df['Credit_Ratio'].iloc[-1]), "sma": float(df['Ratio_20SMA'].iloc[-1]),
            "history": df[['SPY', 'Credit_Ratio', 'Ratio_20SMA']].tail(120)
        }
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=900)
def get_options_skew(ticker="SPY"):
    try:
        df = yf.download(ticker, period="5d", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df = df.dropna()
        if df.empty: return {"status": "offline", "error": "No price data (API Block)"}
        px = float(df['Close'].iloc[-1])
        
        tk = yf.Ticker(ticker)
        exps = tk.options
        if not exps: return {"status": "offline", "error": "Options chain unavailable"}
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

@st.cache_data(ttl=3600)
def get_options_flow_chart_data(live_pcr, ticker="SPY"):
    try:
        df = yf.download([ticker, "^VIX"], period="6mo", progress=False)['Close'].dropna()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        if df.empty: return None
        vix = df['^VIX']
        vix_norm = (vix - vix.min()) / (vix.max() - vix.min())
        sim_pcr = 0.6 + (vix_norm * 1.0)
        offset = live_pcr - float(sim_pcr.iloc[-1])
        df['PCR_Proxy'] = sim_pcr + offset
        return df.tail(120)
    except Exception:
        return None

@st.cache_data(ttl=3600)
def run_rotation_engine(sym1="SPY", sym2="DBC"):
    try:
        df1 = yf.download(sym1, period="1y", progress=False)
        if isinstance(df1.columns, pd.MultiIndex): df1.columns = df1.columns.droplevel(1)
        df1 = df1.dropna()
        if df1.empty: return {"status": "offline", "error": f"API Blocked {sym1}"}
        c1 = df1['Close']
        if c1.index.tz is not None: c1.index = c1.index.tz_localize(None)
        
        df2 = yf.download(sym2, period="1y", progress=False)
        if isinstance(df2.columns, pd.MultiIndex): df2.columns = df2.columns.droplevel(1)
        df2 = df2.dropna()
        if df2.empty: return {"status": "offline", "error": f"API Blocked {sym2}"}
        c2 = df2['Close']
        if c2.index.tz is not None: c2.index = c2.index.tz_localize(None)
        
        df = pd.concat([c1, c2], axis=1, keys=[sym1, sym2]).dropna()
        if df.empty: return {"status": "offline", "error": "Insufficient data overlap / Timezone Conflict"}
        
        df['Ratio'] = df[sym1] / df[sym2]
        df['Ratio_50SMA'] = df['Ratio'].rolling(50).mean()
        
        current_ratio = float(df['Ratio'].iloc[-1])
        current_sma = float(df['Ratio_50SMA'].iloc[-1])
        is_favored = current_ratio > current_sma
        
        return {"status": "online", "favored": is_favored, "ratio": current_ratio, "sma": current_sma, "chart": df[['Ratio', 'Ratio_50SMA']].tail(90)}
    except Exception as e: return {"status": "offline", "error": str(e)}

@st.cache_data(ttl=900)
def run_master_screener():
    """V5.39 UNIFIED GLOBAL SCAN: Consolidates Whale, Dark Pool, and Kinetic into one master table."""
    results = []
    tickers = list(dict.fromkeys(cfg.LIEUTENANTS))
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="6mo", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            df = df.dropna()
            if df.empty or len(df) < 50: continue
            
            c, v = float(df['Close'].iloc[-1]), float(df['Volume'].iloc[-1])
            sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
            ema_9 = float(df['Close'].ewm(span=9, adjust=False).mean().iloc[-1])
            ema_21 = float(df['Close'].ewm(span=21, adjust=False).mean().iloc[-1])
            
            df['Vol_SMA_20'] = df['Volume'].rolling(20).mean()
            vol_sma_9 = float(df['Volume'].rolling(9).mean().iloc[-1])
            vol_sma_20 = float(df['Vol_SMA_20'].iloc[-1])
            vol_sma_50 = float(df['Volume'].rolling(50).mean().iloc[-1])
            
            df['Range'] = df['High'] - df['Low']
            df['ATR_20'] = df['Range'].rolling(20).mean()
            atr_20 = float(df['ATR_20'].iloc[-1])
            rng = float(df['Range'].iloc[-1])
            
            df['Rel_Vol'] = df['Volume'] / (df['Vol_SMA_20'] + 1)
            df['Up_Day'] = df['Close'] > df['Open']
            df['Close_Pos'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'] + 0.0001) 
            
            # --- Dark Pool / System Scores ---
            trend, mom, liq = c > sma_50, ema_9 > ema_21, vol_sma_9 > vol_sma_50
            dp_vol = (v / vol_sma_20) >= 1.5 if vol_sma_20 > 0 else False
            dp_comp = (rng / atr_20) <= 0.75 if atr_20 > 0 else False
            score = sum([trend, mom, liq, dp_vol, dp_comp])
            
            # --- Whale Hunter Physics ---
            last_2 = df.tail(2)
            whale_block = any((row['Rel_Vol'] >= 2.5 and row['Up_Day'] and row['Close_Pos'] >= 0.7) for _, row in last_2.iterrows())
            
            last_10 = df.tail(10)
            acc_days = len(last_10[(last_10['Rel_Vol'] > 1.2) & (last_10['Up_Day'])])
            dist_days = len(last_10[(last_10['Rel_Vol'] > 1.2) & (~last_10['Up_Day'])])
            cluster_acc = acc_days >= 3 and dist_days <= 1
            
            # --- Hierarchy of Signals ---
            if whale_block and cluster_acc: cat = "☢️ WHALE + CLUSTER"
            elif whale_block: cat = "🐋 WHALE BLOCK"
            elif cluster_acc: cat = "🔥 CLUSTER ACCUMULATION"
            elif score == 5: cat = "🔥 PERFECT TIER 1"
            elif dp_vol and dp_comp and not trend: cat = "🦇 STEALTH (DARK POOL)"
            elif mom and liq: cat = "🚀 KINETIC BREAKOUT"
            else: cat = "STANDBY"
            
            if cat != "STANDBY":
                results.append({
                    "Ticker": ticker, 
                    "Price": f"${c:.2f}", 
                    "Category": cat,
                    "Vol Spike (x)": f"{v/vol_sma_20:.1f}x" if vol_sma_20 > 0 else "0.0x",
                    "Acc Days (10d)": f"{acc_days}",
                    "Compression (x)": f"{rng/atr_20:.2f}x" if atr_20 > 0 else "0.00x",
                    "Titan Score": f"{score}/5"
                })
        except Exception: pass
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def run_rrg_engine(universe_key="Macro (Assets)"):
    try:
        universes = {
            "Macro (Assets)": {"benchmark": "SPY", "tickers": cfg.MACRO_ASSETS},
            "Sectors (S&P 500)": {"benchmark": "SPY", "tickers": cfg.SECTORS},
            "Subsectors (Industry)": {"benchmark": "SPY", "tickers": cfg.SUBSECTORS},
            "AI & Tech Infra": {"benchmark": "SPY", "tickers": cfg.AI_THEMATIC},
            "Crypto Proxy": {"benchmark": "SPY", "tickers": cfg.CRYPTO_THEMATIC}
        }
        benchmark = universes[universe_key]["benchmark"]
        tickers = universes[universe_key]["tickers"]
        
        closes = pd.DataFrame()
        volumes = pd.DataFrame()
        for t in tickers + [benchmark]:
            try:
                d = yf.download(t, period="6mo", progress=False)
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.droplevel(1)
                d = d.dropna()
                if not d.empty:
                    c_col = d['Close']
                    v_col = d['Volume']
                    if c_col.index.tz is not None: c_col.index = c_col.index.tz_localize(None)
                    if v_col.index.tz is not None: v_col.index = v_col.index.tz_localize(None)
                    closes[t] = c_col
                    volumes[t] = v_col
            except: pass
            
        closes = closes.dropna()
        volumes = volumes.dropna()
        if closes.empty or benchmark not in closes.columns: return {"status": "offline", "error": "Insufficient RRG Universe Data"}
        
        results = []
        for ticker in tickers:
            if ticker not in closes.columns: continue
            rs = closes[ticker] / closes[benchmark]
            rs_ratio, rs_mom = (rs.rolling(10).mean() / rs.rolling(40).mean()) * 100, ((rs.rolling(10).mean() / rs.rolling(40).mean()) * 100 / (rs.rolling(10).mean() / rs.rolling(40).mean() * 100).rolling(10).mean()) * 100
            vol_ratio = volumes[ticker] / volumes[ticker].rolling(20).mean()
            rs_ratio, rs_mom, vol_ratio = rs_ratio.dropna(), rs_mom.dropna(), vol_ratio.dropna()
            if not rs_ratio.empty and not rs_mom.empty:
                current_vol_spike = float(vol_ratio.iloc[-1])
                dynamic_size = max(6, min(current_vol_spike * 8, 25))
                results.append({
                    "Ticker": ticker, "RS_Ratio": float(rs_ratio.iloc[-1]), "RS_Mom": float(rs_mom.iloc[-1]),     
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
    except Exception as e: return None, None


# ==============================================================================
# BACKTESTER LAB ENGINES
# ==============================================================================
@st.cache_data(ttl=3600)
def build_signal_engine(ticker: str, period: str = "5y") -> pd.DataFrame:
    df = yf.download(ticker, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    df = df.dropna()
    if df.empty: return df

    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['Range'] = df['High'] - df['Low']
    df['ATR_20'] = df['Range'].rolling(window=20).mean()
    df['Vol_SMA_9'] = df['Volume'].rolling(window=9).mean()
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Vol_SMA_50'] = df['Volume'].rolling(window=50).mean()

    trend_bullish = df['Close'] > df['SMA_50']
    ema_above_today = df['EMA_9'] > df['EMA_21']
    ema_below_yesterday = df['EMA_9'].shift(1) <= df['EMA_21'].shift(1)
    kinetic_cross = ema_above_today & ema_below_yesterday
    
    liquidity_expanding = df['Volume'] > (df['Vol_SMA_20'] * 1.2)

    df['Signal_Long'] = trend_bullish & kinetic_cross & liquidity_expanding
    return df.dropna()

@st.cache_data(ttl=3600)
def run_execution_engine(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    trade_ledger = []
    in_position = False
    entry_date = None
    entry_price = 0.0
    current_stop = 0.0

    for i in range(len(df) - 1):
        today_date = df.index[i]
        today = df.iloc[i]
        tomorrow_date = df.index[i + 1]
        tomorrow = df.iloc[i + 1]

        if not in_position:
            if today['Signal_Long']:
                in_position = True
                entry_date = tomorrow_date
                entry_price = float(tomorrow['Open'])
                current_stop = float(today['Close']) - (2 * float(today['ATR_20']))
                if entry_price < current_stop: current_stop = entry_price 
        else:
            if float(today['Low']) <= current_stop:
                exit_price = current_stop
                if float(today['Open']) < current_stop: exit_price = float(today['Open'])
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trade_ledger.append({
                    "Ticker": ticker, "Entry Date": entry_date.strftime('%Y-%m-%d'), "Entry Price": entry_price,
                    "Exit Date": today_date.strftime('%Y-%m-%d'), "Exit Price": exit_price,
                    "Exit Reason": "Tactical Stop (2x ATR)", "PnL (%)": pnl_pct
                })
                in_position = False
                continue

            if float(today['Close']) < float(today['SMA_50']):
                exit_price = float(tomorrow['Open'])
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trade_ledger.append({
                    "Ticker": ticker, "Entry Date": entry_date.strftime('%Y-%m-%d'), "Entry Price": entry_price,
                    "Exit Date": tomorrow_date.strftime('%Y-%m-%d'), "Exit Price": exit_price,
                    "Exit Reason": "Structural Stop (50 SMA)", "PnL (%)": pnl_pct
                })
                in_position = False
                continue

            theoretical_stop = float(today['Close']) - (2 * float(today['ATR_20']))
            if theoretical_stop > current_stop: current_stop = theoretical_stop

    if in_position:
        last_day = df.iloc[-1]
        exit_price = float(last_day['Close'])
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        trade_ledger.append({
            "Ticker": ticker, "Entry Date": entry_date.strftime('%Y-%m-%d'), "Entry Price": entry_price,
            "Exit Date": df.index[-1].strftime('%Y-%m-%d'), "Exit Price": exit_price,
            "Exit Reason": "End of Backtest Dataset", "PnL (%)": pnl_pct
        })
    return pd.DataFrame(trade_ledger)


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
        else:
            st.error(f"DEFCON Engine Offline: {risk.get('error', 'Unknown')}")

    st.markdown("<div class='apex-header' style='margin-top: 20px;'>🏛️ FOMC LIQUIDITY & YIELD CURVE (MACRO PLUMBING)</div>", unsafe_allow_html=True)
    with st.spinner("Fetching FRED Macro Data..."):
        fomc = get_fomc_data()
        if fomc['status'] == 'online':
            df_fomc = fomc['data']
            yc_val = fomc['current_yc']
            ff_val = fomc['current_ff']
            
            yc_color = "#FF4444" if yc_val < 0 else "#39FF14"
            
            st.markdown(f"""
            <div style='display: flex; gap: 20px; margin-bottom: 20px;'>
                <div class='tactical-card' style='flex: 1; min-height: 100px; border-left: 5px solid {yc_color};'>
                    <div class='metric-sub'>10Y-2Y YIELD CURVE</div>
                    <div class='price-text' style='color: {yc_color};'>{yc_val:+.2f}% ({fomc['curve_status']})</div>
                </div>
                <div class='tactical-card' style='flex: 1; min-height: 100px; border-left: 5px solid #58a6ff;'>
                    <div class='metric-sub'>FED FUNDS RATE (COST OF CAPITAL)</div>
                    <div class='price-text' style='color: #58a6ff;'>{ff_val:.2f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            fig_fomc = make_subplots(specs=[[{"secondary_y": True}]])
            fig_fomc.add_trace(go.Scatter(x=df_fomc.index, y=df_fomc['Yield_Curve'], name="10Y-2Y Spread", line=dict(color=yc_color, width=2), fill='tozeroy', fillcolor=f'rgba({255 if yc_val < 0 else 57}, {68 if yc_val < 0 else 255}, {68 if yc_val < 0 else 20}, 0.1)'), secondary_y=False)
            fig_fomc.add_trace(go.Scatter(x=df_fomc.index, y=df_fomc['Fed_Funds'], name="Fed Funds Rate", line=dict(color='#58a6ff', width=2, dash='dot')), secondary_y=True)
            fig_fomc.add_hline(y=0, line_dash="dash", line_color="#FFF", secondary_y=False)
            
            fig_fomc.update_layout(plot_bgcolor='#161b22', paper_bgcolor='#161b22', font=dict(color='#c9d1d9'), margin=dict(l=10, r=10, t=10, b=10), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
            fig_fomc.update_yaxes(title_text="Yield Curve Spread (%)", secondary_y=False, showgrid=False)
            fig_fomc.update_yaxes(title_text="Fed Funds Rate (%)", secondary_y=True, showgrid=False)
            fig_fomc.update_xaxes(showgrid=False)
            
            st.plotly_chart(fig_fomc, width="stretch", key="fomc_chart")
        else:
            st.error(f"FOMC Engine Offline: {fomc.get('error', 'Unknown Error')}")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🌐 GLOBAL LIQUIDITY PHYSICS (CROSS-ASSET PEARSON MATRIX)</div>", unsafe_allow_html=True)
    with st.spinner("Calculating 90-Day Rolling Cross-Asset Correlations..."):
        matrix_res = get_cross_asset_matrix()
        if matrix_res['status'] == 'online':
            corr_df = matrix_res['data']
            
            custom_colorscale = [
                [0.0, '#FF4444'],
                [0.5, '#161b22'],
                [1.0, '#39FF14'] 
            ]
            
            fig_hm = go.Figure(data=go.Heatmap(
                z=corr_df.values,
                x=corr_df.columns,
                y=corr_df.index,
                colorscale=custom_colorscale,
                zmin=-1, zmax=1,
                text=corr_df.values,
                texttemplate="%{text}",
                showscale=False,
                hoverinfo="x+y+z"
            ))
            
            fig_hm.update_layout(
                plot_bgcolor='#0d1117', 
                paper_bgcolor='#0d1117', 
                font=dict(color='#c9d1d9', size=14),
                margin=dict(l=20, r=20, t=20, b=20),
                height=450,
                xaxis=dict(side="bottom", showgrid=False),
                yaxis=dict(autorange="reversed", showgrid=False)
            )
            st.plotly_chart(fig_hm, width="stretch", key="heatmap_chart")
        else:
            st.error(f"Pearson Matrix Offline: {matrix_res.get('error', 'Unknown Error')}")

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
            if not gamma_data:
                st.info("No options data available at this time.")
            else:
                for g in gamma_data:
                    zg = g['Zero Gamma']
                    c1, c2 = g['Call Wall 1'], g['Call Wall 2']
                    p1, p2 = g['Put Wall 1'], g['Put Wall 2']
                    px = g['Price']
                    pcr = g['PCR']

                    if px >= zg:
                        vol_state = "<span style='color:#39FF14;'>+GEX (CHOP/MEAN-REVERT)</span>"
                        cc_main = "card-neutral"
                    else:
                        vol_state = "<span style='color:#FF4444;'>-GEX (TREND/HIGH-VOL)</span>"
                        cc_main = "card-bearish"
                        
                    # Active Flow Tags
                    c1_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('CW1_Active') else ""
                    c2_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('CW2_Active') else ""
                    p1_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('PW1_Active') else ""
                    p2_tag = "<span style='color:#FFAA00; font-size:0.7rem; font-weight:bold; margin-left:5px;'>[⚡ ACTIVE POUR]</span>" if g.get('PW2_Active') else ""

                    pcr_color = "#FF4444" if pcr > 1.2 else "#39FF14" if pcr < 0.8 else "#8b949e"

                    st.markdown(f"""
                    <div class='tactical-card {cc_main}'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <div class='asset-title'>{g['Ticker']} <span style='font-size:0.8rem; color:#8b949e;'>${px:.2f}</span></div>
                            <div style='font-size:0.85rem; font-weight:bold;'>{vol_state} <span style='color:{pcr_color}; margin-left:10px;'>| PCR: {pcr:.2f}</span></div>
                        </div>
                        <div class='metric-sub' style='margin-top:10px;'>
                            <div class='data-row'><span>T2 Call (Squeeze Target): <b style='color:#FFAA00;'>${c2:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['CW2_OI']):,})</span>{c2_tag}</span><span>{g['Dist CW2']:+.1f}%</span></div>
                            <div class='data-row'><span>T1 Call (Primary Ceiling): <b style='color:#FFF;'>${c1:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['CW1_OI']):,})</span>{c1_tag}</span><span>{g['Dist CW1']:+.1f}%</span></div>
                            <div class='data-row' style='background:rgba(255,255,255,0.05); padding:2px 5px;'><span>Zero-Gamma (Volatility Flip): <b style='color:#58a6ff;'>${zg:.2f}</b></span><span>{((zg-px)/px)*100:+.1f}%</span></div>
                            <div class='data-row'><span>T1 Put (Primary Floor): <b style='color:#FFF;'>${p1:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['PW1_OI']):,})</span>{p1_tag}</span><span>{g['Dist PW1']:+.1f}%</span></div>
                            <div class='data-row'><span>T2 Put (The Abyss): <b style='color:#FF4444;'>${p2:.2f}</b> <span style='font-size:0.75rem; color:#8b949e;'>(Mass: {int(g['PW2_OI']):,})</span>{p2_tag}</span><span>{g['Dist PW2']:+.1f}%</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🏦 INSTITUTIONAL CREDIT & VOLATILITY</div>", unsafe_allow_html=True)
    c_col1, c_col2 = st.columns([1, 1], gap="large")
    
    with c_col1:
        with st.spinner("Pulling High Yield Spreads & Rendering Divergence Chart..."):
            credit_data = run_credit_stress_engine()
            if credit_data['status'] == 'online':
                cc, tc, cm = ("card-bearish", "#FF4444", "RISK-OFF DIVERGENCE") if credit_data['divergence'] else ("card-bullish", "#39FF14", "CREDIT ALIGNED (RISK-ON)")
                st.markdown(f"<div class='tactical-card {cc}'><div><div class='asset-title'>CREDIT STRESS RADAR</div><div class='metric-sub' style='margin-top:10px;'><div class='data-row'><span>HYG/IEF RATIO:</span><span style='color:#FFF; font-weight:bold;'>{credit_data['ratio']:.3f}</span></div><div class='data-row'><span>TREND:</span><span style='color:{tc}; font-weight:bold;'>{'DIVERGING' if credit_data['divergence'] else 'SUPPORTIVE'}</span></div></div></div><div class='mandate-box {'mandate-sell' if credit_data['divergence'] else 'mandate-buy'}'>[ {cm} ]</div></div>", unsafe_allow_html=True)
                
                df_c = credit_data['history']
                fig_c = make_subplots(specs=[[{"secondary_y": True}]])
                fig_c.add_trace(go.Scatter(x=df_c.index, y=df_c['SPY'], name="SPY Price", line=dict(color='#58a6ff', width=2)), secondary_y=False)
                fig_c.add_trace(go.Scatter(x=df_c.index, y=df_c['Credit_Ratio'], name="HYG/IEF Ratio", line=dict(color='#FF4444' if credit_data['divergence'] else '#39FF14', width=2)), secondary_y=True)
                fig_c.update_layout(plot_bgcolor='#161b22', paper_bgcolor='#161b22', font=dict(color='#c9d1d9'), margin=dict(l=10, r=10, t=10, b=10), height=280, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
                fig_c.update_yaxes(showgrid=False, zeroline=False)
                fig_c.update_xaxes(showgrid=False, zeroline=False)
                st.plotly_chart(fig_c, width="stretch", key="credit_chart")
            else: st.error(f"Credit Engine Offline: {credit_data.get('error', 'Unknown')}")
            
    with c_col2:
        with st.spinner("Parsing Option Volatility Skew & Rendering Divergence Chart..."):
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
                    fig_o.update_yaxes(showgrid=False, zeroline=False)
                    fig_o.update_xaxes(showgrid=False, zeroline=False)
                    st.plotly_chart(fig_o, width="stretch", key="options_chart")
            else: st.error(f"Options Flow Engine Offline: {skew_data.get('error', 'Unknown')}")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔄 MACRO ROTATION & RRG (EQUITIES vs COMMODITIES vs BREADTH)</div>", unsafe_allow_html=True)
    rot_col1, rot_col2 = st.columns([1, 1], gap="large")

    with rot_col1:
        rot_tabs = st.tabs(["Macro Flow (SPY / DBC)", "Risk Breadth (IJR / SPY)"])
        
        with rot_tabs[0]:
            with st.spinner("Calculating Intermarket See-Saw..."):
                spy_dbc = run_rotation_engine("SPY", "DBC")
                if spy_dbc['status'] == 'online':
                    eq_favored = spy_dbc['favored']
                    box_color, box_bg = ("#39FF14", "rgba(57, 255, 20, 0.05)") if eq_favored else ("#FFAA00", "rgba(255, 170, 0, 0.05)")
                    status_text = "EQUITIES DOMINATING" if eq_favored else "COMMODITIES DOMINATING"
                    st.markdown(f"<div style='border: 2px solid {box_color}; background-color: {box_bg}; border-radius: 8px; padding: 20px; margin-bottom: 20px;'><h3 style='color: {box_color}; margin-top: 0;'>SYSTEM READOUT: {status_text}</h3></div>", unsafe_allow_html=True)
                    st.line_chart(spy_dbc['chart'], color=["#58a6ff", "#8b949e"], width="stretch")
                else:
                    st.error(f"SPY/DBC Engine Offline: {spy_dbc.get('error', 'Unknown Error')}")

        with rot_tabs[1]:
            with st.spinner("Calculating Small-Cap Breadth..."):
                breadth_engine = run_rotation_engine("IJR", "SPY")
                if breadth_engine['status'] == 'online':
                    breadth_favored = breadth_engine['favored']
                    box_color, box_bg = ("#39FF14", "rgba(57, 255, 20, 0.05)") if breadth_favored else ("#8b949e", "rgba(139, 148, 158, 0.05)")
                    status_text = "SMALL CAPS LEADING (RISK-ON BREADTH)" if breadth_favored else "LARGE CAPS DEFENSIVE (NARROW MARKET)"
                    st.markdown(f"<div style='border: 2px solid {box_color}; background-color: {box_bg}; border-radius: 8px; padding: 20px; margin-bottom: 20px;'><h3 style='color: {box_color}; margin-top: 0;'>SYSTEM READOUT: {status_text}</h3></div>", unsafe_allow_html=True)
                    st.line_chart(breadth_engine['chart'], color=["#58a6ff", "#8b949e"], width="stretch")
                else:
                    st.error(f"Breadth Engine Offline: {breadth_engine.get('error', 'Unknown Error')}")

    with rot_col2:
        selected_universe = st.radio("Select RRG Universe:", ["Sectors (S&P 500)", "Subsectors (Industry)", "AI & Tech Infra", "Macro (Assets)", "Crypto Proxy"], horizontal=True, label_visibility="collapsed")
        with st.spinner(f"Mapping {selected_universe} via Config Settings..."):
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
            else:
                st.error(f"RRG Engine Offline: {rrg_engine.get('error', 'Unknown Error')}")

    # --- V5.39 UNIFIED MASTER SCREENER ---
    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🔍 TITAN MASTER SCREENER (UNIFIED GLOBAL SCAN)</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8b949e; font-size: 0.9rem;'>Vectorized 5-Factor scan across the Lieutenants universe, incorporating Whale Blocks and Accumulation Clusters.</p>", unsafe_allow_html=True)

    if st.button("EXECUTE GLOBAL SCAN"):
        with st.spinner("Compiling cross-asset vector data & institutional footprints..."):
            screen_df = run_master_screener()
            if not screen_df.empty:
                st.dataframe(screen_df.sort_values(by="Vol Spike (x)", ascending=False), width="stretch", hide_index=True)
            else:
                st.info("No actionable Tier 1, Stealth setups, or Whale Blocks detected across the universe today.")

    st.markdown("<div class='apex-header' style='margin-top: 40px;'>🎯 TACTICAL RECON & DECODER</div>", unsafe_allow_html=True)
    recon_col1, recon_col2 = st.columns([1, 4], gap="medium")

    with recon_col1:
        target_category = st.selectbox("Category Lens:", ["Lieutenants (Watchlist)", "Indices", "Sectors (Macro)", "Subsectors (Micro)", "Thematic (AI/Crypto)"])
        if target_category == "Indices": active_list = cfg.MACRO_ASSETS
        elif target_category == "Sectors (Macro)": active_list = cfg.SECTORS
        elif target_category == "Subsectors (Micro)": active_list = cfg.SUBSECTORS
        elif target_category == "Thematic (AI/Crypto)": active_list = cfg.AI_THEMATIC + cfg.CRYPTO_THEMATIC
        else: active_list = cfg.LIEUTENANTS
        target_chart = st.selectbox("Select Target:", active_list)

    with recon_col2:
        with st.spinner(f"Loading {target_chart}..."):
            chart_fig, last_data = run_tactical_chart(target_chart)
            if chart_fig: st.plotly_chart(chart_fig, width="stretch")
            else: st.error("Chart Engine Offline. YFinance API Blocked.")

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

# ==============================================================================
# ROUTING LOGIC: BACKTESTER LAB
# ==============================================================================
elif app_mode == "🧪 BACKTESTER LAB":
    st.markdown("<div class='apex-header'>🔬 QUANTITATIVE BACKTESTER LAB</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8b949e; margin-bottom: 30px;'>Run historical, path-dependent simulations using the Titan Omega logic to mathematically validate edge.</p>", unsafe_allow_html=True)

    bk_col1, bk_col2, bk_col3 = st.columns([2, 2, 1])
    with bk_col1:
        test_ticker = st.text_input("Enter Ticker Symbol:", value="NVDA", max_chars=10).upper()
    with bk_col2:
        test_period = st.selectbox("Historical Horizon:", ["1y", "2y", "5y", "10y", "max"], index=2)
    with bk_col3:
        st.write("") # Spacing
        st.write("")
        run_sim = st.button("RUN SIMULATION", use_container_width=True)

    if run_sim:
        with st.spinner(f"Ingesting {test_period} of historical data for {test_ticker}..."):
            df_signals = build_signal_engine(test_ticker, test_period)
            
            if df_signals.empty:
                st.error(f"Failed to fetch data for {test_ticker}. Verify ticker or API limits.")
            else:
                with st.spinner("Executing path-dependent state machine (calculating trailing stops)..."):
                    ledger_df = run_execution_engine(df_signals, test_ticker)
                    
                    if ledger_df.empty:
                        st.warning("Zero trades executed. The Titan Omega criteria did not trigger during this period.")
                    else:
                        st.markdown("<h3 style='color: #FFF; margin-top: 20px;'>📊 PERFORMANCE LEDGER</h3>", unsafe_allow_html=True)
                        
                        # Calculate Analytics
                        total_trades = len(ledger_df)
                        winning_trades = ledger_df[ledger_df['PnL (%)'] > 0]
                        losing_trades = ledger_df[ledger_df['PnL (%)'] <= 0]
                        
                        win_rate = (len(winning_trades) / total_trades) * 100
                        avg_win = winning_trades['PnL (%)'].mean() if not winning_trades.empty else 0.0
                        avg_loss = losing_trades['PnL (%)'].mean() if not losing_trades.empty else 0.0
                        
                        loss_rate_decimal = len(losing_trades) / total_trades
                        win_rate_decimal = win_rate / 100
                        expectancy = (win_rate_decimal * avg_win) / (loss_rate_decimal * abs(avg_loss)) if loss_rate_decimal > 0 and avg_loss != 0 else float('inf')
                        
                        multipliers = 1 + (ledger_df['PnL (%)'] / 100)
                        total_roi_pct = (multipliers.prod() - 1) * 100

                        # Render Metrics
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("System Win Rate", f"{win_rate:.1f}%")
                        m2.metric("Expectancy Ratio", f"{expectancy:.2f}")
                        m3.metric("Total ROI (Compounded)", f"{total_roi_pct:.1f}%")
                        m4.metric("Total Executions", total_trades)

                        st.markdown("---")
                        
                        m5, m6 = st.columns(2)
                        m5.metric("Average Winning Trade", f"+{avg_win:.2f}%")
                        m6.metric("Average Losing Trade", f"{avg_loss:.2f}%")

                        st.markdown("<h3 style='color: #FFF; margin-top: 40px;'>🧾 TRADE LOG</h3>", unsafe_allow_html=True)
                        
                        # Formatting for UI Display
                        display_df = ledger_df.copy()
                        display_df['Entry Price'] = display_df['Entry Price'].map('${:,.2f}'.format)
                        display_df['Exit Price'] = display_df['Exit Price'].map('${:,.2f}'.format)
                        display_df['PnL (%)'] = display_df['PnL (%)'].map('{:+.2f}%'.format)
                        
                        st.dataframe(display_df, width="stretch", hide_index=True)
