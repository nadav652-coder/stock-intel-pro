"""
Portfolio Analytics and Optimization Engine.
Computes portfolio total value, P&L, weighted beta, sector allocation,
correlation matrix, and Markowitz risk-return metrics.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

class PortfolioEngine:
    @staticmethod
    def analyze_portfolio(
        holdings: List[Dict[str, Any]],
        prices_map: Dict[str, float],
        betas_map: Dict[str, float],
        sectors_map: Dict[str, str],
        scores_map: Dict[str, Dict[str, int]],
        history_df_map: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Analyzes a multi-asset portfolio (Stocks & ETFs).
        holdings: list of dicts with keys: ticker, shares, buy_price
        """
        if not holdings:
            return PortfolioEngine._empty_portfolio()

        positions = []
        total_value = 0.0
        total_cost = 0.0

        for h in holdings:
            ticker = h.get("ticker", "").upper().strip()
            shares = float(h.get("shares", 0))
            buy_price = float(h.get("buy_price", 0))
            
            curr_price = prices_map.get(ticker, buy_price or 100.0)
            pos_val = shares * curr_price
            pos_cost = shares * buy_price
            pos_pnl = pos_val - pos_cost
            pos_pnl_pct = ((curr_price - buy_price) / buy_price * 100.0) if buy_price > 0 else 0.0

            total_value += pos_val
            total_cost += pos_cost

            positions.append({
                "ticker": ticker,
                "shares": shares,
                "buy_price": round(buy_price, 2),
                "current_price": round(curr_price, 2),
                "position_value": round(pos_val, 2),
                "cost_basis": round(pos_cost, 2),
                "pnl_amount": round(pos_pnl, 2),
                "pnl_percent": round(pos_pnl_pct, 2),
                "beta": round(betas_map.get(ticker, 1.0), 2),
                "sector": sectors_map.get(ticker, "כללי"),
                "quality_score": scores_map.get(ticker, {}).get("quality", 60),
                "valuation_score": scores_map.get(ticker, {}).get("valuation", 50)
            })

        # Calculate weights and portfolio-level aggregates
        weighted_beta = 0.0
        weighted_quality = 0.0
        weighted_val = 0.0
        sector_allocation: Dict[str, float] = {}

        for p in positions:
            weight = p["position_value"] / total_value if total_value > 0 else 0.0
            p["weight_percent"] = round(weight * 100.0, 1)

            weighted_beta += weight * p["beta"]
            weighted_quality += weight * p["quality_score"]
            weighted_val += weight * p["valuation_score"]

            sec = p["sector"]
            sector_allocation[sec] = sector_allocation.get(sec, 0.0) + p["position_value"]

        # Format sector weights
        sector_chart_data = []
        for sec_name, sec_val in sector_allocation.items():
            pct = (sec_val / total_value * 100.0) if total_value > 0 else 0.0
            sector_chart_data.append({
                "sector": sec_name,
                "value": round(sec_val, 2),
                "percent": round(pct, 1)
            })
        sector_chart_data.sort(key=lambda x: x["value"], reverse=True)

        # Total P&L
        total_pnl = total_value - total_cost
        total_pnl_pct = ((total_value - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

        # Correlation Matrix
        correlation_matrix = PortfolioEngine._build_correlation_matrix(history_df_map)

        # Overall Portfolio Verdict
        if weighted_beta < 0.85:
            risk_profile = "דפנסיבי / שמרני (תנודתיות נמוכה ממדד S&P 500)"
        elif weighted_beta <= 1.15:
            risk_profile = "מאוזן (תנודתיות דומה למדד S&P 500)"
        else:
            risk_profile = "אגרסיבי / צמיחה (תנודתיות גבוהה מהשוק)"

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "weighted_beta": round(weighted_beta, 2),
            "weighted_quality_score": round(weighted_quality),
            "weighted_valuation_score": round(weighted_val),
            "risk_profile": risk_profile,
            "positions": positions,
            "sector_allocation": sector_chart_data,
            "correlation_matrix": correlation_matrix
        }

    @staticmethod
    def _build_correlation_matrix(history_df_map: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Builds pairwise return correlation matrix for assets with historical data."""
        returns_dict = {}
        for ticker, df in history_df_map.items():
            if df is not None and not df.empty and "Close" in df.columns:
                close = df["Close"].dropna()
                if len(close) > 30:
                    returns_dict[ticker] = close.pct_change().dropna()

        if len(returns_dict) < 2:
            return {"tickers": list(returns_dict.keys()), "matrix": []}

        comb_df = pd.DataFrame(returns_dict).dropna()
        if comb_df.empty or len(comb_df) < 10:
            return {"tickers": list(returns_dict.keys()), "matrix": []}

        corr = comb_df.corr().round(2)
        tickers = list(corr.columns)
        matrix = []
        for t1 in tickers:
            row = [float(corr.loc[t1, t2]) for t2 in tickers]
            matrix.append(row)

        return {
            "tickers": tickers,
            "matrix": matrix
        }

    @staticmethod
    def _empty_portfolio() -> Dict[str, Any]:
        return {
            "total_value": 0.0, "total_cost": 0.0, "total_pnl": 0.0,
            "total_pnl_percent": 0.0, "weighted_beta": 1.0,
            "weighted_quality_score": 0, "weighted_valuation_score": 0,
            "risk_profile": "טרם נוספו נכסים לתיק",
            "positions": [], "sector_allocation": [],
            "correlation_matrix": {"tickers": [], "matrix": []}
        }
