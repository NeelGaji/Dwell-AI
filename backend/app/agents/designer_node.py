"""
Designer Node - Hierarchical Zone-Based Layout Generation

FLOW:
1. _generate_layout_plan → Semantic/relative positions (NO coordinates)
2. _generate_layout_image → Edit image using semantic plan with STRICT rules

REMOVED: _resolve_coordinates (useless - image gen ignores pixel values)

STRICT IMAGE RULES:
- Exact object count enforcement
- No new objects allowed
- Door clearance required
- 2D top-down only

FULLY TRACED with LangSmith.
"""

import json
import base64
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
from google import genai
from google.genai import types

from app.config import get_settings
from app.models.state import AgentState
from app.models.room import RoomObject, RoomDimensions, ObjectType
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


# ============================================================================
# ZONE DEFINITIONS
# ============================================================================

class ZoneType(str, Enum):
    WORK = "work_zone"
    SLEEP = "sleep_zone"
    LIVING = "living_zone"


FURNITURE_ZONE_MAP = {
    "bed": ZoneType.SLEEP, "nightstand": ZoneType.SLEEP, "dresser": ZoneType.SLEEP,
    "wardrobe": ZoneType.SLEEP, "closet": ZoneType.SLEEP,
    "desk": ZoneType.WORK, "office_chair": ZoneType.WORK, "chair": ZoneType.WORK,
    "bookshelf": ZoneType.WORK, "filing_cabinet": ZoneType.WORK,
    "sofa": ZoneType.LIVING, "couch": ZoneType.LIVING, "armchair": ZoneType.LIVING,
    "coffee_table": ZoneType.LIVING, "dining_table": ZoneType.LIVING,
    "tv_stand": ZoneType.LIVING, "rug": ZoneType.LIVING, "plant": ZoneType.LIVING,
    "lamp": ZoneType.LIVING, "table": ZoneType.LIVING,
}


LAYOUT_SPECIFICATIONS = {
    "work_focused": {
        "name": "Productivity Focus",
        "zone_priorities": [ZoneType.WORK, ZoneType.SLEEP, ZoneType.LIVING],
        "description": "Optimized for productivity with desk near natural light and clear separation from sleep area.",
        "technical_spec": {
            "work_zone": {
                "position": "ADJACENT_TO_WINDOW",
                "requirements": [
                    "Desk MUST be adjacent to window (for natural light)",
                    "Desk should face the door (for awareness)",
                    "MAXIMUM distance from sleep zone"
                ]
            },
            "sleep_zone": {
                "position": "OPPOSITE_TO_WORK",
                "requirements": [
                    "Bed headboard against wall, away from work area",
                    "Nightstand adjacent to bed"
                ]
            },
            "living_zone": {
                "position": "NEAR_ENTRANCE",
                "requirements": ["Minimal footprint, near door"]
            }
        }
    },
    "cozy": {
        "name": "Cozy Retreat",
        "zone_priorities": [ZoneType.SLEEP, ZoneType.LIVING, ZoneType.WORK],
        "description": "Centered around comfort with bed as focal point and intimate seating arrangements.",
        "technical_spec": {
            "sleep_zone": {
                "position": "ROOM_FOCAL_POINT",
                "requirements": [
                    "Bed CENTERED as room focal point, opposite to door",
                    "Nightstands symmetrical on both sides"
                ]
            },
            "living_zone": {
                "position": "ADJACENT_TO_WINDOW",
                "requirements": [
                    "Reading nook near window",
                    "Cozy seating arrangement"
                ]
            },
            "work_zone": {
                "position": "CORNER_MINIMAL",
                "requirements": ["Desk tucked in corner, minimal presence"]
            }
        }
    },
    "creative": {
        "name": "Creative Flow",
        "zone_priorities": [ZoneType.LIVING, ZoneType.WORK, ZoneType.SLEEP],
        "description": "Unconventional arrangement with angled furniture and open center space.",
        "technical_spec": {
            "living_zone": {
                "position": "ROOM_CENTER",
                "requirements": [
                    "Furniture angled, not parallel to walls",
                    "Open space in center"
                ]
            },
            "work_zone": {
                "position": "DIAGONAL_CORNER",
                "requirements": [
                    "Desk at diagonal angle",
                    "Unexpected placement"
                ]
            },
            "sleep_zone": {
                "position": "ANGLED_PLACEMENT",
                "requirements": [
                    "Bed angled or floated from walls",
                    "Asymmetric nightstand placement"
                ]
            }
        }
    }
}


class InteriorDesignerAgent:
    """AI Interior Designer with Hierarchical Zone-Based Generation."""
    
    def __init__(self):
        settings = get_settings()
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = settings.model_name
        self.image_model = settings.image_model_name

    @traceable(name="designer_agent.generate_layout_variations", run_type="chain", tags=["designer", "hierarchical"])
    async def generate_layout_variations(
        self,
        current_layout: List[RoomObject],
        room_dims: RoomDimensions,
        locked_ids: List[str],
        image_base64: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate layout variations using hierarchical zone-based approach."""
        
        # STEP 1: Prepare objects
        complete_locked_ids, movable_objects, structural_objects, door_info, window_info = \
            self._prepare_objects(current_layout, locked_ids, room_dims)
        
        if not movable_objects:
            raise ValueError("No movable objects to arrange")
        
        # STEP 2: Classify furniture into zones
        zone_assignments = self._classify_furniture_to_zones(movable_objects)
        
        movable_count = len(movable_objects)
        furniture_labels = [obj["label"] for obj in movable_objects]
        
        print(f"[Designer] Zones: {{{', '.join(f'{z.value}: {len(ids)}' for z, ids in zone_assignments.items())}}}")
        print(f"[Designer] Movable objects ({movable_count}): {furniture_labels}")
        print(f"[Designer] Door: {door_info}, Window: {window_info}")
        
        # STEP 3: Generate layout PLANS in parallel (text only, semantic positions)
        print("[Designer] Generating layout plans...")
        
        plan_tasks = [
            self._generate_layout_plan(
                style_key=style_key,
                spec=spec,
                zone_assignments=zone_assignments,
                movable_objects=movable_objects,
                structural_objects=structural_objects,
                room_dims=room_dims,
                door_info=door_info,
                window_info=window_info
            )
            for style_key, spec in LAYOUT_SPECIFICATIONS.items()
        ]
        
        layout_plans = await asyncio.gather(*plan_tasks, return_exceptions=True)
        
        # STEP 4: Generate layout IMAGES in parallel using the plans
        print("[Designer] Generating layout images...")
        
        image_tasks = []
        valid_plans = []
        
        for i, plan in enumerate(layout_plans):
            style_key = list(LAYOUT_SPECIFICATIONS.keys())[i]
            spec = LAYOUT_SPECIFICATIONS[style_key]
            
            if isinstance(plan, Exception):
                print(f"[Designer] Plan generation failed for {style_key}: {plan}")
                continue
            
            if plan and image_base64:
                valid_plans.append((style_key, spec, plan))
                image_tasks.append(
                    self._generate_layout_image(
                        layout_plan=plan,
                        style_key=style_key,
                        spec=spec,
                        movable_objects=movable_objects,
                        structural_objects=structural_objects,
                        door_info=door_info,
                        window_info=window_info,
                        image_base64=image_base64,
                        movable_count=movable_count,
                        furniture_labels=furniture_labels
                    )
                )
        
        if not image_tasks:
            raise ValueError("No valid layout plans generated")
        
        images = await asyncio.gather(*image_tasks, return_exceptions=True)
        
        # STEP 5: Combine results
        variations = []
        for i, (style_key, spec, plan) in enumerate(valid_plans):
            image_result = images[i] if i < len(images) else None
            
            if isinstance(image_result, Exception):
                print(f"[Designer] Image generation failed for {style_key}: {image_result}")
                continue
            
            variations.append({
                "name": spec["name"],
                "style_key": style_key,
                "description": plan.get("description", spec["description"]),
                "layout": current_layout,  # Original layout preserved
                "layout_plan": plan,  # Semantic plan
                "thumbnail_base64": image_result if image_result else None,
                "score": 75.0  # Placeholder
            })
            print(f"[Designer] {style_key} completed successfully")
        
        if not variations:
            raise ValueError("Failed to generate any valid layouts")
        
        return variations

    @traceable(name="generate_layout_plan", run_type="llm", tags=["gemini", "planning"])
    async def _generate_layout_plan(
        self,
        style_key: str,
        spec: Dict,
        zone_assignments: Dict[ZoneType, List[str]],
        movable_objects: List[dict],
        structural_objects: List[dict],
        room_dims: RoomDimensions,
        door_info: Optional[Dict],
        window_info: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate semantic layout plan with RELATIVE positioning only."""
        
        # Build furniture by zone
        obj_lookup = {obj["id"]: obj for obj in movable_objects}
        zone_furniture = {}
        for zone_type, obj_ids in zone_assignments.items():
            zone_furniture[zone_type.value] = [
                {"id": oid, "label": obj_lookup[oid]["label"]}
                for oid in obj_ids if oid in obj_lookup
            ]
        
        tech_spec = json.dumps(spec.get("technical_spec", {}), indent=2)
        door_desc = f"on the {door_info['wall']} wall" if door_info else "location unknown"
        window_desc = f"on the {window_info['wall']} wall" if window_info else "location unknown"
        
        prompt = f"""You are an expert interior designer creating a "{spec['name']}" layout.

## ROOM INFO
- Door: {door_desc}
- Window: {window_desc}

## STYLE: {spec['name']}
{spec['description']}

## TECHNICAL REQUIREMENTS
{tech_spec}

## FURNITURE TO ARRANGE (by zone)
{json.dumps(zone_furniture, indent=2)}

## YOUR TASK
Create a layout plan using RELATIVE/SEMANTIC positions only (no pixel coordinates).
Describe WHERE each piece of furniture should go relative to:
- Walls (north/south/east/west wall)
- Other furniture (next to bed, across from desk)
- Structural elements (near window, facing door)

## CRITICAL RULES
1. DOOR CLEARANCE: Nothing may block the door. Keep clear path from door into room.
2. Include ALL furniture items listed above - do not skip any.
3. Follow the style requirements exactly.

## OUTPUT FORMAT (JSON)
{{
  "description": "2-3 sentences explaining the design rationale",
  "furniture_placement": {{
    "bed": "against south wall, centered, headboard to wall",
    "desk": "adjacent to window on east wall, chair facing door",
    "nightstand": "right side of bed, against wall",
    ... (include ALL furniture)
  }},
  "door_clearance": "describe how door area is kept clear",
  "zone_arrangement": {{
    "work_zone": "east side of room near window",
    "sleep_zone": "south wall, focal point",
    "living_zone": "north corner near entrance"
  }}
}}"""

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5
            )
        )
        
        return json.loads(response.text)

    @traceable(name="generate_layout_image", run_type="llm", tags=["gemini", "image"])
    async def _generate_layout_image(
        self,
        layout_plan: Dict,
        style_key: str,
        spec: Dict,
        movable_objects: List[dict],
        structural_objects: List[dict],
        door_info: Optional[Dict],
        window_info: Optional[Dict],
        image_base64: str,
        movable_count: int,
        furniture_labels: List[str]
    ) -> Optional[str]:
        """Generate layout image using semantic plan with STRICT rules."""
        
        # Build furniture placement from plan
        furniture_placement = layout_plan.get("furniture_placement", {})
        placement_instructions = []
        for item, position in furniture_placement.items():
            placement_instructions.append(f"  • {item.upper()}: {position}")
        
        placement_text = "\n".join(placement_instructions) if placement_instructions else "Follow zone arrangement"
        
        zone_arrangement = layout_plan.get("zone_arrangement", {})
        zone_text = "\n".join([f"  • {zone}: {location}" for zone, location in zone_arrangement.items()])
        
        door_wall = door_info['wall'] if door_info else "unknown"
        window_wall = window_info['wall'] if window_info else "unknown"
        
        furniture_list_str = ", ".join(furniture_labels)
        
        prompt = f"""TASK: Edit this 2D top-down floor plan to show the "{spec['name']}" furniture arrangement.

╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚠️  STRICT RULES - VIOLATIONS MAKE OUTPUT INVALID                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. OBJECT COUNT: Exactly {movable_count} movable furniture items must appear.     ║
║     Count them: {movable_count} items in, {movable_count} items out. No exceptions.              ║
║                                                                              ║
║  2. REQUIRED FURNITURE (ALL must be visible in output):                      ║
║     [{furniture_list_str}]
║                                                                              ║
║  3. DO NOT ADD any new furniture, people, decorations, or objects.           ║
║                                                                              ║
║  4. DO NOT REMOVE any furniture from the list above.                         ║
║                                                                              ║
║  5. DOOR ({door_wall} wall): Keep 2+ feet CLEAR in front of door.                 ║
║     NO furniture blocking the door entrance.                                 ║
║                                                                              ║
║  6. DO NOT MOVE: doors, windows, walls, toilet, shower, sink,                ║
║     refrigerator, stovetop, or any built-in/structural elements.             ║
║                                                                              ║
║  7. OUTPUT MUST BE 2D TOP-DOWN VIEW - NOT 3D perspective.                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

LAYOUT STYLE: {spec['name']}
{layout_plan.get('description', spec['description'])}

FURNITURE PLACEMENT:
{placement_text}

ZONE ARRANGEMENT:
{zone_text}

DOOR CLEARANCE PLAN:
{layout_plan.get('door_clearance', 'Keep door area clear of all furniture')}

STRUCTURAL ELEMENTS (do not move):
- Door: {door_wall} wall
- Window: {window_wall} wall

OUTPUT REQUIREMENTS:
1. Same 2D top-down floor plan perspective as input
2. Same visual style, colors, line weights as input
3. All {movable_count} furniture items visible in new positions
4. Professional architectural floor plan appearance
5. Clear walkway from door into room

Edit the floor plan to show this "{spec['name']}" arrangement."""

        # Prepare image
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        try:
            image_data = base64.b64decode(image_base64)
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.image_model,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=0.2  # Very low for faithful editing
                )
            )
            
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        return base64.b64encode(part.inline_data.data).decode('utf-8')
            
            return None
            
        except Exception as e:
            print(f"[Designer] Image generation error for {style_key}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _prepare_objects(
        self, current_layout: List[RoomObject], locked_ids: List[str], room_dims: RoomDimensions
    ) -> Tuple[Set[str], List[dict], List[dict], Optional[Dict], Optional[Dict]]:
        """Prepare objects and identify door/window positions."""
        complete_locked_ids: Set[str] = set(locked_ids)
        movable_objects, structural_objects = [], []
        door_info, window_info = None, None
        
        for obj in current_layout:
            if obj.type == ObjectType.STRUCTURAL or obj.is_locked:
                complete_locked_ids.add(obj.id)
            
            # Clean label for display
            clean_label = obj.label.lower().replace("_", " ").split("_")[0]
            
            obj_dict = {
                "id": obj.id,
                "label": clean_label,
                "full_label": obj.label,
                "bbox": obj.bbox,
            }
            
            if obj.id in complete_locked_ids:
                structural_objects.append(obj_dict)
                
                # Detect door
                if "door" in obj.label.lower():
                    door_info = self._get_element_wall(obj.bbox, room_dims)
                
                # Detect window
                if "window" in obj.label.lower():
                    window_info = self._get_element_wall(obj.bbox, room_dims)
            else:
                movable_objects.append(obj_dict)
        
        return complete_locked_ids, movable_objects, structural_objects, door_info, window_info

    def _get_element_wall(self, bbox: List[int], room_dims: RoomDimensions) -> Dict:
        """Determine which wall an element is on."""
        x, y, w, h = bbox
        center_x, center_y = x + w/2, y + h/2
        room_w, room_h = room_dims.width_estimate, room_dims.height_estimate
        
        # Determine wall based on position
        if y < room_h * 0.15:
            wall = "north (top)"
        elif y + h > room_h * 0.85:
            wall = "south (bottom)"
        elif x < room_w * 0.15:
            wall = "west (left)"
        elif x + w > room_w * 0.85:
            wall = "east (right)"
        else:
            wall = "interior"
        
        return {"wall": wall, "x": x, "y": y}

    def _classify_furniture_to_zones(self, movable_objects: List[dict]) -> Dict[ZoneType, List[str]]:
        """Classify furniture into zones based on label."""
        zones = {ZoneType.WORK: [], ZoneType.SLEEP: [], ZoneType.LIVING: []}
        
        for obj in movable_objects:
            label = obj["label"].lower()
            assigned = False
            for key, zone in FURNITURE_ZONE_MAP.items():
                if key in label:
                    zones[zone].append(obj["id"])
                    assigned = True
                    break
            if not assigned:
                zones[ZoneType.LIVING].append(obj["id"])
        
        return zones


# ============================================================================
# LANGGRAPH NODE FUNCTIONS
# ============================================================================

@traceable(name="designer_node", run_type="chain", tags=["langgraph", "node"])
async def designer_node(state: AgentState) -> Dict[str, Any]:
    designer = InteriorDesignerAgent()
    try:
        variations = await designer.generate_layout_variations(
            current_layout=state["current_layout"],
            room_dims=state["room_dimensions"],
            locked_ids=state.get("locked_object_ids", []),
            image_base64=state.get("image_base64")
        )
        return {
            "layout_variations": variations,
            "proposed_layout": variations[0]["layout"] if variations else state["current_layout"],
            "explanation": f"Generated {len(variations)} layout variations.",
            "should_continue": False,
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Designer failed: {str(e)}", "should_continue": False}


def designer_node_sync(state: AgentState) -> Dict[str, Any]:
    return asyncio.run(designer_node(state))