"""
Valuation Engine: Institutional DCF (Discounted Cash Flow), Multiples Valuation,
Sensitivity Matrix and Margin of Safety computation.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from app.core.config import settings

class ValuationEngine:
    @staticmethod
    def calculate_valuation(
        raw_info: Dict[str, Any],
        custom_wacc: Optional[float] = None,
        custom_growth: Optional[float] = None
    ) -> Dict[str, Any]:
        info = raw_info or {}
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 100.0
        shares = info.get("sharesOutstanding") or (info.get("marketCap", 1e9) / current_price)
        total_cash = info.get("totalCash") or 0.0
        total_debt = info.get("totalDebt") or 0.0
        base_fcf = info.get("freeCashflow")

        # Fallback if FCF is negative or missing: use Operating Cash Flow or 80% of Net Income
        if not base_fcf or base_fcf <= 0:
            net_income = info.get("netIncomeToCommon") or 0.0
            base_fcf = max(net_income * 0.85, 1e7)  # conservative positive floor

        # 1. Estimate WACC
        beta = info.get("beta") or 1.0
        beta = min(max(beta, 0.5), 2.5)  # clamp realistic range
        rf = settings.DEFAULT_RISK_FREE_RATE
        erp = settings.DEFAULT_MARKET_RISK_PREMIUM
        cost_of_equity = rf + beta * erp  # CAPM
        cost_of_debt = 0.055 * (1 - 0.21)  # After-tax cost of debt
        
        market_cap = info.get("marketCap") or (shares * current_price)
        total_capital = market_cap + total_debt
        weight_equity = market_cap / max(total_capital, 1.0)
        weight_debt = total_debt / max(total_capital, 1.0)
        
        calculated_wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt)
        wacc = custom_wacc if custom_wacc is not None else round(max(calculated_wacc, 0.065), 4)

        # 2. Estimate 5-Year Growth Rate
        rev_growth = info.get("revenueGrowth") or 0.08
        earnings_growth = info.get("earningsGrowth") or 0.10
        # Blended conservative growth rate
        est_growth = min(max((rev_growth * 0.5 + earnings_growth * 0.5), 0.03), 0.25)
        growth_rate = custom_growth if custom_growth is not None else round(est_growth, 4)
        terminal_growth = settings.DEFAULT_TERMINAL_GROWTH_RATE

        # Ensure WACC > terminal_growth to prevent mathematical divergence
        if wacc <= terminal_growth + 0.01:
            wacc = terminal_growth + 0.02

        # 3. Project 5-Year FCF
        projected_fcfs = []
        discount_factors = []
        pv_fcfs = []
        current_fcf = base_fcf
        
        # Growth fades slightly towards terminal growth
        for year in range(1, 6):
            year_growth = growth_rate * (0.95 ** (year - 1))
            current_fcf = current_fcf * (1.0 + year_growth)
            df = 1.0 / ((1.0 + wacc) ** year)
            pv = current_fcf * df
            projected_fcfs.append(round(current_fcf))
            discount_factors.append(round(df, 4))
            pv_fcfs.append(round(pv))

        # 4. Terminal Value (Gordon Growth Model)
        fcf_year_5 = projected_fcfs[-1]
        terminal_value = (fcf_year_5 * (1.0 + terminal_growth)) / (wacc - terminal_growth)
        pv_terminal_value = terminal_value / ((1.0 + wacc) ** 5)

        # 5. Enterprise & Equity Value
        pv_sum_fcf = sum(pv_fcfs)
        enterprise_value = pv_sum_fcf + pv_terminal_value
        equity_value = enterprise_value + total_cash - total_debt
        dcf_fair_value = max(equity_value / max(shares, 1.0), 1.0)
        dcf_fair_value = round(dcf_fair_value, 2)

        # Margin of Safety (%)
        margin_of_safety = ((dcf_fair_value - current_price) / dcf_fair_value) * 100.0
        margin_of_safety = round(margin_of_safety, 1)

        # 6. Multiples-Based Valuation (P/E approach)
        eps = info.get("forwardEps") or info.get("trailingEps") or (current_price / 25.0)
        sector_pe_benchmark = 22.0
        pe_fair_value = round(max(eps * sector_pe_benchmark, 1.0), 2)

        # Blended Target Price (70% DCF, 30% Multiples)
        blended_fair_value = round(0.70 * dcf_fair_value + 0.30 * pe_fair_value, 2)
        blended_upside = round(((blended_fair_value - current_price) / current_price) * 100.0, 1)

        # 7. Sensitivity Matrix (varying WACC +/- 2% and Growth +/- 2%)
        wacc_steps = [round(wacc - 0.02, 3), round(wacc - 0.01, 3), round(wacc, 3), round(wacc + 0.01, 3), round(wacc + 0.02, 3)]
        growth_steps = [round(growth_rate - 0.02, 3), round(growth_rate - 0.01, 3), round(growth_rate, 3), round(growth_rate + 0.01, 3), round(growth_rate + 0.02, 3)]
        
        matrix = []
        for g in growth_steps:
            row = []
            for w in wacc_steps:
                if w <= terminal_growth + 0.005:
                    row.append(None)
                    continue
                # Quick DCF approximation
                fcf_proj = base_fcf
                pv_s = 0.0
                for y in range(1, 6):
                    fcf_proj *= (1.0 + g * (0.95 ** (y - 1)))
                    pv_s += fcf_proj / ((1.0 + w) ** y)
                tv = (fcf_proj * (1.0 + terminal_growth)) / (w - terminal_growth)
                pv_tv = tv / ((1.0 + w) ** 5)
                eq_val = pv_s + pv_tv + total_cash - total_debt
                val_per_share = round(max(eq_val / max(shares, 1.0), 1.0), 1)
                row.append(val_per_share)
            matrix.append({"growth": round(g * 100, 1), "values": row})

        # Valuation Status Summary
        if margin_of_safety > 20:
            status = "undervalued"
            summary_hebrew = f"המניה נסחרת בהנחה משמעותית מתחת לשוויה ההוגן (שולי ביטחון: {margin_of_safety:+.1f}%)."
        elif margin_of_safety >= -10:
            status = "fairly_valued"
            summary_hebrew = f"המניה נסחרת בסביבת שוויה ההוגן (שולי ביטחון: {margin_of_safety:+.1f}%)."
        else:
            status = "overvalued"
            summary_hebrew = f"המניה נסחרת בפרמיה מעל שוויה ההוגן לפי מודל תזרים המזומנים (תמחור יקר ב-{abs(margin_of_safety):.1f}%)."

        return {
            "current_price": round(current_price, 2),
            "dcf_fair_value": dcf_fair_value,
            "pe_fair_value": pe_fair_value,
            "blended_fair_value": blended_fair_value,
            "blended_upside_percent": blended_upside,
            "margin_of_safety_percent": margin_of_safety,
            "status": status,
            "summary_hebrew": summary_hebrew,
            "assumptions": {
                "wacc": round(wacc * 100, 2),
                "growth_rate_5y": round(growth_rate * 100, 2),
                "terminal_growth_rate": round(terminal_growth * 100, 2),
                "base_fcf": base_fcf,
                "shares_outstanding": shares
            },
            "projections": {
                "years": [1, 2, 3, 4, 5],
                "projected_fcf": projected_fcfs,
                "pv_fcfs": pv_fcfs,
                "terminal_value": round(terminal_value),
                "pv_terminal_value": round(pv_terminal_value),
                "enterprise_value": round(enterprise_value),
                "equity_value": round(equity_value)
            },
            "sensitivity": {
                "wacc_headers": [f"{round(w * 100, 1)}%" for w in wacc_steps],
                "matrix": matrix
            }
        }
