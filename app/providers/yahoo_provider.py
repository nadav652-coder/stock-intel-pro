"""
Yahoo Finance Data Provider (Free, zero cost, extensive historical coverage).
Implements BaseDataProvider with automated caching, crumb-authenticated quoteSummary,
funds_data ETF analysis, and resilient direct-API fallbacks for 100% uptime on cloud environments.
"""

from typing import Any, Dict, Optional, Tuple, List
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from app.providers.base import BaseDataProvider
from app.core.cache import cache
from app.core.config import settings

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Curated fallback for popular index and sector ETFs if external endpoints fail on cloud
ETF_CURATED_FALLBACK = {
    "SPY": {
        "category": "קרן סל מחקה מדד S&P 500",
        "expense_ratio": 0.09,
        "yield": 1.25,
        "aum": 610000000000,
        "top_holdings": [
            {"symbol": "AAPL", "name": "Apple Inc.", "percent": 7.70},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "percent": 7.58},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "percent": 5.93},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "percent": 3.61},
            {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "percent": 2.51},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "percent": 2.38},
            {"symbol": "META", "name": "Meta Platforms Inc.", "percent": 2.08},
            {"symbol": "GOOG", "name": "Alphabet Inc. Class C", "percent": 2.02},
            {"symbol": "LLY", "name": "Eli Lilly and Company", "percent": 1.74},
            {"symbol": "TSLA", "name": "Tesla Inc.", "percent": 1.73},
        ],
        "sector_weightings": {
            "טכנולוגיה": 38.2,
            "שירותים פיננסיים": 12.0,
            "בריאות ופארמה": 10.3,
            "צריכה מחזורית": 9.2,
            "שירותי תקשורת": 8.4,
            "תעשייה": 7.6,
            "צריכה בסיסית": 4.9,
            "אנרגיה": 3.9,
            "תשתיות וחשמל": 2.1,
            "נדל\"ן": 1.8,
            "חומרי גלם": 1.6
        }
    },
    "QQQ": {
        "category": "קרן סל מחקה מדד נאסד\"ק 100",
        "expense_ratio": 0.20,
        "yield": 0.58,
        "aum": 315000000000,
        "top_holdings": [
            {"symbol": "AAPL", "name": "Apple Inc.", "percent": 9.10},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "percent": 8.80},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "percent": 8.10},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "percent": 5.30},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "percent": 4.60},
            {"symbol": "META", "name": "Meta Platforms Inc.", "percent": 4.50},
            {"symbol": "TSLA", "name": "Tesla Inc.", "percent": 3.40},
            {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "percent": 2.80},
            {"symbol": "GOOG", "name": "Alphabet Inc. Class C", "percent": 2.70},
            {"symbol": "COST", "name": "Costco Wholesale Corp.", "percent": 2.50},
        ],
        "sector_weightings": {
            "טכנולוגיה": 59.0,
            "שירותי תקשורת": 15.2,
            "צריכה מחזורית": 13.1,
            "בריאות": 6.2,
            "צריכה בסיסית": 4.1,
            "תעשייה": 2.4
        }
    },
    "VOO": {
        "category": "קרן סל מחקה מדד S&P 500 (Vanguard)",
        "expense_ratio": 0.03,
        "yield": 1.30,
        "aum": 550000000000,
        "top_holdings": [
            {"symbol": "AAPL", "name": "Apple Inc.", "percent": 7.70},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "percent": 7.58},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "percent": 5.93},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "percent": 3.61},
            {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "percent": 2.51},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "percent": 2.38},
            {"symbol": "META", "name": "Meta Platforms Inc.", "percent": 2.08},
            {"symbol": "GOOG", "name": "Alphabet Inc. Class C", "percent": 2.02},
            {"symbol": "LLY", "name": "Eli Lilly and Company", "percent": 1.74},
            {"symbol": "TSLA", "name": "Tesla Inc.", "percent": 1.73},
        ],
        "sector_weightings": {
            "טכנולוגיה": 38.2,
            "שירותים פיננסיים": 12.0,
            "בריאות": 10.3,
            "צריכה מחזורית": 9.2,
            "שירותי תקשורת": 8.4
        }
    },
    "DIA": {
        "category": "קרן סל מחקה מדד דאו ג'ונס 30",
        "expense_ratio": 0.16,
        "yield": 1.75,
        "aum": 36000000000,
        "top_holdings": [
            {"symbol": "GS", "name": "Goldman Sachs Group Inc.", "percent": 8.10},
            {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "percent": 7.80},
            {"symbol": "MSFT", "name": "Microsoft Corp.", "percent": 6.50},
            {"symbol": "HD", "name": "Home Depot Inc.", "percent": 6.10},
            {"symbol": "CAT", "name": "Caterpillar Inc.", "percent": 5.80},
            {"symbol": "AMGN", "name": "Amgen Inc.", "percent": 4.90},
            {"symbol": "V", "name": "Visa Inc.", "percent": 4.70},
            {"symbol": "MCD", "name": "McDonald's Corp.", "percent": 4.60},
            {"symbol": "CRM", "name": "Salesforce Inc.", "percent": 4.50},
            {"symbol": "BA", "name": "Boeing Co.", "percent": 3.80}
        ],
        "sector_weightings": {
            "שירותים פיננסיים": 23.4,
            "בריאות": 19.1,
            "טכנולוגיה": 18.5,
            "תעשייה": 14.8,
            "צריכה מחזורית": 13.9
        }
    },
    "IWM": {
        "category": "קרן סל מחקה מדד ראסל 2000 (חברות קטנות)",
        "expense_ratio": 0.19,
        "yield": 1.35,
        "aum": 72000000000,
        "top_holdings": [
            {"symbol": "FTAI", "name": "FTAI Aviation Ltd.", "percent": 0.65},
            {"symbol": "VRT", "name": "Vertiv Holdings Co.", "percent": 0.58},
            {"symbol": "SMR", "name": "NuScale Power Corp.", "percent": 0.52},
            {"symbol": "SFM", "name": "Sprouts Farmers Market Inc.", "percent": 0.49},
            {"symbol": "FN", "name": "Fabrinet", "percent": 0.46}
        ],
        "sector_weightings": {
            "תעשייה": 18.2,
            "שירותים פיננסיים": 16.5,
            "בריאות": 14.8,
            "טכנולוגיה": 13.9,
            "צריכה מחזורית": 11.2
        }
    },
    "SCHD": {
        "category": "קרן סל מניות דיבידנד איכותיות (Schwab U.S. Dividend)",
        "expense_ratio": 0.06,
        "yield": 3.40,
        "aum": 65000000000,
        "top_holdings": [
            {"symbol": "HD", "name": "Home Depot Inc.", "percent": 4.30},
            {"symbol": "CSCO", "name": "Cisco Systems Inc.", "percent": 4.20},
            {"symbol": "CVX", "name": "Chevron Corp.", "percent": 4.10},
            {"symbol": "ABBV", "name": "AbbVie Inc.", "percent": 4.00},
            {"symbol": "TXN", "name": "Texas Instruments Inc.", "percent": 3.90}
        ],
        "sector_weightings": {
            "פיננסים": 17.5,
            "בריאות": 16.0,
            "צריכה בסיסית": 14.2,
            "תעשייה": 13.8,
            "אנרגיה": 12.1
        }
    },
    "SMH": {
        "category": "קרן סל מוליכים למחצה ושבבים (VanEck Semiconductor)",
        "expense_ratio": 0.35,
        "yield": 0.45,
        "aum": 28000000000,
        "top_holdings": [
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "percent": 20.50},
            {"symbol": "TSM", "name": "Taiwan Semiconductor (TSMC)", "percent": 12.80},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "percent": 7.40},
            {"symbol": "ASML", "name": "ASML Holding NV", "percent": 4.90},
            {"symbol": "AMD", "name": "Advanced Micro Devices", "percent": 4.60}
        ],
        "sector_weightings": {
            "טכנולוגיה ושבבים": 99.5
        }
    }
}

class YahooDataProvider(BaseDataProvider):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._crumb: Optional[str] = None

    def _get_crumb(self) -> Optional[str]:
        """Obtain Yahoo Finance authorization crumb and cookie session."""
        if self._crumb:
            return self._crumb
        try:
            self.session.get("https://fc.yahoo.com", timeout=6)
            for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
                try:
                    r = self.session.get(f"https://{host}/v1/test/getcrumb", timeout=6)
                    if r.status_code == 200 and r.text.strip() and "<" not in r.text:
                        self._crumb = r.text.strip()
                        return self._crumb
                except Exception:
                    pass
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

        # Fallback to yfinance standalone info if quoteSummary returned sparse data
        try:
            yf_obj = yf.Ticker(ticker)
            if not flat_info or not flat_info.get("trailingPE"):
                yf_info = getattr(yf_obj, "info", None)
                if yf_info and isinstance(yf_info, dict):
                    for k, v in yf_info.items():
                        if k not in flat_info or flat_info[k] is None:
                            flat_info[k] = v

            # Always enrich with lightweight fast_info for market stats
            fi = getattr(yf_obj, "fast_info", None)
            if fi:
                if not flat_info.get("previousClose") and hasattr(fi, "previous_close"):
                    flat_info["previousClose"] = fi.previous_close
                if not flat_info.get("open") and hasattr(fi, "open"):
                    flat_info["open"] = fi.open
                if not flat_info.get("dayHigh") and hasattr(fi, "day_high"):
                    flat_info["dayHigh"] = fi.day_high
                if not flat_info.get("dayLow") and hasattr(fi, "day_low"):
                    flat_info["dayLow"] = fi.day_low
                if not flat_info.get("fiftyTwoWeekHigh") and hasattr(fi, "year_high"):
                    flat_info["fiftyTwoWeekHigh"] = fi.year_high
                if not flat_info.get("fiftyTwoWeekLow") and hasattr(fi, "year_low"):
                    flat_info["fiftyTwoWeekLow"] = fi.year_low
                if not flat_info.get("marketCap") and hasattr(fi, "market_cap"):
                    flat_info["marketCap"] = fi.market_cap
                if not flat_info.get("volume") and hasattr(fi, "last_volume"):
                    flat_info["volume"] = fi.last_volume
                if not flat_info.get("averageVolume") and hasattr(fi, "three_month_average_volume"):
                    flat_info["averageVolume"] = fi.three_month_average_volume
        except Exception as e:
            print(f"[YahooProvider] yf.info / fast_info fallback note for {ticker}: {e}")

        # Always fetch chart data for rock-solid current price & 52-week stats
        fallback_meta, _ = self._fetch_chart_fallback(ticker, range_period="1mo")

        quote_type = (
            flat_info.get("quoteType")
            or fallback_meta.get("instrumentType")
            or ("ETF" if "fundProfile" in summary_data or ticker in ETF_CURATED_FALLBACK else "EQUITY")
        )
        is_etf = quote_type == "ETF"
        etf_data = None

        if is_etf:
            top_holdings: List[Dict[str, Any]] = []
            sector_weightings: Dict[str, float] = {}

            # 1. Try summaryData topHoldings
            th_data = summary_data.get("topHoldings", {})
            if isinstance(th_data, dict) and th_data.get("holdings"):
                for h in th_data.get("holdings", []):
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

            # 2. Try yfinance funds_data
            if not top_holdings:
                try:
                    yf_t = yf.Ticker(ticker)
                    fd = getattr(yf_t, "funds_data", None)
                    if fd:
                        if hasattr(fd, "top_holdings") and fd.top_holdings is not None and not fd.top_holdings.empty:
                            for sym, row in fd.top_holdings.head(10).iterrows():
                                h_pct = float(row.get("Holding Percent", 0.0) or 0.0)
                                top_holdings.append({
                                    "symbol": str(sym),
                                    "name": str(row.get("Name", sym)),
                                    "percent": round(h_pct * 100.0, 2) if h_pct < 1.0 else round(h_pct, 2)
                                })
                        if hasattr(fd, "sector_weightings") and fd.sector_weightings:
                            for k, v in fd.sector_weightings.items():
                                if v and float(v) > 0:
                                    k_clean = k.replace("_", " ").title()
                                    sector_weightings[k_clean] = round(float(v) * 100.0, 1) if float(v) < 1.0 else round(float(v), 1)
                except Exception as e:
                    print(f"[YahooProvider] funds_data note for {ticker}: {e}")

            # 3. Fallback to curated ETF registry
            if not top_holdings and ticker in ETF_CURATED_FALLBACK:
                curated = ETF_CURATED_FALLBACK[ticker]
                top_holdings = curated.get("top_holdings", [])
                sector_weightings = curated.get("sector_weightings", {})

            fp = summary_data.get("fundProfile", {})
            exp_ratio_val = (
                fp.get("feesExpensesInvestment", {}).get("annualReportExpenseRatio", {}).get("raw")
                if isinstance(fp.get("feesExpensesInvestment"), dict) else None
            )
            if exp_ratio_val is not None:
                exp_ratio = round(float(exp_ratio_val), 3) if float(exp_ratio_val) < 1.0 else round(float(exp_ratio_val) / 100.0, 3)
            else:
                exp_ratio = flat_info.get("netExpenseRatio") or flat_info.get("annualReportExpenseRatio")

            if exp_ratio is None and ticker in ETF_CURATED_FALLBACK:
                exp_ratio = ETF_CURATED_FALLBACK[ticker].get("expense_ratio")

            cat_name = fp.get("categoryName") or flat_info.get("category")
            if (not cat_name or cat_name == "N/A") and ticker in ETF_CURATED_FALLBACK:
                cat_name = ETF_CURATED_FALLBACK[ticker].get("category")

            aum_val = (
                flat_info.get("totalAssets")
                or flat_info.get("netAssets")
                or flat_info.get("marketCap")
                or fallback_meta.get("marketCap")
                or ETF_CURATED_FALLBACK.get(ticker, {}).get("aum")
            )

            etf_data = {
                "category": cat_name or "קרן סל מחקה מדד",
                "expense_ratio": exp_ratio,
                "aum": aum_val,
                "yield": round(float(flat_info.get("yield") or 0.0) * 100, 2) if flat_info.get("yield") else (ETF_CURATED_FALLBACK.get(ticker, {}).get("yield")),
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

        mcap_val = (
            etf_data.get("aum") if is_etf and etf_data else
            (flat_info.get("totalAssets") if is_etf else (flat_info.get("marketCap") or fallback_meta.get("marketCap") or ETF_CURATED_FALLBACK.get(ticker, {}).get("aum")))
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
            "market_cap": mcap_val,
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
            "previous_close": flat_info.get("previousClose") or fallback_meta.get("regularMarketPreviousClose") or fallback_meta.get("chartPreviousClose"),
            "open": flat_info.get("open") or fallback_meta.get("regularMarketOpen"),
            "volume": flat_info.get("volume") or flat_info.get("last_volume") or fallback_meta.get("regularMarketVolume"),
            "average_volume": flat_info.get("averageVolume") or flat_info.get("three_month_average_volume"),
            "trailing_pe": flat_info.get("trailingPE"),
            "forward_pe": flat_info.get("forwardPE"),
            "eps": flat_info.get("trailingEps"),
            "target_price": flat_info.get("targetMeanPrice") or flat_info.get("targetMedianPrice"),
        }

        cache.set(cache_key, profile, ttl=settings.CACHE_TTL_SECONDS)
        return profile

    def get_historical_prices(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        ticker = ticker.upper().strip()
        cache_key = f"hist_{ticker}_{period}"
        cached = cache.get(cache_key)
        if cached:
            df = pd.DataFrame(cached)
            date_col = "Date" if "Date" in df.columns else ("index" if "index" in df.columns else None)
            if not df.empty and date_col:
                df[date_col] = pd.to_datetime(df[date_col])
                df.set_index(date_col, inplace=True)
            return df

        # Primary high-speed direct chart API
        _, df = self._fetch_chart_fallback(ticker, range_period=period)

        # Secondary yfinance fallback if needed
        if df is None or df.empty:
            try:
                yf_ticker = yf.Ticker(ticker)
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

        # Merge with yfinance statements if quoteSummary was empty
        if not inc_dict or not bal_dict or not cf_dict or not flat_info.get("trailingPE"):
            try:
                yf_ticker = yf.Ticker(ticker)
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
                
                if yf_ticker.info:
                    for k, v in yf_ticker.info.items():
                        if k not in flat_info or flat_info[k] is None:
                            flat_info[k] = v
            except Exception as e:
                print(f"[YahooProvider] yfinance extra statements note for {ticker}: {e}")

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
