import yfinance as yf
import pandas as pd
import numpy as np

def build_signal_engine(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    Downloads historical data and calculates all Titan Omega indicators.
    Generates a boolean 'Signal_Long' mask for precise entry triggers.
    """
    print(f"[*] Initializing Phase 1 & 2 for {ticker}...")
    
    # 1. DATA INGESTION
    # -------------------------------------------------------------------------
    df = yf.download(ticker, period=period, progress=False)
    
    # Flatten MultiIndex columns if yfinance returns them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    df = df.dropna()
    if df.empty:
        print(f"[!] Warning: No data fetched for {ticker}.")
        return df

    # 2. TECHNICAL INDICATORS (PRICE)
    # -------------------------------------------------------------------------
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # Calculate Simplified ATR to match live terminal math
    df['Range'] = df['High'] - df['Low']
    df['ATR_20'] = df['Range'].rolling(window=20).mean()

    # 3. VOLUME INDICATORS (LIQUIDITY)
    # -------------------------------------------------------------------------
    df['Vol_SMA_9'] = df['Volume'].rolling(window=9).mean()
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Vol_SMA_50'] = df['Volume'].rolling(window=50).mean()

    # 4. SIGNAL GENERATION (THE LOGIC GATES)
    # -------------------------------------------------------------------------
    # Gate 1: Trend is inherently bullish
    trend_bullish = df['Close'] > df['SMA_50']
    
    # Gate 2: Momentum Ignition (The exact day 9 EMA crosses ABOVE 21 EMA)
    ema_above_today = df['EMA_9'] > df['EMA_21']
    ema_below_yesterday = df['EMA_9'].shift(1) <= df['EMA_21'].shift(1)
    kinetic_cross = ema_above_today & ema_below_yesterday
    
    # Gate 3: Liquidity is expanding
    liquidity_expanding = df['Vol_SMA_9'] > df['Vol_SMA_50']

    # Master Signal: All conditions must be True simultaneously
    df['Signal_Long'] = trend_bullish & kinetic_cross & liquidity_expanding

    # Clean up NaN rows created by the 50-day rolling windows
    df = df.dropna()
    
    # Quick sanity check readout
    total_signals = df['Signal_Long'].sum()
    print(f"[*] Signal Engine complete. {total_signals} kinetic crossover events detected over {period}.")

    return df

# Example Usage:
# target_data = build_signal_engine("NVDA", period="5y")
