"""
Yahoo Finance Data Provider (Free, zero cost, extensive historical coverage).
Implements BaseDataProvider with automated caching, crumb-authenticated quoteSummary,
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
        self._crumb: Optional[str] = None

    def _get_crumb(self) -> Optional[str]:
        """Obtain Yahoo Finance authorization crumb and cookie session."""
        if self._crumb:
            return self._crumb
        try:
            self.session.get("https://fc.yahoo.com", timeout=8)
            r = self.session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=8)
            if r.status_code == 200 and r.text.strip():
                self._crumb = r.text.strip()
                return self._crumb
        except Exception as e:
            print(f"[YahooProvider] Crumb retrieval note: {e}")
        return None

    def _fetch_quote_summary(self, ticker: str) -> Dict[str, Any]:
        """Fetch rich institutional modules via Yahoo quoteSummary endpoint."""
        ticker = ticker.upper().strip()
        crumb = self._get_crumb()
        modules = "summaryDetail,financialData,defaultKeyStatistics,assetProfile,fundProfile,topHoldings,incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory"
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={modules}"
        if crumb:
            url += f"&crumb={crumb}"
        try:
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                results = res.json().get("quoteSummary", {}).get("result", [])
                if results:
                    return results[0]
        except Exception as e:
            print(f"[YahooProvider] quoteSummary error for {ticker}: {e}")
        return {}

    def _flatten_quote_summary(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested Yahoo {'raw': x, 'fmt': y} objects into a clean dictionary."""
        flat: Dict[str, Any] = {}
        for mod in ["summaryDetail", "financialData", "defaultKeyStatistics", "assetProfile", "fundProfile"]:
            mod_data = summary_data.get(mod, {})
            if isinstance(mod_data, dict):
                for k, v in mod_data.items():
                    if isinstance(v, dict):
                        flat[k] = v.get("raw", v.get("fmt", None))
                    else:
                        flat[k] = v
        return flat

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

        summary_data = self._fetch_quote_summary(ticker)
        flat_info = self._flatten_quote_summary(summary_data)

        # Always fetch chart data for rock-solid current price & 52-week stats
        fallback_meta, _ = self._fetch_chart_fallback(ticker, range_period="1mo")

        quote_type = (
            flat_info.get("quoteType")
            or fallback_meta.get("instrumentType")
            or ("ETF" if "fundProfile" in summary_data else "EQUITY")
        )
        is_etf = quote_type == "ETF"
        etf_data = None

        if is_etf:
            top_holdings = []
            sector_weightings = {}
            th_data = summary_data.get("topHoldings", {})
            if isinstance(th_data, dict):
                holdings_list = th_data.get("holdings", [])
                for h in holdings_list:
                    pct = h.get("holdingPercent", {})
                    pct_val = pct.get("raw", 0) if isinstance(pct, dict) else (pct or 0)
                    top_holdings.append({
                        "symbol": str(h.get("symbol", "")),
                        "name": str(h.get("holdingName", h.get("symbol", ""))),
                        "percent": round(float(pct_val) * 100, 2)
                    })
                sw_list = th_data.get("sectorWeightings", [])
                if isinstance(sw_list, list):
                    for sw in sw_list:
                        for k, v in sw.items():
                            v_val = v.get("raw", v) if isinstance(v, dict) else v
                            if v_val and float(v_val) > 0:
                                sector_weightings[k.replace("_", " ").title()] = round(float(v_val) * 100, 1)

            fp = summary_data.get("fundProfile", {})
            exp_ratio_val = (
                fp.get("feesExpensesInvestment", {}).get("annualReportExpenseRatio", {}).get("raw")
                if isinstance(fp.get("feesExpensesInvestment"), dict) else None
            )
            if exp_ratio_val is not None:
                exp_ratio = round(float(exp_ratio_val), 3) if float(exp_ratio_val) < 1.0 else round(float(exp_ratio_val) / 100.0, 3)
            else:
                exp_ratio = flat_info.get("netExpenseRatio") or flat_info.get("annualReportExpenseRatio")

            etf_data = {
                "category": fp.get("categoryName") or flat_info.get("category", "קרן סל מחקה מדד"),
                "expense_ratio": exp_ratio,
                "aum": flat_info.get("totalAssets") or flat_info.get("marketCap"),
                "yield": round(float(flat_info.get("yield") or 0.0) * 100, 2) if flat_info.get("yield") else None,
                "top_holdings": top_holdings,
                "sector_weightings": sector_weightings
            }

        curr_price = (
            fallback_meta.get("regularMarketPrice")
            or flat_info.get("currentPrice")
            or flat_info.get("regularMarketPrice")
            or fallback_meta.get("chartPreviousClose")
            or flat_info.get("previousClose")
        )

        name = (
            flat_info.get("shortName")
            or flat_info.get("longName")
            or fallback_meta.get("shortName")
            or fallback_meta.get("longName")
            or ticker
        )

        profile = {
            "ticker": ticker,
            "name": name,
            "quote_type": quote_type,
            "is_etf": is_etf,
            "etf_data": etf_data,
            "sector": "קרן סל מחקה מדד (ETF)" if is_etf else flat_info.get("sector", "N/A"),
            "industry": flat_info.get("category", "N/A") if is_etf else flat_info.get("industry", "N/A"),
            "country": flat_info.get("country", "N/A"),
            "website": flat_info.get("website", ""),
            "summary": flat_info.get("longBusinessSummary", ""),
            "currency": flat_info.get("currency") or fallback_meta.get("currency", "USD"),
            "market_cap": flat_info.get("totalAssets") if is_etf else (flat_info.get("marketCap") or fallback_meta.get("marketCap")),
            "current_price": round(float(curr_price), 2) if curr_price is not None else None,
            "day_high": flat_info.get("dayHigh") or fallback_meta.get("regularMarketDayHigh"),
            "day_low": flat_info.get("dayLow") or fallback_meta.get("regularMarketDayLow"),
            "fifty_two_week_high": flat_info.get("fiftyTwoWeekHigh") or fallback_meta.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": flat_info.get("fiftyTwoWeekLow") or fallback_meta.get("fiftyTwoWeekLow"),
            "dividend_yield": flat_info.get("yield") if is_etf else flat_info.get("dividendYield"),
            "beta": flat_info.get("beta3Year") or flat_info.get("beta"),
            "shares_outstanding": flat_info.get("sharesOutstanding"),
            "full_time_employees": flat_info.get("fullTimeEmployees"),
            "exchange": flat_info.get("exchange") or fallback_meta.get("exchangeName", "US"),
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

        # Primary high-speed direct chart API
        _, df = self._fetch_chart_fallback(ticker, range_period=period)

        # Secondary yfinance fallback if needed
        if df is None or df.empty:
            try:
                yf_ticker = yf.Ticker(ticker, session=self.session)
                df = yf_ticker.history(period=period)
            except Exception as e:
                print(f"[YahooProvider] yfinance history error for {ticker}: {e}")

        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        cache_data = df.reset_index().to_dict(orient="records")
        cache.set(cache_key, cache_data, ttl=settings.CACHE_TTL_SECONDS)
        return df

    def get_financial_statements(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        cache_key = f"financials_{ticker}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        summary_data = self._fetch_quote_summary(ticker)
        flat_info = self._flatten_quote_summary(summary_data)

        def parse_statement_history(history_list):
            if not history_list or not isinstance(history_list, list):
                return {}
            result = {}
            for period_dict in history_list:
                end_date = period_dict.get("endDate", {})
                date_str = end_date.get("fmt", str(end_date.get("raw", "")))[:10]
                if not date_str:
                    continue
                col_data = {}
                for k, v in period_dict.items():
                    if k == "endDate":
                        continue
                    val = v.get("raw", v.get("fmt")) if isinstance(v, dict) else v
                    col_data[k] = val
                result[date_str] = col_data
            return result

        inc_dict = parse_statement_history(summary_data.get("incomeStatementHistory", {}).get("incomeStatementHistory", []))
        bal_dict = parse_statement_history(summary_data.get("balanceSheetHistory", {}).get("balanceSheetStatements", []))
        cf_dict = parse_statement_history(summary_data.get("cashflowStatementHistory", {}).get("cashflowStatements", []))

        # Merge with yfinance statements if available
        try:
            yf_ticker = yf.Ticker(ticker, session=self.session)
            def df_to_dict(df):
                if df is None or df.empty:
                    return {}
                clean_df = df.copy()
                clean_df.columns = [str(c)[:10] for c in clean_df.columns]
                return clean_df.to_dict(orient="index")

            if not inc_dict:
                inc_dict = df_to_dict(yf_ticker.financials)
            if not bal_dict:
                bal_dict = df_to_dict(yf_ticker.balance_sheet)
            if not cf_dict:
                cf_dict = df_to_dict(yf_ticker.cashflow)
            
            # Combine yfinance info if quoteSummary missed anything
            if yf_ticker.info:
                flat_info = {**yf_ticker.info, **flat_info}
        except Exception as e:
            print(f"[YahooProvider] yfinance extra statements note: {e}")

        financials = {
            "income_statement": inc_dict,
            "quarterly_income_statement": {},
            "balance_sheet": bal_dict,
            "quarterly_balance_sheet": {},
            "cashflow": cf_dict,
            "quarterly_cashflow": {},
            "raw_info": flat_info
        }

        cache.set(cache_key, financials, ttl=settings.CACHE_TTL_SECONDS)
        return financials

    def get_benchmark_prices(self, benchmark_ticker: str = settings.DEFAULT_BENCHMARK, period: str = "5y") -> pd.DataFrame:
        return self.get_historical_prices(benchmark_ticker, period=period)
