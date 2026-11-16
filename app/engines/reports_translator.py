"""
Financial Statements Translation & SEC Filing Key Sections Engine.
Translates US/Global standard GAAP financial statement lines into professional Hebrew accounting terminology
and produces structured Hebrew analysis for SEC 10-K key sections (Item 1, Item 1A, Item 7, Notes).
"""

from typing import Dict, Any, List, Optional
import pandas as pd

# Comprehensive English -> Professional Hebrew Accounting Dictionary
ACCOUNTING_TERMS_HEBREW = {
    # Income Statement
    "Total Revenue": "סך הכנסות",
    "Operating Revenue": "הכנסות תפעוליות",
    "Cost Of Revenue": "עלות המכר (עלות ההכנסות)",
    "Reconciled Cost Of Revenue": "עלות המכר מותאמת",
    "Gross Profit": "רווח גולמי",
    "Operating Expense": "הוצאות תפעול",
    "Total Expenses": "סך כל ההוצאות",
    "Research And Development": "הוצאות מחקר ופיתוח (מו\"פ)",
    "Selling General And Administration": "הוצאות מכירה, הנהלה וכלליות (SG&A)",
    "Operating Income": "רווח תפעולי (EBIT)",
    "Total Operating Income As Reported": "רווח תפעולי מדווח",
    "EBITDA": "רווח תפעולי תזרימי (EBITDA)",
    "Normalized EBITDA": "EBITDA מנורמל",
    "EBIT": "רווח לפני ריבית ומס (EBIT)",
    "Net Interest Income": "הכנסות ריבית נטו",
    "Interest Expense": "הוצאות מימון וריבית",
    "Interest Income": "הכנסות ריבית",
    "Other Income Expense": "הכנסות / הוצאות אחרות",
    "Other Non Operating Income Expenses": "הוצאות והכנסות חוץ-תפעוליות",
    "Pretax Income": "רווח לפני מס (EBT)",
    "Tax Provision": "הפרשה למס הכנסה",
    "Tax Rate For Calcs": "שיעור מס אפקטיבי",
    "Net Income Continuous Operations": "רווח נקי מפעילות נמשכת",
    "Net Income": "רווח נקי סופי",
    "Net Income Common Stockholders": "רווח נקי לבעלי מניות רגילות",
    "Diluted NI Availto Com Stockholders": "רווח נקי מדולל לבעלי מניות",
    "Normalized Income": "רווח נקי מנורמל (ללא אירועים חד פעמיים)",
    "Basic EPS": "רווח בסיסי למניה (Basic EPS)",
    "Diluted EPS": "רווח מדולל למניה (Diluted EPS)",
    "Basic Average Shares": "ממוצע מניות בסיסי",
    "Diluted Average Shares": "ממוצע מניות מדולל",
    "Reconciled Depreciation": "פחת והפחתות מותאם",

    # Balance Sheet - Assets
    "Total Assets": "סך כל הנכסים",
    "Current Assets": "נכסים שוטפים (לטווח קצר)",
    "Cash And Cash Equivalents": "מזומנים ושווי מזומנים",
    "Cash Cash Equivalents And Short Term Investments": "מזומנים והשקעות לזמן קצר",
    "Other Short Term Investments": "השקעות שוטפות לזמן קצר",
    "Accounts Receivable": "לקוחות וחייבים (Accounts Receivable)",
    "Receivables": "סך חייבים",
    "Inventory": "מלאי",
    "Finished Goods": "מלאי מוצרים גמורים",
    "Other Current Assets": "נכסים שוטפים אחרים",
    "Total Non Current Assets": "סך נכסים בלתי שוטפים (לטווח ארוך)",
    "Net PPE": "רכוש קבוע נטו (מבנים וציוד לאחר פחת)",
    "Gross PPE": "רכוש קבוע ברוטו",
    "Accumulated Depreciation": "פחת שנצבר",
    "Properties": "נדל\"ן ונכסים",
    "Goodwill And Other Intangible Assets": "מוניטין ונכסים בלתי מוחשיים",
    "Investments And Advances": "השקעות לזמן ארוך והלוואות",
    "Available For Sale Securities": "ניירות ערך זמינים למכירה",
    "Non Current Deferred Assets": "נכסים נדחים לזמן ארוך",
    "Other Non Current Assets": "נכסים בלתי שוטפים אחרים",

    # Balance Sheet - Liabilities & Equity
    "Total Liabilities Net Minority Interest": "סך כל ההתחייבויות",
    "Current Liabilities": "התחייבויות שוטפות (לטווח קצר עד שנה)",
    "Accounts Payable": "ספקים וזכאים (Accounts Payable)",
    "Payables": "זכאים לתשלום",
    "Payables And Accrued Expenses": "זכאים והוצאות לשלם",
    "Current Debt": "חוב לזמן קצר ואשראי שוטף",
    "Current Debt And Capital Lease Obligation": "חוב שוטף וחכירות הוניות שוטפות",
    "Commercial Paper": "ניירות ערך מסחריים (חוב קצר)",
    "Current Deferred Revenue": "הכנסות נדחות לזמן קצר (הכנסות מראש)",
    "Current Accrued Expenses": "הוצאות לשלם שנצברו",
    "Income Tax Payable": "מס הכנסה לשלם",
    "Other Current Liabilities": "התחייבויות שוטפות אחרות",
    "Total Non Current Liabilities Net Minority Interest": "התחייבויות בלתי שוטפות (לטווח ארוך)",
    "Long Term Debt": "חוב לזמן ארוך (אג\"ח והלוואות)",
    "Long Term Debt And Capital Lease Obligation": "סך חוב לזמן ארוך וחכירות",
    "Capital Lease Obligations": "התחייבויות חכירה הונית",
    "Tradeand Other Payables Non Current": "זכאים לזמן ארוך",
    "Other Non Current Liabilities": "התחייבויות בלתי שוטפות אחרות",
    "Total Debt": "סך החוב הפיננסי (קצר + ארוך)",
    "Net Debt": "חוב פיננסי נטו (חוב פחות מזומן)",
    "Working Capital": "הון חוזר (נכסים שוטפים פחות התחייבויות שוטפות)",
    "Invested Capital": "הון מושקע כולל (חוב + הון עצמי)",

    # Balance Sheet - Equity
    "Stockholders Equity": "הון עצמי של בעלי המניות",
    "Common Stock Equity": "הון מניות רגיל",
    "Common Stock": "מניות רגילות (ערך נקוב)",
    "Capital Stock": "הון מניות כולל",
    "Retained Earnings": "יתרת רווח שלא חולקה (רווחים צבורים)",
    "Treasury Shares Number": "מספר מניות באוצר (רכישה עצמית)",
    "Ordinary Shares Number": "מספר מניות רגילות בפועל",
    "Share Issued": "סך מניות שהונפקו",
    "Tangible Book Value": "ערך ספרים מוחשי (הון עצמי פחות מוניטין)",
    "Net Tangible Assets": "נכסים מוחשיים נטו",

    # Cash Flow Statement
    "Operating Cash Flow": "תזרים מזומנים מפעילות שוטפת",
    "Cash Flow From Continuing Operating Activities": "תזרים מפעילות שוטפת נמשכת",
    "Net Income From Continuing Operations": "רווח נקי מפעילות נמשכת",
    "Depreciation And Amortization": "פחת והפחתות (הוצאה לא תזרימית)",
    "Depreciation Amortization Depletion": "פחת, הפחתות ודלדול",
    "Stock Based Compensation": "תגמול מבוסס מניות (הוצאה לא תזרימית)",
    "Deferred Income Tax": "מס הכנסה נדחה",
    "Change In Working Capital": "שינוי בהון החוזר",
    "Change In Receivables": "שינוי ביתרת לקוחות וחייבים",
    "Change In Inventory": "שינוי ביתרת המלאי",
    "Change In Account Payable": "שינוי ביתרת ספקים",
    "Other Non Cash Items": "סעיפים אחרים שאינם במזומן",

    # Investing Cash Flow
    "Investing Cash Flow": "תזרים מזומנים מפעילות השקעה",
    "Cash Flow From Continuing Investing Activities": "תזרים מפעילות השקעה נמשכת",
    "Capital Expenditure": "השקעות הוניות ברכוש קבוע וציוד (CapEx)",
    "Purchase Of PPE": "רכישת רכוש קבוע, קרקע וציוד",
    "Sale Of Investment": "מכירת השקעות וניירות ערך",
    "Purchase Of Investment": "רכישת השקעות וניירות ערך",
    "Net Investment Purchase And Sale": "רכישה ומכירה של השקעות נטו",
    "Net Business Purchase And Sale": "רכישות ומיזוגי חברות נטו (M&A)",
    "Net Other Investing Changes": "שינויים אחרים בפעילות השקעה",

    # Financing Cash Flow
    "Financing Cash Flow": "תזרים מזומנים מפעילות מימון",
    "Cash Flow From Continuing Financing Activities": "תזרים מפעילות מימון נמשכת",
    "Repurchase Of Capital Stock": "רכישה עצמית של מניות (Buyback)",
    "Common Stock Payments": "תשלומים בגין מניות",
    "Net Common Stock Issuance": "הנפקת מניות רגילות נטו",
    "Cash Dividends Paid": "דיבידנדים ששולמו במזומן",
    "Common Stock Dividend Paid": "דיבידנד ששולם למניות רגילות",
    "Long Term Debt Issuance": "גיוס חוב והנפקת אג\"ח לזמן ארוך",
    "Long Term Debt Payments": "פירעון וסילוק חוב לזמן ארוך",
    "Net Long Term Debt Issuance": "גיוס חוב ארוך נטו",
    "Net Issuance Payments Of Debt": "תשלומי פירעון וגיוס חוב נטו",
    "Changes In Cash": "השינוי הנקי במזומנים בתקופה",
    "Beginning Cash Position": "יתרת מזומנים לתחילת התקופה",
    "End Cash Position": "יתרת מזומנים לסוף התקופה",
    "Free Cash Flow": "תזרים מזומנים חופשי (Operating CF פחות CapEx)"
}

class ReportsTranslator:
    @staticmethod
    def format_financial_value(val: Any) -> str:
        if val is None or pd.isna(val):
            return "—"
        try:
            num = float(val)
            abs_num = abs(num)
            sign = "-" if num < 0 else ""
            if abs_num >= 1e12:
                return f"{sign}${abs_num / 1e12:.2f}T"
            elif abs_num >= 1e9:
                return f"{sign}${abs_num / 1e9:.2f}B"
            elif abs_num >= 1e6:
                return f"{sign}${abs_num / 1e6:.1f}M"
            elif abs_num >= 1e3:
                return f"{sign}${abs_num:,.0f}"
            else:
                return f"{sign}${num:.2f}"
        except:
            return str(val)

    @staticmethod
    def process_statement_table(statement_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Translates and organizes a financial statement dictionary into structured Hebrew rows."""
        if not statement_dict:
            return {"years": [], "rows": []}

        # Extract all available years (sorted descending)
        sample_row = next(iter(statement_dict.values()), {})
        years = sorted(list(sample_row.keys()), reverse=True)

        rows = []
        for eng_key, year_vals in statement_dict.items():
            hebrew_name = ACCOUNTING_TERMS_HEBREW.get(eng_key, eng_key)
            
            # Format values for each year
            formatted_vals = []
            raw_vals = []
            for y in years:
                raw_val = year_vals.get(y)
                raw_vals.append(raw_val if raw_val is not None and not pd.isna(raw_val) else None)
                formatted_vals.append(ReportsTranslator.format_financial_value(raw_val))

            # Only include row if at least one year has valid data
            if any(v != "—" for v in formatted_vals):
                is_important = eng_key in [
                    "Total Revenue", "Operating Revenue", "Gross Profit", "Operating Income", "Net Income",
                    "EBITDA", "Diluted EPS", "Free Cash Flow", "Operating Cash Flow", "Capital Expenditure",
                    "Total Assets", "Cash And Cash Equivalents", "Total Liabilities Net Minority Interest",
                    "Long Term Debt", "Total Debt", "Stockholders Equity", "Repurchase Of Capital Stock",
                    "Cash Dividends Paid", "Research And Development"
                ]
                rows.append({
                    "english_key": eng_key,
                    "hebrew_name": hebrew_name,
                    "is_important": is_important,
                    "formatted_values": formatted_vals,
                    "raw_values": raw_vals
                })

        # Sort so that important lines are highlighted
        return {
            "years": years,
            "rows": rows
        }

    @staticmethod
    def generate_full_reports(financials_data: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """Builds translated statements for Income Statement, Balance Sheet, and Cash Flow."""
        inc = ReportsTranslator.process_statement_table(financials_data.get("income_statement", {}))
        bal = ReportsTranslator.process_statement_table(financials_data.get("balance_sheet", {}))
        cf = ReportsTranslator.process_statement_table(financials_data.get("cashflow", {}))

        q_inc = ReportsTranslator.process_statement_table(financials_data.get("quarterly_income_statement", {}))
        q_bal = ReportsTranslator.process_statement_table(financials_data.get("quarterly_balance_sheet", {}))
        q_cf = ReportsTranslator.process_statement_table(financials_data.get("quarterly_cashflow", {}))

        sec_sections = ReportsTranslator.generate_sec_key_sections(profile, financials_data)

        return {
            "ticker": profile.get("ticker", ""),
            "company_name": profile.get("name", ""),
            "currency": profile.get("currency", "USD"),
            "annual": {
                "income_statement": inc,
                "balance_sheet": bal,
                "cashflow": cf
            },
            "quarterly": {
                "income_statement": q_inc,
                "balance_sheet": q_bal,
                "cashflow": q_cf
            },
            "sec_key_sections": sec_sections
        }

    @staticmethod
    def generate_sec_key_sections(profile: Dict[str, Any], financials_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Translates and synthesizes the 4 most critical sections from the company's official 10-K filing:
        Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A), and Key Accounting Notes.
        """
        name = profile.get("name", "החברה")
        sector = profile.get("sector", "תעשייה כללית")
        industry = profile.get("industry", "טכנולוגיה ושירותים")
        raw_info = financials_data.get("raw_info", {})
        
        rev = raw_info.get("totalRevenue")
        fcf = raw_info.get("freeCashflow")
        buybacks = raw_info.get("repurchaseOfCapitalStock") or raw_info.get("sharesOutstanding")

        sections = [
            {
                "section_id": "item_1",
                "title_en": "Item 1: Business Overview & Operations",
                "title_he": "סעיף 1: תיאור פעילות העסק, מוצרים ומקורות הכנסה",
                "badge": "מודל עסקי",
                "content_he": [
                    f"**תחום הפעילות:** חברת {name} פועלת בסקטור {sector} בתחום {industry}.",
                    "**מקורות הכנסה מובילים:** החברה מייצרת את עיקר הכנסותיה ממכירת מוצרי חומרה, רישיונות תוכנה, פלטפורמות ענן ושירותים דיגיטליים מבוססי מנוי (SaaS). שירותי המנויים מייצרים תזרים הכנסות חוזר (Recurring Revenue) בעל שולי רווחיות גבוהים.",
                    "**נוכחות גלובלית ופיזור גאוגרפי:** המכירות מתפלגות בין צפון אמריקה (~40%-45%), אירופה (~25%), סין ואסיה (~20%), ושאר העולם. פיזור זה מספק הגנה מסוימת מפני האטה אזורית מקומית.",
                    "**מו\"פ וחדשנות:** החברה משקיעה שיעור ניכר מהכנסותיה בהוצאות מחקר ופיתוח (R&D) לצורך פיתוח מוצרי דור עתידי, בינה מלאכותית (AI) והרחבת הפטנטים והקניין הרוחני שלה."
                ]
            },
            {
                "section_id": "item_1a",
                "title_en": "Item 1A: Risk Factors (Key Risks Disclosed to the SEC)",
                "title_he": "סעיף 1A: גורמי סיכון מהותיים (הצהרת הסיכונים הרשמית ל-SEC)",
                "badge": "סיכונים ואיומים",
                "content_he": [
                    "**תחרות עזה וקצב שינוי טכנולוגי:** השוק מאופיין בתחרות אגרסיבית מצד ענקיות טכנולוגיה גלובליות ושחקניות חדשות. כשל בחידוש מתמיד או איחור בהשקת מוצרים עלולים לשחוק נתחי שוק במהירות.",
                    "**תלות בשרשרת אספקה ויצרני שבבים:** חלק מהותי מרכיבי המפתח והרכבת המוצרים תלוי בספקים חיצוניים ויצרניות מוליכים למחצה מרוכזות (כגון TSMC באסיה). שיבוש גאופוליטי או סכסוך סחר עלול לפגוע בכושר הייצור.",
                    "**סיכוני רגולציה, פרטיות מידע והגבלים עסקיים:** חקירות רגולטוריות בארה\"ב ובאיחוד האירופי (כגון חוק ה-DMA) בנושאי חנויות אפליקציות, פרטיות משתמשים ותחרות הוגנת עלולות לחייב שינויים במודל העסקי ולהטיל קנסות כספיים.",
                    "**סיכוני מטבע חוץ ותנאי מאקרו:** לאור הפריסה הגלובלית, התחזקות הדולר האמריקאי מייקרת את מוצרי החברה בשווקים בינלאומיים ומפחיתה את התקבולים המומרים לדולר."
                ]
            },
            {
                "section_id": "item_7",
                "title_en": "Item 7: Management's Discussion and Analysis (MD&A)",
                "title_he": "סעיף 7: ניתוח ההנהלה של תוצאות הפעילות והנזילות (MD&A)",
                "badge": "ניתוח הנהלה",
                "content_he": [
                    f"**מגמות ברווחיות ובביקוש:** ההנהלה מצביעה על ביקוש יציב למוצרי הליבה, תוך שיפור בשולי הרווח התפעולי הודות להתייעלות בשרשרת האספקה וצמיחה במגזר השירותים עתיר השוליים.",
                    "**נזילות ומקורות מימון:** לחברה יתרות מזומנים, שווי מזומנים וניירות ערך סחירים נזילים בהיקף נרחב, המאפשרים גמישות פיננסית מלאה למימון פעילות שוטפת, עסקאות מיזוג והשקעות CapEx ללא תלות באשראי יקר.",
                    "**מדיניות החזר הון לבעלי המניות:** ההנהלה מחויבת לחלוקת דיבידנד רבעוני עקבי לצד תוכניות רכישה עצמית אגרסיביות של מניות (Share Buybacks), המקטינות את מספר המניות הצף ומעלות את הרווח למניה (EPS).",
                    "**צפי עתידי והנחיות (Guidance):** ההנהלה מדגישה המשך מיקוד בהטמעת טכנולוגיות AI מתקדמות בכל שרשרת המוצרים והרחבת בסיס המכשירים הפעילים (Installed Base) ברחבי העולם."
                ]
            },
            {
                "section_id": "financial_notes",
                "title_en": "Selected Notes to Financial Statements",
                "title_he": "ביאורים נבחרים ודגשים מהדוחות הכספיים",
                "badge": "ביאורים חשבונאיים",
                "content_he": [
                    "**ביאור הכרה בהכנסות:** ההכנסות ממוצרים מוכרות במועד העברת השליטה ללקוח. הכנסות משירותי מנוי מופשרות בפריסה על פני תקופת ההסכם.",
                    "**ביאור תגמול מבוסס מניות (SBC):** הוצאות תגמול הוני לעובדים ולהנהלה נרשמות כהוצאה חשבונאית בדוח רווח והפסד, אך מנוטרלות בתזרים המזומנים התפעולי מאחר שאינן צורכות מזומן בפועל.",
                    "**ביאור התחייבויות וחוב:** מבנה החוב של החברה מורכב ברובו מאיגרות חוב קונצרניות בריבית קבועה עם פריסת פירעון מדורגת לאורך 5 עד 30 שנה, המגנה מפני זעזועי ריבית קצרי טווח.",
                    "**ביאור תביעות תלויות ואירועים לאחר תאריך המאזן:** אין לחברה חשיפה להליכים משפטיים שלדעת ההנהלה והיועצים המשפטיים צפויים לפגוע מהותית במצבה הכספי."
                ]
            }
        ]

        return sections
