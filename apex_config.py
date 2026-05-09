# FILE: apex_config.py
# ROLE: Master Configuration Dictionary
# ARCHITECTURE: Titan Omega V5.40 (Subsector Roster Expanded)

# ==============================================================================
# API KEYS & SECURITY
# ==============================================================================
# Generate free key here: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = "50ff1e637effabba2fe09afee01aae98"

# ==============================================================================
# QUANTITATIVE THRESHOLDS
# ==============================================================================
MIN_VOLUME_SPIKE = 1.2    # Kinetic Ignition: Volume must be 20% higher than 20-day avg
MIN_DONCHIAN_PROX = -2.0  # Max distance from 40-day high to be considered a valid breakout (%)

# ==============================================================================
# RRG UNIVERSE CONFIGURATIONS (RELATIVE ROTATION GRAPHS)
# ==============================================================================
MACRO_ASSETS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "USO", "UUP", "DBC", "IEMG", "INDA"]
SECTORS = ["XLE", "XLF", "XLU", "XLI", "XLRE", "XLV", "XLP", "XLY", "XLC", "XLK", "XLB"]

# V5.40 Expanded Industry Breakdown
SUBSECTORS = ["SMH", "IGV", "CIBR", "XBI", "KRE", "XHB", "IYT", "XOP", "XME", "ITA", "XRT"]

AI_THEMATIC = ["NVDA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "TSM", "AVGO", "BOTZ", "ROBO", "AIQ", "CHAT", "AINF", "SRVR"]
CRYPTO_THEMATIC = ["BTC-USD", "ETH-USD", "MSTR", "COIN", "MARA"]

# ==============================================================================
# THE MASTER LIEUTENANTS ROSTER (GLOBAL SCREENER UNIVERSE)
# ==============================================================================
# This list feeds the 'Titan Master Screener' and 'Tactical Recon' modules.
# It contains highly liquid, institutional-grade proxies across all thematic vectors.

LIEUTENANTS = [
    # Broad Market & Macro
    "SPY", "QQQ", "IWM", 
    
    # Core Industries (The Subsectors)
    "IGV", "CIBR", "KRE", "XHB", "IYT", "XOP", "XME", "ITA", "XRT", "XBI",
    
    # Energy & Power (Inflation Hedges)
    "XLE", "VDE", 
    
    # Clean Energy & Nuclear (Baseload & Policy)
    "ICLN", "QCLN", "URA", "NLR",
    
    # Physical AI (Robotics & Automation)
    "BOTZ", "ROBO",
    
    # Virtual AI (Software & GenAI)
    "AIQ", "CHAT",
    
    # AI Infrastructure (Picks & Shovels & Real Estate)
    "SMH", "AINF", "SRVR",
    
    # Emerging Markets (Global Beta)
    "IEMG", "INDA",
    
    # Key Mega-Caps (High Beta Alpha)
    "NVDA", "AMD", "MSFT", "AMZN", "META", "GOOGL", "AAPL", "TSLA"
]
