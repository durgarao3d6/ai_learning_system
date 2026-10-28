# API Versioning — Mandatory `/api/v1/` Prefix from Day One

## What it is
All backend HTTP endpoints in the Proctored RAG Quiz System are explicitly prefixed with `/api/v1/` starting from the very first commit. This establishes a clean architectural boundary between client-side Single Page Application (SPA) routes and backend endpoints, while providing a non-breaking version identifier for future contract migrations.

## Why we need it / Why this approach
Exposing unversioned routes like `/auth/login` or `/quizzes` creates technical debt that becomes exponentially harder and more expensive to resolve once client software is deployed.
1. **Collision avoidance with SPA routes**: Modern single-page applications use client-side routing (via React Router). If both the frontend router and backend API use unversioned paths (e.g., `/login`, `/dashboard`, `/quizzes`), reverse proxies (such as Nginx, Cloudflare, or AWS ALB) require brittle regular expression rules to differentiate HTML document requests from JSON data endpoints. Namespacing the backend under `/api/` eliminates ambiguity: any path starting with `/api/` is reverse-proxied to FastAPI, and all other paths serve `index.html`.
2. **Preventing coordinated deployment locks**: If a frontend is deployed in production calling `/auth/login`, migrating to `/api/v1/auth/login` later requires a synchronized, high-risk lockstep deployment of both frontend and backend. Any user running a cached frontend bundle in their browser immediately experiences broken requests.
3. **Seamless API evolution (`/v1` to `/v2`)**: Inevitably, breaking changes occur (e.g., redesigning the proctoring event payload or quiz question schema). With `/v1/` explicit in the URL path, a new `/api/v2/` router can be deployed alongside `/api/v1/` in the same backend instance. The new frontend release transitions to `/v2/` endpoints while legacy clients or mobile web views remain functional until phased deprecation.
4. **Prohibitive cost of retrofitting**: Retrofitting a prefix after the initial build requires modifying every frontend API client function, Axios base URL configuration, integration test, mock fixture, OpenAPI documentation link, and monitoring alert rule. Enforcing `/api/v1/` on day one costs literally five lines of code.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Unversioned endpoints (`/auth/login`, `/quizzes`) | High risk of route collisions with React Router frontend pages; impossible to make breaking schema changes without breaking active clients. |
| Header-based versioning (`Accept: application/vnd.app.v1+json`) | Inflexible and hard to inspect. Browsers cannot easily preview endpoints via address bar; complicates caching in CDNs, OpenAPI/Swagger auto-generation, and simple `curl` debugging. |
| Query parameter versioning (`/auth/login?version=1`) | Easily omitted by frontend callers, muddies URL query parameters, breaks caching semantics, and clutters FastAPI dependency injection. |
| Versioning only when breaking changes happen | Requires a massive coordinated code refactor across both frontend and backend repositories once technical debt has already accumulated. |

## Implementation details

In FastAPI, versioning is enforced at the router aggregation level. Individual route modules (e.g., `auth.py`, `quizzes.py`) define subpaths without repeating the `/api/v1` prefix. The root router in `backend/app/routers/api_v1.py` bundles them, and `backend/app/main.py` mounts the router with the global prefix.

### 1. Route Aggregator (`backend/app/routers/api_v1.py`)
```python
# backend/app/routers/api_v1.py
from fastapi import APIRouter
from app.routers import auth, quizzes, documents, attempts, proctor

api_router = APIRouter()

# Group all domain routers under /api/v1
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["Quizzes"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(attempts.router, prefix="/attempts", tags=["Attempts"])
api_router.include_router(proctor.router, prefix="/proctor", tags=["Proctoring"])
```

### 2. Main Application Mounting (`backend/app/main.py`)
```python
# backend/app/main.py
from fastapi import FastAPI
from app.config import get_settings
from app.routers.api_v1 import api_router

settings = get_settings()

app = FastAPI(
    title="Proctored RAG Quiz System API",
    version="1.0.0",
    docs_url="/api/v1/docs",      # Swagger UI co-located under API namespace
    openapi_url="/api/v1/openapi.json",
)

# Mount the unified v1 router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    """Unversioned infrastructure probe for load balancers and orchestrators."""
    return {"status": "healthy", "version": settings.APP_VERSION}
```

### 3. Frontend Client Configuration (`frontend/src/api/client.ts`)
```typescript
// frontend/src/api/client.ts
import axios from 'axios';

// Vite env variable with fallback to local v1 backend
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

## Tradeoffs and known limitations
1. **URL path verbosity**: Every API endpoint has a longer path string (`/api/v1/...`). This is a trivial aesthetic cost with no performance impact.
2. **Coarse granularity**: Versioning at the path level versioning applies to entire router groups. If only one endpoint changes (e.g., question schema), creating a `/v2/` router can lead to duplication of unchanged endpoints if not cleanly delegated to shared service layers.
3. **Health check exception**: Infrastructure probes (e.g., `/health`, Kubernetes liveness/readiness checks) should intentionally remain outside the `/api/v1` namespace to prevent infrastructure failure if API routing middleware encounters errors.
