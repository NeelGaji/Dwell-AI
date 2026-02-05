"""
Optimize Route

POST /optimize - Generate AI-powered layout variations with preview images.

FULLY TRACED with LangSmith.

FIXES APPLIED:
1. Auto-populate locked_ids with all structural object IDs
2. Better error handling and validation
"""

import asyncio
from fastapi import APIRouter, HTTPException

from app.models.api import OptimizeRequest, OptimizeResponse, LayoutVariation
from app.models.room import ObjectType
from app.agents.designer_node import InteriorDesignerAgent
from app.core.scoring import score_layout

# LangSmith tracing
try:
    from langsmith import traceable
    LANGSMITH_ENABLED = True
except ImportError:
    LANGSMITH_ENABLED = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


router = APIRouter(prefix="/optimize", tags=["Optimization"])


@router.post("", response_model=OptimizeResponse)
@traceable(name="optimize_layout_endpoint", run_type="chain", tags=["api", "optimization", "designer"])
async def optimize_layout(request: OptimizeRequest) -> OptimizeResponse:
    """
    Generate AI-powered layout variations with preview images.
    
    This endpoint:
    1. Takes current layout, locked objects, and ORIGINAL IMAGE
    2. Auto-adds all structural objects to locked_ids
    3. Generates 3 layout variations (Work Focused, Cozy, Creative)
    4. Creates photorealistic preview images by editing the original floor plan
    5. Returns variations with thumbnails for user selection
    
    TRACED: Full trace including Designer agent and thumbnail generation.
    """
    try:
        # STEP 1: Build complete locked_ids including ALL structural objects
        # This ensures structural objects are NEVER moved
        complete_locked_ids = set(request.locked_ids)
        
        for obj in request.current_layout:
            # Add structural objects to locked list
            if obj.type == ObjectType.STRUCTURAL:
                complete_locked_ids.add(obj.id)
                obj.is_locked = True  # Also mark as locked
            
            # Mark user-locked objects
            if obj.id in request.locked_ids:
                obj.is_locked = True
        
        locked_ids_list = list(complete_locked_ids)
        
        # Log for debugging
        movable_count = sum(1 for o in request.current_layout if o.id not in complete_locked_ids)
        structural_count = len(complete_locked_ids)
        print(f"[Optimize] Objects: {len(request.current_layout)} total, {movable_count} movable, {structural_count} locked/structural")
        print(f"[Optimize] Locked IDs: {locked_ids_list}")
        
        # STEP 2: Validate we have movable objects
        if movable_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No movable objects found. All objects are either structural or locked."
            )
        
        # STEP 3: Initialize designer agent (traced internally)
        designer = InteriorDesignerAgent()
        
        # STEP 4: Generate variations WITH preview images
        variations_data = await designer.generate_layout_variations(
            current_layout=request.current_layout,
            room_dims=request.room_dimensions,
            locked_ids=locked_ids_list,  # Pass complete locked IDs
            image_base64=request.image_base64
        )
        
        # STEP 5: Convert to LayoutVariation models
        variations = []
        for var in variations_data:
            # Calculate score if not already done
            layout_score = var.get("score")
            if layout_score is None:
                score_obj = score_layout(
                    var["layout"],
                    int(request.room_dimensions.width_estimate),
                    int(request.room_dimensions.height_estimate)
                )
                layout_score = score_obj.total_score
            
            variations.append(LayoutVariation(
                name=var["name"],
                description=var["description"],
                layout=var["layout"],
                thumbnail_base64=var.get("thumbnail_base64"),
                score=layout_score
            ))
        
        # STEP 6: Sort by score (highest first)
        variations.sort(key=lambda v: v.score or 0, reverse=True)
        
        # Get best variation for legacy fields
        best = variations[0] if variations else None
        
        # Count thumbnails generated
        thumbnails_generated = sum(1 for v in variations if v.thumbnail_base64)
        
        return OptimizeResponse(
            variations=variations,
            message=f"Generated {len(variations)} layouts ({thumbnails_generated} with preview images). {structural_count} structural objects locked.",
            new_layout=best.layout if best else request.current_layout,
            explanation=best.description if best else "No variations generated",
            layout_score=best.score if best else 0.0,
            iterations=1,
            constraint_violations=[],
            improvement=0.0
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        print(f"[Optimize] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Layout optimization failed: {str(e)}"
        )