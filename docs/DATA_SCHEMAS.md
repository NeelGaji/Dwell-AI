# Data Schemas Documentation

This document defines all data structures used in the Pocket Planner system.

## 1. Vision Output (Gemini → Python)

The `VisionNode` must return this exact structure from Gemini:

```json
{
  "room_dimensions": {
    "width_estimate": 300,
    "height_estimate": 400
  },
  "objects": [
    {
      "id": "bed_1",
      "label": "bed",
      "bbox": [10, 10, 100, 200],
      "type": "movable",
      "orientation": 0
    },
    {
      "id": "door_1",
      "label": "door",
      "bbox": [0, 150, 20, 80],
      "type": "structural",
      "orientation": 90
    }
  ]
}
```

### Pydantic Schema

```python
from pydantic import BaseModel
from typing import List, Literal
from enum import Enum

class ObjectType(str, Enum):
    MOVABLE = "movable"
    STRUCTURAL = "structural"

class RoomDimensions(BaseModel):
    width_estimate: int   # Estimated width in pixels/units
    height_estimate: int  # Estimated height in pixels/units

class RoomObject(BaseModel):
    id: str                              # Unique identifier (e.g., "bed_1")
    label: str                           # Human-readable label (e.g., "bed", "desk")
    bbox: List[int]                      # [x, y, width, height]
    type: ObjectType                     # "movable" or "structural"
    orientation: int = 0                 # Rotation in degrees (0, 90, 180, 270)

class VisionOutput(BaseModel):
    room_dimensions: RoomDimensions
    objects: List[RoomObject]
```

## 2. Agent State (LangGraph)

The shared state passed between nodes in the agent loop:

```python
from typing import TypedDict, List, Annotated
import operator

class AgentState(TypedDict):
    # Input image as base64
    image_base64: str
    
    # Current layout of all objects
    current_layout: List[RoomObject]
    
    # IDs of objects locked by the user
    locked_object_ids: List[str]
    
    # List of constraint violations found
    constraint_violations: Annotated[List[str], operator.add]
    
    # Number of optimization iterations
    iteration_count: int
    
    # Proposed new layout (from solver)
    proposed_layout: List[RoomObject] | None
    
    # Explanation of changes made
    explanation: str | None
    
    # Final rendered image URL
    output_image_url: str | None
    
    # Usability score (0-100)
    layout_score: float | None
```

### State Flow Between Nodes

```
VisionNode
    └── Sets: current_layout, room_dimensions

ConstraintNode
    └── Reads: current_layout, locked_object_ids
    └── Sets: constraint_violations

SolverNode
    └── Reads: current_layout, locked_object_ids, constraint_violations
    └── Sets: proposed_layout, iteration_count, explanation

ReviewNode (Optional)
    └── Reads: proposed_layout
    └── Sets: layout_score

RenderNode
    └── Reads: proposed_layout, image_base64
    └── Sets: output_image_url
```

## 3. API Schemas

### POST /analyze

**Request:**
```python
from fastapi import UploadFile

class AnalyzeRequest(BaseModel):
    # Image is uploaded as multipart/form-data
    pass  # Use UploadFile directly

# OR for base64:
class AnalyzeRequestBase64(BaseModel):
    image_base64: str
```

**Response:**
```python
class AnalyzeResponse(BaseModel):
    room_dimensions: RoomDimensions
    objects: List[RoomObject]
    detected_issues: List[str]  # Initial constraint violations
```

### POST /optimize

**Request:**
```python
class OptimizeRequest(BaseModel):
    current_layout: List[RoomObject]
    locked_ids: List[str]
    room_dimensions: RoomDimensions
```

**Response:**
```python
class OptimizeResponse(BaseModel):
    new_layout: List[RoomObject]
    explanation: str
    layout_score: float
    constraint_violations: List[str]  # Empty if all resolved
```

### POST /render

**Request:**
```python
class RenderRequest(BaseModel):
    original_image_base64: str
    final_layout: List[RoomObject]
    original_layout: List[RoomObject]  # For diff calculation
```

**Response:**
```python
class RenderResponse(BaseModel):
    image_url: str        # URL to rendered image
    image_base64: str     # Or inline base64
```

## 4. Constraint Definitions

### Hard Constraints

```python
class HardConstraint(BaseModel):
    name: str
    description: str
    min_clearance: float  # Minimum distance in units

HARD_CONSTRAINTS = [
    HardConstraint(
        name="door_clearance",
        description="Door must remain unblocked with swing path clear",
        min_clearance=60  # 60cm clearance
    ),
    HardConstraint(
        name="walking_path",
        description="Minimum walking clearance between objects",
        min_clearance=45  # 45cm minimum path width
    ),
    HardConstraint(
        name="locked_objects",
        description="Locked objects cannot be moved",
        min_clearance=0
    )
]
```

### Soft Constraints (Preferences)

```python
class SoftConstraint(BaseModel):
    name: str
    description: str
    weight: float  # Impact on layout score (0.0 - 1.0)

SOFT_CONSTRAINTS = [
    SoftConstraint(
        name="desk_near_window",
        description="Desk should be positioned near natural light",
        weight=0.3
    ),
    SoftConstraint(
        name="bed_away_from_door",
        description="Bed should be away from main entry",
        weight=0.2
    ),
    SoftConstraint(
        name="nightstand_near_bed",
        description="Nightstand should be adjacent to bed",
        weight=0.2
    )
]
```

## 5. Geometry Types

### For Shapely Operations

```python
from shapely.geometry import Polygon, box

def bbox_to_polygon(bbox: List[int]) -> Polygon:
    """Convert [x, y, width, height] to Shapely Polygon."""
    x, y, w, h = bbox
    return box(x, y, x + w, y + h)

class FurniturePolygon(BaseModel):
    object_id: str
    polygon: Polygon  # Shapely polygon
    is_locked: bool
    
    class Config:
        arbitrary_types_allowed = True
```

### Collision Detection Results

```python
class CollisionResult(BaseModel):
    object_a_id: str
    object_b_id: str
    overlap_area: float
    is_blocking: bool  # True if completely blocking path
```

### Clearance Calculation

```python
class ClearanceResult(BaseModel):
    from_object_id: str
    to_object_id: str
    distance: float
    is_sufficient: bool  # Based on min_clearance requirement
    required_clearance: float
```

## 6. Room Graph Structure

### Node Attributes

```python
class RoomGraphNode(BaseModel):
    id: str
    object_type: ObjectType
    position: tuple[int, int]  # (x, y) center
    size: tuple[int, int]      # (width, height)
    is_locked: bool
    orientation: int
```

### Edge Types

```python
class EdgeRelation(str, Enum):
    ADJACENT = "adjacent"       # Objects are next to each other
    NEAR = "near"               # Within proximity threshold
    BLOCKING = "blocking"       # One object blocks another
    DEPENDS_ON = "depends_on"   # Nightstand depends on bed position
```

## 7. Gemini Prompt Output Schema

### For Structured JSON Output with google-genai

```python
from google.genai import types

VISION_SCHEMA = {
    'type': 'OBJECT',
    'required': ['room_dimensions', 'objects'],
    'properties': {
        'room_dimensions': {
            'type': 'OBJECT',
            'required': ['width_estimate', 'height_estimate'],
            'properties': {
                'width_estimate': {'type': 'INTEGER'},
                'height_estimate': {'type': 'INTEGER'}
            }
        },
        'objects': {
            'type': 'ARRAY',
            'items': {
                'type': 'OBJECT',
                'required': ['id', 'label', 'bbox', 'type'],
                'properties': {
                    'id': {'type': 'STRING'},
                    'label': {'type': 'STRING'},
                    'bbox': {
                        'type': 'ARRAY',
                        'items': {'type': 'INTEGER'}
                    },
                    'type': {'type': 'STRING'},
                    'orientation': {'type': 'INTEGER'}
                }
            }
        }
    }
}
```

Usage with google-genai SDK:

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-1.5-pro',
    contents=[image_part, "Analyze this room and extract all furniture..."],
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=VISION_SCHEMA
    )
)
```
