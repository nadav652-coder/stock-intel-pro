"""
Seasonality & Cyclicality Analysis Engine.
Computes multi-year monthly return distributions, win rates, calendar year heatmaps,
and quantitative market anomaly verifications (Santa Claus rally, September effect, Sell in May).
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

MONTH_NAMES_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
]

MONTH_NAMES_EN = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

class SeasonalityEngine:
    @staticmethod
    def analyze(stock_df: pd.DataFrame, ticker: str = "") -> Dict[str, Any]:
        """
        Analyze multi-year monthly seasonality for a stock or ETF.
        Returns monthly statistics, year-by-month matrix, and institutional insights.
        """
        if stock_df is None or stock_df.empty or len(stock_df) < 30:
            return SeasonalityEngine._empty_seasonality()

        df = stock_df.copy()
        date_col = "Date" if "Date" in df.columns else ("index" if "index" in df.columns else None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
        elif not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                return SeasonalityEngine._empty_seasonality()

        if "Close" not in df.columns:
            return SeasonalityEngine._empty_seasonality()

        df.sort_index(inplace=True)

        # Resample to monthly closing prices
        # 'ME' in modern pandas (or 'M' as fallback)
        try:
            monthly_close = df["Close"].resample("ME").last().dropna()
        except Exception:
            monthly_close = df["Close"].resample("M").last().dropna()

        if len(monthly_close) < 6:
            return SeasonalityEngine._empty_seasonality()

        # Monthly percentage returns
        monthly_returns = monthly_close.pct_change() * 100.0

        records: List[Dict[str, Any]] = []
        for dt, ret in monthly_returns.dropna().items():
            records.append({
                "year": int(dt.year),
                "month": int(dt.month),
                "return": round(float(ret), 2)
            })

        if not records:
            return SeasonalityEngine._empty_seasonality()

        m_df = pd.DataFrame(records)

        # 1. Monthly Statistics (1 to 12)
        monthly_stats: List[Dict[str, Any]] = []
        for m in range(1, 13):
            sub = m_df[m_df["month"] == m]
            if len(sub) > 0:
                rets = sub["return"].values
                avg_ret = round(float(np.mean(rets)), 2)
                med_ret = round(float(np.median(rets)), 2)
                pos = int(np.sum(rets > 0))
                total = len(rets)
                win_rate = round((pos / total) * 100.0, 1)
                best_val = round(float(np.max(rets)), 2)
                worst_val = round(float(np.min(rets)), 2)
                std_val = round(float(np.std(rets)), 2) if total > 1 else 0.0

                monthly_stats.append({
                    "month": m,
                    "name_he": MONTH_NAMES_HE[m - 1],
                    "name_en": MONTH_NAMES_EN[m - 1],
                    "avg_return": avg_ret,
                    "median_return": med_ret,
                    "win_rate": win_rate,
                    "positive_years": pos,
                    "negative_years": total - pos,
                    "total_years": total,
                    "best_return": best_val,
                    "worst_return": worst_val,
                    "volatility": std_val
                })
            else:
                monthly_stats.append({
                    "month": m,
                    "name_he": MONTH_NAMES_HE[m - 1],
                    "name_en": MONTH_NAMES_EN[m - 1],
                    "avg_return": 0.0,
                    "median_return": 0.0,
                    "win_rate": 0.0,
                    "positive_years": 0,
                    "negative_years": 0,
                    "total_years": 0,
                    "best_return": 0.0,
                    "worst_return": 0.0,
                    "volatility": 0.0
                })

        # 2. Years Matrix (Heatmap Table: Rows = Years descending, Columns = Months 1..12 + Annual)
        unique_years = sorted(m_df["year"].unique(), reverse=True)
        years_matrix: List[Dict[str, Any]] = []

        # Yearly cumulative return from daily close (or compounded monthly)
        try:
            annual_close = df["Close"].resample("YE").last().dropna()
        except Exception:
            annual_close = df["Close"].resample("Y").last().dropna()
        annual_returns_series = annual_close.pct_change() * 100.0
        annual_returns_map = {dt.year: round(float(val), 2) for dt, val in annual_returns_series.dropna().items()}

        for yr in unique_years:
            yr_int = int(yr)
            yr_sub = m_df[m_df["year"] == yr]
            month_vals: Dict[str, Optional[float]] = {}
            for m in range(1, 13):
                m_row = yr_sub[yr_sub["month"] == m]
                if not m_row.empty:
                    month_vals[str(m)] = round(float(m_row["return"].iloc[0]), 2)
                else:
                    month_vals[str(m)] = None

            # Annual return fallback: compound available months if annual_returns_map doesn't have it
            ann_ret = annual_returns_map.get(yr)
            if ann_ret is None:
                valid_rets = [r for r in month_vals.values() if r is not None]
                if valid_rets:
                    compound = 1.0
                    for r in valid_rets:
                        compound *= (1.0 + r / 100.0)
                    ann_ret = round(float((compound - 1.0) * 100.0), 2)
                else:
                    ann_ret = 0.0
            else:
                ann_ret = round(float(ann_ret), 2)

            years_matrix.append({
                "year": yr_int,
                "months": month_vals,
                "annual_return": ann_ret
            })

        # 3. Macro & Market Anomaly Insights
        active_stats = [s for s in monthly_stats if s["total_years"] > 0]
        if not active_stats:
            return SeasonalityEngine._empty_seasonality()

        best_m = max(active_stats, key=lambda s: s["avg_return"])
        worst_m = min(active_stats, key=lambda s: s["avg_return"])
        highest_win = max(active_stats, key=lambda s: (s["win_rate"], s["avg_return"]))

        # Current & Next Month
        now = datetime.now()
        current_month_idx = now.month
        next_month_idx = (current_month_idx % 12) + 1
        current_month_stat = monthly_stats[current_month_idx - 1]
        next_month_stat = monthly_stats[next_month_idx - 1]

        # Santa Claus Rally (December)
        dec_stat = monthly_stats[11]
        santa_rally = {
            "name": "ראלי סנטה קלאוס (אפקט דצמבר)",
            "avg_return": dec_stat["avg_return"],
            "win_rate": dec_stat["win_rate"],
            "positive_years": dec_stat["positive_years"],
            "total_years": dec_stat["total_years"],
            "is_favorable": dec_stat["avg_return"] > 0 and dec_stat["win_rate"] >= 60.0,
            "description": f"בחודש דצמבר המניה הניבה בממוצע {dec_stat['avg_return']:+0.1f}% עם {dec_stat['win_rate']}% שנות עלייה ({dec_stat['positive_years']} מתוך {dec_stat['total_years']} שנים)."
        }

        # September Effect
        sep_stat = monthly_stats[8]
        sep_effect = {
            "name": "אפקט ספטמבר (חודש חלש בוול סטריט)",
            "avg_return": sep_stat["avg_return"],
            "win_rate": sep_stat["win_rate"],
            "positive_years": sep_stat["positive_years"],
            "total_years": sep_stat["total_years"],
            "is_weak": sep_stat["avg_return"] < 0 or sep_stat["win_rate"] < 50.0,
            "description": f"בחודש ספטמבר המניה הניבה בממוצע {sep_stat['avg_return']:+0.1f}% עם {sep_stat['win_rate']}% שנות עלייה ({sep_stat['positive_years']} מתוך {sep_stat['total_years']} שנים)."
        }

        # Sell in May and Go Away (Nov-Apr vs May-Oct)
        winter_months = [11, 12, 1, 2, 3, 4]  # Nov - Apr
        summer_months = [5, 6, 7, 8, 9, 10]   # May - Oct

        winter_sub = m_df[m_df["month"].isin(winter_months)]
        summer_sub = m_df[m_df["month"].isin(summer_months)]

        winter_avg = round(float(winter_sub["return"].mean()), 2) if len(winter_sub) > 0 else 0.0
        summer_avg = round(float(summer_sub["return"].mean()), 2) if len(summer_sub) > 0 else 0.0

        sell_in_may = {
            "name": "Sell in May and Go Away",
            "winter_avg_return": winter_avg,
            "summer_avg_return": summer_avg,
            "winter_favorable": winter_avg > summer_avg,
            "description": f"תשואה חודשית ממוצעת בחודשי החורף (נובמבר-אפריל): {winter_avg:+0.1f}% לעומת חודשי הקיץ (מאי-אוקטובר): {summer_avg:+0.1f}%."
        }

        sample_years_count = len(unique_years)

        return {
            "ticker": ticker.upper(),
            "sample_years": sample_years_count,
            "monthly_stats": monthly_stats,
            "years_matrix": years_matrix,
            "best_month": {
                "month": best_m["month"],
                "name_he": best_m["name_he"],
                "name_en": best_m["name_en"],
                "avg_return": best_m["avg_return"],
                "win_rate": best_m["win_rate"]
            },
            "worst_month": {
                "month": worst_m["month"],
                "name_he": worst_m["name_he"],
                "name_en": worst_m["name_en"],
                "avg_return": worst_m["avg_return"],
                "win_rate": worst_m["win_rate"]
            },
            "highest_win_rate_month": {
                "month": highest_win["month"],
                "name_he": highest_win["name_he"],
                "name_en": highest_win["name_en"],
                "avg_return": highest_win["avg_return"],
                "win_rate": highest_win["win_rate"]
            },
            "current_month": {
                "month": current_month_idx,
                "name_he": current_month_stat["name_he"],
                "avg_return": current_month_stat["avg_return"],
                "win_rate": current_month_stat["win_rate"]
            },
            "next_month": {
                "month": next_month_idx,
                "name_he": next_month_stat["name_he"],
                "avg_return": next_month_stat["avg_return"],
                "win_rate": next_month_stat["win_rate"]
            },
            "anomalies": {
                "santa_rally": santa_rally,
                "september_effect": sep_effect,
                "sell_in_may": sell_in_may
            }
        }

    @staticmethod
    def _empty_seasonality() -> Dict[str, Any]:
        return {
            "ticker": "",
            "sample_years": 0,
            "monthly_stats": [],
            "years_matrix": [],
            "best_month": None,
            "worst_month": None,
            "highest_win_rate_month": None,
            "current_month": None,
            "next_month": None,
            "anomalies": {}
        }
