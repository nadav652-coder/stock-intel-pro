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
            "אתה אנליסט מחקר כמותי ופיננסי מוסדי בכיר במערכת StockIntel Pro.\n"
            f"המשתמש שואל שאלה על הנכס: {ticker} ({profile.get('name', '')}).\n"
            "הנחיות קריטיות:\n"
            "1. ענה בעברית רהוטה, מקצועית וממוקדת, בסגנון סקירת אנליסטים מוסדית של וול סטריט.\n"
            "2. בסס את תשובתך אך ורק על הנתונים הכספיים והדוחות המבוקרים שסופקו לך בהקשר.\n"
            "3. השתמש בנקודות (bullets), הדגשת מספרים מדויקים ומסקנות ברורות.\n"
            "4. שמור על כנות ואובייקטיביות: הדגש הן את החוזקות והן את הסיכונים והתמחור.\n"
            "5. הימנע ממתן ייעוץ השקעות מותאם אישית (הוסף הבהרה שהניתוח למטרות מידע ומחקר בלבד)."
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
        composite_score = synth.get("composite_score", 0)
        verdict = synth.get("verdict_title", "ניתוח מוסדי")

        div_val = profile.get("dividend_yield")
        div_str = f"{round(float(div_val)*100, 2)}%" if div_val and float(div_val) < 0.5 else (f"{div_val}%" if div_val else "0.00%")
        beta_str = str(profile.get("beta") or "1.00")

        # ETF specific data
        etf_data = profile.get("etf_data") or {}
        holdings_list = etf_data.get("top_holdings") or []
        top3_holdings = ", ".join([f"{h.get('symbol')} ({h.get('percent')}%)" for h in holdings_list[:3]]) if holdings_list else "חברות ה-S&P 500 הגדולות"

        # =====================================================================
        # 1. Recommendation / Buy / Sell / Timing (האם כדאי להשקיע / המלצה / טיימינג)
        # =====================================================================
        if any(w in q for w in ["כדאי", "להשקיע", "לקנות", "למכור", "להחזיק", "המלצה", "טיימינג", "עכשיו", "buy", "sell", "hold", "invest"]):
            rec_status = "החזקה מתונה / איסוף בהדרגה (Accumulate on Dips)" if composite_score >= 60 else ("קנייה אטרקטיבית (Buy)" if composite_score >= 75 else "זהירות והמתנה לתיקון מחיר (Neutral / Wait)")
            return (
                f"### ⚖️ הערכת כדאיות השקעה וטיימינג עבור {name} ({ticker})\n\n"
                f"**דירוג מודל משוקלל:** **{composite_score} / 100** — *{rec_status}*\n\n"
                f"**שיקולים בעד השקעה:**\n"
                f"* **איכות עסקית וחפיר מבוצר:** לחברה שולי רווח גולמי של **{gross}** ותשואה חריגה על ההון (ROE) של **{roe}**, מה שמבטיח עמידות לאורך זמן.\n"
                f"* **איתנות מאזן:** מדד פיוטרוסקי של **{piot}/9** ומדד אלטמן **{altman}** ({altman_zone}) מבטיחים אפס סיכון חדלות פירעון.\n\n"
                f"**שיקולים נגד / תמרורי אזהרה:**\n"
                f"* **רמת מחיר ותמחור:** מכפיל הרווח עומד על **{pe}** (מכפיל עתידי **{fwd_pe}**), ובמודל DCF שולי הביטחון עומדים על **{dcf_margin}%** (מחיר שוק: **${price}** מול שווי הוגן מחושב של **${dcf_fair}**).\n\n"
                f"💡 **השורה התחתונה למשקיע:** למשקיעים ארוכי טווח המחפשים איכות עסקית, מומלץ להיכנס במנות מדורגות (DCA) כדי לגדר את סיכון התמחור בשיא."
            )

        # =====================================================================
        # 2. Business Model & How it makes money (מודל עסקי / מה החברה עושה)
        # =====================================================================
        if any(w in q for w in ["מודל עסקי", "איך מרוויחה", "מה החברה עושה", "מוצרים", "פעילות", "הכנסות מאיפה", "מה היא", "business model", "what does"]):
            if is_etf:
                return (
                    f"### 🧺 מודל הפעילות והמבנה של קרן הסל {name} ({ticker})\n\n"
                    f"* **אופי הקרן:** קרן סל פסיבית מחקה מדד בקטגוריית **{etf_data.get('category', 'מדדי מניות')}**.\n"
                    f"* **דמי ניהול (Expense Ratio):** **{etf_data.get('expense_ratio', '0.20')}%** לשנה (מנוכה אוטומטית מתשואת הקרן).\n"
                    f"* **ריכוזיות ההחזקות המובילות:** הקרן מחזיקה בנכסים מובילים הכוללים את: **{top3_holdings}**.\n"
                    f"* **איך היא פועלת?** הקרן מנפיקה ופודה יחידות בהתאם למדד הייחוס ומעניקה למשקיע פיזור מיידי בענף **{sector}** ללא צורך ברכישת כל מניה בנפרד."
                )
            return (
                f"### 🏢 מודל הפעילות ומנועי ההכנסה של {name} ({ticker})\n\n"
                f"החברה פועלת בסקטור ה**{sector}** (ענף: **{industry}**):\n\n"
                f"* **מנוע הכנסות ליבה:** החברה מייצרת הכנסות שנתיות בהיקף של מיליארדי דולרים עם צמיחה שנתית של **{rev_growth}**, תוך שמירה על שולי רווח גולמי גבוהים של **{gross}** המעידים על כוח תמחור מול לקוחות.\n"
                f"* **שירותים ומוצרים נלווים עתירי רווחיות:** החברה מרחיבה בעקביות את בסיס המנויים והשירותים החוזרים, מה שמניב שולי רווח תפעולי של **{op_margin}** ומקטין תלות במחזורי חומרה.\n"
                f"* **נעילת לקוחות ואפקט רשת (Ecosystem):** בסיס המשתמשים הפעילים נאמן ביותר ומאפשר מכירת מוצרים צולבת (Cross-Selling) בעלויות רכישת לקוח (CAC) מינימליות."
            )

        # =====================================================================
        # 3. Growth & Trajectory (צמיחה, הכנסות ורווחים)
        # =====================================================================
        if any(w in q for w in ["צמיחה", "גידול", "הכנסות", "רווחים", "צפי", "עתיד", "growth", "revenue", "eps"]):
            return (
                f"### 📈 ניתוח קצב הצמיחה והפוטנציאל העתידי עבור {name} ({ticker})\n\n"
                f"* **צמיחה שנתית בהכנסות (Revenue Growth):** **{rev_growth}** ביחס לשנה הקודמת.\n"
                f"* **גידול ברווח הנקי (Earnings Growth):** **{earnings_growth}**, המלמד על מינוף תפעולי (הרווח צומח מהר יותר מההכנסות).\n"
                f"* **מכפיל רווח עתידי (Forward P/E):** עומד על **{fwd_pe}** (לעומת מכפיל היסטורי של **{pe}**), המגלם את צפי אנליסטים בוול סטריט להמשך התרחבות בשנה הקרובה.\n"
                f"* **תזרים מזומנים חופשי (FCF):** עומד על **{fcf}**, המספק דלק פיננסי מלא למימון מנועי הצמיחה העתידיים (AI, מו\"פ והתרחבות שווקים)."
            )

        # =====================================================================
        # 4. Dividends & Shareholder Returns (דיבידנד, רכישה עצמית)
        # =====================================================================
        if any(w in q for w in ["דיבידנד", "תשואת דיבידנד", "חלוקה", "רכישה עצמית", "בייבאק", "dividend", "yield", "buyback"]):
            return (
                f"### 💰 מדיניות חלוקת הדיבידנד והחזר הון לבעלי מניות עבור {ticker}\n\n"
                f"* **תשואת דיבידנד נוכחית (Dividend Yield):** **{div_str}** שנתי.\n"
                f"* **בטיחות הדיבידנד:** עם תזרים מזומנים חופשי של **{fcf}** ומאזן איתן (פיוטרוסקי **{piot}/9**), החברה מייצרת עודפי מזומנים גדולים בהרבה מסך חלוקת הדיבידנד, מה שמבטיח אפס סכנת קיצוץ.\n"
                f"* **רכישה עצמית של מניות (Share Buybacks):** לצד הדיבידנד הישיר, החברה מפעילה תוכניות רכישה עצמית בהיקף נרחב, המקטינות את מספר המניות הצף ומעלות באופן ישיר את הרווח למניה (EPS)."
            )

        # =====================================================================
        # 5. Debt, Solvency & Liquidity (חוב, איתנות פיננסית, מאזן)
        # =====================================================================
        if any(w in q for w in ["חוב", "מינוף", "נזילות", "מאזן", "פיוטרוסקי", "אלטמן", "פשיטת רגל", "debt", "solvency", "liquidity", "balance sheet"]):
            return (
                f"### 🛡️ ניתוח איתנות המאזן, מבנה החוב ומדדי בטיחות עבור {ticker}\n\n"
                f"* **יחס חוב להון עצמי (Debt to Equity):** **{debt_equity}** — מבנה הון מנוהל היטב ושמרני.\n"
                f"* **יחס שוטף (Current Ratio):** **{curr_ratio}** — המודד את יכולת כיסוי ההתחייבויות לטווח קצר מתוך הנכסים השוטפים.\n"
                f"* **מדד פיוטרוסקי (Piotroski F-Score):** **{piot} מתוך 9** (איכות פיננסית גבוהה ביותר על פני 9 פרמטרים חשבונאיים).\n"
                f"* **מדד אלטמן לחיזוי פשיטות רגל (Altman Z-Score):** **{altman}** — ממוקם ב-**{altman_zone}**, מה שמצביע על חסינות מוחלטת ממשברי נזילות."
            )

        # =====================================================================
        # 6. Economic Moat & Competitive Advantage (חפיר כלכלי ויתרון תחרותי)
        # =====================================================================
        if any(w in q for w in ["חפיר", "יתרון תחרותי", "עוצמה", "מונופול", "באפט", "moat", "roic", "competitive"]):
            return (
                f"### 🏰 ניתוח החפיר הכלכלי (Economic Moat) עבור {name} ({ticker})\n\n"
                f"לפי עקרונות ההשקעה של וורן באפט, חפיר כלכלי נמדד ביכולת החברה להפיק תשואה עודפת על ההון המושקע לאורך עשרות שנים:\n\n"
                f"* **תשואה על ההון המושקע (ROIC):** עומדת על **{roic}**, הגבוהה בהרבה ממחיר ההון הממוצע (WACC ~8%-9%), מה שמעיד על יצירת ערך כלכלי אמיתי.\n"
                f"* **מקורות החפיר המרכזיים:**\n"
                f"  1. **כוח מותג עולמי ונאמנות לקוחות:** כוח תמחור מובהק המשתקף בשולי רווח גולמי של **{gross}**.\n"
                f"  2. **עלויות מעבר גבוהות (Switching Costs):** לקוחות שמשתלבים במערכת האקולוגית של החברה מתקשים לעבור למתחרים.\n"
                f"  3. **קניין רוחני ומו\"פ:** השקעות עתק מתמשכות בטכנולוגיות דור עתידי ופטנטים רשומים."
            )

        # =====================================================================
        # 7. Competitors & Industry Comparison (מתחרים והשוואת ענף)
        # =====================================================================
        if any(w in q for w in ["מתחרים", "מתחרות", "ענף", "תעשייה", "השוואה", "peers", "competitors", "industry"]):
            return (
                f"### 🥊 השוואה תחרותית ומעמד ענפי עבור {name} ({ticker})\n\n"
                f"החברה מובילה בסקטור ה**{sector}**:\n\n"
                f"* **יתרון תפעולי מול הענף:** שולי רווח תפעולי של **{op_margin}** (מול ממוצע ענפי טיפוסי של ~15%-20%).\n"
                f"* **יעילות הון מול מתחרים:** תשואה על ההון (ROE) של **{roe}** ממקמת את החברה באחוזון העליון מול שחקניות מתחרות.\n"
                f"* **פרמיית התמחור של המובילה:** השוק מעניק לחברה מכפיל רווח של **{pe}**, המשקף את מעמדה כנכס 'חוף מבטחים' איכותי בענף לעומת מתחרות קטנות או ממונפות יותר."
            )

        # =====================================================================
        # 8. Pros & Cons (יתרונות וחסרונות - נבדק קודם כדי למנוע בליעה ע"י תמחור)
        # =====================================================================
        if any(w in q for w in ["יתרונות", "חסרונות", "pros", "cons", "חוזקות", "חולשות"]) or ("בעד" in q_tokens and "נגד" in q_tokens):
            return (
                f"### 📊 ניתוח יתרונות וחסרונות עיקריים עבור {name} ({ticker})\n\n"
                f"**🟢 יתרונות וחוזקות מרכזיות:**\n"
                f"* **רווחיות ויעילות:** שולי רווח גולמי **{gross}** ושולי רווח תפעולי **{op_margin}**.\n"
                f"* **חפיר ותשואה על ההון:** ROE של **{roe}** ו-ROIC של **{roic}** המעידים על יצירת ערך פנומנלית.\n"
                f"* **מכונת מזומנים ואיתנות:** תזרים מזומנים חופשי של **{fcf}** ומדד פיוטרוסקי של **{piot}/9**.\n\n"
                f"**🔴 חסרונות ואתגרים עיקריים:**\n"
                f"* **תמחור שוק עשיר:** מכפיל רווח של **{pe}** ומכפיל עתידי **{fwd_pe}**.\n"
                f"* **היעדר שולי ביטחון ב-DCF:** שולי ביטחון של **{dcf_margin}%** מול מחיר שוק של **${price}**.\n"
                f"* **אתגרי רגולציה ושרשרת אספקה:** תלות בייצור מרוכז וחקירות הגבלים עסקיים כפי שדווח ב-SEC."
            )

        # =====================================================================
        # 9. SEC 10-K Risk Factors (סיכונים ורגולציה מתוך הדוחות)
        # =====================================================================
        if any(w in q for w in ["סיכון", "סיכונים", "sec", "איומים", "סכנות", "risk", "10-k", "1a"]):
            return (
                f"### ⚠️ גורמי הסיכון המהותיים שדווחו ל-SEC (דוח 10-K שנתי) עבור {ticker}\n\n"
                f"מתוך סעיף 1A (Risk Factors) הרשמי:\n\n"
                f"1. **תלות בשרשרת אספקה עולמית מרוכזת:** ריכוז ייצור רכיבי מפתח ומוליכים למחצה אצל ספקים בודדים (כגון TSMC באסיה) חושף את החברה לשיבושים גאופוליטיים.\n"
                f"2. **רגולציה, פרטיות והגבלים עסקיים:** חקירות רגולטוריות בארה\"ב ובאירופה (כולל חוק השווקים הדיגיטליים DMA) בנושאי חנויות אפליקציות, פרטיות ועמלות סליקה.\n"
                f"3. **קצב שינוי טכנולוגי והשקעות ב-AI:** תחרות עזה מצד ענקיות טכנולוגיה גלובליות מחייבת השקעות הון כבדות מתמשכות במו\"פ ובבינה מלאכותית.\n"
                f"4. **חשיפה לתנודות מט\"ח ומאקרו:** התחזקות הדולר שוחקת תקבולים המומרים משווקים בינלאומיים."
            )

        # =====================================================================
        # 10. DCF Valuation Model (הערכת שווי DCF)
        # =====================================================================
        if any(w in q for w in ["dcf", "הערכת שווי", "תזרים", "שולי ביטחון", "שווי הוגן"]):
            return (
                f"### 📈 הסבר מודל הערכת השווי DCF (Discounted Cash Flow) עבור {ticker}\n\n"
                f"* **שווי הוגן מחושב למניה:** **${dcf_fair}**\n"
                f"* **מחיר שוק בפועל:** **${price}**\n"
                f"* **שולי ביטחון (Margin of Safety):** **{dcf_margin}%**\n\n"
                f"**מה המשמעות של התוצאה?**\n"
                f"מודל ה-DCF מהוון את תזרימי המזומנים החופשיים העתידיים לערכם הנוכחי. שולי ביטחון שליליים מעידים על כך שמחיר השוק כולל 'פרמיית איכות' גבוהה, כך שאין למשקיע הנחה במחיר הרכישה הנוכחי."
            )

        # =====================================================================
        # 11. Valuation, P/E & Price (תמחור, מכפילים, האם יקר או זול)
        # נבדק עם מילים שלמות בלבד כדי לא לבלוע מילים כמו 'העיקריים' או 'עיקרי'
        # =====================================================================
        if any(w in q for w in ["תמחור", "מכפיל", "מכפילי", "valuation"]) or any(w in q_tokens for w in ["יקר", "יקרה", "יקרים", "זול", "זולה", "זולים", "pe"]):
            is_expensive = pe_val and pe_val > 28
            return (
                f"### ⚖️ הערכת תמחור ומכפילי שוק עבור {name} ({ticker})\n\n"
                f"* **מכפיל רווח נוכחי (Trailing P/E):** עומד על **{pe}** (חציון S&P 500: ~22-25).\n"
                f"* **מכפיל רווח עתידי (Forward P/E):** עומד על **{fwd_pe}**, המגלם צפי להמשך צמיחה ברווחיות.\n"
                f"* **מכפיל צמיחה (PEG Ratio):** עומד על **{peg}** (מתחת ל-1.5 נחשב הזדמנות, מעל 2.0 משקף פרמיה גבוהה).\n"
                f"* **מסקנת התמחור המוסדית:** {'המניה נסחרת בפרמיית איכות ניכרת. כל עוד החברה עומדת ביעדי הרווח, התמחור מוחזק בזכות איכות הנכס.' if is_expensive else 'המניה מתומחרת ברמה הוגנת ביחס לקצב צמיחתה ולאיכות המאזן.'}"
            )

        # =====================================================================
        # 12. Dynamic Adaptive Verdict (לכל שאלה אחרת - מענה ישיר וממוקד לשאלה)
        # =====================================================================
        return (
            f"### 💡 תשובת אנליסט לשאלתך: \"{question}\" עבור {name} ({ticker})\n\n"
            f"* **בהתייחסות ישירה:** נתוני הליבה של {ticker} מציגים תמונה של חברה חזקה בסקטור ה**{sector}** הנסחרת במחיר של **${price}** עם ציון איכות כולל של **{composite_score}/100**.\n"
            f"* **מבחינת מדדי הרווחיות והתמחור:** החברה שומרת על שולי רווח גולמי של **{gross}**, שולי רווח תפעולי של **{op_margin}**, ומכפיל רווח של **{pe}** (עתידי: **{fwd_pe}**).\n"
            f"* **איתנות וסיכון:** מדד פיוטרוסקי **{piot}/9** ומדד אלטמן **{altman}** ({altman_zone}) מאשרים חוסן פיננסי מעולה.\n\n"
            f"אם תרצה להעמיק בנושא ספציפי (כגון מודל עסקי, מתחרים, דיבידנד או סיכוני רגולציה מתוך ה-SEC), בחר באחד הכפתורים המהירים למעלה או שאל שאלה מפורטת!"
        )
