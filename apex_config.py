# FILE: apex_config.py
# ROLE: Master Configuration & Radar Parameters
# ARCHITECTURE: Global Variable Engine & Dynamic Universe Aggregation

# ==============================================================================
# 1. THE TARGET UNIVERSES (Cascading Matrix)
# ==============================================================================

MACRO_ASSETS = [
    "SPY", "QQQ", "IWM", "DIA", # Core Equities
    "USO", "GLD", "SLV", "DBC", # Commodities
    "TLT", "UUP"                # Bonds & Dollar
]

SECTORS = [
    "XLK", # Tech
    "XLF", # Financials
    "XLV", # Healthcare
    "XLE", # Energy
    "XLY", # Consumer Discretionary
    "XLI", # Industrials
    "XLP", # Consumer Staples
    "XLU", # Utilities
    "XLB", # Materials
    "XLRE" # Real Estate
]

SUBSECTORS = [
    "SMH",  # Semiconductors (Highly Liquid)
    "XBI",  # Biotech (Speculative Risk Proxy)
    "KRE",  # Regional Banks (Domestic Credit Health)
    "ITB",  # Homebuilders (Interest Rate Sensitivity)
    "XOP",  # Oil & Gas Exploration
    "OIH",  # Oil Services
    "XRT",  # Retail
    "IYT",  # Transports (Dow Theory)
    "ITA",  # Aerospace & Defense
    "CIBR", # Cybersecurity
    "URA",  # Uranium / Nuclear
    "COPX", # Copper Miners (Global Growth Proxy)
    "GDX"   # Gold Miners
]

# The AI Supply Chain Matrix
AI_THEMATIC = [
    "NVDA", "AMD",          # Tier 1: Core Compute GPUs
    "AVGO", "MRVL",         # Tier 2: Custom Silicon & ASICs
    "ANET", "COHR", "LITE", # Tier 3: Networking & Photonics/Optics
    "MU", "WDC",            # Tier 4: High Bandwidth Memory & Storage
    "TSM", "ASML", "AMAT",  # Tier 5: Foundries & CapEx Equipment
    "VRT", "ETN",           # Tier 6: Power, Liquid Cooling, Infrastructure
    "PLTR", "ARM", "CRWD"   # Tier 7: Data, IP, & Endpoint Security
]

CRYPTO_THEMATIC = [
    "IBIT", # Bitcoin Spot Proxy
    "MSTR", # Corporate Treasury Proxy
    "COIN", # Exchange/Infrastructure
    "MARA"  # Miners
]

# ==============================================================================
# 2. DYNAMIC AGGREGATION (The Lieutenants)
# ==============================================================================
# Automatically compiles all unique tickers above into the master radar scan list.
_all_targets = MACRO_ASSETS + SECTORS + SUBSECTORS + AI_THEMATIC + CRYPTO_THEMATIC
LIEUTENANTS = list(dict.fromkeys(_all_targets)) # Removes duplicates automatically

# ==============================================================================
# 3. RADAR PARAMETERS
# ==============================================================================
MIN_DONCHIAN_PROX = -2.0 
MIN_VOLUME_SPIKE = 1.5

FRED_API_KEY = "50ff1e637effabba2fe09afee01aae98"
