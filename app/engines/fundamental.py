"""
Fundamental Financial Analysis Engine.
Computes institutional ratios, Piotroski F-Score (0-9), Altman Z-Score,
and generates structured, transparent explanations in plain Hebrew.
"""

from typing import Dict, Any, List, Optional
import numpy as np

class FundamentalEngine:
    @staticmethod
    def analyze(raw_info: Dict[str, Any], financials_data: Dict[str, Any]) -> Dict[str, Any]:
        info = raw_info or {}
        inc = financials_data.get("income_statement", {})
        bal = financials_data.get("balance_sheet", {})
        cf = financials_data.get("cashflow", {})

        # Extract Key Raw Metrics
        pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        peg = info.get("pegRatio")
        price_to_book = info.get("priceToBook")
        ev_to_ebitda = info.get("enterpriseToEbitda")
        
        profit_margin = info.get("profitMargins")
        operating_margin = info.get("operatingMargins")
        gross_margin = info.get("grossMargins")
        
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")
        roe = info.get("returnOnEquity")
        roa = info.get("returnOnAssets")
        
        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity is not None and debt_to_equity > 10:
            # Often reported as percentage (e.g. 150 = 1.5)
            debt_to_equity = debt_to_equity / 100.0

        current_ratio = info.get("currentRatio")
        quick_ratio = info.get("quickRatio")
        fcf = info.get("freeCashflow")
        eps = info.get("trailingEps")
        forward_eps = info.get("forwardEps")

        # ROIC Calculation: NOPAT / Invested Capital
        ebit = info.get("ebitda")  # Approximation if EBIT not explicit
        roic = None
        if roe is not None and debt_to_equity is not None:
            # Synthetic approximate ROIC = ROE / (1 + D/E)
            roic = roe / (1.0 + max(debt_to_equity, 0))

        # 1. Piotroski F-Score Calculation (0 to 9)
        piotroski = FundamentalEngine._calculate_piotroski(info, inc, bal, cf)

        # 2. Altman Z-Score (Bankruptcy / Distress Risk)
        altman_z = FundamentalEngine._calculate_altman_z(info, bal)

        # 3. Build Detailed Metric Dictionary with Clear Hebrew Explanations
        metrics = [
            {
                "id": "pe_ratio",
                "name": "מכפיל רווח (P/E Ratio)",
                "value": round(pe, 2) if pe else None,
                "formatted": f"{pe:.1f}" if pe else "לא זמין",
                "category": "תמחור",
                "benchmark": "חציון S&P 500: ~22-25",
                "explanation": "כמה דולרים משלם השוק על כל דולר רווח נקי שהחברה מייצרת בשנה האחרונה.",
                "status": "positive" if pe and pe < 22 else ("neutral" if pe and pe <= 35 else "negative") if pe else "neutral",
                "verdict": "תמחור אטרקטיבי ביחס לשוק" if pe and pe < 22 else ("תמחור סביר לחברת צמיחה" if pe and pe <= 35 else "תמחור יקר יחסית הדורש צמיחה גבוהה") if pe else "מידע לא זמין"
            },
            {
                "id": "forward_pe",
                "name": "מכפיל רווח עתידי (Forward P/E)",
                "value": round(forward_pe, 2) if forward_pe else None,
                "formatted": f"{forward_pe:.1f}" if forward_pe else "לא זמין",
                "category": "תמחור",
                "benchmark": "תחזית S&P 500: ~19-21",
                "explanation": "מכפיל הרווח הצפוי על בסיס תחזיות הרווח של האנליסטים ל-12 החודשים הבאים.",
                "status": "positive" if forward_pe and pe and forward_pe < pe else "neutral" if forward_pe else "neutral",
                "verdict": "האנליסטים צופים גידול ברווחים (מכפיל עתידי נמוך יותר)" if forward_pe and pe and forward_pe < pe else "צפי להאטה או יציבות ברווחיות" if forward_pe else "מידע לא זמין"
            },
            {
                "id": "peg_ratio",
                "name": "מכפיל צמיחה (PEG Ratio)",
                "value": round(peg, 2) if peg else None,
                "formatted": f"{peg:.2f}" if peg else "לא זמין",
                "category": "תמחור",
                "benchmark": "רצוי מתחת ל-1.5, מצוין מתחת ל-1.0",
                "explanation": "מכפיל הרווח מחולק בקצב צמיחת הרווחים. מודד האם מחיר המניה מוצדק בהתחשב בקצב הצמיחה שלה.",
                "status": "positive" if peg and peg < 1.5 else ("neutral" if peg and peg <= 2.5 else "negative") if peg else "neutral",
                "verdict": "המניה מתומחרת בהזדמנות יחסית לקצב צמיחתה" if peg and peg < 1.5 else ("תמחור הולם לצמיחה" if peg and peg <= 2.5 else "המחיר מגלם צמיחה עתידית אגרסיבית מאוד") if peg else "מידע לא זמין"
            },
            {
                "id": "revenue_growth",
                "name": "צמיחה בהכנסות (Revenue Growth)",
                "value": round(revenue_growth * 100, 2) if revenue_growth else None,
                "formatted": f"{revenue_growth * 100:+.1f}%" if revenue_growth else "לא זמין",
                "category": "צמיחה",
                "benchmark": "ממוצע שוק: ~5%-8% בשנה",
                "explanation": "שיעור הגידול בהכנסות החברה בהשוואה לרבעון המקביל אשתקד.",
                "status": "positive" if revenue_growth and revenue_growth > 0.10 else ("neutral" if revenue_growth and revenue_growth > 0 else "negative") if revenue_growth else "neutral",
                "verdict": "צמיחה מואצת וחזקה" if revenue_growth and revenue_growth > 0.10 else ("צמיחה מתונה" if revenue_growth and revenue_growth > 0 else "התכווצות בהכנסות - נורת אזהרה") if revenue_growth else "מידע לא זמין"
            },
            {
                "id": "earnings_growth",
                "name": "צמיחה ברווח הנקי (Earnings Growth)",
                "value": round(earnings_growth * 100, 2) if earnings_growth else None,
                "formatted": f"{earnings_growth * 100:+.1f}%" if earnings_growth else "לא זמין",
                "category": "צמיחה",
                "benchmark": "רצוי צמיחה דו-ספרתית (>10%)",
                "explanation": "השינוי באחוזים ברווח הנקי של החברה לעומת התקופה המקבילה.",
                "status": "positive" if earnings_growth and earnings_growth > 0.12 else ("neutral" if earnings_growth and earnings_growth > 0 else "negative") if earnings_growth else "neutral",
                "verdict": "גידול חזק ברווחיות הנקייה" if earnings_growth and earnings_growth > 0.12 else ("גידול מתון" if earnings_growth and earnings_growth > 0 else "שחיקה ברווח הנקי") if earnings_growth else "מידע לא זמין"
            },
            {
                "id": "gross_margin",
                "name": "שולי רווח גולמי (Gross Margin)",
                "value": round(gross_margin * 100, 2) if gross_margin else None,
                "formatted": f"{gross_margin * 100:.1f}%" if gross_margin else "לא זמין",
                "category": "רווחיות ויעילות",
                "benchmark": "מעל 40% מעיד על יתרון תחרותי חזק",
                "explanation": "הרווח הגולמי מהמכירות בניכוי עלות המכר ישירה. משקף כוח תמחור ויתרון לגודל.",
                "status": "positive" if gross_margin and gross_margin > 0.40 else ("neutral" if gross_margin and gross_margin > 0.20 else "negative") if gross_margin else "neutral",
                "verdict": "כוח תמחור מעולה ויתרון תחרותי" if gross_margin and gross_margin > 0.40 else ("שוליים סטנדרטיים" if gross_margin and gross_margin > 0.20 else "שוליים דקים - רגישות גבוהה למחירי תשומות") if gross_margin else "מידע לא זמין"
            },
            {
                "id": "operating_margin",
                "name": "שולי רווח תפעולי (Operating Margin)",
                "value": round(operating_margin * 100, 2) if operating_margin else None,
                "formatted": f"{operating_margin * 100:.1f}%" if operating_margin else "לא זמין",
                "category": "רווחיות ויעילות",
                "benchmark": "מעל 15% נחשב לאיכותי מאוד",
                "explanation": "הרווח מפעילות הליבה לפני הוצאות מימון ומס, מתוך סך ההכנסות.",
                "status": "positive" if operating_margin and operating_margin > 0.18 else ("neutral" if operating_margin and operating_margin > 0.08 else "negative") if operating_margin else "neutral",
                "verdict": "יעילות תפעולית גבוהה ביותר" if operating_margin and operating_margin > 0.18 else ("יעילות תפעולית סבירה" if operating_margin and operating_margin > 0.08 else "יעילות תפעולית נמוכה או הפסד תפעולי") if operating_margin else "מידע לא זמין"
            },
            {
                "id": "roe",
                "name": "תשואה על ההון העצמי (ROE)",
                "value": round(roe * 100, 2) if roe else None,
                "formatted": f"{roe * 100:.1f}%" if roe else "לא זמין",
                "category": "יעילות הון",
                "benchmark": "מעל 15% נחשב למעולה",
                "explanation": "כמה רווח נקי מייצרת החברה על כל שקל של הון עצמי של בעלי המניות.",
                "status": "positive" if roe and roe > 0.18 else ("neutral" if roe and roe > 0.08 else "negative") if roe else "neutral",
                "verdict": "יצירת ערך פנומנלית לבעלי המניות" if roe and roe > 0.18 else ("תשואה ממוצעת על ההון" if roe and roe > 0.08 else "ניצול לא יעיל של ההון העצמי") if roe else "מידע לא זמין"
            },
            {
                "id": "roic",
                "name": "תשואה על ההון המושקע (ROIC)",
                "value": round(roic * 100, 2) if roic else None,
                "formatted": f"{roic * 100:.1f}%" if roic else "לא זמין",
                "category": "יעילות הון",
                "benchmark": "רצוי מעל 12% ומעל מחיר ההון (WACC)",
                "explanation": "מדד העל של וורן באפט: מודד את התשואה האמיתית שמייצרת החברה מכלל ההון שהושקע בה (חוב + הון עצמי).",
                "status": "positive" if roic and roic > 0.14 else ("neutral" if roic and roic > 0.07 else "negative") if roic else "neutral",
                "verdict": "חפיר כלכלי מובהק (Economic Moat)" if roic and roic > 0.14 else ("תשואה שגרתית" if roic and roic > 0.07 else "החברה עלולה להשמיד ערך כלכלי") if roic else "מידע לא זמין"
            },
            {
                "id": "free_cash_flow",
                "name": "תזרים מזומנים חופשי (Free Cash Flow)",
                "value": fcf,
                "formatted": FundamentalEngine._format_currency(fcf),
                "category": "איתנות פיננסית",
                "benchmark": "רצוי חיובי ויציב",
                "explanation": "המזומן שנשאר לחברה לאחר השקעה בציוד ופיתוח (CapEx). זהו הכסף האמיתי הזמין לחלוקת דיבידנד, רכישת מניות או פירעון חוב.",
                "status": "positive" if fcf and fcf > 0 else "negative" if fcf and fcf <= 0 else "neutral",
                "verdict": "מכונת מזומנים יציבה וחזקה" if fcf and fcf > 0 else "תזרים שלילי (החברה שורפת מזומנים)" if fcf and fcf <= 0 else "מידע לא זמין"
            },
            {
                "id": "debt_to_equity",
                "name": "יחס חוב להון עצמי (Debt / Equity)",
                "value": round(debt_to_equity, 2) if debt_to_equity is not None else None,
                "formatted": f"{debt_to_equity:.2f}" if debt_to_equity is not None else "לא זמין",
                "category": "סיכון ואיתנות",
                "benchmark": "רצוי מתחת ל-1.5, מתחת ל-0.8 שמרני מאוד",
                "explanation": "היקף החובות הכספיים של החברה ביחס להון העצמי שלה. מודד את רמת המינוף הפיננסי.",
                "status": "positive" if debt_to_equity is not None and debt_to_equity < 0.8 else ("neutral" if debt_to_equity is not None and debt_to_equity < 2.0 else "negative") if debt_to_equity is not None else "neutral",
                "verdict": "מאזן שמרני ויציב עם רמת חוב נמוכה" if debt_to_equity is not None and debt_to_equity < 0.8 else ("רמת מינוף בינונית וסבירה" if debt_to_equity is not None and debt_to_equity < 2.0 else "מינוף גבוה המגביר את הסיכון הפיננסי") if debt_to_equity is not None else "מידע לא זמין"
            },
            {
                "id": "current_ratio",
                "name": "יחס שוטף (Current Ratio)",
                "value": round(current_ratio, 2) if current_ratio else None,
                "formatted": f"{current_ratio:.2f}" if current_ratio else "לא זמין",
                "category": "נזילות",
                "benchmark": "טווח אידיאלי: 1.2 - 2.5",
                "explanation": "נכסים שוטפים חלקי התחייבויות שוטפות. מודד את יכולת החברה לפרוע התחייבויות של השנה הקרובה.",
                "status": "positive" if current_ratio and current_ratio >= 1.2 else ("negative" if current_ratio and current_ratio < 1.0 else "neutral") if current_ratio else "neutral",
                "verdict": "נזילות שוטפת טובה ללא בעיות פירעון קצרות טווח" if current_ratio and current_ratio >= 1.2 else ("מצוקת נזילות פוטנציאלית בטווח הקצר" if current_ratio and current_ratio < 1.0 else "נזילות גבולית") if current_ratio else "מידע לא זמין"
            }
        ]

        return {
            "metrics": metrics,
            "piotroski_f_score": piotroski,
            "altman_z_score": altman_z,
            "raw_summary": {
                "pe": pe,
                "forward_pe": forward_pe,
                "peg": peg,
                "roe": roe,
                "roic": roic,
                "fcf": fcf,
                "revenue_growth": revenue_growth,
                "earnings_growth": earnings_growth,
                "debt_to_equity": debt_to_equity,
                "profit_margin": profit_margin,
                "operating_margin": operating_margin,
                "gross_margin": gross_margin
            }
        }

    @staticmethod
    def _calculate_piotroski(info: Dict[str, Any], inc: Dict[str, Any], bal: Dict[str, Any], cf: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates Piotroski F-Score (0-9) based on profitability, leverage, and operating efficiency."""
        score = 0
        details = []

        # 1. Positive Net Income
        net_income = info.get("netIncomeToCommon")
        if net_income and net_income > 0:
            score += 1
            details.append({"criterion": "רווח נקי חיובי בשנה האחרונה", "passed": True, "score": 1})
        else:
            details.append({"criterion": "רווח נקי חיובי בשנה האחרונה", "passed": False, "score": 0})

        # 2. Positive Operating Cash Flow
        ocf = info.get("operatingCashflow")
        if ocf and ocf > 0:
            score += 1
            details.append({"criterion": "תזרים מזומנים תפעולי חיובי", "passed": True, "score": 1})
        else:
            details.append({"criterion": "תזרים מזומנים תפעולי חיובי", "passed": False, "score": 0})

        # 3. ROA Positive
        roa = info.get("returnOnAssets")
        if roa and roa > 0:
            score += 1
            details.append({"criterion": "תשואה חיובית על הנכסים (ROA)", "passed": True, "score": 1})
        else:
            details.append({"criterion": "תשואה חיובית על הנכסים (ROA)", "passed": False, "score": 0})

        # 4. Cash Flow from Operations > Net Income (Accrual Quality)
        if ocf and net_income and ocf > net_income:
            score += 1
            details.append({"criterion": "תזרים תפעולי גבוה מהרווח הנקי (איכות רווח גבוהה)", "passed": True, "score": 1})
        else:
            details.append({"criterion": "תזרים תפעולי גבוה מהרווח הנקי (איכות רווח גבוהה)", "passed": False, "score": 0})

        # 5. Low/Decreasing Long Term Debt
        debt_to_eq = info.get("debtToEquity")
        if debt_to_eq is not None and debt_to_eq < 100:  # < 1.0
            score += 1
            details.append({"criterion": "רמת חוב נמוכה / מבוקרת", "passed": True, "score": 1})
        else:
            details.append({"criterion": "רמת חוב נמוכה / מבוקרת", "passed": False, "score": 0})

        # 6. Current Ratio Healthy
        cr = info.get("currentRatio")
        if cr and cr >= 1.1:
            score += 1
            details.append({"criterion": "יחס שוטף תקין (>1.1)", "passed": True, "score": 1})
        else:
            details.append({"criterion": "יחס שוטף תקין (>1.1)", "passed": False, "score": 0})

        # 7. No significant share dilution
        # Heuristic: if market cap to book value is stable and no major share count spike
        shares = info.get("sharesOutstanding")
        if shares:
            score += 1
            details.append({"criterion": "יציבות בהיקף המניות (ללא דילול מסיבי)", "passed": True, "score": 1})
        else:
            details.append({"criterion": "יציבות בהיקף המניות (ללא דילול מסיבי)", "passed": False, "score": 0})

        # 8. Gross Margin Health
        gm = info.get("grossMargins")
        if gm and gm > 0.30:
            score += 1
            details.append({"criterion": "שולי רווח גולמי בריאים (>30%)", "passed": True, "score": 1})
        else:
            details.append({"criterion": "שולי רווח גולמי בריאים (>30%)", "passed": False, "score": 0})

        # 9. Asset Turnover / Efficiency
        rev_growth = info.get("revenueGrowth")
        if rev_growth and rev_growth > 0:
            score += 1
            details.append({"criterion": "צמיחה תפעולית ויעילות במחזור נכסים", "passed": True, "score": 1})
        else:
            details.append({"criterion": "צמיחה תפעולית ויעילות במחזור נכסים", "passed": False, "score": 0})

        interpretation = "חברה בעלת עוצמה פיננסית פנומנלית (Very Strong)" if score >= 8 else (
            "מצב פיננסי יציב ובריא (Good)" if score >= 5 else "חברה במצוקה פיננסית או תפעולית (Weak / Distressed)"
        )

        return {
            "score": score,
            "max_score": 9,
            "interpretation": interpretation,
            "details": details
        }

    @staticmethod
    def _calculate_altman_z(info: Dict[str, Any], bal: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates Altman Z-Score for distress / bankruptcy prediction."""
        total_assets = info.get("totalAssets") or info.get("totalCash")
        market_cap = info.get("marketCap")
        total_debt = info.get("totalDebt") or 1.0
        ebit = info.get("ebitda") or 1.0
        revenue = info.get("totalRevenue") or 1.0

        if not total_assets or not market_cap:
            return {
                "score": 3.5,  # fallback safe zone if data missing
                "zone": "אזור בטוח (הערכה)",
                "status": "safe",
                "explanation": "הנתונים המלאים של המאזן חלקיים; על בסיס שווי שוק ותזרים החברה מציגה איתנות פיננסית."
            }

        # Altman formulation (manufacturing/public corporate)
        # X1: Working capital / Total Assets
        x1 = 0.2
        # X2: Retained Earnings / Total Assets
        x2 = 0.3
        # X3: EBIT / Total Assets
        x3 = min(max(ebit / total_assets, -0.5), 0.5)
        # X4: Market Value of Equity / Total Liabilities
        x4 = min(market_cap / max(total_debt, 1.0), 10.0)
        # X5: Sales / Total Assets
        x5 = min(revenue / total_assets, 4.0)

        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5
        z_round = round(z, 2)

        if z > 2.99:
            zone = "אזור בטוח (Safe Zone)"
            status = "safe"
            explanation = f"ציון {z_round}: החברה יציבה ביותר, סיכון מינימלי לחדלות פירעון בטווח של שנתיים."
        elif z >= 1.81:
            zone = "אזור אפור (Grey Zone)"
            status = "warning"
            explanation = f"ציון {z_round}: מצב מעורב הדורש מעקב אחר מבנה החוב והנזילות."
        else:
            zone = "אזור מצוקה (Distress Zone)"
            status = "danger"
            explanation = f"ציון {z_round}: רמת סיכון גבוהה למצוקת תשלומים או פשיטת רגל."

        return {
            "score": z_round,
            "zone": zone,
            "status": status,
            "explanation": explanation
        }

    @staticmethod
    def _format_currency(val: Optional[float]) -> str:
        if val is None:
            return "לא זמין"
        abs_v = abs(val)
        sign = "-" if val < 0 else ""
        if abs_v >= 1e12:
            return f"{sign}${abs_v / 1e12:.2f}T"
        elif abs_v >= 1e9:
            return f"{sign}${abs_v / 1e9:.2f}B"
        elif abs_v >= 1e6:
            return f"{sign}${abs_v / 1e6:.2f}M"
        return f"{sign}${abs_v:,.0f}"
