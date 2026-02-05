"""
Chat Editor Node

Conversational image editing agent that allows natural language
commands to modify the rendered room perspective.

FULLY TRACED with LangSmith - including command parsing and image edits.
"""

import json
import base64
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from google import genai
from google.genai import types

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


class ChatEditor:
    """
    Conversational editing agent for room layouts and renders.
    All methods are traced with LangSmith.
    """
    
    def __init__(self):
        from app.config import get_settings
        from app.tools.edit_image import EditImageTool
        
        settings = get_settings()
        api_key = settings.google_api_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in .env file")
        self.client = genai.Client(api_key=api_key)
        self.reasoning_model = settings.model_name
        self.image_model = settings.image_model_name
        self.edit_tool = EditImageTool()

    @traceable(
        name="chat_editor.process_edit_command", 
        run_type="chain", 
        tags=["chat", "edit", "command"],
        metadata={"description": "Process natural language edit command"}
    )
    async def process_edit_command(
        self,
        command: str,
        current_layout: List[RoomObject],
        room_dims: RoomDimensions,
        current_image_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language editing command.
        TRACED: Full chain with command parsing and edit application.
        """
        # First, classify the edit type (traced)
        edit_type, parsed_command = await self._parse_command(command, current_layout)
        
        if edit_type == "layout":
            # Structural edit - modify layout positions
            updated_layout, explanation = await self._apply_layout_edit(
                parsed_command, current_layout, room_dims
            )
            return {
                "edit_type": "layout",
                "updated_layout": updated_layout,
                "updated_image_base64": None,
                "explanation": explanation,
                "needs_rerender": True
            }
        else:
            # Cosmetic edit - modify the image directly
            if current_image_base64:
                updated_image, explanation = await self._apply_image_edit(
                    parsed_command, current_image_base64
                )
                return {
                    "edit_type": "cosmetic",
                    "updated_layout": current_layout,
                    "updated_image_base64": updated_image,
                    "explanation": explanation,
                    "needs_rerender": False
                }
            else:
                return {
                    "edit_type": "error",
                    "updated_layout": current_layout,
                    "updated_image_base64": None,
                    "explanation": "No rendered image available for cosmetic editing. Please generate a render first.",
                    "needs_rerender": True
                }

    @traceable(
        name="gemini_parse_command", 
        run_type="llm", 
        tags=["gemini", "chat", "parsing", "api-call"],
        metadata={"model_type": "gemini-pro", "task": "command_parsing"}
    )
    async def _parse_command(
        self, 
        command: str, 
        current_layout: List[RoomObject]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Parse natural language command into structured edit instruction.
        TRACED as an LLM call.
        """
        furniture_list = [{"id": obj.id, "label": obj.label} for obj in current_layout]
        
        prompt = f"""You are an interior design assistant parsing user edit commands.

CURRENT FURNITURE IN ROOM:
{json.dumps(furniture_list, indent=2)}

USER COMMAND: "{command}"

Classify this command and parse it into a structured format.

EDIT TYPES:
1. "layout" - Commands that move, rotate, or reposition furniture
   Examples: "move desk to left", "rotate bed 90 degrees", "swap desk and dresser"
   
2. "cosmetic" - Commands that change appearance without moving furniture
   Examples: "make it more cozy", "add plants", "change lighting", "make rug blue"

Return JSON:
{{
  "edit_type": "layout" | "cosmetic",
  "action": "move" | "rotate" | "style" | "add" | "remove",
  "target_object_id": "id or null",
  "parameters": {{
    "direction": "left|right|up|down" (for move),
    "distance": "small|medium|large" (for move),
    "rotation": 90 (degrees, for rotate),
    "style_change": "description" (for cosmetic)
  }},
  "natural_description": "Human-readable description of the change"
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            parsed = json.loads(response.text)
            return parsed.get("edit_type", "cosmetic"), parsed
            
        except Exception as e:
            # Default to cosmetic if parsing fails
            return "cosmetic", {
                "edit_type": "cosmetic",
                "action": "style",
                "natural_description": command
            }

    @traceable(name="apply_layout_edit", run_type="chain", tags=["edit", "layout"])
    async def _apply_layout_edit(
        self,
        parsed_command: Dict[str, Any],
        current_layout: List[RoomObject],
        room_dims: RoomDimensions
    ) -> Tuple[List[RoomObject], str]:
        """
        Apply a structural layout edit.
        TRACED: Layout modification logic.
        """
        target_id = parsed_command.get("target_object_id")
        action = parsed_command.get("action", "move")
        params = parsed_command.get("parameters", {})
        
        # Find target object
        target_obj = None
        if target_id:
            target_obj = next((o for o in current_layout if o.id == target_id), None)
        
        if not target_obj and action in ["move", "rotate"]:
            return current_layout, f"Could not find target object for edit. Available: {[o.label for o in current_layout]}"
        
        # Create updated layout
        updated_layout = []
        explanation = ""
        
        for obj in current_layout:
            new_obj = RoomObject(
                id=obj.id,
                label=obj.label,
                bbox=obj.bbox.copy(),
                type=obj.type,
                orientation=obj.orientation,
                is_locked=obj.is_locked,
                z_index=obj.z_index,
                material_hint=obj.material_hint
            )
            
            if target_obj and obj.id == target_obj.id:
                if action == "move":
                    direction = params.get("direction", "")
                    distance_map = {"small": 5, "medium": 10, "large": 20}
                    distance = distance_map.get(params.get("distance", "medium"), 10)
                    
                    if direction == "left":
                        new_obj.bbox[0] = max(0, new_obj.bbox[0] - distance)
                    elif direction == "right":
                        new_obj.bbox[0] = min(100 - new_obj.bbox[2], new_obj.bbox[0] + distance)
                    elif direction == "up":
                        new_obj.bbox[1] = max(0, new_obj.bbox[1] - distance)
                    elif direction == "down":
                        new_obj.bbox[1] = min(100 - new_obj.bbox[3], new_obj.bbox[1] + distance)
                    
                    explanation = f"Moved {obj.label} {direction} by {distance}%"
                
                elif action == "rotate":
                    rotation = params.get("rotation", 90)
                    new_obj.orientation = (new_obj.orientation + rotation) % 360
                    explanation = f"Rotated {obj.label} by {rotation} degrees (now facing {new_obj.orientation}deg)"
            
            updated_layout.append(new_obj)
        
        if not explanation:
            explanation = f"Processed command: {parsed_command.get('natural_description', 'Unknown edit')}"
        
        return updated_layout, explanation

    @traceable(
        name="gemini_image_edit", 
        run_type="llm", 
        tags=["gemini", "image", "edit", "api-call"],
        metadata={"model_type": "gemini-image", "task": "cosmetic_edit"}
    )
    async def _apply_image_edit(
        self,
        parsed_command: Dict[str, Any],
        current_image_base64: str
    ) -> Tuple[str, str]:
        """
        Apply a cosmetic edit to the rendered image.
        TRACED as an LLM/image-gen call.
        """
        edit_description = parsed_command.get("natural_description", "Apply the requested change")
        
        try:
            new_image = await self.edit_tool.edit_image(
                base_image=current_image_base64,
                instruction=edit_description
            )
            return new_image, f"Applied: {edit_description}"
            
        except Exception as e:
            return current_image_base64, f"Edit failed: {str(e)}"


# LangGraph node functions

@traceable(name="chat_editor_node", run_type="chain", tags=["langgraph", "node", "chat"])
async def chat_editor_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node for conversational editing.
    TRACED: Full trace with command processing.
    """
    editor = ChatEditor()
    
    edit_command = state.get("edit_command", "")
    if not edit_command:
        return {
            "explanation": "No edit command provided. Use natural language to describe changes."
        }
    
    try:
        result = await editor.process_edit_command(
            command=edit_command,
            current_layout=state.get("current_layout", []),
            room_dims=state["room_dimensions"],
            current_image_base64=state.get("output_image_base64")
        )
        
        updates = {
            "explanation": result["explanation"],
            "should_continue": result.get("needs_rerender", False)
        }
        
        if result["edit_type"] == "layout" and result["updated_layout"]:
            updates["current_layout"] = result["updated_layout"]
            updates["proposed_layout"] = result["updated_layout"]
        
        if result["updated_image_base64"]:
            updates["output_image_base64"] = result["updated_image_base64"]
        
        return updates
        
    except Exception as e:
        return {
            "error": f"Chat editor failed: {str(e)}",
            "explanation": f"Could not process edit command: {str(e)}"
        }


def chat_editor_node_sync(state: AgentState) -> Dict[str, Any]:
    """Synchronous wrapper for LangGraph compatibility."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(chat_editor_node(state))
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, chat_editor_node(state))
            return future.result()