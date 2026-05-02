# FILE: apex_config.py
# ROLE: Master Configuration & Radar Parameters
# ARCHITECTURE: Global Variable Engine

# ==============================================================================
# 1. THE LIEUTENANTS (Target Acquisition List)
# ==============================================================================
# This is the primary universe of assets the Kinetic and Dark Pool Radars will scan.
# To maintain high-speed API performance, keep this list under 50 highly liquid targets.

LIEUTENANTS = [
    # Mega-Cap Tech & Core Indices
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA",
    
    # AI & Tech Infrastructure (The High-Beta Matrix)
    "NVDA", "AMD", "AVGO", "SMCI", "ANET", "VRT", "PLTR", "TSM", "ARM", "MU",
    
    # Financials (Liquidity Proxies)
    "JPM", "GS", "MS", "BAC", 
    
    # Hard Assets & Energy (Inflation/War Hedges)
    "XOM", "CVX", "SLB", "COP", "OXY", "USO", "GLD",
    
    # Industrials, Defense & Crypto Proxies
    "CAT", "GE", "LMT", "RTX", "MSTR", "COIN"
]

# ==============================================================================
# 2. KINETIC RADAR PARAMETERS
# ==============================================================================
# The threshold for price proximity to the 40-Day High (Donchian Channel).
# A value of -2.0 means the asset must be trading within 2% of its highest 
# price over the last 40 days to qualify as a valid breakout setup.
MIN_DONCHIAN_PROX = -2.0 

# ==============================================================================
# 3. VOLUME IGNITION THRESHOLDS
# ==============================================================================
# The minimum institutional footprint required to trigger the radar.
# A value of 1.5 means today's volume must be at least 150% (1.5x) of the 
# standard 20-Day Simple Moving Average.
MIN_VOLUME_SPIKE = 1.5
