"""
Risk and Performance Analytics Engine.
Calculates annualized volatility, Beta vs S&P 500, Jensen's Alpha,
Maximum Drawdown, VaR (95%/99%), Sharpe, Sortino and Technical Regimes.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.core.config import settings

class RiskEngine:
    @staticmethod
    def analyze(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame, risk_free_rate: float = settings.DEFAULT_RISK_FREE_RATE) -> Dict[str, Any]:
        if stock_df.empty:
            return RiskEngine._empty_result()

        # Ensure Close prices exist
        stock_close = stock_df["Close"].dropna()
        if len(stock_close) < 20:
            return RiskEngine._empty_result()

        # Daily Returns
        stock_returns = stock_close.pct_change().dropna()
        
        # Benchmark returns alignment
        if not benchmark_df.empty and "Close" in benchmark_df.columns:
            bench_close = benchmark_df["Close"].dropna()
            bench_returns = bench_close.pct_change().dropna()
            # Align dates
            combined = pd.concat([stock_returns, bench_returns], axis=1, join="inner").dropna()
            combined.columns = ["stock", "benchmark"]
            stock_aligned = combined["stock"]
            bench_aligned = combined["benchmark"]
        else:
            stock_aligned = stock_returns
            bench_aligned = pd.Series(dtype=float)

        # 1. Volatility (Annualized, 252 trading days)
        daily_vol = stock_returns.std()
        annual_vol = daily_vol * np.sqrt(252)

        # 2. Beta & Alpha
        if len(bench_aligned) > 30 and bench_aligned.var() > 0:
            covariance = np.cov(stock_aligned, bench_aligned)[0][1]
            benchmark_variance = bench_aligned.var()
            beta = float(covariance / benchmark_variance)
            annual_stock_ret = float(stock_aligned.mean() * 252)
            annual_bench_ret = float(bench_aligned.mean() * 252)
            alpha = float(annual_stock_ret - (risk_free_rate + beta * (annual_bench_ret - risk_free_rate)))
        else:
            beta = 1.0
            alpha = 0.0

        # 3. Maximum Drawdown (MDD)
        cumulative = (1 + stock_returns).cumprod()
        running_max = cumulative.cummax()
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = float(drawdowns.min())

        # 4. Value at Risk (VaR - 1 Day 95% and 99%)
        var_95_daily = float(np.percentile(stock_returns, 5))
        var_99_daily = float(np.percentile(stock_returns, 1))
        # Annualized approx
        var_95_annual = float(var_95_daily * np.sqrt(252))

        # 5. Sharpe & Sortino Ratios
        daily_rf = risk_free_rate / 252
        excess_returns = stock_returns - daily_rf
        mean_excess = excess_returns.mean()
        sharpe = float((mean_excess / daily_vol) * np.sqrt(252)) if daily_vol > 0 else 0.0

        downside_returns = stock_returns[stock_returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else daily_vol
        sortino = float((mean_excess / downside_std) * np.sqrt(252)) if downside_std > 0 else 0.0

        # 6. Technical Indicators (SMA 50, SMA 200, RSI 14)
        latest_price = float(stock_close.iloc[-1])
        sma_50 = float(stock_close.rolling(window=min(50, len(stock_close))).mean().iloc[-1])
        sma_200 = float(stock_close.rolling(window=min(200, len(stock_close))).mean().iloc[-1]) if len(stock_close) >= 100 else sma_50
        
        # RSI 14
        delta = stock_close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0

        # 7. Period Performance Comparison (Stock vs S&P 500)
        periods = {
            "1M": 21,
            "3M": 63,
            "6M": 126,
            "1Y": 252,
            "3Y": 252 * 3,
            "5Y": 252 * 5
        }
        performance = []
        for label, days in periods.items():
            if len(stock_close) >= days:
                st_ret = float((stock_close.iloc[-1] / stock_close.iloc[-days]) - 1.0)
            else:
                st_ret = float((stock_close.iloc[-1] / stock_close.iloc[0]) - 1.0) if len(stock_close) > 10 else 0.0
            
            if not bench_close.empty and len(bench_close) >= days:
                bm_ret = float((bench_close.iloc[-1] / bench_close.iloc[-days]) - 1.0)
            else:
                bm_ret = float((bench_close.iloc[-1] / bench_close.iloc[0]) - 1.0) if not bench_close.empty and len(bench_close) > 10 else 0.0
            
            diff = st_ret - bm_ret
            performance.append({
                "period": label,
                "stock_return": round(st_ret * 100, 1),
                "benchmark_return": round(bm_ret * 100, 1),
                "alpha_diff": round(diff * 100, 1),
                "beating_benchmark": diff > 0
            })

        # Trend summary
        if latest_price > sma_50 and sma_50 > sma_200:
            trend_status = "מגמת עלייה מובהקת (שורית חזקה)"
        elif latest_price < sma_50 and sma_50 < sma_200:
            trend_status = "מגמת ירידה (דובית)"
        else:
            trend_status = "מגמה מעורבת / דשדוש"

        return {
            "annual_volatility": round(annual_vol * 100, 1),
            "beta": round(beta, 2),
            "alpha": round(alpha * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 1),
            "var_95_daily": round(var_95_daily * 100, 2),
            "var_99_daily": round(var_99_daily * 100, 2),
            "var_95_annual": round(var_95_annual * 100, 1),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "sma_50": round(sma_50, 2),
            "sma_200": round(sma_200, 2),
            "rsi_14": round(current_rsi, 1),
            "trend_status": trend_status,
            "performance_comparison": performance,
            "risk_verdict": RiskEngine._risk_verdict(annual_vol, max_drawdown, beta)
        }

    @staticmethod
    def _risk_verdict(vol: float, mdd: float, beta: float) -> str:
        if vol < 0.20 and abs(mdd) < 25 and beta < 1.0:
            return "פרופיל סיכון נמוך ויציב ביחס לשוק"
        elif vol <= 0.35 and abs(mdd) <= 45:
            return "פרופיל סיכון בינוני - תנודתיות אופיינית למניית צמיחה"
        else:
            return "פרופיל סיכון גבוה - תנודתיות משמעותית עם פוטנציאל לירידות חדות"

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "annual_volatility": 0.0, "beta": 1.0, "alpha": 0.0,
            "max_drawdown": 0.0, "var_95_daily": 0.0, "var_99_daily": 0.0,
            "var_95_annual": 0.0, "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
            "sma_50": 0.0, "sma_200": 0.0, "rsi_14": 50.0,
            "trend_status": "מידע לא זמין",
            "performance_comparison": [],
            "risk_verdict": "מידע היסטורי חסר"
        }
