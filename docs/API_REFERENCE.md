# API Reference Documentation

This document defines all REST API endpoints for the Pocket Planner backend.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently no authentication required for MVP.

---

## Endpoints

### 1. POST /analyze

Analyzes an uploaded room image and extracts furniture objects with their positions.

**Description:**
- Accepts a raw image (photo of a bedroom)
- Uses Gemini 1.5 Pro Vision to detect and classify objects
- Returns structured JSON with room layout

**Request:**

```http
POST /api/v1/analyze
Content-Type: multipart/form-data
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image` | file | Yes | Room photo (JPEG, PNG, WebP) |

**OR** (for base64):

```http
POST /api/v1/analyze
Content-Type: application/json
```

```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Response (200 OK):**

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
    },
    {
      "id": "desk_1",
      "label": "desk",
      "bbox": [200, 50, 80, 50],
      "type": "movable",
      "orientation": 0
    }
  ],
  "detected_issues": [
    "Desk is blocking window access",
    "Walking path from door to bed is only 30cm (minimum 45cm required)"
  ]
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Invalid image format or corrupted file |
| 422 | Validation error (missing required field) |
| 500 | Gemini API error |

---

### 2. POST /optimize

Optimizes the room layout while respecting locked objects.

**Description:**
- Takes current layout and user-locked object IDs
- Runs the constraint engine and solver
- Returns optimized layout with explanation

**Request:**

```http
POST /api/v1/optimize
Content-Type: application/json
```

```json
{
  "current_layout": [
    {
      "id": "bed_1",
      "label": "bed",
      "bbox": [10, 10, 100, 200],
      "type": "movable",
      "orientation": 0
    },
    {
      "id": "desk_1",
      "label": "desk",
      "bbox": [200, 50, 80, 50],
      "type": "movable",
      "orientation": 0
    }
  ],
  "locked_ids": ["bed_1"],
  "room_dimensions": {
    "width_estimate": 300,
    "height_estimate": 400
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `current_layout` | array | Yes | Current furniture positions |
| `locked_ids` | array | Yes | Object IDs that cannot be moved |
| `room_dimensions` | object | Yes | Room size estimates |

**Response (200 OK):**

```json
{
  "new_layout": [
    {
      "id": "bed_1",
      "label": "bed",
      "bbox": [10, 10, 100, 200],
      "type": "movable",
      "orientation": 0
    },
    {
      "id": "desk_1",
      "label": "desk",
      "bbox": [150, 300, 80, 50],
      "type": "movable",
      "orientation": 90
    }
  ],
  "explanation": "Moved desk to the opposite wall to create a 60cm walking path from the door. Rotated desk 90° to fit the narrower space while maintaining window proximity for natural light.",
  "layout_score": 85.5,
  "constraint_violations": []
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `new_layout` | array | Optimized furniture positions |
| `explanation` | string | Human-readable explanation of changes |
| `layout_score` | float | Usability score (0-100) |
| `constraint_violations` | array | Any remaining issues (should be empty) |

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Invalid layout data |
| 422 | Impossible to optimize (all space blocked) |
| 500 | Internal solver error |

---

### 3. POST /render

Generates the final edited image with optimized layout.

**Description:**
- Takes original image and layout diff
- Uses Gemini image editing to relocate furniture
- Returns the edited room image

**Request:**

```http
POST /api/v1/render
Content-Type: application/json
```

```json
{
  "original_image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
  "final_layout": [
    {
      "id": "desk_1",
      "label": "desk",
      "bbox": [150, 300, 80, 50],
      "type": "movable",
      "orientation": 90
    }
  ],
  "original_layout": [
    {
      "id": "desk_1",
      "label": "desk",
      "bbox": [200, 50, 80, 50],
      "type": "movable",
      "orientation": 0
    }
  ]
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `original_image_base64` | string | Yes | Original room photo (base64) |
| `final_layout` | array | Yes | Target furniture positions |
| `original_layout` | array | Yes | Original positions (for diff) |

**Response (200 OK):**

```json
{
  "image_url": "https://storage.googleapis.com/pocket-planner/renders/abc123.jpg",
  "image_base64": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Invalid image data |
| 422 | Cannot render (layout conflicts) |
| 500 | Gemini image generation error |

---

## Full Workflow Example

### Step 1: Analyze Room

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "image=@room_photo.jpg"
```

### Step 2: User Locks Bed, Request Optimization

```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "current_layout": [...],
    "locked_ids": ["bed_1"],
    "room_dimensions": {"width_estimate": 300, "height_estimate": 400}
  }'
```

### Step 3: Render Final Image

```bash
curl -X POST http://localhost:8000/api/v1/render \
  -H "Content-Type: application/json" \
  -d '{
    "original_image_base64": "...",
    "final_layout": [...],
    "original_layout": [...]
  }'
```

---

## Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error description",
  "error_code": "CONSTRAINT_VIOLATION",
  "context": {
    "objects_involved": ["bed_1", "desk_1"],
    "min_clearance": 45,
    "actual_clearance": 30
  }
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/analyze` | 10 requests | per minute |
| `/optimize` | 20 requests | per minute |
| `/render` | 5 requests | per minute |

---

## WebSocket (Future)

For real-time optimization feedback:

```
ws://localhost:8000/ws/optimize
```

Message format:
```json
{
  "type": "iteration",
  "iteration": 3,
  "current_score": 72.5,
  "status": "improving"
}
```
