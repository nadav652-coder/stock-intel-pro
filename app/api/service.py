"""
Analysis Service Layer.
Coordinates all providers, caching, and analytical engines to produce
a comprehensive, institutional-grade analysis payload.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
from app.providers.yahoo_provider import YahooDataProvider
from app.providers.sec_provider import SECProvider
from app.engines.fundamental import FundamentalEngine
from app.engines.valuation import ValuationEngine
from app.engines.risk import RiskEngine
from app.engines.forecast import ForecastEngine
from app.engines.synthesis import SynthesisEngine
from app.engines.reports_translator import ReportsTranslator
from app.engines.portfolio import PortfolioEngine
from app.core.cache import cache

class AnalysisService:
    def __init__(self):
        self.provider = YahooDataProvider()
        self.sec = SECProvider()

    def run_full_analysis(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        cache_key = f"full_analysis_{ticker}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # 1. Fetch raw data
        profile = self.provider.get_company_profile(ticker)
        financials = self.provider.get_financial_statements(ticker)
        raw_info = financials.get("raw_info", {})
        combined_info = {**raw_info, **profile}

        # Price histories
        stock_df = self.provider.get_historical_prices(ticker, period="5y")
        benchmark_df = self.provider.get_benchmark_prices(period="5y")

        # 2. Run Fundamental Engine
        fundamental = FundamentalEngine.analyze(combined_info, financials)

        # 3. Run Valuation Engine
        valuation = ValuationEngine.calculate_valuation(combined_info)

        # 4. Run Risk & Performance Engine
        risk = RiskEngine.analyze(stock_df, benchmark_df)

        # 5. Run Probabilistic Forecasting Engine
        forecast = ForecastEngine.simulate(stock_df, benchmark_df)

        # 6. Run Synthesis & Scoring Engine
        synthesis = SynthesisEngine.synthesize(profile, fundamental, valuation, risk, forecast)

        # 7. Official SEC metadata
        sec_info = self.sec.get_filing_info(ticker)

        # 8. Historical chart series (Sample last 250 trading days for frontend price chart)
        price_chart_data = []
        if not stock_df.empty:
            tail_stock = stock_df.tail(252)
            tail_bench = benchmark_df.tail(252) if not benchmark_df.empty else pd.DataFrame()
            
            # Normalize to 100 at start of period for visual return comparison
            stock_start = tail_stock["Close"].iloc[0] if len(tail_stock) > 0 else 1.0
            bench_start = tail_bench["Close"].iloc[0] if len(tail_bench) > 0 else 1.0

            for date_idx, row in tail_stock.iterrows():
                date_str = str(date_idx)[:10]
                st_close = float(row["Close"])
                st_norm = round(((st_close / stock_start) - 1.0) * 100.0, 2)
                
                # Align benchmark
                bm_norm = 0.0
                if not tail_bench.empty and date_idx in tail_bench.index:
                    bm_close = float(tail_bench.loc[date_idx]["Close"])
                    bm_norm = round(((bm_close / bench_start) - 1.0) * 100.0, 2)

                price_chart_data.append({
                    "date": date_str,
                    "price": round(st_close, 2),
                    "stock_pct": st_norm,
                    "benchmark_pct": bm_norm
                })

        # 9. Translated Financial Statements & SEC Key Sections
        translated_reports = ReportsTranslator.generate_full_reports(financials, profile)

        payload = {
            "ticker": ticker,
            "profile": profile,
            "sec_info": sec_info,
            "fundamental": fundamental,
            "valuation": valuation,
            "risk": risk,
            "forecast": forecast,
            "synthesis": synthesis,
            "price_chart_data": price_chart_data,
            "translated_reports": translated_reports
        }

        # Cache full payload for 1 hour
        cache.set(cache_key, payload, ttl=3600)
        return payload

    def get_financial_reports(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        profile = self.provider.get_company_profile(ticker)
        financials = self.provider.get_financial_statements(ticker)
        return ReportsTranslator.generate_full_reports(financials, profile)

    def analyze_portfolio(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Runs full portfolio analysis across multiple stocks and ETFs."""
        prices_map = {}
        betas_map = {}
        sectors_map = {}
        scores_map = {}
        history_map = {}

        for h in holdings:
            ticker = h.get("ticker", "").upper().strip()
            if not ticker:
                continue
            try:
                prof = self.provider.get_company_profile(ticker)
                curr_p = prof.get("current_price") or float(h.get("buy_price", 100.0))
                prices_map[ticker] = curr_p
                betas_map[ticker] = prof.get("beta") or 1.0
                sectors_map[ticker] = prof.get("sector") or "כללי"
                
                # Fetch quick history for correlations
                hist_df = self.provider.get_historical_prices(ticker, period="1y")
                history_map[ticker] = hist_df

                # Quick scores
                scores_map[ticker] = {
                    "quality": 75 if prof.get("is_etf") else 70,
                    "valuation": 65
                }
            except Exception as e:
                print(f"[AnalysisService] Portfolio item error for {ticker}: {e}")
                prices_map[ticker] = float(h.get("buy_price", 100.0))
                betas_map[ticker] = 1.0
                sectors_map[ticker] = "כללי"
                scores_map[ticker] = {"quality": 60, "valuation": 50}

        return PortfolioEngine.analyze_portfolio(
            holdings=holdings,
            prices_map=prices_map,
            betas_map=betas_map,
            sectors_map=sectors_map,
            scores_map=scores_map,
            history_df_map=history_map
        )

    def simulate_custom_dcf(self, ticker: str, custom_wacc: Optional[float], custom_growth: Optional[float]) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        financials = self.provider.get_financial_statements(ticker)
        raw_info = financials.get("raw_info", {})
        profile = self.provider.get_company_profile(ticker)
        combined_info = {**raw_info, **profile}

        return ValuationEngine.calculate_valuation(
            combined_info,
            custom_wacc=custom_wacc,
            custom_growth=custom_growth
        )

analysis_service = AnalysisService()
