"""
Vision Node

Handles room image analysis using Gemini Vision.
FULLY TRACED with LangSmith - including Gemini API calls.
"""

import json
import base64
import io
from typing import List, Optional
from PIL import Image
from google import genai
from google.genai import types

from app.config import get_settings
from app.models.room import RoomObject, RoomDimensions, ObjectType, VisionOutput

# LangSmith tracing
try:
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree
    LANGSMITH_ENABLED = True
except ImportError:
    LANGSMITH_ENABLED = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def get_current_run_tree():
        return None


# === STRUCTURAL OBJECTS LIST ===
# Objects that should ALWAYS be classified as structural (cannot be moved)
STRUCTURAL_OBJECTS = {
    "door", "window", "wall", "shower", "bathtub", "bath", "toilet", 
    "sink", "stovetop", "stove", "oven", "refrigerator", "fridge",
    "built-in", "builtin", "radiator", "fireplace", "stairs", "staircase",
    "column", "pillar", "beam", "hvac", "vent", "ac_unit", "washer",
    "dryer", "dishwasher", "water_heater", "boiler", "furnace"
}


# Enhanced prompt for room analysis with better bounding box instructions
ROOM_ANALYSIS_PROMPT = """You are an expert architectural floor plan analyzer. Analyze this top-down 2D floor plan image with EXTREME PRECISION.

## YOUR TASK
Detect ALL objects in this floor plan and provide TIGHT, ACCURATE bounding boxes.

## CRITICAL BOUNDING BOX INSTRUCTIONS
- The bounding box format is [ymin, xmin, ymax, xmax] normalized to 0-1000 scale
- (0,0) is TOP-LEFT corner, (1000,1000) is BOTTOM-RIGHT corner
- BOUNDING BOXES MUST BE TIGHT - fit exactly around each object with minimal padding
- For rectangular furniture (beds, desks, tables): box should match the furniture edges precisely
- For circular objects (rugs, round tables): use the smallest rectangle that contains the circle
- DO NOT include shadows or reflections in the bounding box
- Each object should have its OWN separate bounding box - do not merge objects

## OBJECT CLASSIFICATION

### STRUCTURAL (type: "structural") - CANNOT be moved:
- Doors, windows, walls
- Plumbing fixtures: toilet, sink, shower, bathtub
- Kitchen appliances: refrigerator, stove, stovetop, oven, dishwasher
- Built-in elements: fireplace, radiator, stairs, columns
- HVAC: vents, AC units

### MOVABLE (type: "movable") - CAN be rearranged:
- Beds, nightstands, dressers, wardrobes
- Desks, chairs, office furniture
- Sofas, couches, armchairs
- Tables (dining, coffee, side)
- Rugs, lamps, artwork
- Shelving units (freestanding)

## DETECTION GUIDELINES
1. Scan the ENTIRE image systematically from top-left to bottom-right
2. Identify room boundaries (walls) first
3. Detect EVERY piece of furniture, no matter how small
4. For multi-room floor plans, detect objects in ALL rooms
5. Give each object a unique ID: "{label}_{number}" (e.g., "bed_1", "chair_2")
6. Pay special attention to:
   - Nightstands (small rectangles near beds)
   - Chairs (often at desks or tables)
   - Rugs (usually rectangular areas under or near furniture)
   - Artwork (rectangles on walls)

## OUTPUT FORMAT
Return ONLY valid JSON:
{
    "room_dimensions": {
        "width_estimate": <room width in feet, estimate from furniture scale>,
        "height_estimate": <room height in feet, estimate from furniture scale>
    },
    "wall_bounds": [ymin, xmin, ymax, xmax],
    "objects": [
        {
            "id": "<label>_<number>",
            "label": "<object_type>",
            "box_2d": [ymin, xmin, ymax, xmax],
            "type": "movable" | "structural"
        }
    ]
}

IMPORTANT: Be thorough - detect ALL objects. Better to detect too many than too few.
"""


class VisionAgent:
    """
    Agent for analyzing room images and extracting object data.
    All methods are traced with LangSmith.
    """
    
    def __init__(self):
        settings = get_settings()
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = settings.model_name

    @traceable(name="vision_agent.analyze_room", run_type="chain", tags=["vision", "gemini"])
    async def analyze_room(self, image_base64: str) -> VisionOutput:
        """
        Analyze a room image using Gemini Vision.
        """
        # Decode image to get dimensions
        image = self._decode_base64_image(image_base64)
        image_width, image_height = image.size
        
        # Call Gemini with tracing
        response_text = await self._call_gemini_vision(image, image_width, image_height)
        
        # Parse response
        return self._parse_gemini_response(response_text, image_width, image_height)

    @traceable(
        name="gemini_vision_call", 
        run_type="llm", 
        tags=["gemini", "vision", "api-call"],
        metadata={"model_type": "gemini-vision"}
    )
    async def _call_gemini_vision(self, image: Image.Image, width: int, height: int) -> str:
        """
        Make the actual Gemini Vision API call.
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1  # Low temperature for more precise detection
        )
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=[image, ROOM_ANALYSIS_PROMPT],
            config=config
        )
        
        return response.text

    def _decode_base64_image(self, image_base64: str) -> Image.Image:
        """Decode base64 string to PIL Image."""
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        image_data = base64.b64decode(image_base64)
        return Image.open(io.BytesIO(image_data))

    def _convert_box_2d_to_bbox(
        self,
        box_2d: List[int], 
        image_width: int, 
        image_height: int
    ) -> List[int]:
        """Convert normalized [ymin, xmin, ymax, xmax] to [x, y, width, height]."""
        ymin, xmin, ymax, xmax = box_2d
        
        # Clamp values to valid range
        ymin = max(0, min(1000, ymin))
        xmin = max(0, min(1000, xmin))
        ymax = max(0, min(1000, ymax))
        xmax = max(0, min(1000, xmax))
        
        x = int(xmin / 1000 * image_width)
        y = int(ymin / 1000 * image_height)
        width = int((xmax - xmin) / 1000 * image_width)
        height = int((ymax - ymin) / 1000 * image_height)
        
        # Ensure minimum dimensions
        width = max(1, width)
        height = max(1, height)
        
        return [x, y, width, height]

    def _is_structural_object(self, label: str) -> bool:
        """Check if an object should be classified as structural."""
        label_lower = label.lower().replace(" ", "_").replace("-", "_")
        
        # Check exact match
        if label_lower in STRUCTURAL_OBJECTS:
            return True
        
        # Check if label contains any structural keyword
        for structural in STRUCTURAL_OBJECTS:
            if structural in label_lower or label_lower in structural:
                return True
        
        return False

    @traceable(name="parse_vision_response", run_type="parser", tags=["parsing"])
    def _parse_gemini_response(
        self,
        response_text: str,
        image_width: int,
        image_height: int
    ) -> VisionOutput:
        """
        Parse Gemini's JSON response into VisionOutput schema.
        """
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}")
        
        # Parse room dimensions
        dims = data.get("room_dimensions", {})
        room_dimensions = RoomDimensions(
            width_estimate=dims.get("width_estimate", image_width),
            height_estimate=dims.get("height_estimate", image_height)
        )
        
        # Parse wall bounds
        wall_bounds = None
        if "wall_bounds" in data and data["wall_bounds"]:
            wall_bounds = self._convert_box_2d_to_bbox(
                data["wall_bounds"], image_width, image_height
            )
        
        # Parse objects with enhanced type classification
        objects = []
        for obj_data in data.get("objects", []):
            label = obj_data.get("label", "unknown").lower()
            
            # Determine object type - OVERRIDE Gemini's classification for known structural objects
            if self._is_structural_object(label):
                obj_type = ObjectType.STRUCTURAL
            elif obj_data.get("type") == "structural":
                obj_type = ObjectType.STRUCTURAL
            else:
                obj_type = ObjectType.MOVABLE
            
            box_2d = obj_data.get("box_2d", [0, 0, 100, 100])
            bbox = self._convert_box_2d_to_bbox(box_2d, image_width, image_height)
            
            room_obj = RoomObject(
                id=obj_data.get("id", f"obj_{len(objects)}"),
                label=label,
                bbox=bbox,
                type=obj_type,
                orientation=0
            )
            objects.append(room_obj)
        
        return VisionOutput(
            room_dimensions=room_dimensions,
            objects=objects,
            wall_bounds=wall_bounds
        )