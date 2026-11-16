"""
Pydantic Request & Response Schemas for API validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class DCFSimulationRequest(BaseModel):
    ticker: str
    wacc: Optional[float] = Field(None, ge=0.04, le=0.25, description="Discount rate / WACC (0.04 to 0.25)")
    growth_rate: Optional[float] = Field(None, ge=-0.10, le=0.50, description="5-Year FCF growth rate (-0.10 to 0.50)")

class QuickSearchItem(BaseModel):
    ticker: str
    name: str
    sector: str

class PortfolioItem(BaseModel):
    ticker: str
    shares: float = Field(..., gt=0)
    buy_price: float = Field(..., ge=0)

class PortfolioAnalyzeRequest(BaseModel):
    holdings: List[PortfolioItem]

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
