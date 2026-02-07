"""
Perspective Node

Generates photorealistic 3D perspective views of room layouts.
FULLY TRACED with LangSmith - including Gemini image generation calls.

Approach: Pass ONLY the layout image to Gemini with a short prompt
telling it to convert the top-down view into an eye-level photograph.
No furniture position text — the image contains all the info needed.
"""

import base64
import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from app.config import get_settings
from app.models.state import AgentState
from app.models.room import RoomObject, RoomDimensions

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


# ============================================================================
# DEBUG HELPER
# ============================================================================
import os
import json
from datetime import datetime

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "debug_logs")

def _ensure_debug_dir():
    os.makedirs(DEBUG_DIR, exist_ok=True)

def _save_debug_json(filename: str, data: Any):
    try:
        _ensure_debug_dir()
        filepath = os.path.join(DEBUG_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[Perspective] Saved debug: {filepath}")
    except Exception as e:
        print(f"[Perspective] Failed to save debug {filename}: {e}")


class PerspectiveGenerator:
    """
    Generates photorealistic perspective renders of room layouts.
    All methods are traced with LangSmith.
    """
    
    def __init__(self):
        settings = get_settings()
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=settings.google_api_key)
        self.image_model = settings.image_model_name


    @traceable(
        name="perspective_generator.generate_side_view", 
        run_type="chain", 
        tags=["perspective", "3d", "generation"]
    )
    async def generate_side_view(
        self,
        layout: List[RoomObject],
        room_dims: RoomDimensions,
        style: str = "modern",
        view_angle: str = "corner",
        lighting: str = "natural daylight",
        image_base64: Optional[str] = None,
        layout_plan: Optional[dict] = None,
    ) -> str:
        """
        Generate a photorealistic perspective view from a layout image.
        
        The layout image already contains all furniture positions visually.
        We pass ONLY the image + a short prompt to avoid confusing Gemini
        with text positions that might contradict what it sees.
        """
        prompt = self._build_perspective_prompt(room_dims, style, view_angle, lighting)
        
        # Debug logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _save_debug_json(f"{timestamp}_perspective_INPUT.json", {
            "prompt": prompt,
            "layout_count": len(layout),
            "room_dims": room_dims.dict(),
            "style": style,
            "has_image": image_base64 is not None,
        })

        if not image_base64:
            raise RuntimeError("No layout image provided for perspective generation.")

        try:
            result = await self._call_gemini_image_generation(prompt, image_base64)
            print(f"[Perspective] Generation successful")
            return result
        except Exception as e:
            _save_debug_json(f"{timestamp}_perspective_ERROR.json", {"error": str(e)})
            print(f"[Perspective] Generation failed: {e}")
            raise e

    @traceable(
        name="gemini_perspective_generation", 
        run_type="llm", 
        tags=["gemini", "image", "perspective", "api-call"],
        metadata={"model_type": "gemini-image", "task": "perspective_generation"}
    )
    async def _call_gemini_image_generation(self, prompt: str, image_base64: str) -> str:
        """
        Make the Gemini image generation API call.
        Image is always required for perspective generation.
        """
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        image_data = base64.b64decode(image_base64)
        contents = [
            types.Part.from_bytes(data=image_data, mime_type="image/png"),
            prompt
        ]

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.image_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["image", "text"],
                temperature=0.3,
            )
        )
        
        if (response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts):
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    return base64.b64encode(part.inline_data.data).decode('utf-8')
        
        raise RuntimeError("No image generated in response")

    def _build_perspective_prompt(
        self,
        room_dims: RoomDimensions,
        style: str,
        view_angle: str,
        lighting: str
    ) -> str:
        """Build a short, focused prompt. The image does the heavy lifting."""
        return f"""Convert this 2D top-down floor plan into a photorealistic EYE-LEVEL photograph of the same room.

RULES:
1. Keep ALL furniture exactly as shown in the floor plan — same items, same positions.
2. Camera: eye-level (5 feet high), standing at the {view_angle}/doorway, looking across the room.
3. Output MUST show walls, floor with perspective depth, and ceiling.
4. DO NOT produce another top-down or bird's-eye view.

Room: ~{room_dims.width_estimate:.0f} x {room_dims.height_estimate:.0f} ft, 9ft ceiling, {style} style, {lighting}.

Generate a photorealistic interior photograph from eye-level."""


# LangGraph node functions

@traceable(name="perspective_node", run_type="chain", tags=["langgraph", "node", "perspective"])
async def perspective_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that generates perspective renders.
    """
    generator = PerspectiveGenerator()
    
    try:
        layout = state.get("proposed_layout") or state.get("current_layout", [])
        room_dims = state["room_dimensions"]
        
        image_base64 = await generator.generate_side_view(
            layout=layout,
            room_dims=room_dims,
            style="modern",
            view_angle="corner",
            lighting="natural daylight"
        )
        
        return {
            "output_image_url": None,
            "output_image_base64": image_base64,
            "explanation": state.get("explanation", "") + "\n\nGenerated photorealistic perspective view.",
        }
        
    except Exception as e:
        return {
            "error": f"Perspective generation failed: {str(e)}",
            "output_image_base64": None
        }


def perspective_node_sync(state: AgentState) -> Dict[str, Any]:
    """Synchronous wrapper for LangGraph compatibility."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(perspective_node(state))
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, perspective_node(state))
            return future.result()