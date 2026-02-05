"""
Perspective Node

Generates photorealistic 3D perspective views of room layouts.
FULLY TRACED with LangSmith - including Gemini image generation calls.
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
        lighting: str = "natural daylight"
    ) -> str:
        """
        Generate a photorealistic side/perspective view of the room.
        
        TRACED: Full chain with Gemini image generation details.
        """
        # Build furniture descriptions
        furniture_descriptions = [
            self._describe_object(obj, room_dims)
            for obj in layout
            if obj.type.value == "movable"
        ]
        
        furniture_text = "\n".join(furniture_descriptions)
        
        # Build the generation prompt
        prompt = self._build_perspective_prompt(
            furniture_text, room_dims, style, view_angle, lighting
        )
        
        # Generate the image (traced)
        return await self._call_gemini_image_generation(prompt)

    @traceable(
        name="gemini_perspective_generation", 
        run_type="llm", 
        tags=["gemini", "image", "perspective", "api-call"],
        metadata={"model_type": "gemini-image", "task": "perspective_generation"}
    )
    async def _call_gemini_image_generation(self, prompt: str) -> str:
        """
        Make the Gemini image generation API call.
        TRACED as an LLM/image-gen call.
        """
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.image_model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["image", "text"]
            )
        )
        
        # Extract image from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                return base64.b64encode(image_data).decode('utf-8')
        
        raise RuntimeError("No image generated in response")

    def _build_perspective_prompt(
        self,
        furniture_text: str,
        room_dims: RoomDimensions,
        style: str,
        view_angle: str,
        lighting: str
    ) -> str:
        """Build the prompt for perspective generation."""
        return f"""Generate a photorealistic interior photograph of a bedroom.

ROOM SPECIFICATIONS:
- Dimensions: approximately {room_dims.width_estimate/10:.0f} x {room_dims.height_estimate/10:.0f} feet
- Style: {style}
- Lighting: {lighting}

FURNITURE LAYOUT (positions from top-down view, translate to 3D):
{furniture_text}

CAMERA:
- View angle: {view_angle} of the room (standing at entrance looking in)
- Height: eye-level (approximately 5 feet)
- Show the full room layout

QUALITY REQUIREMENTS:
- Photorealistic rendering quality
- Proper perspective and depth
- Realistic shadows and lighting
- Show furniture textures and materials
- Professional interior photography style

Generate a single high-quality interior photograph."""

    def _describe_object(
        self,
        obj: RoomObject,
        room_dims: RoomDimensions
    ) -> str:
        """Generate natural language description of object position."""
        x_pct = obj.bbox[0]
        y_pct = obj.bbox[1]
        
        # Determine position in room
        x_pos = "left" if x_pct < 33 else ("center" if x_pct < 66 else "right")
        y_pos = "front" if y_pct < 33 else ("middle" if y_pct < 66 else "back")
        
        # Orientation description
        orientation_map = {
            0: "facing north (away from viewer)", 
            90: "facing east (to the right)",
            180: "facing south (toward viewer)", 
            270: "facing west (to the left)"
        }
        orientation_desc = orientation_map.get(obj.orientation, "")
        
        # Material description
        material = f" made of {obj.material_hint}" if obj.material_hint else ""
        
        # Build description
        desc = f"- {obj.label.title()}{material} positioned in the {y_pos}-{x_pos} area of the room"
        
        if obj.label in ['bed', 'desk', 'sofa', 'chair'] and orientation_desc:
            desc += f", {orientation_desc}"
        
        return desc

    @traceable(
        name="generate_thumbnail_preview", 
        run_type="llm", 
        tags=["gemini", "thumbnail", "api-call"]
    )
    async def generate_thumbnail(
        self, 
        layout: List[RoomObject],
        room_dims: RoomDimensions,
        style: str = "modern"
    ) -> str:
        """
        Generate a quick thumbnail preview of the layout.
        TRACED: Simplified generation for thumbnails.
        """
        furniture_list = ", ".join([
            obj.label for obj in layout if obj.type.value == "movable"
        ])
        
        prompt = f"""Quick sketch-style overhead view of a bedroom with: {furniture_list}.
{style} style, simple clean illustration, top-down perspective.
Show furniture placement clearly, minimal details, clean lines."""

        try:
            response = self.client.models.generate_content(
                model=self.image_model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["image", "text"]
                )
            )
            
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    return base64.b64encode(image_data).decode('utf-8')
            
            return ""
            
        except Exception:
            return ""


# LangGraph node functions

@traceable(name="perspective_node", run_type="chain", tags=["langgraph", "node", "perspective"])
async def perspective_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that generates perspective renders.
    TRACED: Full trace with image generation details.
    """
    generator = PerspectiveGenerator()
    
    try:
        layout = state.get("proposed_layout") or state.get("current_layout", [])
        room_dims = state["room_dimensions"]
        
        # Generate the main perspective view
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