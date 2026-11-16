"""
Abstract Base Data Provider.
Defines the standard contract for fetching financial data, enabling future provider swapping
(e.g., Yahoo Finance, SEC EDGAR, Bloomberg, FactSet) without impacting business logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import pandas as pd

class BaseDataProvider(ABC):
    @abstractmethod
    def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Fetch general company profile, metadata, description, industry, sector."""
        pass

    @abstractmethod
    def get_historical_prices(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        """Fetch historical OHLCV price series."""
        pass

    @abstractmethod
    def get_financial_statements(self, ticker: str) -> Dict[str, Any]:
        """Fetch income statement, balance sheet, and cash flow statement."""
        pass

    @abstractmethod
    def get_benchmark_prices(self, benchmark_ticker: str = "^GSPC", period: str = "5y") -> pd.DataFrame:
        """Fetch benchmark index historical price series (default S&P 500)."""
        pass
