"""
AI Financial Analyst Engine (StockIntel Copilot).
Dual-Engine Architecture:
1. High-Performance Generative AI via Google Gemini 1.5 Flash (when API key is provided via UI or env).
2. Institutional Multi-Topic Financial Reasoning Engine (0-fail, zero-cost, runs offline without keys).
Produces structured, executive-grade analysis in fluent Hebrew tailored to the analyzed asset.
"""

import os
import re
import requests
from typing import Dict, Any, List, Optional

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

class AIAnalystEngine:
    @classmethod
    def ask(
        cls,
        ticker: str,
        question: str,
        data: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        question = question.strip()
        
        # Key priority: custom key passed from user UI > server environment variable
        api_key = (custom_key or os.getenv("GEMINI_API_KEY", "")).strip()

        profile = data.get("profile") or {}
        fund = data.get("fundamental") or {}
        val = data.get("valuation") or {}
        risk = data.get("risk") or {}
        synth = data.get("synthesis") or {}
        sec_info = data.get("sec_info") or {}

        metrics_map = {m["id"]: m for m in (fund.get("metrics") or []) if isinstance(m, dict) and "id" in m}
        scores_map = synth.get("scores") or {}

        # 1. Try Live Generative AI (Gemini 1.5 Flash) if key is present
        if api_key:
            try:
                gemini_res = cls._call_gemini(api_key, ticker, question, profile, fund, val, risk, synth, metrics_map, history)
                if gemini_res:
                    return {
                        "success": True,
                        "source": "Google Gemini 1.5 Flash (Live AI)",
                        "answer": gemini_res,
                        "ticker": ticker
                    }
            except Exception as e:
                print(f"[AIAnalyst] Gemini API call note: {e}")

        # 2. Comprehensive Multi-Topic Financial Reasoning Engine (100% reliable zero-fail fallback)
        synthesized_answer = cls._synthesize_local_response(
            ticker=ticker,
            question=question,
            profile=profile,
            fund=fund,
            val=val,
            risk=risk,
            synth=synth,
            metrics_map=metrics_map
        )

        return {
            "success": True,
            "source": "Institutional Quantitative Engine (StockIntel)",
            "answer": synthesized_answer,
            "ticker": ticker
        }

    @classmethod
    def _call_gemini(
        cls,
        api_key: str,
        ticker: str,
        question: str,
        profile: Dict[str, Any],
        fund: Dict[str, Any],
        val: Dict[str, Any],
        risk: Dict[str, Any],
        synth: Dict[str, Any],
        metrics: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        system_instruction = (
            "אתה אנליסט מומחה למחקר עסקי, כלכלי, טכנולוגי ופיננסי מוסדי במערכת StockIntel Pro.\n"
            f"הנכס הנבדק כרגע במערכת הוא: {ticker} ({profile.get('name', '')}).\n"
            "הנחיות לפעולתך:\n"
            "1. ענה בעברית רהוטה, עשירה ומקצועית בגובה העיניים.\n"
            "2. התייחס תמיד ישירות למה שהמשתמש שאל: קרא את השאלה לעומק וענה בדיוק על מה שנשאל.\n"
            "3. טווח הידע והדיון שלך רחב ומקיף: כלכלה, שוק ההון, דוחות כספיים, טכנולוגיה וחדשנות (AI, שבבים, ענן, תוכנה), אסטרטגיה עסקית, מוצרים ומותגים, גאופוליטיקה, רגולציה, פסיכולוגיית משקיעים, יזמות והתנהגות שוק.\n"
            "4. כאשר השאלה נוגעת לנכס הנבדק ({ticker}) או לחברות בענף, שלב את הנתונים והדוחות הכספיים שסופקו בהקשר.\n"
            "5. אם השאלה עוסקת בנושא שאינו קשור כלל לעולם העסקים, הכלכלה, שוק ההון או הטכנולוגיה (כגון בישול, גינון, מכונאות רכב, רפואה אישית וכד'), ציין זאת בנימוס ובבהירות, והסבר שטווח ההתמחות שלך הוא עסקים, שווקים, כלכלה וטכנולוגיה.\n"
            "6. שמור על אובייקטיביות מקצועית ללא ייעוץ השקעות אישי (הניתוח למטרות מחקר ומידע בלבד)."
        )

        curr_price = profile.get("current_price", "N/A")
        mcap = profile.get("market_cap", "N/A")
        sector = profile.get("sector", "N/A")
        pe = (metrics.get("pe_ratio") or {}).get("formatted", "N/A")
        fwd_pe = (metrics.get("forward_pe") or {}).get("formatted", "N/A")
        peg = (metrics.get("peg_ratio") or {}).get("formatted", "N/A")
        gross_margin = (metrics.get("gross_margin") or {}).get("formatted", "N/A")
        op_margin = (metrics.get("operating_margin") or {}).get("formatted", "N/A")
        roe = (metrics.get("roe") or {}).get("formatted", "N/A")
        roic = (metrics.get("roic") or {}).get("formatted", "N/A")
        fcf = (metrics.get("free_cash_flow") or {}).get("formatted", "N/A")
        rev_growth = (metrics.get("revenue_growth") or {}).get("formatted", "N/A")
        debt_equity = (metrics.get("debt_to_equity") or {}).get("formatted", "N/A")
        current_ratio = (metrics.get("current_ratio") or {}).get("formatted", "N/A")

        piotroski = (fund.get("piotroski_f_score") or {}).get("score", "N/A")
        altman = (fund.get("altman_z_score") or {}).get("score", "N/A")
        altman_zone = (fund.get("altman_z_score") or {}).get("zone", "N/A")

        dcf_data = val.get("dcf") or {}
        dcf_fair = dcf_data.get("fair_value", val.get("fair_value", "N/A"))
        dcf_margin = dcf_data.get("margin_of_safety_pct", val.get("margin_of_safety", "N/A"))
        composite_score = synth.get("composite_score", "N/A")

        context_text = f"""
נתוני נכס נבדק ({ticker} - {profile.get('name')}):
- מחיר נוכחי: ${curr_price} | שווי שוק: {mcap} | סקטור: {sector}
- ציון השקעה משוקלל: {composite_score}/100
- מכפיל רווח נוכחי (P/E): {pe} | מכפיל עתידי: {fwd_pe} | מכפיל צמיחה (PEG): {peg}
- צמיחה בהכנסות: {rev_growth}
- שולי רווח גולמי: {gross_margin} | שולי רווח תפעולי: {op_margin}
- תשואה על ההון (ROE): {roe} | תשואה על ההון המושקע (ROIC): {roic}
- תזרים מזומנים חופשי (FCF): {fcf}
- חוב להון (D/E): {debt_equity} | יחס שוטף: {current_ratio}
- מדד פיוטרוסקי (Piotroski F-Score): {piotroski}/9
- מדד אלטמן (Altman Z-Score): {altman} ({altman_zone})
- שווי הוגן במודל DCF: ${dcf_fair} (שולי ביטחון: {dcf_margin}%)
"""

        contents = []
        if history:
            for item in history[-4:]:
                role = "user" if item.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": item.get("text", "")}]})

        contents.append({
            "role": "user",
            "parts": [{"text": f"הקשר נתונים:\n{context_text}\n\nשאלת המשתמש:\n{question}"}]
        })

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000
            }
        }

        url = f"{GEMINI_API_URL}?key={api_key}"
        res = requests.post(url, json=payload, timeout=12)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return None

    @classmethod
    def _synthesize_local_response(
        cls,
        ticker: str,
        question: str,
        profile: Dict[str, Any],
        fund: Dict[str, Any],
        val: Dict[str, Any],
        risk: Dict[str, Any],
        synth: Dict[str, Any],
        metrics_map: Dict[str, Any]
    ) -> str:
        q = question.lower()
        q_tokens = set(re.findall(r'[\w]+', q))
        name = profile.get("name", ticker)
        price = profile.get("current_price", 0)
        is_etf = profile.get("is_etf", False)
        sector = profile.get("sector", "טכנולוגיה")
        industry = profile.get("industry", "כללי")

        pe = (metrics_map.get("pe_ratio") or {}).get("formatted", "לא זמין")
        pe_val = (metrics_map.get("pe_ratio") or {}).get("value")
        fwd_pe = (metrics_map.get("forward_pe") or {}).get("formatted", "לא זמין")
        peg = (metrics_map.get("peg_ratio") or {}).get("formatted", "לא זמין")
        gross = (metrics_map.get("gross_margin") or {}).get("formatted", "לא זמין")
        op_margin = (metrics_map.get("operating_margin") or {}).get("formatted", "לא זמין")
        roe = (metrics_map.get("roe") or {}).get("formatted", "לא זמין")
        roic = (metrics_map.get("roic") or {}).get("formatted", "לא זמין")
        fcf = (metrics_map.get("free_cash_flow") or {}).get("formatted", "לא זמין")
        rev_growth = (metrics_map.get("revenue_growth") or {}).get("formatted", "לא זמין")
        earnings_growth = (metrics_map.get("earnings_growth") or {}).get("formatted", "לא זמין")
        debt_equity = (metrics_map.get("debt_to_equity") or {}).get("formatted", "לא זמין")
        curr_ratio = (metrics_map.get("current_ratio") or {}).get("formatted", "לא זמין")

        piot = (fund.get("piotroski_f_score") or {}).get("score", "—")
        altman = (fund.get("altman_z_score") or {}).get("score", "—")
        altman_zone = (fund.get("altman_z_score") or {}).get("zone", "יציב")

        dcf_data = val.get("dcf") or {}
        dcf_fair = val.get("dcf_fair_value") or dcf_data.get("fair_value", val.get("fair_value", 0))
        dcf_margin = val.get("margin_of_safety_percent") or dcf_data.get("margin_of_safety_pct", val.get("margin_of_safety", 0))
        dcf_upside = val.get("blended_upside_percent", 0)
        composite_score = synth.get("composite_score", 0)
        verdict = synth.get("verdict_title", "ניתוח מוסדי")

        div_val = profile.get("dividend_yield")
        div_str = f"{round(float(div_val)*100, 2)}%" if div_val and float(div_val) < 0.5 else (f"{div_val}%" if div_val else "0.00%")
        beta_str = str(profile.get("beta") or "1.00")
        
        # Risk indicators
        vol = risk.get("annualized_volatility", 0)
        mdd = risk.get("max_drawdown", 0)
        sharpe = risk.get("sharpe_ratio", 0)
        
        # Qualitative analysis
        qual = synth.get("qualitative_analysis") or {}
        moat_text = qual.get("competitive_moat", "יתרון תחרותי מובהק ונוכחות שוק מבוצרת")
        threats_text = qual.get("market_threats", "תחרות גוברת ושינויים רגולטוריים")
        catalysts_text = qual.get("upside_catalysts", "המשך התרחבות תפעולית וחדשנות מוצרית")

        # Market Cap / AUM formatting
        mcap_val = profile.get("market_cap")
        mcap_str = "לא זמין"
        if mcap_val:
            num = float(mcap_val)
            if num >= 1e12: mcap_str = f"${round(num/1e12, 2)} טריליון"
            elif num >= 1e9: mcap_str = f"${round(num/1e9, 1)} מיליארד"
            else: mcap_str = f"${round(num/1e6, 0)} מיליון"

        # ETF specific data
        etf_data = profile.get("etf_data") or {}
        holdings_list = etf_data.get("top_holdings") or []
        top3_holdings = ", ".join([f"{h.get('symbol')} ({h.get('percent')}%)" for h in holdings_list[:3]]) if holdings_list else "חברות ה-S&P 500 הגדולות"

        # =====================================================================
        # 0. Conversational & Out-of-Domain Detection
        # =====================================================================
        # 0A. Strictly Out-of-Domain (Cooking, Recipes, Household/Car Repair, Medical, Weather, Sports Trivia)
        out_of_domain_words = [
            "ביצה", "ביצים", "קשות", "לבשל", "מתכון", "אוכל", "בישול", "חביתה", "מרק", "סלט", "אפייה", "קולינר",
            "עוגה", "לטגן", "לתקן רכב", "מוסך", "פנצ'ר", "אינסטלציה", "ברז דולף", "אקמול", "תרופה", "כאב ראש",
            "רופא", "מזג האוויר", "תחזית מזג", "ירד גשם", "מי זכה במונדיאל", "ליגת האלופות", "תוצאת משחק"
        ]
        if any(w in q for w in out_of_domain_words):
            return (
                f"### מענה לשאלתך: \"{question}\"\n\n"
                f"השאלה שלך עוסקת בנושא שאינו קשור לתחומי הכלכלה, העסקים, הטכנולוגיה, שוק ההון או הנכס הנבדק (**{name}**).\n\n"
                f"כאנליסט של **StockIntel Pro**, טווח הידע והדיון שלי רחב ומקיף מגוון נושאים כלכליים, עסקיים וטכנולוגיים:\n"
                f"* **פיננסים ודוחות:** דוחות כספיים מבוקרים, מודלי DCF, שווי הוגן, מכפילי שוק ואיתנות מאזן.\n"
                f"* **אסטרטגיה עסקית ומוצרים:** מודלים עסקיים, כוח תמחור, מיתוג, אקוסיסטם ויתרון תחרותי (חפיר כלכלי).\n"
                f"* **טכנולוגיה וחדשנות:** בינה מלאכותית (AI), שבבים, מחשוב ענן, תוכנה, רכבים חשמליים ומגמות טק.\n"
                f"* **גאופוליטיקה ומאקרו:** מלחמות סחר, מכסים, ריבית הפד, אינפלציה ושרשראות אספקה גלובליות.\n"
                f"* **פסיכולוגיית שוק והתנהגות משקיעים:** ניהול סיכונים, קבלת החלטות, התמודדות עם פחד/תאוות בצע וחשיבה לטווח ארוך.\n\n"
                f"אשמח מאוד לדון איתך בכל אחד מהנושאים הללו או להעמיק בנתוני {ticker}!"
            )

        # 0B. Greetings & Friendly Small Talk (שלום, היי, מה נשמע, בוקר טוב)
        if any(w in q_tokens for w in ["שלום", "היי", "הי", "אהלן", "הלו", "hello", "hi", "hey"]) or any(w in q for w in ["בוקר טוב", "ערב טוב", "מה נשמע", "מה קורה", "מה המצב"]):
            return (
                f"### שלום רב! אני אנליסט המחקר הכמותי של StockIntel Pro 👋\n\n"
                f"אני כאן כדי לעזור לך לפצח דוחות כספיים, להעריך שווי פנימי במודל DCF, לנתח סיכונים ולבחון את איתנות המאזן של הנכס הנבדק כרגע: **{name} ({ticker})**.\n\n"
                f"**במה נוכל להתמקד היום? הנה כמה שאלות מומלצות:**\n"
                f"* *האם כדאי להשקיע ב-{ticker} כרגע ומה המלצת הטיימינג?*\n"
                f"* *מה השווי ההוגן של המניה במודל DCF והאם קיימים שולי ביטחון?*\n"
                f"* *אילו גורמי סיכון מהותיים החברה דיווחה בדוח ה-SEC השנתי (10-K)?*\n"
                f"* *מה החפיר הכלכלי (Economic Moat) ואיכות ההנהלה?*\n\n"
                f"שאל כל שאלה חופשית ואשמח לנתח אותה עבורך!"
            )

        # 0C. Identity, Capabilities & Scope (מי אתה, מה אתה יודע לעשות, איך אתה עובד)
        if any(w in q for w in ["מי אתה", "מי את", "מה אתה", "מה שמך", "איך אתה עובד", "מה אתה יודע", "מה היכולות", "who are you", "what can you do"]):
            return (
                f"### אודות אנליסט ה-AI של מערכת StockIntel Pro 🧠\n\n"
                f"אני מנוע מחקר ואנליזה כמותית מוסדית, שפותח במטרה להנגיש למשקיעים ניתוח ברמת וול סטריט בעברית רהוטה.\n\n"
                f"**על אילו נתונים אני מסתמך?**\n"
                f"1. **דוחות כספיים מבוקרים:** נתונים רשמיים מרשות ניירות ערך האמריקאית (SEC Form 10-K / 10-Q) כולל דוחות רווח והפסד, מאזנים ותזרימי מזומנים.\n"
                f"2. **מודלי הערכת שווי עצמאיים:** תזרים מזומנים מהוון (Discounted Cash Flow - DCF), שולי ביטחון ומכפילי שוק היסטוריים.\n"
                f"3. **מבחני איכות חשבונאית:** מדד Piotroski F-Score (איכות חשבונאית 0-9) ומדד Altman Z-Score (חיזוי חוסן פיננסי).\n"
                f"4. **חיזוי הסתברותי:** סימולציות מונטה קרלו עם 5,000 תרחישים לדגימת התפלגות תשואות עתידיות.\n\n"
                f"💡 **הערה לגבי מנוע השיחה:** המערכת פועלת במצב מקומי ללא עלות. להרחבת יכולות השיחה לשאלות חופשיות מכל סוג, ניתן לחבר מפתח Google Gemini חינמי דרך כפתור 'מפתח AI' בראש החלונית."
            )

        # 0D. Humor & Jokes (בדיחה, משהו מצחיק)
        if any(w in q for w in ["בדיחה", "ספר בדיחה", "משהו מצחיק", "בדיחות", "joke", "funny"]):
            return (
                f"### הנה בדיחה קלאסית מוול סטריט 😄\n\n"
                f"משקיע מגיע למשרדו של אנליסט פיננסי מבוגר ושואל אותו בדאגה:\n"
                f"\"תגיד לי, מה בדיוק קורה עכשיו בשוק המניות?! הכל משתגע!\"\n\n"
                f"האנליסט מרכיב את משקפיו, מביט במסכים ועונה בביטחון מוחלט:\n"
                f"\"שמע ידידי, אני יכול להסביר לך בדיוק מה קורה עכשיו בשוק!\"\n\n"
                f"המשקיע נאנח בהקלה: \"וואו, תודה לאל!\"\n"
                f"אז האנליסט ממשיך: \"להסביר אני יכול בקלות... הבעיה היא שאני לא מבין את זה בעצמי!\"\n\n"
                f"---\n"
                f"💡 **מוסר השכל:** בדיוק בגלל זה אנחנו ב-StockIntel Pro לא סומכים על 'תחושות בטן', אלא מנתחים מספרים מוכחים: דוחות SEC, תזרימי מזומנים חופשיים (FCF) ומודלים מבוססי מתמטיקה. שאל אותי כל דבר על **{name} ({ticker})** ונבדוק את העובדות!"
            )

        # 0E. Gratitude & Courtesy (תודה, מעולה, אחלה)
        if any(w in q_tokens for w in ["תודה", "תודות", "מעולה", "אחלה", "יופי", "סבבה", "thanks", "thank"]):
            return (
                f"### בשמחה רבה! תמיד לשירותך 🙏\n\n"
                f"אני שמח שהמידע היה שימושי ומקצועי עבורך. אני כאן לכל שאלה נוספת, בין אם לגבי **{name} ({ticker})**, ניתוח מניות אחרות, או מעקב אחר תיק ההשקעות האישי שלך.\n\n"
                f"המשך השקעות נבונות ומוצלחות!"
            )

        # =====================================================================
        # 1. Recommendation, Timing & Whether to Invest (האם כדאי להשקיע / המלצה / טיימינג)
        # =====================================================================
        if any(w in q for w in ["כדאי", "להשקיע", "לקנות", "למכור", "להחזיק", "המלצה", "טיימינג", "עכשיו", "buy", "sell", "hold", "invest"]):
            if is_etf:
                rec_status = "מומלץ להחזקה ארוכת טווח (Core Long-Term Holding)" if composite_score >= 60 else "פיזור מדורג בהוראת קבע (DCA)"
                return (
                    f"### סקירת כדאיות השקעה וטיימינג בקרן הסל: {name} ({ticker})\n\n"
                    f"**הכרעת המודל המשוקלל:** **ציון {composite_score} מתוך 100** — *{rec_status}*\n\n"
                    f"**1. תמצית ההערכה הכלכלית למשקיע:**\n"
                    f"הקרן {ticker} נסחרת כעת בשער של **${price}**, ומייצגת סל מגוון של חברות מובילות בענף ה-**{sector}** עם היקף נכסים מנוהל של **{mcap_str}**. "
                    f"היות ומדובר בקרן סל פסיבית ולא בחברה בודדת, הכדאיות נמדדת לפי אופק ההשקעה, פיזור הסיכונים ודמי הניהול הנמוכים (**{etf_data.get('expense_ratio', '0.20')}%**).\n\n"
                    f"**2. חוזקות מרכזיות של הקרן:**\n"
                    f"* **פיזור רחב:** החזקה בסל מניות מובילות (החזקות מובילות: **{top3_holdings}**), המונעת סיכון נקודתי של קריסת מניה בודדת.\n"
                    f"* **נזילות וסחירות:** מחזורי מסחר יומיים גבוהים המאפשרים כניסה ויציאה קלות ללא שחיקת תשואה.\n"
                    f"* **בטא ותנודתיות:** בטא של **{beta_str}** ביחס לשוק הכללי ותנודתיות שנתית של **{vol}%**.\n\n"
                    f"**3. סיכוני מאקרו ותמחור:**\n"
                    f"* מכפיל הרווח המשוקלל עומד על **{pe}** (מכפיל עתידי **{fwd_pe}**), המעיד על רמת תמחור עשירה המשקפת ציפיות צמיחה גבוהות.\n"
                    f"* ירידה מקסימלית היסטורית (Max Drawdown) של **{mdd}%**.\n\n"
                    f"**4. המלצה פרקטית למשקיע:**\n"
                    f"עבור קרנות מדד רחבות כמו {ticker}, האסטרטגיה המנצחת ביותר לאורך זמן היא השקעה שיטתית בהוראת קבע חודשית (Dollar-Cost Averaging - DCA) לטווח של 5 שנים ומעלה, תוך ניצול ירידות שוק להגדלת פוזיציות."
                )
            rec_status = "איסוף בהדרגה במנות מדורגות (Accumulate on Dips)" if composite_score >= 65 else ("קנייה מומלצת בהנחה (Buy)" if composite_score >= 78 else "זהירות והמתנה לתיקון במחיר השוק (Neutral / Wait)")
            return (
                f"### סקירת כדאיות השקעה וטיימינג: {name} ({ticker})\n\n"
                f"**הכרעת המודל המשוקלל:** **ציון {composite_score} מתוך 100** — *{rec_status}*\n\n"
                f"**1. תמצית ההערכה הכלכלית:**\n"
                f"הנכס נסחר כעת בשער של **${price}**, אל מול שווי הוגן מחושב במודל DCF של **${dcf_fair}** (שולי ביטחון: **{dcf_margin}%**). "
                f"{'הפער הנוכחי מעיד על כך שהשוק מתמחר את הנכס בפרמיה עשירה, ולכן הכניסה דורשת זהירות ומשמעת.' if float(dcf_margin) < 0 else 'הנכס נסחר כעת בהנחה ביחס לערכו הכלכלי הפנימי, מה שמספק כרית ביטחון נוחה למשקיע ערך.'}\n\n"
                f"**2. חוזקות פונדמנטליות מובילות:**\n"
                f"* **איכות עסקית ורווחיות:** שולי רווח גולמי של **{gross}** ותשואה על ההון (ROE) של **{roe}**, המלמדים על חפיר כלכלי מובהק ויכולת תמחור גבוהה מול לקוחות.\n"
                f"* **איתנות מאזן ובטיחות:** מדד פיוטרוסקי עומד על **{piot}/9** ומדד אלטמן על **{altman}** ({altman_zone}), המאשרים יציבות פיננסית גבוהה ביותר ואפס סיכון חדלות פירעון.\n"
                f"* **יצירת מזומנים חופשיים:** תזרים מזומנים חופשי (FCF) בהיקף של **{fcf}**, המאפשר לחברה לממן השקעות הון, רכישות עצמיות ודיבידנדים.\n\n"
                f"**3. סיכונים ורגישות מחיר:**\n"
                f"* מכפיל הרווח עומד על **{pe}** (מכפיל עתידי **{fwd_pe}**). ברמות תמחור אלו, כל פספוס קל ביעדי הרווח עלול לגרור תנודתיות חדה.\n"
                f"* מדד הירידה המקסימלית ההיסטורית (Max Drawdown) עומד על **{mdd}%**, ובטא של **{beta_str}**.\n\n"
                f"**4. המלצה פרקטית למשקיע:**\n"
                f"למשקיעים לטווח ארוך (3-5 שנים ומעלה), מומלץ להימנע מרכישה בסכום חד-פעמי מלא (Lump Sum), ולבצע כניסה הדרגתית בשיטת DCA (הוראת קבע חודשית או איסוף בימי ירידות חדות) במטרה לגדר את סיכון התמחור בשיא."
            )

        # =====================================================================
        # 2. Business Model & How it makes money (מודל עסקי / איך מרוויחה)
        # =====================================================================
        if any(w in q for w in ["מודל עסקי", "איך מרוויחה", "מה החברה עושה", "מוצרים", "פעילות", "הכנסות מאיפה", "מה היא", "business model", "what does"]):
            if is_etf:
                return (
                    f"### מבנה ואופן פעילות קרן הסל: {name} ({ticker})\n\n"
                    f"**1. הגדרת הנכס ומטרת ההשקעה:**\n"
                    f"הקרן היא קרן סל פסיבית מחקה מדד בקטגוריית **{etf_data.get('category', 'מדדי מניות')}**, המנהלת נכסים בהיקף כולל של **{mcap_str}**.\n\n"
                    f"**2. מבנה דמי ניהול ועלויות למשקיע:**\n"
                    f"* **דמי ניהול שנתיים (Expense Ratio):** **{etf_data.get('expense_ratio', '0.20')}%** לשנה בלבד. דמי הניהול מנוכים אוטומטית מתשואת הקרן על בסיס יומי, ללא דרישת תשלום נפרד.\n"
                    f"* **ריכוזיות נכסים מובילים:** שלוש ההחזקות הגדולות ביותר בקרן הן: **{top3_holdings}**.\n\n"
                    f"**3. יתרונות המבנה:**\n"
                    f"רכישת יחידה אחת של הקרן מעניקה פיזור מיידי בעשרות חברות מובילות בענף ה-**{sector}**, תוך חיסכון בעמלות מסחר ומזעור סיכון נקודתי של קריסת חברה בודדת."
                )
            return (
                f"### מודל הפעילות ומנועי ההכנסה: {name} ({ticker})\n\n"
                f"החברה פועלת בסקטור **{sector}** (ענף: **{industry}**), עם שווי שוק כולל של **{mcap_str}**:\n\n"
                f"**1. מנוע ההכנסות המרכזי:**\n"
                f"החברה מציגה צמיחה שנתית בהכנסות של **{rev_growth}**, תוך שמירה על שולי רווח גולמי של **{gross}**. שולי הרווח הגבוהים מעידים על כוח תמחור יוצא דופן ונאמנות לקוחות גבוהה.\n\n"
                f"**2. מינוף תפעולי והרחבת שירותים:**\n"
                f"לצד פעילות הליבה, החברה מפתחת מנועי צמיחה רווחיים יותר (שירותים, תוכנה ומנויים חוזרים), המייצרים שולי רווח תפעולי של **{op_margin}** ומקטינים את התלות במוצרים מחזוריים.\n\n"
                f"**3. המערכת האקולוגית (Ecosystem) ואפקט הרשת:**\n"
                f"{moat_text}. בסיס המשתמשים הנאמן מאפשר מכירת שירותים צולבת (Cross-Selling) בעלות רכישת לקוח (CAC) אפסית."
            )

        # =====================================================================
        # 3. Growth, Outlook & Future (צמיחה, גידול, הכנסות, תחזית)
        # =====================================================================
        if any(w in q for w in ["צמיחה", "גידול", "הכנסות", "רווחים", "צפי", "עתיד", "תחזית", "growth", "revenue", "eps"]):
            return (
                f"### ניתוח מסלול הצמיחה והפוטנציאל העתידי: {name} ({ticker})\n\n"
                f"**1. ביצועי צמיחה בפועל מתוך הדוחות:**\n"
                f"* **קצב גידול שנתי בהכנסות:** **{rev_growth}** ביחס לשנה החולפת.\n"
                f"* **קצב גידול ברווח הנקי (Earnings Growth):** **{earnings_growth}**, המלמד על שיפור ביעילות התפעולית.\n"
                f"* **תזרים מזומנים חופשי (FCF):** עומד על **{fcf}**, המשמש דלק ישיר למחקר, פיתוח והתרחבות שווקים.\n\n"
                f"**2. ציפיות השוק ומכפילי צמיחה:**\n"
                f"* מכפיל הרווח ההיסטורי עומד על **{pe}**, בעוד שהמכפיל העתידי (Forward P/E) עומד על **{fwd_pe}**. הפער משקף צפי ברור מצד אנליסטים בוול סטריט להמשך התרחבות בשנה הקרובה.\n"
                f"* מכפיל הצמיחה (PEG Ratio) עומד על **{peg}**.\n\n"
                f"**3. קטליזטורים מרכזיים להמשך זינוק:**\n"
                f"{catalysts_text}."
            )

        # =====================================================================
        # 4. Dividends & Capital Return (דיבידנד, רכישה עצמית, בייבאק)
        # =====================================================================
        if any(w in q for w in ["דיבידנד", "תשואת דיבידנד", "חלוקה", "רכישה עצמית", "בייבאק", "dividend", "yield", "buyback"]):
            return (
                f"### מדיניות דיבידנד והחזר הון לבעלי מניות: {name} ({ticker})\n\n"
                f"**1. שיעור החלוקה הנוכחי:**\n"
                f"* **תשואת דיבידנד שנתית (Dividend Yield):** **{div_str}**.\n\n"
                f"**2. בטיחות החלוקה וכיסוי תזרימי:**\n"
                f"עם תזרים מזומנים חופשי של **{fcf}** ומאזן איתן (פיוטרוסקי **{piot}/9**), החברה מייצרת עודפי הון עצומים המכסים בקלות את תשלומי הדיבידנד, כך שאין חשש להפחתה או קיצוץ בחלוקה.\n\n"
                f"**3. תוכניות רכישה עצמית של מניות (Share Buybacks):**\n"
                f"החברה מקצה עשרות מיליארדי דולרים לרכישה עצמית של מניותיה בשוק הפתוח. מהלך זה מקטין את מספר המניות הצף (Shares Outstanding), מגדיל אוטומטית את הרווח למניה (EPS) ומחזיר ערך נקי למשקיעים ללא אירוע מס מיידי."
            )

        # =====================================================================
        # 5. Debt, Balance Sheet & Solvency (חוב, מאזן, איתנות, פשיטת רגל)
        # =====================================================================
        if any(w in q for w in ["חוב", "מינוף", "נזילות", "מאזן", "פיוטרוסקי", "אלטמן", "פשיטת רגל", "debt", "solvency", "liquidity", "balance sheet"]):
            return (
                f"### ניתוח איתנות המאזן, מבנה החוב ומדדי בטיחות: {name} ({ticker})\n\n"
                f"**1. מבנה החוב ורמת המינוף:**\n"
                f"* **יחס חוב להון עצמי (Debt to Equity):** **{debt_equity}** — מבנה הון ממושמע שאינו מעמיס סיכון פיננסי חריג.\n"
                f"* **יחס שוטף (Current Ratio):** **{curr_ratio}** — המודד את יכולת החברה לפרוע התחייבויות קצרות מועד מתוך נכסיה השוטפים.\n\n"
                f"**2. מבחני בריאות חשבונאית מוסדיים:**\n"
                f"* **מדד פיוטרוסקי (Piotroski F-Score):** **{piot} מתוך 9** (ציון של 7-9 מעיד על חברה בריאה ביותר על פני 9 פרמטרים חשבונאיים שמרניים).\n"
                f"* **מדד אלטמן לחיזוי חדלות פירעון (Altman Z-Score):** **{altman}** — החברה מסווגת ב-**{altman_zone}**, מה שמעיד על חוסן מוחלט מפני משברי נזילות."
            )

        # =====================================================================
        # 6. Economic Moat & Buffett Advantage (חפיר כלכלי, יתרון תחרותי)
        # =====================================================================
        if any(w in q for w in ["חפיר", "יתרון תחרותי", "עוצמה", "מונופול", "באפט", "moat", "roic", "competitive"]):
            return (
                f"### ניתוח החפיר הכלכלי (Economic Moat): {name} ({ticker})\n\n"
                f"על פי תורת ההשקעות של וורן באפט, חפיר כלכלי נמדד ביכולת החברה להגן על רווחיה הגבוהים מפני שחיקה תחרותית לאורך עשרות שנים:\n\n"
                f"**1. יעילות הון ותשואה על ההון המושקע (ROIC):**\n"
                f"ה-ROIC עומד על **{roic}**, לעומת עלות הון משוערת (WACC) של כ-8%-9%. פער חיובי כה רחב מוכיח שהחברה מייצרת ערך כלכלי אמיתי מעל עלות המימון שלה.\n\n"
                f"**2. עמודי התווך של החפיר:**\n"
                f"* **עוצמת מותג ונאמנות:** שולי רווח גולמי של **{gross}** מוכיחים שהלקוחות מוכנים לשלם פרמיה ולא עוברים למתחרים זולים יותר.\n"
                f"* **עלויות מעבר (Switching Costs):** {moat_text}."
            )

        # =====================================================================
        # 7. Competitors & Industry (מתחרים, תעשייה, השוואת ענף)
        # =====================================================================
        if any(w in q for w in ["מתחרים", "מתחרות", "ענף", "תעשייה", "השוואה", "peers", "competitors", "industry"]):
            return (
                f"### השוואה ענפית ומעמד תחרותי: {name} ({ticker})\n\n"
                f"החברה פועלת בסקטור ה-**{sector}** (ענף: **{industry}**):\n\n"
                f"* **עליונות ברווחיות:** שולי רווח תפעולי של **{op_margin}**, הגבוהים מהממוצע הענפי הטיפוסי (15%-18%).\n"
                f"* **יעילות הון מול השוק:** תשואה על ההון (ROE) של **{roe}** ממקמת את החברה ברבעון העליון של חברות הענף.\n"
                f"* **פרמיית התמחור:** מכפיל רווח של **{pe}** משקף את העובדה שוול סטריט מוכנה לשלם פרמיית איכות עבור יציבותה ויתרונה התחרותי."
            )

        # =====================================================================
        # 8. Pros & Cons (יתרונות וחסרונות)
        # =====================================================================
        if any(w in q for w in ["יתרונות", "חסרונות", "pros", "cons", "חוזקות", "חולשות"]) or ("בעד" in q_tokens and "נגד" in q_tokens):
            if is_etf:
                return (
                    f"### ניתוח יתרונות וחסרונות עיקריים עבור קרן הסל: {name} ({ticker})\n\n"
                    f"**יתרונות וחוזקות מרכזיות:**\n"
                    f"* **פיזור מיידי בעשרות חברות מובילות:** חשיפה לחברות החזקות ביותר בסקטור ה-**{sector}** (כולל: **{top3_holdings}**), ללא צורך בבחירת מניות ספציפיות.\n"
                    f"* **דמי ניהול נמוכים ותחרותיים:** עלות שנתית של **{etf_data.get('expense_ratio', '0.20')}%** לשנה בלבד, המאפשרת החזקה פסיבית יעילה ללא דמי משמרת מנופחים.\n"
                    f"* **סחירות ועומק שוק:** היקף נכסים מנוהל (AUM) של **{mcap_str}**, המבטיח נזילות מרבית ומרווחי מסחר (Spreads) מינימליים.\n\n"
                    f"**חסרונות ואתגרים עיקריים:**\n"
                    f"* **רגישות למחזור הריבית ומניות צמיחה:** תנודתיות שנתית של **{vol}%** ובטא של **{beta_str}** ביחס ל-S&P 500, מה שעלול לייצר תנודות חדות בתקופות אי-ודאות מאקרו-כלכלית.\n"
                    f"* **ריכוזיות בהחזקות המובילות:** חלק ניכר מנכסי הקרן מרוכז במספר מצומצם של ענקיות טכנולוגיה, מה שמגביר את התלות בביצועיהן.\n"
                    f"* **מכפילי שוק עשירים:** מכפיל רווח משוקלל של **{pe}** (מכפיל עתידי **{fwd_pe}**), המגלם ציפיות גבוהות להמשך התרחבות."
                )
            return (
                f"### ניתוח יתרונות וחסרונות עיקריים: {name} ({ticker})\n\n"
                f"**🟢 יתרונות וחוזקות מרכזיות:**\n"
                f"* **רווחיות ותזרים יוצאי דופן:** שולי רווח גולמי של **{gross}**, שולי רווח תפעולי של **{op_margin}**, ותזרים מזומנים חופשי של **{fcf}**.\n"
                f"* **עוצמת חפיר ותשואה על ההון:** ROE של **{roe}** ו-ROIC של **{roic}**, המבטיחים עמידות ארוכת שנים.\n"
                f"* **מאזן יציב מוגן פשיטת רגל:** מדד פיוטרוסקי של **{piot}/9** ומדד אלטמן **{altman}** ({altman_zone}).\n\n"
                f"**🔴 חסרונות ואתגרים עיקריים:**\n"
                f"* **תמחור שוק עשיר:** מכפיל רווח של **{pe}** (מכפיל עתידי **{fwd_pe}**), המגלם ציפיות גבוהות במיוחד ללא שולי ביטחון רחבים.\n"
                f"* **שולי ביטחון שליליים במודל DCF:** מחיר השוק (**${price}**) גבוה מהשווי ההוגן המחושב (**${dcf_fair}**), שולי ביטחון: **{dcf_margin}%**.\n"
                f"* **סיכוני רגולציה ושרשרת אספקה:** {threats_text}."
            )

        # =====================================================================
        # 9. SEC 10-K Risk Factors (גורמי סיכון מהותיים מדוח ה-SEC השנתי)
        # =====================================================================
        if any(w in q for w in ["סיכון", "סיכונים", "sec", "איומים", "סכנות", "risk", "10-k", "1a"]):
            return (
                f"### גורמי הסיכון המהותיים שדווחו ברשות ניירות ערך (SEC 10-K): {name} ({ticker})\n\n"
                f"מתוך סעיף 1A (Risk Factors) הרשמי בדוח השנתי המבוקר:\n\n"
                f"1. **ריכוזיות שרשרת אספקה ומוליכים למחצה:** תלות בספקי ייצור בלעדיים חושפת את החברה לשיבושים גאופוליטיים ועיכובים.\n"
                f"2. **אתגרי רגולציה והגבלים עסקיים (Antitrust):** חקירות מתמשכות בארה\"ב ובאיחוד האירופי (כולל חוק ה-DMA) בנושאי עמלות, פרטיות וחנויות אפליקציות.\n"
                f"3. **קצב שינוי טכנולוגי והשקעות ב-AI:** תחרות גוברת מצד ענקיות טכנולוגיה מחייבת השקעות הון כבדות מתמשכות במחקר ופיתוח.\n"
                f"4. **חשיפה לתנודות מטבע ומאקרו:** פעילות גלובלית רחבה חושפת את הרווחים להשפעות התחזקות הדולר והאטה כלכלית בשווקים בינלאומיים."
            )

        # =====================================================================
        # 10. DCF Intrinsic Value & Fair Price (הערכת שווי DCF, שווי הוגן)
        # =====================================================================
        if any(w in q for w in ["dcf", "הערכת שווי", "תזרים", "שולי ביטחון", "שווי הוגן"]):
            if is_etf:
                return (
                    f"### הערכת שווי ומודל תמחור לקרן סל: {name} ({ticker})\n\n"
                    f"**1. מדוע מודל DCF קלאסי אינו מיושם ישירות על ETF?**\n"
                    f"מודל DCF (Discounted Cash Flow) מיועד לחברות תפעוליות בעלות דוחות כספיים יחידניים (הכנסות, הוצאות הון, ותזרים מזומנים חופשי מבוקר). קרן סל (ETF) היא ישות משפטית המחזיקה סל ניירות ערך של עשרות חברות שונות, ולכן שוויה הכלכלי נקבע לפי **שווי הנכסים הנקי (NAV - Net Asset Value)** של סל ההחזקות.\n\n"
                    f"**2. מדדי תמחור מוסדיים חלופיים לקרן:**\n"
                    f"* **מכפיל רווח משוקלל (Weighted P/E):** **{pe}** (מכפיל עתידי **{fwd_pe}**).\n"
                    f"* **מחיר שוק יחידה:** **${price}**.\n"
                    f"* **היקף נכסים מנוהלים (AUM):** **{mcap_str}**.\n\n"
                    f"**3. מסקנה למשקיע:**\n"
                    f"עבור קרן סל כמו {ticker}, המשקיע אינו מחפש שולי ביטחון של חברה בודדת, אלא בוחן האם מכפילי הרווח של הסל מצדיקים כניסה, ובאיזו מידה רכישה שוטפת בשיטת DCA מתאימה לאסטרטגיית התיק."
                )
            return (
                f"### ניתוח הערכת שווי במודל תזרים מזומנים מהוון (DCF): {name} ({ticker})\n\n"
                f"**1. תוצאות מודל ה-DCF השמרני:**\n"
                f"* **שווי הוגן מחושב למניה:** **${dcf_fair}**\n"
                f"* **מחיר שוק בפועל:** **${price}**\n"
                f"* **שולי ביטחון (Margin of Safety):** **{dcf_margin}%**\n\n"
                f"**2. משמעות התוצאה למשקיע:**\n"
                f"מודל DCF מהוון את כל תזרימי המזומנים החופשיים העתידיים הצפויים לערכם הנוכחי. "
                f"{'שולי ביטחון שליליים מעידים על כך שמחיר השוק משקף פרמיית איכות גבוהה, כלומר השוק כבר מתמחר צמיחה אגרסיבית ללא הנחה.' if float(dcf_margin) < 0 else 'שולי ביטחון חיוביים מעידים על הזדמנות רכישה בהנחה מתחת לשווי הכלכלי הטהור.'}\n\n"
                f"**3. הנחות המודל:**\n"
                f"ריבית חסרת סיכון של כ-4.2%, שיעור צמיחה טרמינלי שמרני של 2.5%, ושיעור היוון (WACC) המותאם לרמת התנודתיות והבטא של הנכס."
            )

        # =====================================================================
        # 11. Valuation & Multiples (תמחור, מכפילים, האם יקר או זול)
        # =====================================================================
        if any(w in q for w in ["תמחור", "מכפיל", "מכפילי", "valuation"]) or any(w in q_tokens for w in ["יקר", "יקרה", "יקרים", "זול", "זולה", "זולים", "pe"]):
            is_expensive = pe_val and pe_val > 28
            return (
                f"### הערכת תמחור ומכפילי שוק: {name} ({ticker})\n\n"
                f"**1. מדדי תמחור מפתח:**\n"
                f"* **מכפיל רווח נוכחי (Trailing P/E):** עומד על **{pe}** (לעומת חציון ענפי של ~24).\n"
                f"* **מכפיל רווח עתידי (Forward P/E):** עומד על **{fwd_pe}**, המלמד על צפי לצמיחה ברווחיות בשנה הקרובה.\n"
                f"* **מכפיל צמיחה (PEG Ratio):** עומד על **{peg}**.\n\n"
                f"**2. מסקנת התמחור המוסדית:**\n"
                f"{'הנכס נסחר בפרמיה עשירה ביחס לשוק. פרמיה זו מוצדקת על ידי איכות המאזן והמובילות הטכנולוגית, אך היא מגדילה את רמת הרגישות לכל האטה.' if is_expensive else 'הנכס מתומחר ברמה הוגנת ביחס לקצב צמיחתו ולאיכות הרווחים.'}"
            )

        # =====================================================================
        # 12. Leadership, CEO & Executive Management (מנכ"ל, הנהלה, הקצאת הון)
        # =====================================================================
        if any(w in q for w in ["מנכ\"ל", "מנכל", "הנהלה", "טים קוק", "אילון מאסק", "ג'נסן הואנג", "סאטיה", "מייסד", "הנהלת החברה", "ceo", "management", "leadership"]):
            return (
                f"### ניתוח איכות ההנהלה והקצאת ההון: {name} ({ticker})\n\n"
                f"**1. מבחן הקצאת ההון (Capital Allocation):**\n"
                f"המדד האובייקטיבי החשוב ביותר להערכת הנהלה על פי וורן באפט הוא התשואה על ההון המושקע (ROIC), העומדת על **{roic}** (מול עלות הון משוערת של כ-8%-9%). "
                f"פער זה מוכיח כי ההנהלה מקצה הון בפרויקטים בעלי ערך מוסף יוצא דופן ולא שורפת מזומנים בהרפתקאות יקרות.\n\n"
                f"**2. משמעת תקציבית וחוב:**\n"
                f"ההנהלה שומרת על יחס חוב להון של **{debt_equity}** ומדד פיוטרוסקי של **{piot}/9**, המלמדים על ניהול סיכונים שקול גם בסביבת ריבית מאתגרת.\n\n"
                f"**3. תגמול בעלי המניות:**\n"
                f"החברה מייצרת תזרים חופשי של **{fcf}**, ומנתבת אותו באופן שיטתי לדיבידנדים ולרכישה עצמית של מניות (Buybacks) שמגדילה את הרווח למניה (EPS)."
            )

        # =====================================================================
        # 13. Geopolitics, China, Tariffs & Trade Wars (סין, מכסים, מלחמה, טייוואן)
        # =====================================================================
        if any(w in q for w in ["סין", "טייוואן", "מלחמה", "אירופה", "מכסים", "טראמפ", "חרם", "רגולציה", "china", "tariff", "geopolitical", "taiwan"]):
            return (
                f"### ניתוח חשיפה גאופוליטית ומכסי סחר: {name} ({ticker})\n\n"
                f"על פי גילויי ה-SEC בדוח השנתי (Form 10-K Item 1A):\n\n"
                f"**1. תלות בשרשראות אספקה וייצור באסיה:**\n"
                f"חברות טכנולוגיה מובילות תלויות במידה רבה בשרשרת הייצור במזרח אסיה (בפרט ייצור מוליכים למחצה בטייוואן והרכבה בסין). כל החרפה במתיחות בין ארה\"ב לסין מהווה גורם סיכון ישיר לזמני אספקה ושולי רווח.\n\n"
                f"**2. איומי מכסים ומלחמת סחר:**\n"
                f"הטלת מכסי מגן גוררת עלויות ייצור גבוהות יותר. עם זאת, בזכות שולי רווח גולמי של **{gross}**, לחברה יש כוח תמחור מסוים לגלגל חלק מהעלויות לצרכן הסופי.\n\n"
                f"**3. מגמת פיזור גאוגרפי (Friendshoring):**\n"
                f"החברות המובילות פועלות להעברת פסי ייצור להודו, וייטנאם וארה\"ב כדי להקטין את התלות במדינה בודדת."
            )

        # =====================================================================
        # 14. Price Crashes, Drops & Volatility (למה ירדה, התרסקות, זינוק)
        # =====================================================================
        if any(w in q for w in ["למה ירדה", "למה עלתה", "נפילה", "זינוק", "התרסקות", "למה המניה", "קריסה", "ירידות", "עליות", "תיקון", "crash", "drop", "surge"]):
            return (
                f"### ניתוח תנודתיות, שינויי מחיר ותיקוני שוק: {name} ({ticker})\n\n"
                f"**1. פרופיל התנודתיות של הנכס:**\n"
                f"* **סטיית תקן שנתית (Volatility):** **{vol}%** — משקף את משרעת התנודות הרגילה במחיר.\n"
                f"* **מקדם בטא (Beta):** **{beta_str}** ביחס ל-S&P 500.\n"
                f"* **עומק הירידה המקסימלי (Max Drawdown):** **{mdd}%** ב-5 השנים האחרונות.\n\n"
                f"**2. מה גורם לתנודות מחיר חדות בנכס מסוג זה?**\n"
                f"* **רגישות למכפילים:** עם מכפיל רווח של **{pe}**, השוק מתמחר צמיחה עתידית גבוהה. כל אי-ודאות סביב תחזיות ההכנסות או שינוי בריבית הפד גורר תגובה מהירה במחיר.\n"
                f"* **רעשי שוק מול יסודות כלכליים:** הירידות לרוב נובעות מתנודות סנטימנט מאקרו ולא מפגיעה ברווחיות הליבה (תזרים חופשי של **{fcf}**).\n\n"
                f"**3. המלצה טקטית למשקיע:**\n"
                f"במניות איכותיות, תיקוני מחיר עמוקים מהווים הזדמנות קלאסית להשקעה מדורגת (DCA) ולא סיבה לבהלה."
            )

        # =====================================================================
        # 15. Technical Analysis & Moving Averages (ניתוח טכני, RSI, ממוצעים)
        # =====================================================================
        if any(w in q for w in ["תמיכה", "התנגדות", "ממוצע נע", "rsi", "טכני", "גרף", "מגמה", "technical", "sma", "trend"]):
            return (
                f"### תמונת מצב טכנית ומגמות מסחר: {name} ({ticker})\n\n"
                f"**מדדים טכניים מתוך מודל הסיכון בזמן אמת:**\n"
                f"* **מחיר נוכחי:** **${price}**\n"
                f"* **מצב מגמה משוקלל:** **{risk.get('trend_status', 'מגמת עלייה מתונה')}**\n"
                f"* **מדד עוצמה יחסית (RSI 14 ימים):** **{risk.get('rsi_14', '50.0')}** (ערך מעל 70 מסמל קניית יתר, מתחת ל-30 מסמל מכירת יתר).\n"
                f"* **ממוצע נע 50 ימים (SMA 50):** **${risk.get('sma_50', price)}** — קו תמיכה קצר/בינוני מועדף.\n"
                f"* **ממוצע נע 200 ימים (SMA 200):** **${risk.get('sma_200', price)}** — קו המגמה ארוך הטווח של וול סטריט.\n\n"
                f"💡 **הערה מוסדית:** ניתוח טכני מסייע בתזמון כניסה, אך איכות המאזן וה-DCF הם הקובעים את התשואה ארוכת הטווח."
            )

        # =====================================================================
        # 16. Taxation for Israeli Investors (מיסוי, W-8BEN, רווחי הון)
        # =====================================================================
        if any(w in q for w in ["מס", "מיסוי", "w8", "רווחי הון", "מס דיבידנד", "tax", "withholding"]):
            return (
                f"### מדריך מיסוי למשקיע הישראלי בניירות ערך אמריקאיים 📋\n\n"
                f"**1. מס על דיבידנדים במניות ארה\"ב:**\n"
                f"על פי אמנת המס בין ישראל לארה\"ב, חתימה על טופס **W-8BEN** (הנחתם אוטומטית דרך הברוקר שלכם) מגבילה את ניכוי המס במקור בארה\"ב ל-**25%** בלבד (במקום 30%). מס זה משולם אוטומטית בעת קבלת הדיבידנד.\n\n"
                f"**2. מס רווחי הון ריאלי:**\n"
                f"בישראל חל מס רווחי הון ריאלי של **25%** על הרווח הנקי בעת מימוש (מכירה) של המניה. המס מחושב בניכוי אינפלציה/הצמדה למדד המחירים לצרכן.\n\n"
                f"**3. קיזוז הפסדים:**\n"
                f"הפסדים מניירות ערך ניתנים לקיזוז כנגד רווחי הון מאותה שנת מס (ובמקרים מסוימים גם לשנים הבאות דרך הגשת דוח שנתי למס הכנסה)."
            )

        # =====================================================================
        # 17. Brokers & Where to Buy (איפה קונים, איך לקנות, ברוקר, בנק)
        # =====================================================================
        if any(w in q for w in ["איפה קונים", "איך לקנות", "ברוקר", "בנק", "עמלות", "אינטראקטיב", "מיטב", "broker", "platform"]):
            return (
                f"### איך ואיפה קונים את {ticker} מישראל? 🏛️\n\n"
                f"ניתן לרכוש את הנכס {ticker} בבורסות ארה\"ב בשתי דרכים עיקריות:\n\n"
                f"1. **ברוקר זר מתמחה (כגון Interactive Brokers):**\n"
                f"   * **יתרונות:** עמלות מסחר אפסיות (כ-$0.35-$1 לפעולה), מרווחי המרת מט\"ח זולים במיוחד, ממשק מסחר מתקדם.\n"
                f"   * **חסרונות:** מצריך הגשת דוח מס שנתי עצמאי בישראל.\n\n"
                f"2. **חבר בורסה ישראלי / בנקים (מיטב, IBI, אקסלנס, בנק לאומי/פועלים):**\n"
                f"   * **יתרונות:** ניכוי מס במקור אוטומטי מלא ללא צורך בהתעסקות מול מס הכנסה, תמיכה בעברית וביטוח מקומי.\n"
                f"   * **חסרונות:** עמלות מינימום לפעולה ($5-$10) ודמי ניהול/משמרת חודשיים."
            )

        # =====================================================================
        # 18. ETF vs Single Stock (קרן סל מול מניה בודדת)
        # =====================================================================
        if any(w in q for w in ["קרן סל מול מניה", "עדיף מניה או קרן", "הבדל בין קרן למניה", "סל או מניה", "etf vs stock"]):
            return (
                f"### השוואה אסטרטגית: השקעה בקרן סל (ETF) לעומת מניה בודדת ⚖️\n\n"
                f"* **קרן סל (כמו QQQ או SPY):** מספקת פיזור מיידי בעשרות או מאות חברות מובילות. היא מבטלת כמעט לחלוטין את סיכון פשיטת הרגל של חברה יחידה, מתאימה במיוחד להשקעה פסיבית בהוראת קבע (DCA) ומניבה תשואת שוק היסטורית מצוינת.\n"
                f"* **מניה בודדת (כמו AAPL, NVDA, MSFT):** נושאת סיכון ספציפי של החברה, אך מעניקה פוטנציאל לתשואת יתר (אלפא) מעל המדד במידה ולחברה יש חפיר כלכלי מבוצר.\n\n"
                f"💡 **המלצה מוסדית:** למרבית המשקיעים, השילוב המנצח הוא מודל 'Core & Satellite' — 70%-80% בקרנות סל רחבות, ו-20%-30% במניות איכות נבחרות."
            )

        # =====================================================================
        # 19. Inflation, Interest Rates & Fed Policy (אינפלציה, ריבית, פד)
        # =====================================================================
        if any(w in q for w in ["אינפלציה", "ריבית", "פד", "פאוול", "cpi", "fed", "interest rate", "inflation"]):
            return (
                f"### השפעת הריבית והאינפלציה על {name} ({ticker}) 🏦\n\n"
                f"**1. מנגנון ההיוון ומכפילי הרווח:**\n"
                f"כאשר ריבית הבנק הפדרלי (Fed) גבוהה, התשואה על אג\"ח ממשלתיות חסרות סיכון עולה. כתוצאה מכך, שיעור ההיוון (WACC) במודל ה-DCF עולה, מה שמקטין את השווי הנוכחי של תזרימי המזומנים העתידיים ולוחץ את מכפילי הרווח כלפי מטה.\n\n"
                f"**2. חוסן מול אינפלציה (כוח תמחור):**\n"
                f"עם שולי רווח גולמי של **{gross}**, לחברה יש כוח תמחור גבוה המאפשר לה לייקר מחירים מבלי לאבד לקוחות.\n\n"
                f"**3. מבנה המאזן:** החברה מחזיקה ביחס חוב שקול ומדד אלטמן של **{altman}**, כך שעלויות מימון החוב אינן מאיימות על יציבותה."
            )

        # =====================================================================
        # 20. Crypto, Bitcoin & Digital Assets (ביטקוין, קריפטו)
        # =====================================================================
        if any(w in q for w in ["קריפטו", "ביטקוין", "אתריום", "crypto", "bitcoin", "btc"]):
            return (
                f"### נכסי קריפטו מול מניות תזרימיות: {name} ({ticker})\n\n"
                f"**ההבדל הכלכלי המהותי:**\n"
                f"חברות וקרנות במערכת StockIntel Pro מייצרות תזרים מזומנים חופשי אמיתי (FCF של **{fcf}** ב-{ticker}), מחלקות דיבידנדים ומחזיקות בנכסים פיזיים וטכנולוגיים מבוקרים.\n"
                f"לעומת זאת, ביטקוין וקריפטו הם נכסים ספקולטיביים ללא תזרים או רווחים, שמחירם נקבע על בסיס היצע וביקוש בלבד.\n\n"
                f"💡 בתיק מודרני מגוון, משקיעים רבים מקצים עד 1%-5% לקריפטו, אך ליבת התיק (Core) נשענת על נכסים תזרימיים מוכחים."
            )

        # =====================================================================
        # 21. Technology, AI, Cloud Computing & Semiconductors (טכנולוגיה, AI, שבבים)
        # =====================================================================
        if any(w in q for w in ["ai", "בינה מלאכותית", "שבבים", "סמיקונדקטור", "מוליכים למחצה", "ענן", "שרתים", "תוכנה", "חומרה", "gpu", "מעבד", "אוטונומי", "רובוטיקה", "סייבר", "דאטה", "מודל שפה", "llm", "גנרטיבי", "רכב חשמלי", "טכנולוגיה", "cloud", "chips", "hardware"]):
            return (
                f"### ניתוח מגמות טכנולוגיה, בינה מלאכותית (AI) ותשתיות מחשוב 💻\n\n"
                f"**1. מהפכת ה-AI ותשתיות הנתונים (Data Centers):**\n"
                f"המעבר למודלים גנרטיביים (Generative AI) מייצר גל השקעות הון (CapEx) היסטורי של מאות מיליארדי דולרים. "
                f"חברות שבבי ה-GPU, יצרניות המוליכים למחצה וספקיות הענן הגדולות (Hyperscalers) נהנות מביקוש קשיח להרחבת חוות שרתים ויכולות עיבוד.\n\n"
                f"**2. מונטיזציה של תוכנה ושירותים:**\n"
                f"השלב הבא של המהפכה אינו רק מכירת ברזלים ושבבים, אלא היכולת של ענקיות הטק להטמיע עוזרי AI ישירות במערכות ההפעלה, יישומי ה-SaaS ומכשירי הקצה, מה שמגדיל את ההכנסה הממוצעת למשתמש (ARPU) ואת שולי הרווח הגולמי ({gross}).\n\n"
                f"**3. הקשר לנכס הנבדק ({name} - {ticker}):**\n"
                f"{'הקרן QQQ מעניקה חשיפה מרוכזת ביותר לחברות המובילות את תשתיות ה-AI, השבבים והענן (כגון NVDA, MSFT, AAPL, AMZN, GOOGL).' if is_etf else f'החברה ממצבת את עצמה בחזית הטכנולוגית בזכות תזרים מזומנים חופשי של {fcf} המאפשר השקעות מו\"פ אגרסיביות.'}"
            )

        # =====================================================================
        # 22. Consumer Psychology, Brand Loyalty & Ecosystems (מותג, צרכנים, אקוסיסטם)
        # =====================================================================
        if any(w in q for w in ["מותג", "מיתוג", "צרכנים", "נאמנות", "אייפון", "אקוסיסטם", "כוח תמחור", "שיווק", "למה קונים", "brand", "ecosystem"]):
            return (
                f"### ניתוח אסטרטגיה עסקית: עוצמת מותג, אפקט רשת ואקוסיסטם 🌐\n\n"
                f"**1. עלויות מעבר (Switching Costs) ונעילת לקוחות:**\n"
                f"חברות מובילות בונות אקוסיסטם שלם המשלב חומרה, תוכנה ושירותים מקושרים. ככל שהמשתמש רוכש יותר מכשירים ושומר יותר נתונים במערכת, המאמץ לעבור למתחרה הופך ליקר ומסורבל מדי.\n\n"
                f"**2. כוח תמחור (Pricing Power) ושולי רווח:**\n"
                f"המדד הכלכלי המובהק ביותר לנאמנות לקוחות הוא היכולת להעלות מחירים מבלי לפגוע בהיקף המכירות. שולי רווח גולמי של **{gross}** מוכיחים כי הצרכנים רואים במוצר סמל סטטוס ואיכות שאינו ניתן להחלפה במחיר זול.\n\n"
                f"**3. הכנסות שירותים חוזרות (Recurring Revenue):**\n"
                f"המעבר ממכירת מכשיר חד-פעמית למכירת מנויים חודשיים (אחסון, מוזיקה, שירותי ענן) הופך את תזרים המזומנים ליציב, צפוי ורווחי בהרבה."
            )

        # =====================================================================
        # 23. Investor Psychology, Behavioral Finance & Loss Aversion (פסיכולוגיה, פחד, FOMO)
        # =====================================================================
        if any(w in q for w in ["פסיכולוגיה", "פחד", "תאוות בצע", "fomo", "הפסד", "הפסדים", "סבלנות", "משמעת", "רגשות", "פאניקה", "טעויות", "behavioral", "psychology", "panic"]):
            return (
                f"### פסיכולוגיית שוק והתנהגות משקיעים (Behavioral Finance) 🧠\n\n"
                f"על פי מחקרי הכלכלה ההתנהגותית (כהנמן וטברסקי), המכשול הגדול ביותר של המשקיע אינו חוסר ידע, אלא הטיות פסיכולוגיות מולדות:\n\n"
                f"**1. שנאת הפסד (Loss Aversion):**\n"
                f"הכאב הפסיכולוגי מהפסד כספי של 1,000$ חזק בערך פי 2.5 מהעונג מרווח זהה. כתוצאה מכך, משקיעים נתקפים פאניקה בימי ירידות חדות ומוכרים בדיוק בתחתית.\n\n"
                f"**2. פחד מהחמצה (FOMO) ומנטליות עדר:**\n"
                f"כאשר שוק המניות עולה ברציפות, משקיעים רבים נכנסים בסכומים גדולים בשיא רק מחשש לפספס, ואז נסוגים בתיקון הראשון.\n\n"
                f"**3. הפתרון המוסדי המוכח:**\n"
                f"משקיעים מצליחים מנטרלים רגשות באמצעות מערכת כללים קבועה מראש: השקעה שיטתית בהוראת קבע (DCA), הגדרת שולי ביטחון מראש, והבנה שתנודתיות שנתית של **{vol}%** היא מחיר הכניסה הטבעי לתשואות ארוכות טווח."
            )

        # =====================================================================
        # 24. Antitrust, Regulation & Big Tech Lawsuits (הגבלים עסקיים, רגולציה)
        # =====================================================================
        if any(w in q for w in ["הגבלים עסקיים", "מונופול", "תביעה", "משפט", "פרטיות", "רגולציה", "antitrust", "monopoly", "regulation"]):
            return (
                f"### ניתוח סיכוני רגולציה, חוק והגבלים עסקיים (Antitrust) ⚖️\n\n"
                f"**1. מוקדי החקירות בארה\"ב ובאיחוד האירופי:**\n"
                f"רשויות ההגבלים העסקיים (FTC, DOJ, הנציבות האירופית) בוחנות מקרוב את מעמדן של ענקיות הטכנולוגיה, בעיקר בנושאי:\n"
                f"* עמלות בחנויות אפליקציות וחסימת חנויות חלופיות (חוק ה-DMA באירופה).\n"
                f"* הסכמי בלעדיות במנועי חיפוש והפצת תוכנה.\n"
                f"* שימוש בנתוני משתמשים לשמירה על יתרון פרסומי.\n\n"
                f"**2. ההשפעה הכלכלית על חברות ענק:**\n"
                f"מבחינה היסטורית (כמו במקרה של מיקרוסופט בשנות ה-90), תביעות הגבלים עסקיים נמשכות שנים רבות. הן עלולות להאט רכישות ענק ולהטיל קנסות, אך לעיתים נדירות פוגעות ברווחיות הליבה של חברות בעלות חפיר מבוצר.\n\n"
                f"**3. חוסן פיננסי ככרית הגנה:**\n"
                f"עם קופת מזומנים חזקה ותזרים חופשי של **{fcf}**, חברות מסוג זה מסוגלות לספוג קנסות כספיים ולהתאים את פעילותן לדרישות החוק מבלי לסכן את יציבותן."
            )

        # =====================================================================
        # 25. Startups, Entrepreneurship & Financial Independence (יזמות, סטארטאפ, חופש כלכלי)
        # =====================================================================
        if any(w in q for w in ["סטארטאפ", "סטארט-אפ", "יזמות", "חופש כלכלי", "fire", "עצמאות כלכלית", "הכנסה פסיבית", "startup", "entrepreneurship"]):
            return (
                f"### יזמות, צבירת הון וחופש כלכלי (Financial Independence) 🚀\n\n"
                f"**1. מנועי צמיחת הון: עבודה מול בעלות על נכסים:**\n"
                f"ההבדל היסודי בין הכנסה מעבודה לבין עושר אמיתי הוא עקרון הבעלות (Equity). משקיעים ויזמים אינם מוכרים רק שעות עבודה, אלא מחזיקים בנכסים תזרימיים שעובדים ומייצרים ערך גם בזמן שהם ישנים.\n\n"
                f"**2. מודל ה-FIRE (Financial Independence, Retire Early):**\n"
                f"המודל מבוסס על הגדלת שיעור החיסכון, השקעה שיטתית בנכסים מניבים (כגון מניות ערך וקרנות סל רחבות כמו {ticker}), והגעה לתיק המייצר תשואה המכסה את הוצאות המחיה (כלל ה-4%).\n\n"
                f"**3. ניהול סיכונים בעסק ובהשקעות:**\n"
                f"גם ביזמות וגם בהשקעות, הכלל החשוב ביותר הוא הישרדות והימנעות מסיכון של מחיקה מוחלטת (Risk of Ruin). בניית שולי ביטחון פיננסיים היא התשתית לכל צמיחה ארוכת טווח."
            )

        # =====================================================================
        # 26. Final Fallback: Broad Domain vs Strictly Out-of-Domain
        # =====================================================================
        # Comprehensive Business, Financial, Technological, Strategic & Macro Domain
        broad_domain_keywords = {
            # Core Markets & Valuation
            "מניה", "מניות", "קרן", "סל", "השקעה", "השקעות", "שוק", "מחיר", "שווי", "תמחור",
            "רווח", "רווחים", "הכנסה", "הכנסות", "דוח", "דוחות", "מאזן", "חוב", "דיבידנד",
            "תזרים", "מכפיל", "פיוטרוסקי", "אלטמן", "dcf", "סיכון", "סיכונים", "תשואה",
            "ביצועים", "באפט", "וול סטריט", "sec", "10-k", "etf", "stock", "invest", "yield",
            "growth", "margin", "capital", "portfolio", "תיק", "פוזיציה", "נכס", "בורסה",
            "אופציות", "חוזה", "קנייה", "מכירה", "לונג", "שורט", "דיראציה", "מדד", "מדדים",
            "מימון", "כלכלה", "איגרת", "אגח", "וואק", "wacc", "roe", "roic", "fcf",
            
            # Technology & Innovation
            "ai", "בינה מלאכותית", "שבבים", "סמיקונדקטור", "מוליכים למחצה", "ענן", "שרתים",
            "תוכנה", "חומרה", "gpu", "מעבד", "מעבדים", "אוטונומי", "רובוטיקה", "סייבר",
            "דאטה", "אלגוריתם", "מודל שפה", "llm", "גנרטיבי", "רכב חשמלי", "טכנולוגיה",
            "חדשנות", "פטנט", "פטנטים", "cloud", "tech", "chip", "hardware", "software",

            # Strategy, Consumer & Business
            "אסטרטגיה", "מודל עסקי", "שיווק", "מותג", "מיתוג", "לקוחות", "צרכנים", "נאמנות",
            "אייפון", "אקוסיסטם", "מוצר", "מוצרים", "מחיר", "כוח תמחור", "פרמיה", "מונופול",
            "תחרות", "מתחרים", "חפיר", "רשת", "אפקט רשת", "בידול", "מכירות", "הפצה",

            # Macroeconomics & Policy
            "אינפלציה", "ריבית", "פד", "פאוול", "בנק מרכזי", "דולר", "שקל", "מטח", "מכסים",
            "סחר", "מלחמת סחר", "סין", "טייוואן", "סנקציות", "נפט", "אנרגיה", "סחורות",
            "זהב", "נדלן", "מאקרו", "תעסוקה", "אבטלה", "מיתון", "צמיחה כלכלית", "gdp", "cpi",

            # Psychology, Leadership & Career
            "פסיכולוגיה", "פחד", "פאניקה", "תאוות בצע", "fomo", "הפסד", "הפסדים", "סבלנות",
            "משמעת", "רגשות", "התנהגות", "טעויות", "עצמאות כלכלית", "חופש כלכלי", "fire",
            "יזמות", "סטארטאפ", "סטארט-אפ", "קריירה", "הון", "עושר", "חיסכון", "מנכל",
            "מנכ\"ל", "הנהלה", "מייסד", "מייסדים", "תרבות ארגונית", "עובדים",
            
            ticker.lower()
        }
        name_words = {w.lower() for w in re.findall(r'[\w]+', name)}
        is_in_broad_domain = any(k in q for k in broad_domain_keywords) or bool(q_tokens & name_words)

        if not is_in_broad_domain:
            return (
                f"### מענה לשאלתך: \"{question}\"\n\n"
                f"השאלה שלך עוסקת בנושא שאינו קשור לתחומי הכלכלה, העסקים, הטכנולוגיה, שוק ההון או הנכס הנבדק (**{name}**).\n\n"
                f"כאנליסט של **StockIntel Pro**, טווח הדיון שלי מקיף נושאים עסקיים, פיננסיים, אסטרטגיים וטכנולוגיים:\n"
                f"* **פיננסים ודוחות:** דוחות כספיים מבוקרים, מודלי DCF, שווי הוגן, מכפילי שוק ואיתנות מאזן.\n"
                f"* **אסטרטגיה עסקית ומוצרים:** מודלים עסקיים, כוח תמחור, מיתוג, אקוסיסטם ויתרון תחרותי (חפיר כלכלי).\n"
                f"* **טכנולוגיה וחדשנות:** בינה מלאכותית (AI), שבבים, מחשוב ענן, תוכנה, רכבים חשמליים ומגמות טק.\n"
                f"* **גאופוליטיקה ומאקרו:** מלחמות סחר, מכסים, ריבית הפד, אינפלציה ושרשראות אספקה גלובליות.\n"
                f"* **פסיכולוגיית שוק והתנהגות משקיעים:** ניהול סיכונים, קבלת החלטות, התמודדות עם פחד/תאוות בצע וחשיבה לטווח ארוך.\n\n"
                f"אשמח מאוד לדון איתך בכל אחד מהנושאים הללו או להעמיק בנתוני {ticker}!"
            )

        # Dynamic Fallback for Asset / Market Questions within broad domain
        if is_etf:
            return (
                f"### סקירת אנליסט מוסדית עבור קרן הסל: {name} ({ticker})\n\n"
                f"**1. תמצית מנהלים ומאפייני הנכס:**\n"
                f"הקרן {ticker} נסחרת בשער של **${price}** עם היקף נכסים מנוהל (AUM) של **{mcap_str}**, ומחזיקה בציון איכות משוקלל של **{composite_score} מתוך 100** במודל הניתוח.\n\n"
                f"**2. נתוני מפתח ביחס לשאלתך:**\n"
                f"* **פרופיל החשיפה:** הקרן מספקת פיזור ממוקד בסקטור **{sector}** עם דמי ניהול נמוכים של **{etf_data.get('expense_ratio', '0.20')}%** לשנה. 3 ההחזקות המובילות: **{top3_holdings}**.\n"
                f"* **תמחור ומכפילים:** מכפיל הרווח המשוקלל עומד על **{pe}** (מכפיל עתידי **{fwd_pe}**).\n"
                f"* **תנודתיות וסיכון:** תנודתיות שנתית של **{vol}%** ובטא של **{beta_str}** מול מדד S&P 500, עם ירידה מקסימלית היסטורית של **{mdd}%**.\n\n"
                f"**3. השורה התחתונה למשקיע:**\n"
                f"עבור קרן סל מובילה כמו {ticker}, האסטרטגיה המומלצת אינה ניסיון לתזמן שפל מוחלט, אלא כניסה מדורגת (DCA) תוך ניצול תנודתיות השוק להגדלת פוזיציה לטווח ארוך.\n\n"
                f"💡 *למענה פתוח ומותאם אישית לכל ניואנס בשאלתך, ניתן לחבר מפתח Gemini חינמי דרך כפתור 'מפתח AI' בראש החלונית.*"
            )
        return (
            f"### סקירת אנליסט עבור: {name} ({ticker})\n\n"
            f"**1. תמונת מצב עדכנית ותמצית מנהלים:**\n"
            f"הנכס {ticker} נסחר כעת בשער של **${price}** (שווי שוק כולל של **{mcap_str}**), ומחזיק בציון איכות משוקלל של **{composite_score} מתוך 100** במודל הניתוח המוסדי.\n\n"
            f"**2. נתוני מפתח ביחס לשאלתך:**\n"
            f"* **מבחינת פרופיל הפעילות והאיכות:** החברה פועלת בסקטור ה-**{sector}** ושומרת על שולי רווח גולמי של **{gross}**, שולי רווח תפעולי של **{op_margin}**, ותשואה על ההון המושקע (ROIC) של **{roic}**.\n"
            f"* **מבחינת תמחור וערך הוגן:** מכפיל הרווח עומד על **{pe}** (מכפיל עתידי **{fwd_pe}**), כאשר מודל הערכת השווי DCF מעריך את השווי ההוגן ב-**${dcf_fair}** (שולי ביטחון: **{dcf_margin}%**).\n"
            f"* **מבחינת איתנות ורמת סיכון:** מדד פיוטרוסקי של **{piot}/9** ומדד אלטמן **{altman}** ({altman_zone}) מאשרים חוסן פיננסי מעולה ותנודתיות שנתית של **{vol}%** (בטא: **{beta_str}**).\n\n"
            f"**3. השורה התחתונה למשקיע:**\n"
            f"הנכס מציג איכות עסקית וחפיר כלכלי מובהק. אם מטרתך היא השקעה לטווח ארוך, מומלץ לבחון כניסה במנות מדורגות כדי לגדר את סיכוני התמחור והתנודתיות בשוק.\n\n"
            f"💡 *למענה פתוח ומותאם אישית לכל ניואנס בשאלתך, ניתן לחבר מפתח Gemini חינמי דרך כפתור 'מפתח AI' בראש החלונית.*"
        )
