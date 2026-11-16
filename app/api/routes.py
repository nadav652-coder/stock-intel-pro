"""
FastAPI Routes module: Endpoints for Stock Analysis, DCF Simulation, Search, and Web UI.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from typing import Dict, Any, List
from app.api.service import analysis_service
from app.engines.search_resolver import SearchResolver
from app.api.schemas import DCFSimulationRequest, QuickSearchItem, ApiResponse, PortfolioAnalyzeRequest

router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"

POPULAR_TICKERS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "טכנולוגיה (חומרה ושירותים)"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "תוכנה וענן"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "מוליכים למחצה ו-AI"},
    {"ticker": "GOOGL", "name": "Alphabet Inc. (Google)", "sector": "שירותי תקשורת ואינטרנט"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "מסחר אלקטרוני וענן AWS"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "מדיה חברתית ו-AI"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "רכב חשמלי ואנרגיה"},
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "sector": "קרן סל מחקה מדד S&P 500"},
    {"ticker": "QQQ", "name": "Invesco QQQ Trust (Nasdaq 100)", "sector": "קרן סל מחקה מדד נאסד\"ק 100"},
    {"ticker": "SCHD", "name": "Schwab U.S. Dividend Equity ETF", "sector": "קרן סל מניות דיבידנד איכותיות"},
    {"ticker": "SMH", "name": "VanEck Semiconductor ETF", "sector": "קרן סל שבבים ומוליכים למחצה"}
]

@router.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard template not found")
    return FileResponse(index_path)

@router.get("/api/stock/{ticker}", response_model=ApiResponse)
async def get_stock_analysis(ticker: str):
    ticker = ticker.strip()
    # If a Hebrew alias or non-ascii word is passed in URL, resolve it to its primary ticker
    if not ticker.isascii():
        resolved_matches = SearchResolver.resolve(ticker)
        if resolved_matches:
            ticker = resolved_matches[0]["ticker"]
        else:
            ticker = "AAPL"

    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 15:
        raise HTTPException(status_code=400, detail="סימול מניה לא תקין")
    try:
        data = analysis_service.run_full_analysis(ticker)
        return ApiResponse(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=f"שגיאה בניתוח המניה {ticker}: {str(e)}")

@router.get("/api/stock/{ticker}/reports", response_model=ApiResponse)
async def get_stock_financial_reports(ticker: str):
    ticker = ticker.upper().strip()
    try:
        reports = analysis_service.get_financial_reports(ticker)
        return ApiResponse(success=True, data=reports)
    except Exception as e:
        return ApiResponse(success=False, error=f"שגיאה בשליפת דוחות מתורגמים עבור {ticker}: {str(e)}")

@router.post("/api/valuation/dcf", response_model=ApiResponse)
async def simulate_dcf(request: DCFSimulationRequest):
    try:
        val = analysis_service.simulate_custom_dcf(
            ticker=request.ticker,
            custom_wacc=request.wacc,
            custom_growth=request.growth_rate
        )
        return ApiResponse(success=True, data=val)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))

@router.post("/api/portfolio/analyze", response_model=ApiResponse)
async def analyze_portfolio_endpoint(request: PortfolioAnalyzeRequest):
    try:
        holdings_dicts = [h.dict() for h in request.holdings]
        analysis = analysis_service.analyze_portfolio(holdings_dicts)
        return ApiResponse(success=True, data=analysis)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=f"שגיאה בניתוח התיק: {str(e)}")

@router.get("/api/search")
async def search_tickers(q: str = Query("", min_length=0)):
    q = q.strip()
    if not q:
        return POPULAR_TICKERS
    try:
        resolved = SearchResolver.resolve(q)
        return resolved
    except Exception as e:
        print(f"[Routes] Search error: {e}")
        return [{"ticker": q.upper(), "name": q, "desc": "חיפוש ישיר", "type": "מניה"}]

@router.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Stock Intelligence Platform", "version": "1.0.0"}
