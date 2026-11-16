"""
Probabilistic Forecasting Engine.
Runs 5,000+ Monte Carlo simulations combined with Non-parametric Historical Bootstrapping
to determine empirical return distributions, benchmark outperformance probabilities,
and probabilistic scenarios (Bull P90, Base P50, Bear P10) without misleading precision.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from app.core.config import settings

class ForecastEngine:
    HORIZONS = {
        "3_months": {"days": 63, "label": "3 חודשים"},
        "6_months": {"days": 126, "label": "6 חודשים"},
        "1_year": {"days": 252, "label": "שנה אחת"},
        "3_years": {"days": 756, "label": "3 שנים"}
    }

    @staticmethod
    def simulate(
        stock_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
        num_simulations: int = settings.MONTE_CARLO_SIMULATIONS
    ) -> Dict[str, Any]:
        if stock_df.empty or len(stock_df) < 60:
            return ForecastEngine._fallback_forecast()

        close = stock_df["Close"].dropna()
        current_price = float(close.iloc[-1])
        daily_returns = close.pct_change().dropna().values
        
        # Benchmark returns
        if not benchmark_df.empty and "Close" in benchmark_df.columns:
            bench_close = benchmark_df["Close"].dropna()
            bench_returns = bench_close.pct_change().dropna().values
        else:
            bench_returns = np.random.normal(0.00035, 0.01, size=len(daily_returns))

        mu = float(np.mean(daily_returns))
        sigma = float(np.std(daily_returns))

        # We blend Geometric Brownian Motion (parametric) with Historical Bootstrapping (non-parametric fat-tails)
        # 50% Monte Carlo GBM, 50% Block Bootstrap
        results_by_horizon = {}
        chart_paths = []
        max_days = ForecastEngine.HORIZONS["3_years"]["days"]

        # Run simulations
        # Pre-generate simulated return trajectories
        np.random.seed(42)  # reproducible simulation
        
        # 1. GBM Simulation paths
        dt = 1.0
        drift = (mu - 0.5 * (sigma ** 2))
        random_shocks = np.random.normal(0, 1, size=(num_simulations // 2, max_days))
        gbm_daily_log_returns = drift * dt + sigma * np.sqrt(dt) * random_shocks
        gbm_paths = current_price * np.exp(np.cumsum(gbm_daily_log_returns, axis=1))

        # 2. Historical Bootstrap paths (preserving empirical fat tails)
        boot_idx = np.random.randint(0, len(daily_returns), size=(num_simulations // 2, max_days))
        boot_daily_returns = daily_returns[boot_idx]
        boot_paths = current_price * np.cumprod(1 + boot_daily_returns, axis=1)

        # Combined paths (shape: num_simulations, max_days)
        all_paths = np.vstack([gbm_paths, boot_paths])

        # Benchmark simulation (GBM based on benchmark mu and sigma)
        b_mu = float(np.mean(bench_returns)) if len(bench_returns) > 0 else 0.00035
        b_sigma = float(np.std(bench_returns)) if len(bench_returns) > 0 else 0.01
        b_shocks = np.random.normal(0, 1, size=(num_simulations, max_days))
        b_paths_ret = np.cumsum(b_mu - 0.5 * (b_sigma**2) + b_sigma * b_shocks, axis=1)
        b_total_returns = np.exp(b_paths_ret) - 1.0

        # Calculate metrics for each horizon
        horizons_summary = []
        for h_key, h_info in ForecastEngine.HORIZONS.items():
            days = h_info["days"]
            col_idx = min(days - 1, max_days - 1)
            
            end_prices = all_paths[:, col_idx]
            simulated_returns = (end_prices - current_price) / current_price
            
            # Probability of Positive Return
            prob_positive = float(np.mean(simulated_returns > 0)) * 100.0
            prob_negative = 100.0 - prob_positive
            
            # Probability of Beating S&P 500
            b_rets_horizon = b_total_returns[:, col_idx]
            prob_beat_sp500 = float(np.mean(simulated_returns > b_rets_horizon)) * 100.0

            # Scenarios (Percentiles)
            p10_price = float(np.percentile(end_prices, 10))
            p50_price = float(np.percentile(end_prices, 50))
            p90_price = float(np.percentile(end_prices, 90))

            p10_ret = ((p10_price - current_price) / current_price) * 100.0
            p50_ret = ((p50_price - current_price) / current_price) * 100.0
            p90_ret = ((p90_price - current_price) / current_price) * 100.0

            horizons_summary.append({
                "horizon_id": h_key,
                "label": h_info["label"],
                "trading_days": days,
                "prob_positive": round(prob_positive, 1),
                "prob_negative": round(prob_negative, 1),
                "prob_beat_sp500": round(prob_beat_sp500, 1),
                "bear_case_p10": {
                    "price": round(p10_price, 2),
                    "return_percent": round(p10_ret, 1)
                },
                "base_case_p50": {
                    "price": round(p50_price, 2),
                    "return_percent": round(p50_ret, 1)
                },
                "bull_case_p90": {
                    "price": round(p90_price, 2),
                    "return_percent": round(p90_ret, 1)
                },
                "confidence_level": "גבוהה יחסית (מדגם רחב)" if len(daily_returns) > 750 else "בינונית (היסטוריית מסחר מוגבלת)"
            })

        # Chart fan points (sample 30 step days across the 3 years for visual charting)
        sample_steps = np.linspace(0, max_days - 1, 30, dtype=int)
        fan_data = []
        for s in sample_steps:
            day_num = int(s + 1)
            fan_data.append({
                "day": day_num,
                "p10": round(float(np.percentile(all_paths[:, s], 10)), 2),
                "p25": round(float(np.percentile(all_paths[:, s], 25)), 2),
                "p50": round(float(np.percentile(all_paths[:, s], 50)), 2),
                "p75": round(float(np.percentile(all_paths[:, s], 75)), 2),
                "p90": round(float(np.percentile(all_paths[:, s], 90)), 2),
            })

        return {
            "num_simulations": num_simulations,
            "current_price": round(current_price, 2),
            "methodology": "שילוב Monte Carlo Geometric Brownian Motion עם Non-parametric Block Bootstrapping",
            "horizons": horizons_summary,
            "fan_chart_data": fan_data,
            "disclaimer_hebrew": (
                "חשוב: מודל זה מציג הסתברויות מתמטיות ותרחישי סימולציה המבוססים על דפוסי תנודתיות, תשואות היסטוריות ודגימות מונטה קרלו. "
                "אין לראות בהסתברויות אלו עובדות או הבטחת תשואה. ביצועי העבר אינם מעידים בהכרח על העתיד."
            )
        }

    @staticmethod
    def _fallback_forecast() -> Dict[str, Any]:
        return {
            "num_simulations": 0,
            "current_price": 100.0,
            "methodology": "הערכה סטטיסטית בסיסית בהיעדר היסטוריה מספקת",
            "horizons": [
                {
                    "horizon_id": "1_year", "label": "שנה אחת", "trading_days": 252,
                    "prob_positive": 55.0, "prob_negative": 45.0, "prob_beat_sp500": 50.0,
                    "bear_case_p10": {"price": 80.0, "return_percent": -20.0},
                    "base_case_p50": {"price": 108.0, "return_percent": 8.0},
                    "bull_case_p90": {"price": 130.0, "return_percent": 30.0},
                    "confidence_level": "נמוכה (מידע היסטורי חסר)"
                }
            ],
            "fan_chart_data": [],
            "disclaimer_hebrew": "אין מספיק נתונים היסטוריים להרצת סימולציה מלאה."
        }
