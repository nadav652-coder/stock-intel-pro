"""
Configuration module for the Stock Intelligence Platform.
Centralizes analytical assumptions, scoring weights, caching parameters and system settings.
"""

from dataclasses import dataclass
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DB_PATH = BASE_DIR / "cache.sqlite3"

@dataclass(frozen=True)
class Settings:
    APP_NAME: str = "מערכת חכמה לניתוח מניות ותיקי השקעות"
    APP_VERSION: str = "1.0.0 (MVP)"
    DEFAULT_BENCHMARK: str = "^GSPC"  # S&P 500
    CACHE_TTL_SECONDS: int = 3600  # 1 hour cache to prevent rate-limiting and maximize speed
    
    # Financial Modeling Defaults
    DEFAULT_RISK_FREE_RATE: float = 0.042  # ~4.2% US 10-Year Treasury Yield
    DEFAULT_MARKET_RISK_PREMIUM: float = 0.055  # Historical Equity Risk Premium (5.5%)
    DEFAULT_TERMINAL_GROWTH_RATE: float = 0.025  # Long-term GDP terminal growth (2.5%)
    DEFAULT_PROJECTION_YEARS: int = 5
    
    # Scoring Weights (Must sum to 1.0)
    WEIGHT_QUALITY: float = 0.25
    WEIGHT_VALUATION: float = 0.30
    WEIGHT_GROWTH: float = 0.25
    WEIGHT_RISK: float = 0.20
    
    # Simulation Parameters
    MONTE_CARLO_SIMULATIONS: int = 5000
    HISTORICAL_LOOKBACK_YEARS: int = 5

settings = Settings()
