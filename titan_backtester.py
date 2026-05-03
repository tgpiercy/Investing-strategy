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


def run_execution_engine(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Path-dependent state machine. Loops through history day-by-day to 
    simulate live trading execution and trailing ATR risk management.
    """
    print(f"[*] Initializing Phase 3: Execution Engine for {ticker}...")
    
    trade_ledger = []
    in_position = False
    entry_date = None
    entry_price = 0.0
    current_stop = 0.0

    # Iterate through the DataFrame using a standard loop to access 'tomorrow' safely
    for i in range(len(df) - 1):
        today_date = df.index[i]
        today = df.iloc[i]
        tomorrow_date = df.index[i + 1]
        tomorrow = df.iloc[i + 1]

        # ---------------------------------------------------------------------
        # ENTRY LOGIC
        # ---------------------------------------------------------------------
        if not in_position:
            if today['Signal_Long']:
                # Execute buy on the NEXT morning's open to prevent look-ahead bias
                in_position = True
                entry_date = tomorrow_date
                entry_price = tomorrow['Open']
                
                # Set initial stop based on the signal day's volatility
                current_stop = today['Close'] - (2 * today['ATR_20'])
                
                # Gap Down Guardrail: If tomorrow opens below our stop, we are stopped out instantly
                if entry_price < current_stop:
                    current_stop = entry_price 

        # ---------------------------------------------------------------------
        # RISK MANAGEMENT (WHILE IN POSITION)
        # ---------------------------------------------------------------------
        else:
            # 1. TACTICAL EXIT (Intraday Stop Loss)
            if today['Low'] <= current_stop:
                exit_price = current_stop
                
                # Gap Down Guardrail: If it gapped down below stop at the open, we take the open price
                if today['Open'] < current_stop:
                    exit_price = today['Open']
                    
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trade_ledger.append({
                    "Ticker": ticker, "Entry Date": entry_date, "Entry Price": entry_price,
                    "Exit Date": today_date, "Exit Price": exit_price,
                    "Exit Reason": "Tactical Stop (2x ATR)", "PnL (%)": pnl_pct
                })
                in_position = False
                continue # Trade closed, move to next day

            # 2. STRUCTURAL EXIT (Lost 50 SMA Trend)
            if today['Close'] < today['SMA_50']:
                # Trend is broken. Sell on the NEXT morning's open.
                exit_price = tomorrow['Open']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                
                trade_ledger.append({
                    "Ticker": ticker, "Entry Date": entry_date, "Entry Price": entry_price,
                    "Exit Date": tomorrow_date, "Exit Price": exit_price,
                    "Exit Reason": "Structural Stop (50 SMA)", "PnL (%)": pnl_pct
                })
                in_position = False
                continue # Trade closed, move to next day

            # 3. TRAILING STOP RATCHET
            # If we survived today, calculate the new theoretical stop
            theoretical_stop = today['Close'] - (2 * today['ATR_20'])
            # Only update if the new stop is HIGHER than the current stop
            if theoretical_stop > current_stop:
                current_stop = theoretical_stop

    # -------------------------------------------------------------------------
    # CLEANUP: Close open positions at the end of the dataset
    # -------------------------------------------------------------------------
    if in_position:
        last_day = df.iloc[-1]
        exit_price = last_day['Close']
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        trade_ledger.append({
            "Ticker": ticker, "Entry Date": entry_date, "Entry Price": entry_price,
            "Exit Date": df.index[-1], "Exit Price": exit_price,
            "Exit Reason": "End of Backtest Dataset", "PnL (%)": pnl_pct
        })

    ledger_df = pd.DataFrame(trade_ledger)
    print(f"[*] Execution Engine complete. Processed {len(ledger_df)} trades.")
    return ledger_df


def generate_performance_analytics(ledger_df: pd.DataFrame):
    """
    Compiles the trade ledger into core quantitative metrics.
    """
    print("\n" + "="*50)
    print("🦅 TITAN OMEGA: PERFORMANCE LEDGER 🦅")
    print("="*50)
    
    if ledger_df.empty:
        print("[!] No trades executed during this period based on current logic.")
        return

    total_trades = len(ledger_df)
    winning_trades = ledger_df[ledger_df['PnL (%)'] > 0]
    losing_trades = ledger_df[ledger_df['PnL (%)'] <= 0]
    
    win_rate = (len(winning_trades) / total_trades) * 100
    avg_win = winning_trades['PnL (%)'].mean() if not winning_trades.empty else 0.0
    avg_loss = losing_trades['PnL (%)'].mean() if not losing_trades.empty else 0.0
    
    # Expectancy Ratio (The ultimate measure of system health)
    loss_rate_decimal = len(losing_trades) / total_trades
    win_rate_decimal = win_rate / 100
    
    if loss_rate_decimal == 0 or avg_loss == 0:
        expectancy = float('inf')
    else:
        expectancy = (win_rate_decimal * avg_win) / (loss_rate_decimal * abs(avg_loss))
        
    # Total System ROI (Compound approach)
    multipliers = 1 + (ledger_df['PnL (%)'] / 100)
    total_roi_pct = (multipliers.prod() - 1) * 100

    print(f"Total Trades Exited:  {total_trades}")
    print(f"System Win Rate:      {win_rate:.2f}%")
    print(f"Average Winning PnL:  +{avg_win:.2f}%")
    print(f"Average Losing PnL:   {avg_loss:.2f}%")
    print(f"Expectancy Ratio:     {expectancy:.2f}")
    print(f"Total System ROI:     {total_roi_pct:.2f}%")
    print("="*50 + "\n")


# ==============================================================================
# MASTER EXECUTION BLOCK
# ==============================================================================
if __name__ == "__main__":
    # 1. Define Target and Time Horizon
    TARGET_TICKER = "NVDA" 
    TEST_PERIOD = "5y"
    
    # 2. Run the Engine Pipeline
    df_signals = build_signal_engine(TARGET_TICKER, period=TEST_PERIOD)
    
    if not df_signals.empty:
        df_ledger = run_execution_engine(df_signals, TARGET_TICKER)
        generate_performance_analytics(df_ledger)
        
        if not df_ledger.empty:
            print("Recent Trade Logs (Last 5):")
            # Format the output for readability
            st_ledger = df_ledger.tail(5).copy()
            st_ledger['Entry Price'] = st_ledger['Entry Price'].map('${:,.2f}'.format)
            st_ledger['Exit Price'] = st_ledger['Exit Price'].map('${:,.2f}'.format)
            st_ledger['PnL (%)'] = st_ledger['PnL (%)'].map('{:+.2f}%'.format)
            print(st_ledger.to_string(index=False))
