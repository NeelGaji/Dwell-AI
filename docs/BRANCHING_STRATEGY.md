# Git Branching Strategy

This document outlines the branching strategy for the Pocket Planner project, designed for parallel development by 3 developers over ~14 days.

## Branch Overview

```
main
 │
 └── develop
      │
      ├── feature/vision-image       (Developer A)
      ├── feature/core-intelligence  (Developer B)
      └── feature/frontend-demo      (Developer C)
```

## Branch Descriptions

### `main`
- **Purpose:** Production-ready code only
- **Protection:** Requires PR approval + CI passing
- **Merge from:** `develop` only (via release PRs)

### `develop`
- **Purpose:** Integration branch for all features
- **Protection:** Requires PR approval
- **Merge from:** Feature branches
- **Merge to:** `main` (for releases)

### `feature/vision-image` (Developer A)
**Focus:** Vision + Image Editing

| Days | Tasks |
|------|-------|
| 1-4 | Gemini prompts for object detection, JSON schema for room extraction, Initial image edit prompts |
| 5-9 | Targeted object movement prompts, Preserve lighting/geometry, Handle locked vs unlocked objects |
| 10-14 | Refine realism, Handle failure cases, Support demo scenarios |

**Key Files:**
- `backend/app/agents/vision_node.py`
- `backend/app/agents/render_node.py`
- `backend/app/agents/review_node.py`

### `feature/core-intelligence` (Developer B)
**Focus:** Core Intelligence / Main Brain

| Days | Tasks |
|------|-------|
| 1-4 | Room graph data structure, Object locking logic, State persistence |
| 5-9 | Constraint engine, Clearance heuristics, Layout scoring |
| 10-14 | Iterative planner loop, Re-optimization logic, Integration testing |

**Key Files:**
- `backend/app/core/geometry.py`
- `backend/app/core/room_graph.py`
- `backend/app/core/constraints.py`
- `backend/app/core/scoring.py`
- `backend/app/agents/constraint_node.py`
- `backend/app/agents/solver_node.py`
- `backend/app/agents/graph.py`
- `backend/app/models/*.py`

### `feature/frontend-demo` (Developer C)
**Focus:** Frontend + Demo

| Days | Tasks |
|------|-------|
| 1-4 | Image upload flow, Basic UI scaffolding |
| 5-9 | Lock object selection, Before/after comparison, Overlay visualization |
| 10-14 | Explainability UI, Demo polish, Video and submission assets |

**Key Files:**
- `frontend/app/*`
- `frontend/components/*`
- `frontend/hooks/*`

---

## Workflow

### Starting a Feature

```bash
# Ensure you're on develop and up to date
git checkout develop
git pull origin develop

# Create your feature branch
git checkout -b feature/core-intelligence
```

### Daily Work

```bash
# Commit frequently with clear messages
git add .
git commit -m "feat(core): add Shapely collision detection for furniture polygons"

# Push to remote
git push origin feature/core-intelligence
```

### Keeping Up with Develop

```bash
# Regularly sync with develop to avoid merge conflicts
git checkout develop
git pull origin develop

git checkout feature/core-intelligence
git merge develop

# Resolve any conflicts, then push
git push origin feature/core-intelligence
```

### Creating a Pull Request

1. Push your latest changes
2. Go to GitHub/GitLab and create a PR
3. Target: `develop` branch
4. Add relevant reviewers
5. Include:
   - Description of changes
   - Screenshots/demos if applicable
   - Related issue numbers

### Code Review Process

- At least 1 approval required
- CI must pass (linting, tests)
- No unresolved discussions

---

## Commit Message Convention

Use Conventional Commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructure, no feature change |
| `test` | Adding or fixing tests |
| `chore` | Build, tooling, dependencies |

### Scopes

| Scope | Description |
|-------|-------------|
| `core` | Core intelligence module |
| `agents` | LangGraph nodes |
| `api` | FastAPI routes |
| `models` | Pydantic schemas |
| `frontend` | Next.js frontend |
| `docs` | Documentation |

### Examples

```
feat(core): implement Shapely-based collision detection
fix(agents): handle empty object list in vision node
docs(api): add /optimize endpoint documentation
test(core): add unit tests for constraint engine
```

---

## Integration Schedule

| Day | Integration Milestone |
|-----|----------------------|
| Day 4 | First sync - basic structures in place |
| Day 7 | Mid-project merge - core features working |
| Day 10 | Feature freeze - all features complete |
| Day 12 | Final merge to develop |
| Day 14 | Release to main + demo |

---

## Merge Conflict Resolution

### Priority Order

If conflicts arise between branches:

1. **Core Intelligence** has priority for:
   - `backend/app/core/*`
   - `backend/app/models/*`
   - `backend/app/agents/graph.py`

2. **Vision/Image** has priority for:
   - `backend/app/agents/vision_node.py`
   - `backend/app/agents/render_node.py`

3. **Frontend** has priority for:
   - `frontend/*`

4. **Shared files** (e.g., `main.py`, routes) - coordinate via team chat

---

## Quick Reference

```bash
# Create branch
git checkout -b feature/core-intelligence develop

# Daily push
git push origin feature/core-intelligence

# Sync with develop
git fetch origin
git merge origin/develop

# Prepare for PR
git push origin feature/core-intelligence
# Then create PR on GitHub/GitLab
```

---

## Emergency Hotfixes

For critical production bugs:

```bash
git checkout main
git checkout -b hotfix/critical-bug
# Make fixes
git push origin hotfix/critical-bug
# Create PR to main AND develop
```
