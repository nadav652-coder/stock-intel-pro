"""
Yahoo Finance Data Provider (Free, zero cost, extensive historical coverage).
Implements BaseDataProvider with automated caching, custom browser headers,
and resilient direct-API fallbacks for 100% uptime on cloud environments.
"""

from typing import Any, Dict, Optional, Tuple
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from app.providers.base import BaseDataProvider
from app.core.cache import cache
from app.core.config import settings

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

class YahooDataProvider(BaseDataProvider):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _fetch_chart_fallback(self, ticker: str, range_period: str = "5y") -> Tuple[Dict[str, Any], pd.DataFrame]:
        """Direct call to Yahoo v8 chart endpoint - requires no auth/crumb, ultra reliable."""
        ticker = ticker.upper().strip()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={range_period}"
        try:
            res = self.session.get(url, timeout=12)
            if res.status_code != 200:
                return {}, pd.DataFrame()
            json_data = res.json()
            results = json_data.get("chart", {}).get("result", [])
            if not results:
                return {}, pd.DataFrame()
            res_obj = results[0]
            meta = res_obj.get("meta", {})
            timestamps = res_obj.get("timestamp", [])
            indicators = res_obj.get("indicators", {}).get("quote", [{}])[0]
            if not timestamps:
                return meta, pd.DataFrame()
            df = pd.DataFrame({
                "Open": indicators.get("open", []),
                "High": indicators.get("high", []),
                "Low": indicators.get("low", []),
                "Close": indicators.get("close", []),
                "Volume": indicators.get("volume", [])
            }, index=pd.to_datetime(timestamps, unit="s"))
            df.dropna(subset=["Close"], inplace=True)
            return meta, df
        except Exception as e:
            print(f"[YahooProvider] Fallback chart error for {ticker}: {e}")
            return {}, pd.DataFrame()

    def get_company_profile(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        cache_key = f"profile_{ticker}"
        cached = cache.get(cache_key)
        if cached and cached.get("current_price"):
            return cached

        info: Dict[str, Any] = {}
        is_etf = False
        etf_data = None
        yf_ticker = None

        try:
            yf_ticker = yf.Ticker(ticker, session=self.session)
            info = yf_ticker.info or {}
        except Exception as e:
            print(f"[YahooProvider] yfinance info warning for {ticker}: {e}")

        # If yfinance failed to get price/name, use resilient direct chart API
        fallback_meta = {}
        if not info or not (info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")):
            fallback_meta, _ = self._fetch_chart_fallback(ticker, range_period="1mo")

        quote_type = info.get("quoteType") or fallback_meta.get("instrumentType", "EQUITY")
        is_etf = quote_type == "ETF"

        if is_etf and yf_ticker is not None:
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

        # Guaranteed price resolution
        curr_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
            or fallback_meta.get("regularMarketPrice")
            or fallback_meta.get("chartPreviousClose")
        )

        name = (
            info.get("shortName")
            or info.get("longName")
            or fallback_meta.get("shortName")
            or fallback_meta.get("longName")
            or ticker
        )

        # Profile extraction with robust fallbacks
        profile = {
            "ticker": ticker,
            "name": name,
            "quote_type": quote_type,
            "is_etf": is_etf,
            "etf_data": etf_data,
            "sector": "קרן סל מחקה מדד (ETF)" if is_etf else info.get("sector", "N/A"),
            "industry": info.get("category", "N/A") if is_etf else info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "website": info.get("website", ""),
            "summary": info.get("longBusinessSummary", ""),
            "currency": info.get("currency") or fallback_meta.get("currency", "USD"),
            "market_cap": info.get("totalAssets") if is_etf else info.get("marketCap"),
            "current_price": round(float(curr_price), 2) if curr_price is not None else None,
            "day_high": info.get("dayHigh") or fallback_meta.get("regularMarketDayHigh"),
            "day_low": info.get("dayLow") or fallback_meta.get("regularMarketDayLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh") or fallback_meta.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow") or fallback_meta.get("fiftyTwoWeekLow"),
            "dividend_yield": info.get("yield") if is_etf else info.get("dividendYield"),
            "beta": info.get("beta3Year") or info.get("beta"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "full_time_employees": info.get("fullTimeEmployees"),
            "exchange": info.get("exchange") or fallback_meta.get("exchangeName", "US"),
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

        df = pd.DataFrame()
        try:
            yf_ticker = yf.Ticker(ticker, session=self.session)
            df = yf_ticker.history(period=period)
        except Exception as e:
            print(f"[YahooProvider] yfinance history error for {ticker}: {e}")

        # Fallback to direct chart endpoint if yfinance returned empty
        if df is None or df.empty:
            _, df = self._fetch_chart_fallback(ticker, range_period=period)

        if df is None or df.empty:
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

        def df_to_dict(df):
            if df is None or df.empty:
                return {}
            clean_df = df.copy()
            clean_df.columns = [str(c)[:10] for c in clean_df.columns]
            return clean_df.to_dict(orient="index")

        try:
            yf_ticker = yf.Ticker(ticker, session=self.session)
            financials = {
                "income_statement": df_to_dict(yf_ticker.financials),
                "quarterly_income_statement": df_to_dict(yf_ticker.quarterly_financials),
                "balance_sheet": df_to_dict(yf_ticker.balance_sheet),
                "quarterly_balance_sheet": df_to_dict(yf_ticker.quarterly_balance_sheet),
                "cashflow": df_to_dict(yf_ticker.cashflow),
                "quarterly_cashflow": df_to_dict(yf_ticker.quarterly_cashflow),
                "raw_info": yf_ticker.info or {}
            }
        except Exception as e:
            print(f"[YahooProvider] financials error for {ticker}: {e}")
            financials = {
                "income_statement": {},
                "quarterly_income_statement": {},
                "balance_sheet": {},
                "quarterly_balance_sheet": {},
                "cashflow": {},
                "quarterly_cashflow": {},
                "raw_info": {}
            }

        cache.set(cache_key, financials, ttl=settings.CACHE_TTL_SECONDS)
        return financials

    def get_benchmark_prices(self, benchmark_ticker: str = settings.DEFAULT_BENCHMARK, period: str = "5y") -> pd.DataFrame:
        return self.get_historical_prices(benchmark_ticker, period=period)
