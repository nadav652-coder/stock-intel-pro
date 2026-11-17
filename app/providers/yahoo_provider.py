"""
Yahoo Finance Data Provider (Free, zero cost, extensive historical coverage).
Implements BaseDataProvider with automated caching and resilient error handling.
"""

from typing import Any, Dict, Optional
import yfinance as yf
import pandas as pd
import numpy as np
from app.providers.base import BaseDataProvider
from app.core.cache import cache
from app.core.config import settings

class YahooDataProvider(BaseDataProvider):
    def __init__(self):
        pass

    def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        cache_key = f"profile_{ticker}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info or {}

        quote_type = info.get("quoteType", "EQUITY")
        is_etf = quote_type == "ETF"
        etf_data = None

        if is_etf:
            top_holdings = []
            sector_weightings = {}
            try:
                fd = yf_ticker.funds_data
                if fd is not None:
                    top = getattr(fd, "top_holdings", None)
                    if top is not None and hasattr(top, "iterrows"):
                        for sym, row in top.iterrows():
                            pct = row.get("Holding Percent", 0)
                            top_holdings.append({
                                "symbol": str(sym),
                                "name": str(row.get("Name", sym)),
                                "percent": round(float(pct) * 100, 2) if pct else 0.0
                            })
                    sw = getattr(fd, "sector_weightings", None)
                    if isinstance(sw, dict):
                        for k, v in sw.items():
                            if v and v > 0:
                                sector_weightings[k.replace("_", " ").title()] = round(float(v) * 100, 1)
            except Exception as e:
                print(f"[YahooProvider] ETF funds_data note for {ticker}: {e}")

            raw_exp = info.get("netExpenseRatio") or info.get("annualReportExpenseRatio")
            if raw_exp is not None:
                exp_ratio = round(float(raw_exp), 3) if float(raw_exp) < 1.0 else round(float(raw_exp) / 100.0, 3)
            else:
                exp_ratio = None

            etf_data = {
                "category": info.get("category", "N/A"),
                "expense_ratio": exp_ratio,
                "aum": info.get("totalAssets"),
                "yield": round(float(info.get("yield") or 0.0) * 100, 2) if info.get("yield") else None,
                "top_holdings": top_holdings,
                "sector_weightings": sector_weightings
            }

        # Profile extraction with robust fallbacks
        profile = {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "quote_type": quote_type,
            "is_etf": is_etf,
            "etf_data": etf_data,
            "sector": "קרן סל מחקה מדד (ETF)" if is_etf else info.get("sector", "N/A"),
            "industry": info.get("category", "N/A") if is_etf else info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "website": info.get("website", ""),
            "summary": info.get("longBusinessSummary", ""),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("totalAssets") if is_etf else info.get("marketCap"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "dividend_yield": info.get("yield") if is_etf else info.get("dividendYield"),
            "beta": info.get("beta3Year") or info.get("beta"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "full_time_employees": info.get("fullTimeEmployees"),
            "exchange": info.get("exchange", "US"),
        }

        cache.set(cache_key, profile, ttl=settings.CACHE_TTL_SECONDS)
        return profile

    def get_historical_prices(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        ticker = ticker.upper().strip()
        cache_key = f"hist_{ticker}_{period}"
        cached = cache.get(cache_key)
        if cached:
            df = pd.DataFrame(cached)
            if not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            return df

        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(period=period)
        if df.empty:
            return pd.DataFrame()

        # Clean index and tz
        df = df.copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Cache as records
        cache_data = df.reset_index().to_dict(orient="records")
        cache.set(cache_key, cache_data, ttl=settings.CACHE_TTL_SECONDS)
        return df

    def get_financial_statements(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        cache_key = f"financials_{ticker}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        yf_ticker = yf.Ticker(ticker)
        
        def df_to_dict(df):
            if df is None or df.empty:
                return {}
            # Columns are dates, convert to string
            clean_df = df.copy()
            clean_df.columns = [str(c)[:10] for c in clean_df.columns]
            return clean_df.to_dict(orient="index")

        financials = {
            "income_statement": df_to_dict(yf_ticker.financials),
            "quarterly_income_statement": df_to_dict(yf_ticker.quarterly_financials),
            "balance_sheet": df_to_dict(yf_ticker.balance_sheet),
            "quarterly_balance_sheet": df_to_dict(yf_ticker.quarterly_balance_sheet),
            "cashflow": df_to_dict(yf_ticker.cashflow),
            "quarterly_cashflow": df_to_dict(yf_ticker.quarterly_cashflow),
            "raw_info": yf_ticker.info or {}
        }

        cache.set(cache_key, financials, ttl=settings.CACHE_TTL_SECONDS)
        return financials

    def get_benchmark_prices(self, benchmark_ticker: str = settings.DEFAULT_BENCHMARK, period: str = "5y") -> pd.DataFrame:
        return self.get_historical_prices(benchmark_ticker, period=period)
