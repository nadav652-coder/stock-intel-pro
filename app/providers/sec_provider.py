"""
SEC EDGAR Data & Filing Integration.
Provides direct links and automatic CIK resolution to official US SEC filings (10-K, 10-Q).
Primary, audited, zero-cost official source for US equities.
"""

from typing import Dict, Any, Optional
import requests
import time
from app.core.cache import cache

# Fallback mapping for top popular US tickers in case of offline/network issues
BUILTIN_CIK_MAP = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
    "INTC": "0000050863",
    "TSLA": "0001318605",
    "AMD": "0000002488",
    "NFLX": "0001065280",
    "BRK-B": "0001067983",
    "BRK-A": "0001067983",
    "JPM": "0000019617",
    "V": "0001403161",
    "JNJ": "0000200406",
    "WMT": "0000104169",
    "PG": "0000080424"
}

class SECProvider:
    _cik_cache: Optional[Dict[str, str]] = None
    _last_fetched: float = 0

    @classmethod
    def _load_cik_mapping(cls) -> Dict[str, str]:
        now = time.time()
        # Refresh cache once every 24 hours
        if cls._cik_cache and (now - cls._last_fetched < 86400):
            return cls._cik_cache

        # Check persistent cache
        cached_map = cache.get("sec_cik_full_map")
        if cached_map and isinstance(cached_map, dict):
            cls._cik_cache = cached_map
            cls._last_fetched = now
            return cached_map

        # Fetch official SEC company_tickers.json
        headers = {"User-Agent": "StockIntelPlatform ResearchApp/1.0 (contact@stockintel.local)"}
        try:
            res = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                mapping = {}
                for item in data.values():
                    ticker_sym = str(item.get("ticker", "")).upper()
                    cik_num = item.get("cik_str")
                    if ticker_sym and cik_num:
                        mapping[ticker_sym] = str(cik_num).zfill(10)
                
                # Merge with builtins
                mapping.update(BUILTIN_CIK_MAP)
                cls._cik_cache = mapping
                cls._last_fetched = now
                cache.set("sec_cik_full_map", mapping, ttl=86400)
                return mapping
        except Exception as e:
            print(f"[SECProvider] Note: Could not fetch remote SEC CIK map ({e}). Using built-in dictionary.")

        cls._cik_cache = BUILTIN_CIK_MAP.copy()
        cls._last_fetched = now
        return cls._cik_cache

    @classmethod
    def get_cik(cls, ticker: str) -> Optional[str]:
        ticker = ticker.upper().strip()
        mapping = cls._load_cik_mapping()
        return mapping.get(ticker)

    @classmethod
    def get_sec_filing_url(cls, ticker: str) -> str:
        """
        Returns exact direct URL to company filings on SEC EDGAR.
        Uses 10-digit CIK if found, otherwise falls back to SEC EDGAR search query.
        """
        ticker = ticker.upper().strip()
        cik = cls.get_cik(ticker)
        if cik:
            return f"https://www.sec.gov/edgar/browse/?CIK={cik}"
        # Fallback to general EDGAR Search for the symbol
        return f"https://www.sec.gov/edgar/search/#/q={ticker}"

    @classmethod
    def get_filing_info(cls, ticker: str) -> Dict[str, Any]:
        """Provides metadata for official SEC compliance verification."""
        ticker = ticker.upper().strip()
        cik = cls.get_cik(ticker)
        filings_url = cls.get_sec_filing_url(ticker)
        
        return {
            "source": "U.S. Securities and Exchange Commission (SEC EDGAR)",
            "cik": cik,
            "filings_url": filings_url,
            "is_us_listed": not ticker.endswith((".TA", ".L", ".PA", ".DE", ".TO")),
            "description": f"דוחות כספיים מבוקרים ראשוניים ב-SEC (10-K שנתי, 10-Q רבעוני)" + (f" | CIK: {cik}" if cik else "")
        }
