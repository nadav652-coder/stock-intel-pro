"""
Smart Search & Natural Language Query Resolver.
Enables free-form, casual, and multilingual (Hebrew & English) stock & ETF searches,
supporting company names, Hebrew phonetic aliases, thematic sectors, and live fuzzy search.
"""

from typing import List, Dict, Any
import requests

# Hebrew Phonetic & Common Names Dictionary
HEBREW_NAME_MAPPING = {
    "אפל": ("AAPL", "Apple Inc.", "טכנולוגיה (חומרה ושירותים)"),
    "אפל מיוזיק": ("AAPL", "Apple Inc.", "טכנולוגיה"),
    "מיקרוסופט": ("MSFT", "Microsoft Corporation", "תוכנה וענן Azure"),
    "אנבידיה": ("NVDA", "NVIDIA Corporation", "מוליכים למחצה ו-AI"),
    "נווידיה": ("NVDA", "NVIDIA Corporation", "מוליכים למחצה ו-AI"),
    "נוידיה": ("NVDA", "NVIDIA Corporation", "מוליכים למחצה ו-AI"),
    "גוגל": ("GOOGL", "Alphabet Inc. (Google)", "חיפוש, פרסום ו-AI"),
    "אלפבית": ("GOOGL", "Alphabet Inc.", "טכנולוגיה ותקשורת"),
    "אמזון": ("AMZN", "Amazon.com Inc.", "מסחר אלקטרוני וענן AWS"),
    "מטא": ("META", "Meta Platforms Inc.", "פייסבוק, אינסטגרם ו-AI"),
    "פייסבוק": ("META", "Meta Platforms Inc.", "רשתות חברתיות"),
    "טסלה": ("TSLA", "Tesla Inc.", "רכב חשמלי ואנרגיה נקייה"),
    "טסלא": ("TSLA", "Tesla Inc.", "רכב חשמלי ואנרגיה"),
    "נטפליקס": ("NFLX", "Netflix Inc.", "סטרימינג ומדיה"),
    "אינטל": ("INTC", "Intel Corporation", "מעבדים ושבבים"),
    "אי אמ די": ("AMD", "Advanced Micro Devices", "שבבים ומעבדים גרפיים"),
    "טייוואן סמיקונדקטור": ("TSM", "Taiwan Semiconductor (TSMC)", "ייצור שבבים עולמי"),
    "טי אס אם סי": ("TSM", "TSMC", "ייצור שבבים"),
    "ברקשייר": ("BRK-B", "Berkshire Hathaway", "חברת ההשקעות של וורן באפט"),
    "ברקשיר": ("BRK-B", "Berkshire Hathaway", "השקעות ערך וביטוח"),
    "באפט": ("BRK-B", "Berkshire Hathaway", "וורן באפט"),
    "פלנטיר": ("PLTR", "Palantir Technologies", "ניתוח נתונים, ביטחון ו-AI"),
    "פאלאנטיר": ("PLTR", "Palantir Technologies", "תוכנה ביטחונית ו-AI"),
    "טבע": ("TEVA", "Teva Pharmaceutical", "תרופות גנריות"),
    "צ'ק פוינט": ("CHKP", "Check Point Software", "אבטחת סייבר וחומות אש"),
    "צק פוינט": ("CHKP", "Check Point Software", "סייבר ישראלי"),
    "וויקס": ("WIX", "Wix.com", "פלטפורמת בניית אתרים"),
    "מובילאיי": ("MBLY", "Mobileye Global", "מערכות נהיגה אוטונומית"),
    "פייבר": ("FVRR", "Fiverr International", "פלטפורמת פרילנסרים"),
    "נייקי": ("NKE", "Nike Inc.", "הנעלה וביגוד ספורט"),
    "קוקה קולה": ("KO", "The Coca-Cola Company", "משקאות ודיבידנד יציב"),
    "פפסי": ("PEP", "PepsiCo Inc.", "משקאות וחטיפים"),
    "דיסני": ("DIS", "The Walt Disney Company", "בידור, פארקים ומדיה"),
    "פייפאל": ("PYPL", "PayPal Holdings", "תשלומים דיגיטליים ופינטק"),
    "אובר": ("UBER", "Uber Technologies", "תחבורה שיתופית ומשלוחים"),
    "איירביאנבי": ("ABNB", "Airbnb Inc.", "אירוח ותיירות"),
    "ספוטיפיי": ("SPOT", "Spotify Technology", "סטרימינג מוזיקלי"),
    "קראודסטרייק": ("CRWD", "CrowdStrike Holdings", "אבטחת סייבר מתקדמת"),
    "אלי לילי": ("LLY", "Eli Lilly and Company", "תרופות והרזיה (GLP-1)"),
    "נובו נורדיסק": ("NVO", "Novo Nordisk", "תרופות וסוכרת / אוזמפיק"),
    "אורקל": ("ORCL", "Oracle Corporation", "מאגרי מידע וענן"),
    "קוואלקום": ("QCOM", "Qualcomm Inc.", "שבבים לתקשורת וסלולר"),
    "ברודקום": ("AVGO", "Broadcom Inc.", "שבבי תקשורת ותוכנה ארגונית")
}

# Thematic / Sector Keywords
THEMATIC_KEYWORD_MAPPING = {
    "שבבים": [
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "desc": "מובילת מהפכת שבבי ה-AI", "type": "מניה"},
        {"ticker": "SMH", "name": "VanEck Semiconductor ETF", "desc": "קרן סל ענף השבבים", "type": "קרן סל ETF"},
        {"ticker": "AMD", "name": "Advanced Micro Devices", "desc": "מעבדים וכרטיסים גרפיים", "type": "מניה"},
        {"ticker": "TSM", "name": "TSMC", "desc": "יצרנית השבבים הגדולה בעולם", "type": "מניה"},
        {"ticker": "AVGO", "name": "Broadcom", "desc": "שבבי תקשורת ורשתות", "type": "מניה"}
    ],
    "סייבר": [
        {"ticker": "CRWD", "name": "CrowdStrike Holdings", "desc": "אבטחת נקודות קצה וענן", "type": "מניה"},
        {"ticker": "PANW", "name": "Palo Alto Networks", "desc": "פלטפורמות אבטחת מידע", "type": "מניה"},
        {"ticker": "CHKP", "name": "Check Point Software", "desc": "חלוצת חומות האש (Firewall)", "type": "מניה"},
        {"ticker": "FTNT", "name": "Fortinet Inc.", "desc": "אבטחת רשתות ארגוניות", "type": "מניה"}
    ],
    "דיבידנד": [
        {"ticker": "SCHD", "name": "Schwab US Dividend Equity ETF", "desc": "קרן סל מניות דיבידנד איכותיות", "type": "קרן סל ETF"},
        {"ticker": "JNJ", "name": "Johnson & Johnson", "desc": "בריאות ודיבידנד יציב עשרות שנים", "type": "מניה"},
        {"ticker": "PG", "name": "Procter & Gamble", "desc": "מוצרי צריכה בסיסיים ודיבידנד צומח", "type": "מניה"},
        {"ticker": "KO", "name": "The Coca-Cola Company", "desc": "מניית ערך ודיבידנד מועדפת על באפט", "type": "מניה"}
    ],
    "מדד": [
        {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "desc": "500 החברות הגדולות בארה\"ב", "type": "קרן סל ETF"},
        {"ticker": "QQQ", "name": "Invesco QQQ Trust (Nasdaq 100)", "desc": "100 חברות הטכנולוגיה המובילות", "type": "קרן סל ETF"},
        {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "desc": "קרן סל S&P 500 בדמי ניהול אפסיים (0.03%)", "type": "קרן סל ETF"},
        {"ticker": "DIA", "name": "SPDR Dow Jones Industrial ETF", "desc": "מדד דאו ג'ונס (30 ענקיות התעשייה)", "type": "קרן סל ETF"}
    ],
    "נאסדק": [
        {"ticker": "QQQ", "name": "Invesco QQQ Trust", "desc": "מדד נאסד\"ק 100", "type": "קרן סל ETF"},
        {"ticker": "TQQQ", "name": "ProShares UltraPro QQQ", "desc": "קרן ממונפת פי 3 על מדד נאסד\"ק", "type": "קרן סל ETF"}
    ],
    "אס אנד פי": [
        {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "desc": "מדד S&P 500", "type": "קרן סל ETF"},
        {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "desc": "מדד S&P 500 בדמי ניהול מזעריים", "type": "קרן סל ETF"}
    ],
    "סנופי": [
        {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "desc": "כינוי עממי למדד S&P 500", "type": "קרן סל ETF"},
        {"ticker": "VOO", "name": "Vanguard S&P 500", "desc": "קרן סל S&P 500", "type": "קרן סל ETF"}
    ],
    "בינה מלאכותית": [
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "desc": "שבבי בינה מלאכותית ומאיצים", "type": "מניה"},
        {"ticker": "MSFT", "name": "Microsoft Corporation", "desc": "שותפת OpenAI וענן Azure AI", "type": "מניה"},
        {"ticker": "PLTR", "name": "Palantir Technologies", "desc": "פלטפורמת AIP ליישומי בינה מלאכותית", "type": "מניה"},
        {"ticker": "GOOGL", "name": "Alphabet (Google Gemini)", "desc": "מודלי שפה וענן בינה מלאכותית", "type": "מניה"}
    ]
}

class SearchResolver:
    @staticmethod
    def resolve(query: str, limit: int = 8) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        lower_q = query.lower()
        results: List[Dict[str, Any]] = []
        seen_tickers = set()

        # 1. Exact or partial Hebrew name matches
        for heb_name, (sym, name, sec) in HEBREW_NAME_MAPPING.items():
            if lower_q in heb_name.lower() or heb_name.lower() in lower_q:
                if sym not in seen_tickers:
                    seen_tickers.add(sym)
                    results.append({
                        "ticker": sym,
                        "name": name,
                        "desc": sec,
                        "type": "מניה"
                    })

        # 2. Thematic keyword matches
        for theme_key, items in THEMATIC_KEYWORD_MAPPING.items():
            if lower_q in theme_key.lower() or theme_key.lower() in lower_q:
                for it in items:
                    sym = it["ticker"]
                    if sym not in seen_tickers:
                        seen_tickers.add(sym)
                        results.append({
                            "ticker": sym,
                            "name": it["name"],
                            "desc": it["desc"],
                            "type": it["type"]
                        })

        # 3. Live Yahoo Finance search (handles English names, tickers, international assets)
        # Only if we still have room in limits
        if len(results) < limit:
            try:
                url = "https://query2.finance.yahoo.com/v1/finance/search"
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(url, params={"q": query, "quotesCount": 10}, headers=headers, timeout=2.5)
                if res.status_code == 200:
                    quotes = res.json().get("quotes", [])
                    for q in quotes:
                        sym = q.get("symbol", "")
                        # Filter out obscure futures/options contracts, keep equities and ETFs
                        if not sym or "=" in sym or "^" in sym or "+" in sym:
                            continue
                        if sym not in seen_tickers:
                            seen_tickers.add(sym)
                            q_type = "קרן סל ETF" if q.get("quoteType") == "ETF" else "מניה"
                            desc = q.get("sector") or q.get("industry") or q.get("exchange") or ""
                            results.append({
                                "ticker": sym,
                                "name": q.get("shortname") or q.get("longname") or sym,
                                "desc": desc,
                                "type": q_type
                            })
                            if len(results) >= limit:
                                break
            except Exception as e:
                print(f"[SearchResolver] Live search note: {e}")

        # If user typed an exact short English ticker that didn't match yet
        clean_upper = query.upper()
        if query.isascii() and len(clean_upper) <= 5 and clean_upper.isalnum() and clean_upper not in seen_tickers:
            results.insert(0, {
                "ticker": clean_upper,
                "name": f"סימול: {clean_upper}",
                "desc": "חיפוש לפי סימול ישיר",
                "type": "מניה / קרן"
            })

        return results[:limit]
