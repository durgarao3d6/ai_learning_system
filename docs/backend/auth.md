# Authentication — Argon2id Hashing, JWT Access/Refresh Token Design, and Rate Limiting

## What it is
The authentication architecture uses state-of-the-art Argon2id password hashing, stateless dual-token JSON Web Tokens (a short-lived 15-minute access token and a 7-day refresh token), automated silent token renewal via Axios interceptors, and strict IP-based rate limiting on login endpoints using `slowapi`.

## Why we need it / Why this approach
User authentication is the primary barrier protecting quiz integrity, proctoring violation logs, and student performance data:
1. **Argon2id over bcrypt**: Argon2 won the international Password Hashing Competition (PHC). While bcrypt has been standard for two decades, it is CPU-bound and vulnerable to modern mass-parallelized GPU/ASIC cracking arrays. Argon2id is a hybrid variant combining data-dependent and data-independent memory access. It is explicitly memory-hard: cracking it requires large amounts of dedicated RAM per thread, rendering GPU clustering ineffective. We use `argon2-cffi`, which binds directly to the battle-tested reference C implementation.
2. **Dual-token JWT lifecycle (15 min access / 7 day refresh)**:
   - If an access token is valid for days, any token compromised via network snooping or cross-site scripting (XSS) gives attackers prolonged, irrevocable access.
   - Restricting the access token lifespan to 15 minutes minimizes the exposure window of a stolen credential.
   - The 7-day refresh token permits users to maintain seamless sessions without repeatedly re-entering credentials.
3. **Stateless scalability without database bottleneck**: Traditional server-side sessions require querying a database or shared Redis cache on every single HTTP request to validate session IDs. Stateless JWTs allow FastAPI workers to authenticate requests purely through cryptographic signature verification (`jwt.decode`) without touching the database, preserving high backend throughput. The database is only queried during initial login and refresh token exchange.
4. **Seamless user experience via interceptors**: An expired 15-minute access token must never interrupt a student during an active exam. The frontend HTTP client automatically catches `401 Unauthorized` responses in the background, exchanges the refresh token for a new access token at `/api/v1/auth/refresh`, and transparently replays the original failed request.
5. **Brute-force protection**: Credential stuffing and dictionary attacks against `/api/v1/auth/login` are mitigated using `slowapi` rate limiting (5 attempts per minute per IP). Exceeding this threshold triggers an immediate `429 Too Many Requests` lockout for 15 minutes.

## Alternatives considered
| Option | Why rejected |
|---|---|
| bcrypt for password hashing | Older design (1999); not memory-hard. Modern GPUs can calculate millions of bcrypt hashes per second compared to memory-bound Argon2id. |
| Server-side session cookies (e.g. Redis sessions) | Requires maintaining and scaling a persistent Redis session store; adds a network/database lookup to every single API request. |
| Single long-lived JWT token (e.g., 30 days) | High security risk. If a client token is intercepted, there is no way to invalidate or expire it prior to expiration without maintaining a server-side denylist. |
| Storing refresh token in memory only | Forces users to log in again every time they refresh the page or open a new browser tab, severely degrading usability. |

## Implementation details

Authentication logic is encapsulated in `backend/app/services/auth_service.py` and wrapped by `backend/app/routers/auth.py`.

### 1. Password Hashing with `argon2-cffi`
```python
# backend/app/services/auth_service.py
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

ph = PasswordHasher(
    time_cost=2,        # Number of iterations
    memory_cost=65536,  # 64 MiB memory usage per hash
    parallelism=2,      # Number of parallel threads
    hash_len=32,
    salt_len=16,
)

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False
```

### 2. Token Generation and Decoding
```python
# backend/app/services/auth_service.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.config import get_settings

settings = get_settings()

def create_access_token(user_id: str, role: str) -> str:
    """Generate a short-lived access token (15 minutes)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),  # 15 mins
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    """Generate a long-lived refresh token (7 days)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),      # 7 days
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT token payload."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_type = payload.get("type")
        if token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}, got {token_type}",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### 3. Rate Limiting on Login (`backend/app/routers/auth.py`)
```python
# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user, create_access_token, create_refresh_token

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest, db = Depends(get_db)):
    """Authenticate user and return access + refresh tokens. Rate-limited to 5/min per IP."""
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
```

### 4. Client-Side Axios Refresh Flow (`frontend/src/api/client.ts`)
```typescript
// frontend/src/api/client.ts
import axios from 'axios';
import { useAuthStore } from '../store/authStore';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
});

// Request interceptor: attach access token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: auto-refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        if (!refreshToken) throw new Error('No refresh token available');

        const { data } = await axios.post(`${apiClient.defaults.baseURL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);
```

## Tradeoffs and known limitations
1. **Refresh token storage tradeoff**: In Phase 1, the refresh token is stored in `localStorage` via Zustand's `persist` middleware. This simplifies cross-tab session synchronization and SPA development, but presents a known vulnerability to Cross-Site Scripting (XSS). In Phase 7 (Hardening), the refresh token will be migrated to a `SameSite=Strict`, `HttpOnly`, `Secure` cookie.
2. **Immediate revocation limitation**: Because JWTs are stateless, an access token cannot be revoked immediately if a user's permissions change before the 15-minute expiration, unless a distributed token revocation blocklist is introduced.
3. **Argon2 memory consumption**: Argon2id requires 64MB of RAM per hash verification. While highly effective at blocking brute-force attacks, high concurrency login spikes require adequate backend server memory provisioning.
