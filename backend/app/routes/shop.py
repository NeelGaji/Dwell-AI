"""
Shop Route

POST /shop - Find real products matching the furniture in the user's room.

Uses Gemini for style analysis + SerpAPI for Google Shopping search.
FULLY TRACED with LangSmith.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.models.room import RoomObject

try:
    from langsmith import traceable
    LANGSMITH_ENABLED = True
except ImportError:
    LANGSMITH_ENABLED = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


router = APIRouter(prefix="/shop", tags=["Shopping"])


# === Request / Response Models ===

class ShopRequest(BaseModel):
    """Request body for /shop endpoint."""
    current_layout: List[RoomObject] = Field(..., description="Current furniture layout")
    total_budget: float = Field(..., gt=0, description="Total room budget in USD")
    perspective_image_base64: Optional[str] = Field(None, description="Perspective render for style context")


class ProductResult(BaseModel):
    """A single product from Google Shopping."""
    title: str = ""
    price: Optional[float] = None
    price_raw: str = ""
    link: str = ""
    thumbnail: str = ""
    source: str = ""
    rating: Optional[float] = None
    reviews: Optional[int] = None


class ShopItemResult(BaseModel):
    """Products found for a single furniture item."""
    furniture_id: str
    furniture_label: str
    search_query: str = ""
    budget_allocated: float = 0
    products: List[ProductResult] = []
    error: Optional[str] = None


class ShopResponse(BaseModel):
    """Response from /shop endpoint."""
    items: List[ShopItemResult]
    total_estimated: float = 0
    total_budget: float = 0
    message: str = ""


# === Endpoint ===

@router.post("", response_model=ShopResponse)
@traceable(
    name="shop_products_endpoint",
    run_type="chain",
    tags=["api", "shopping", "agent"],
    metadata={"description": "Find real products for room furniture"}
)
async def shop_products(request: ShopRequest) -> ShopResponse:
    """
    Find real products matching the furniture in the user's room.

    This endpoint:
    1. Uses Gemini to analyze furniture style and generate search queries
    2. Allocates the budget proportionally across items
    3. Searches Google Shopping via SerpAPI for each item
    4. Returns product recommendations with prices and links

    TRACED: Full trace including Gemini + SerpAPI calls.
    """
    try:
        from app.agents.shopping_node import ShoppingAgent

        agent = ShoppingAgent()

        result = await agent.find_products(
            current_layout=request.current_layout,
            total_budget=request.total_budget,
            perspective_image_base64=request.perspective_image_base64,
        )

        # Convert raw dicts to response models
        items = []
        for item_data in result.get("items", []):
            products = [
                ProductResult(**p) for p in item_data.get("products", [])
            ]
            items.append(ShopItemResult(
                furniture_id=item_data["furniture_id"],
                furniture_label=item_data["furniture_label"],
                search_query=item_data.get("search_query", ""),
                budget_allocated=item_data.get("budget_allocated", 0),
                products=products,
                error=item_data.get("error"),
            ))

        return ShopResponse(
            items=items,
            total_estimated=result.get("total_estimated", 0),
            total_budget=result.get("total_budget", request.total_budget),
            message=result.get("message", ""),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Shopping agent failed: {str(e)}"
        )