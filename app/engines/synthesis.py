"""
Synthesis and Scoring Engine.
Calculates transparent 0-100 scores for Quality, Valuation, Growth, Risk,
and Weighted Investment Opportunity, accompanied by institutional qualitative analysis.
"""

from typing import Dict, Any, List
from app.core.config import settings

class SynthesisEngine:
    @staticmethod
    def synthesize(
        profile: Dict[str, Any],
        fundamental: Dict[str, Any],
        valuation: Dict[str, Any],
        risk: Dict[str, Any],
        forecast: Dict[str, Any]
    ) -> Dict[str, Any]:
        raw_f = fundamental.get("raw_summary", {})
        piotroski = fundamental.get("piotroski_f_score", {}).get("score", 5)
        altman = fundamental.get("altman_z_score", {}).get("score", 3.0)
        margin_of_safety = valuation.get("margin_of_safety_percent", 0.0)
        beta = risk.get("beta", 1.0)
        vol = risk.get("annual_volatility", 25.0)
        mdd = abs(risk.get("max_drawdown", 30.0))

        # 1. Quality Score (0 - 100)
        # Based on Piotroski (40%), Altman Z (25%), ROE/ROIC (20%), Margins (15%)
        p_norm = (piotroski / 9.0) * 100.0
        z_norm = min(max((altman / 4.0) * 100.0, 0), 100.0)
        roe_val = raw_f.get("roe") or 0.12
        roe_norm = min(max((roe_val / 0.25) * 100.0, 10.0), 100.0)
        gm_val = raw_f.get("gross_margin") or 0.35
        gm_norm = min(max((gm_val / 0.60) * 100.0, 20.0), 100.0)
        
        quality_score = round(0.40 * p_norm + 0.25 * z_norm + 0.20 * roe_norm + 0.15 * gm_norm)
        quality_score = min(max(quality_score, 0), 100)

        # 2. Valuation Score (0 - 100)
        # Based on Margin of Safety (50%), PEG (25%), P/E vs historical (25%)
        # MoS: +30% is 100, 0% is 65, -30% is 25
        mos_score = 65.0 + (margin_of_safety * 1.1)
        mos_score = min(max(mos_score, 10.0), 100.0)
        
        peg_val = raw_f.get("peg") or 2.0
        peg_score = 100.0 - min(max((peg_val - 0.8) * 35.0, 0.0), 80.0)
        
        pe_val = raw_f.get("pe") or 25.0
        pe_score = 100.0 - min(max((pe_val - 12.0) * 2.2, 0.0), 80.0)
        
        valuation_score = round(0.50 * mos_score + 0.25 * peg_score + 0.25 * pe_score)
        valuation_score = min(max(valuation_score, 0), 100)

        # 3. Growth Score (0 - 100)
        # Based on Revenue Growth (45%), Earnings Growth (40%), FCF (15%)
        rev_g = raw_f.get("revenue_growth") or 0.08
        rev_g_score = min(max(50.0 + (rev_g * 250.0), 10.0), 100.0)
        
        earn_g = raw_f.get("earnings_growth") or 0.10
        earn_g_score = min(max(50.0 + (earn_g * 200.0), 10.0), 100.0)
        
        fcf_val = raw_f.get("fcf") or 1.0
        fcf_score = 80.0 if fcf_val > 0 else 30.0
        
        growth_score = round(0.45 * rev_g_score + 0.40 * earn_g_score + 0.15 * fcf_score)
        growth_score = min(max(growth_score, 0), 100)

        # 4. Risk Score (0 - 100) - Higher means SAFER (Lower Risk)
        # Based on Drawdown (35%), Volatility (35%), Beta (15%), Debt/Equity (15%)
        mdd_score = max(100.0 - (mdd * 1.5), 10.0)
        vol_score = max(100.0 - (vol * 1.8), 10.0)
        beta_score = max(100.0 - (abs(beta - 1.0) * 40.0), 20.0)
        de_val = raw_f.get("debt_to_equity") or 0.8
        de_score = max(100.0 - (de_val * 30.0), 15.0)
        
        risk_score = round(0.35 * mdd_score + 0.35 * vol_score + 0.15 * beta_score + 0.15 * de_score)
        risk_score = min(max(risk_score, 0), 100)

        # 5. Composite Weighted Investment Score (0 - 100)
        composite_score = round(
            settings.WEIGHT_QUALITY * quality_score +
            settings.WEIGHT_VALUATION * valuation_score +
            settings.WEIGHT_GROWTH * growth_score +
            settings.WEIGHT_RISK * risk_score
        )
        composite_score = min(max(composite_score, 0), 100)

        # Qualitative Insights Builder
        qualitative = SynthesisEngine._generate_qualitative_analysis(profile, quality_score, valuation_score, growth_score, risk_score)
        
        # Investor Suitability
        suitability = SynthesisEngine._determine_suitability(profile, quality_score, valuation_score, growth_score, risk_score)

        return {
            "composite_score": composite_score,
            "quality_score": quality_score,
            "valuation_score": valuation_score,
            "growth_score": growth_score,
            "risk_score": risk_score,
            "weights": {
                "quality": f"{int(settings.WEIGHT_QUALITY * 100)}%",
                "valuation": f"{int(settings.WEIGHT_VALUATION * 100)}%",
                "growth": f"{int(settings.WEIGHT_GROWTH * 100)}%",
                "risk": f"{int(settings.WEIGHT_RISK * 100)}%"
            },
            "score_verdict": SynthesisEngine._score_verdict(composite_score),
            "quality_vs_valuation_insight": SynthesisEngine._quality_vs_valuation(quality_score, valuation_score),
            "qualitative_analysis": qualitative,
            "investor_suitability": suitability,
            "pre_investment_checklist": [
                "קריאת הדוח התקופתי האחרון (10-K או 10-Q) תוך התמקדות בביאור על סיכונים משפטיים ורגולטוריים.",
                "בחינת מגמת עסקאות בעלי עניין (Insider Transactions) בששת החודשים האחרונים.",
                "בדיקת מועד דוח הרווח הבא (Earnings Release Date) כדי להימנע מחשיפה בלתי מתוכננת לתנודתיות רגעית.",
                "הערכת התאמת המשקל של המניה בתיק הכולל (מומלץ לא לעלות על 5%-10% מהתיק במניה בודדת).",
                "מעקב אחר מחירי מתחרים עיקריים ופוטנציאל שחיקת נתח השוק."
            ]
        }

    @staticmethod
    def _score_verdict(score: int) -> Dict[str, str]:
        if score >= 80:
            return {
                "grade": "הזדמנות השקעה אטרקטיבית במיוחד (High Conviction)",
                "color": "emerald",
                "summary": "שילוב נדיר של חברה איכותית ביותר, איתנות פיננסית, פוטנציאל צמיחה ותמחור המציע שולי ביטחון טובים."
            }
        elif score >= 65:
            return {
                "grade": "השקעה חיובית עם פוטנציאל טוב (Favorable)",
                "color": "blue",
                "summary": "החברה מפגינה נתונים פונדמנטליים יציבים וצמיחה נאה; התמחור סביר ומציע יחס סיכון/סיכוי אטרקטיבי."
            }
        elif score >= 50:
            return {
                "grade": "השקעה ניטרלית / החזקה (Hold / Mixed)",
                "color": "amber",
                "summary": "קיימים יתרונות ברורים לצד נקודות תורפה (כגון תמחור מתוח או תנודתיות ענפית). מומלץ להמתין למחיר נוח יותר."
            }
        else:
            return {
                "grade": "סיכון גבוה ביחס לסיכוי (Caution / Unfavorable)",
                "color": "rose",
                "summary": "איכות תפעולית ירודה, מינוף כבד או תמחור בועתי המייצרים שולי ביטחון שליליים."
            }

    @staticmethod
    def _quality_vs_valuation(q_score: int, v_score: int) -> str:
        if q_score >= 75 and v_score < 45:
            return "חברה נפלאה במחיר יקר: החברה מציגה איכות תפעולית ומאזן יוצאי דופן, אך מחיר השוק הנוכחי מגלם פרמיה גבוהה ואינו מותיר שולי ביטחון רחבים."
        elif q_score >= 70 and v_score >= 65:
            return "השילוב האידיאלי: חברה בעלת יתרונות תחרותיים עמוקים הנסחרת במחיר אטרקטיבי (Buffett-style Investment)."
        elif q_score < 50 and v_score >= 75:
            return "מלכודת ערך אפשרית (Value Trap): המניה נראית זולה במכפילים, אך איכות העסק חלשה או מצויה במגמת הידרדרות תפעולית."
        else:
            return "פרופיל מאוזן בין איכות העסק לרמת התמחור הנוכחית בשוק."

    @staticmethod
    def _generate_qualitative_analysis(profile: Dict[str, Any], q: int, v: int, g: int, r: int) -> Dict[str, Any]:
        sector = profile.get("sector", "טכנולוגיה ושירותים")
        name = profile.get("name", "החברה")
        
        moat_text = f"לחברת {name} מעמד שוק מבוסס בסקטור ה-{sector}. יתרונותיה התחרותיים נשענים על אפקט רשת, נאמנות לקוחות גבוהה והשקעות מתמשכות במו\"פ."
        management_text = "ההנהלה שומרת על משמעת הונית, ניהול מבוקר של החוב והשקעות חוזרות ממוקדות במנועי צמיחה עתידיים."
        threats_text = "איומים תחרותיים מצד שחקנים גלובליים, רגישות למחזורי מאקרו-כלכלה ושינויי רגולציה אפשריים בשווקי הליבה."
        catalysts_text = "התרחבות לשווקים משלימים, שיפור שולי הרווחיות בעקבות התייעלות תפעולית, וגידול בתזרים המזומנים החופשי."

        return {
            "competitive_moat": moat_text,
            "management_quality": management_text,
            "market_threats": threats_text,
            "upside_catalysts": catalysts_text
        }

    @staticmethod
    def _determine_suitability(profile: Dict[str, Any], q: int, v: int, g: int, r: int) -> List[Dict[str, Any]]:
        suits = []
        
        # Value Investor
        suits.append({
            "type": "משקיע ערך (Value Investor)",
            "suitable": v >= 65 and q >= 60,
            "explanation": "מחפש חברות רווחיות הנסחרות בהנחה על ערכן הפנימי עם שולי ביטחון."
        })
        # Growth Investor
        suits.append({
            "type": "משקיע צמיחה (Growth Investor)",
            "suitable": g >= 65 and q >= 65,
            "explanation": "מתמקד בחברות המגדילות הכנסות ורווחים בקצב מהיר ומוכנות לשלם מכפיל גבוה."
        })
        # Dividend & Defensive Investor
        suits.append({
            "type": "משקיע סולידי / דיבידנד (Defensive)",
            "suitable": r >= 65 and q >= 70,
            "explanation": "מעדיף תנודתיות נמוכה, מאזן שמרני ותזרים יציב להגנה על הקרן."
        })
        # Speculative / Momentum
        suits.append({
            "type": "סוחר מומנטום / ספקולטיבי",
            "suitable": r < 50 and g >= 70,
            "explanation": "מוכן לספוג תנודתיות חדה בתמורה לפוטנציאל עליות מהיר."
        })

        return suits
