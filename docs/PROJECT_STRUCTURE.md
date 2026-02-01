# Pocket Planner - Project Structure Documentation

## Overview

**Small Space Optimization Agent** - An agentic spatial planner that optimizes small rooms for movement and multi-use, while allowing users to lock key furniture and letting the agent intelligently re-optimize the rest of the space.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│                    (Next.js + React-Konva Canvas)                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼ REST API
┌─────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    LangGraph Workflow                            │    │
│  │  ┌──────────┐   ┌────────────────┐   ┌──────────────┐           │    │
│  │  │ Vision   │──▶│  Constraint    │──▶│   Solver     │           │    │
│  │  │  Node    │   │    Node        │   │    Node      │           │    │
│  │  └──────────┘   └────────────────┘   └──────────────┘           │    │
│  │       │                                     │                    │    │
│  │       │              ┌──────────────────────┘                    │    │
│  │       │              ▼                                           │    │
│  │  ┌──────────┐   ┌────────────────┐   ┌──────────────┐           │    │
│  │  │ Review   │◀──│   Human Lock   │──▶│   Render     │           │    │
│  │  │  Node    │   │    (HITL)      │   │    Node      │           │    │
│  │  └──────────┘   └────────────────┘   └──────────────┘           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌──────────────────────┐   ┌──────────────────────┐                    │
│  │   Shapely Geometry   │   │   Pydantic Schemas   │                    │
│  │       Engine         │   │                      │                    │
│  └──────────────────────┘   └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        GOOGLE VERTEX AI                                  │
│         Gemini 1.5 Pro (Vision) + Gemini Flash (Reasoning)              │
└─────────────────────────────────────────────────────────────────────────┘
```

## Folder Structure

```
pocket-planner/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entrypoint
│   │   ├── config.py               # Environment configuration
│   │   │
│   │   ├── agents/                 # LangGraph nodes
│   │   │   ├── __init__.py
│   │   │   ├── graph.py            # Main LangGraph workflow definition
│   │   │   ├── vision_node.py      # Gemini vision for object detection
│   │   │   ├── constraint_node.py  # Shapely-based constraint checking
│   │   │   ├── solver_node.py      # Layout optimization logic
│   │   │   ├── review_node.py      # Optional Gemini Flash review
│   │   │   └── render_node.py      # Gemini image editing/inpainting
│   │   │
│   │   ├── core/                   # Shapely logic & geometry utils
│   │   │   ├── __init__.py
│   │   │   ├── geometry.py         # Polygon operations, collision detection
│   │   │   ├── room_graph.py       # Room graph data structure (NetworkX)
│   │   │   ├── constraints.py      # Hard/soft constraint definitions
│   │   │   └── scoring.py          # Layout usability scoring
│   │   │
│   │   ├── models/                 # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── room.py             # Room and object schemas
│   │   │   ├── state.py            # AgentState for LangGraph
│   │   │   └── api.py              # API request/response schemas
│   │   │
│   │   └── routes/                 # FastAPI routes
│   │       ├── __init__.py
│   │       ├── analyze.py          # POST /analyze endpoint
│   │       ├── optimize.py         # POST /optimize endpoint
│   │       └── render.py           # POST /render endpoint
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_geometry.py
│   │   ├── test_constraints.py
│   │   └── test_agents.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # Next.js application
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── api/                    # API routes (proxy to backend)
│   │
│   ├── components/
│   │   ├── ImageUpload.tsx
│   │   ├── RoomCanvas.tsx          # React-Konva canvas
│   │   ├── ObjectLock.tsx
│   │   └── ExplanationPanel.tsx
│   │
│   ├── hooks/
│   │   ├── useAnalyze.ts
│   │   ├── useOptimize.ts
│   │   └── useRender.ts
│   │
│   ├── lib/
│   │   └── api.ts                  # API client
│   │
│   ├── package.json
│   └── next.config.js
│
├── docs/
│   ├── PROJECT_STRUCTURE.md        # This file
│   ├── DATA_SCHEMAS.md             # Data schema documentation
│   ├── API_REFERENCE.md            # API endpoint documentation
│   └── BRANCHING_STRATEGY.md       # Git branching guide
│
├── .env.example
├── docker-compose.yml
└── README.md
```

## Branch Strategy

Based on the 3-developer parallel execution plan:

| Branch | Developer | Focus Area | Description |
|--------|-----------|------------|-------------|
| `main` | All | Production | Stable, deployable code |
| `develop` | All | Integration | Integration branch for all features |
| `feature/vision-image` | Developer A | Vision + Image Editing | Gemini prompts, JSON extraction, image edits |
| `feature/core-intelligence` | Developer B | Core Intelligence | Room graph, constraints, planner logic |
| `feature/frontend-demo` | Developer C | Frontend + Demo | UI, canvas, demo polish |

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **AI/Vision** | Google Vertex AI | Gemini 1.5 Pro (Vision), Flash (Reasoning) |
| **AI SDK** | `google-genai` | Unified Python SDK for Gemini |
| **Agent Framework** | LangGraph | Stateful workflow orchestration |
| **Geometry** | Shapely | Polygon operations, collision detection |
| **Graph** | NetworkX | Room object relationship management |
| **Backend** | FastAPI | High-performance Python API server |
| **Validation** | Pydantic | Data schemas and validation |
| **Frontend** | Next.js (React) | User interface framework |
| **Canvas** | React-Konva | Interactive room visualization |

## What is the "Main Brain"?

The **Core Intelligence** (Developer B's domain) consists of:

1. **Room Graph Data Structure** (`core/room_graph.py`)
   - NetworkX-based graph representing furniture relationships
   - Object locking/unlocking logic
   - State persistence across iterations

2. **Constraint Engine** (`core/constraints.py`)
   - Hard constraints: Door clearance, minimum walking paths, locked objects
   - Soft constraints: Desk near window, bed away from door

3. **Geometry Utilities** (`core/geometry.py`)
   - Shapely-based polygon operations
   - Collision detection between furniture
   - Clearance calculations

4. **Layout Scoring** (`core/scoring.py`)
   - Usability scoring algorithms
   - Path accessibility metrics

5. **LangGraph Workflow** (`agents/graph.py`)
   - Orchestrates the agent loop
   - Manages state between nodes
   - Handles re-optimization cycles

## Next Steps

1. **Set up the backend project structure**
2. **Define all Pydantic data models**
3. **Implement the core geometry utilities**
4. **Build the LangGraph workflow skeleton**
5. **Connect to Gemini via google-genai SDK**
