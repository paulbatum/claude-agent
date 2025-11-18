# Deployment Guide

## Development Setup

### Prerequisites

- **Python**: 3.12+ (check with `python --version`)
- **Node.js**: 18+ (check with `node --version`)
- **pnpm**: Latest (install with `npm install -g pnpm`)
- **uv**: Latest Python package manager (install from https://github.com/astral-sh/uv)
- **Anthropic API Key**: Get from https://console.anthropic.com/

### Initial Setup

**1. Clone Repository**

```bash
git clone <repository-url>
cd claude-agent
```

**2. Configure Environment**

Create `.env` file in project root:

```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

**Important**: Never commit `.env` to version control. It's in `.gitignore`.

**3. Backend Setup**

```bash
cd backend

# Install dependencies
uv pip install -e .

# Verify installation
python -c "from claude_agent_sdk import ClaudeSDKClient; print('SDK installed')"
```

**4. Frontend Setup**

```bash
cd frontend

# Install dependencies
pnpm install

# Verify installation
pnpm --version
```

### Running Locally

**Terminal 1 - Backend**:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using watchfiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Terminal 2 - Frontend**:

```bash
cd frontend
pnpm dev
```

**Output**:
```
  VITE v6.0.6  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**3. Open Browser**

Navigate to `http://localhost:5173` and start chatting!

## Production Deployment

### Architecture Considerations

**Current Limitations**:
- In-memory state (lost on restart)
- No authentication
- No rate limiting
- Single-server deployment only
- CORS configured for localhost only

**Recommended Production Stack**:
- **Frontend**: Static hosting (Vercel, Netlify, Cloudflare Pages)
- **Backend**: Container platform (Fly.io, Railway, AWS ECS)
- **Database**: PostgreSQL for conversation storage
- **Cache**: Redis for session management
- **Reverse Proxy**: nginx or Caddy for HTTPS

### Option 1: Docker Deployment

#### Dockerfile (Backend)

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Dockerfile (Frontend)

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy dependencies
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY . .

# Build
RUN pnpm build

# Production image
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### nginx.conf (Frontend)

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional - can point to separate backend URL)
    location /v1/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # Important for SSE
        proxy_buffering off;
        proxy_cache off;
    }
}
```

#### docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - PORT=8000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  # Optional: Redis for session storage
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

#### Running with Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: Platform-Specific Deployments

#### Fly.io

**1. Install Fly CLI**:

```bash
curl -L https://fly.io/install.sh | sh
```

**2. Login**:

```bash
fly auth login
```

**3. Deploy Backend**:

```bash
cd backend

# Initialize
fly launch --name claude-agent-backend

# Set secrets
fly secrets set ANTHROPIC_API_KEY=sk-ant-...

# Deploy
fly deploy
```

**4. Deploy Frontend**:

```bash
cd frontend

# Build
pnpm build

# Deploy static site
fly launch --name claude-agent-frontend
```

#### Railway

**1. Install Railway CLI**:

```bash
npm install -g @railway/cli
```

**2. Login**:

```bash
railway login
```

**3. Deploy**:

```bash
# Initialize project
railway init

# Link to project
railway link

# Set environment variables
railway variables set ANTHROPIC_API_KEY=sk-ant-...

# Deploy
railway up
```

#### Vercel (Frontend Only)

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Point VITE_API_URL to backend
vercel env add VITE_API_URL
```

Update `frontend/src/App.tsx`:

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const response = await fetch(`${API_URL}/v1/responses`, {
  // ...
})
```

### Environment Variables

#### Backend

**Required**:
- `ANTHROPIC_API_KEY` - Your Anthropic API key

**Optional**:
- `PORT` - Server port (default: 8000)
- `HOST` - Server host (default: 0.0.0.0)
- `ALLOWED_ORIGINS` - CORS allowed origins (comma-separated)

**Example** `.env.production`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
PORT=8000
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Update `backend/main.py` to use dynamic origins:

```python
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # ...
)
```

#### Frontend

**Optional**:
- `VITE_API_URL` - Backend API URL

**Example** `.env.production`:

```bash
VITE_API_URL=https://api.yourdomain.com
```

### Database Integration (Optional)

For production, replace in-memory storage with PostgreSQL.

**1. Install Dependencies**:

```bash
cd backend
uv pip install asyncpg sqlalchemy
```

**2. Create Database Schema**:

```python
# backend/database.py
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/claude_agent")

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"

    response_id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    request = Column(JSON, nullable=False)
    response = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
```

**3. Update `main.py`**:

Replace in-memory dicts with database queries:

```python
from database import async_session, Conversation

# Instead of:
# session_ids[response_id] = session_id

# Use:
async with async_session() as db:
    conversation = Conversation(
        response_id=response_id,
        session_id=session_id,
        request=request.model_dump(),
        response=response.model_dump(),
        created_at=datetime.utcnow()
    )
    db.add(conversation)
    await db.commit()
```

### HTTPS / SSL

#### Using Caddy (Recommended)

**Caddyfile**:

```
yourdomain.com {
    reverse_proxy localhost:80
}

api.yourdomain.com {
    reverse_proxy localhost:8000

    # Important for SSE
    flush_interval -1
}
```

#### Using nginx with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Auto-renewal is configured automatically
```

### Monitoring and Logging

#### Structured Logging

Update `backend/main.py`:

```python
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

@app.post("/v1/responses")
async def create_response(request: CreateResponseRequest):
    logger.info(f"Received request: model={request.model}, stream={request.stream}")
    # ...
```

#### Health Checks

The `/health` endpoint is already implemented:

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "claude-agent-api"}
```

Use this for:
- Load balancer health checks
- Uptime monitoring (UptimeRobot, Pingdom)
- Container orchestration health probes

#### Application Monitoring

Consider integrating:
- **Sentry**: Error tracking
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **DataDog**: All-in-one monitoring

### Performance Optimization

#### Backend

**1. Connection Pooling** (if using database):

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10
)
```

**2. Response Caching** (for identical requests):

```python
from functools import lru_cache

# Cache responses for 5 minutes
@lru_cache(maxsize=1000)
def get_cached_response(input_hash: str):
    # ...
```

**3. Rate Limiting**:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/v1/responses")
@limiter.limit("10/minute")
async def create_response(request: Request, ...):
    # ...
```

#### Frontend

**1. Code Splitting**:

```typescript
// Lazy load markdown renderer
const ReactMarkdown = lazy(() => import('react-markdown'))
```

**2. Service Worker** (for caching):

```javascript
// public/sw.js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('v1').then((cache) => {
      return cache.addAll(['/index.html', '/assets/'])
    })
  )
})
```

**3. Bundle Optimization**:

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']
        }
      }
    }
  }
})
```

### Security Hardening

**1. API Key Validation**:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/v1/responses", dependencies=[Depends(verify_api_key)])
async def create_response(...):
    # ...
```

**2. Input Validation**:

```python
class CreateResponseRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=10000)
    # ...
```

**3. CORS Restrictions**:

```python
# Only allow specific domains in production
allow_origins=["https://yourdomain.com"]
```

**4. Rate Limiting** (see above)

**5. Request Size Limits**:

```python
# Limit request body size to 1MB
app.add_middleware(
    BodySizeLimitMiddleware,
    max_size=1_000_000
)
```

### Backup and Recovery

**1. Database Backups** (if using PostgreSQL):

```bash
# Daily backup
pg_dump -U postgres claude_agent > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres claude_agent < backup_20240101.sql
```

**2. Conversation Export**:

Add endpoint to export conversations:

```python
@app.get("/v1/conversations/export")
async def export_conversations():
    return conversations
```

## Troubleshooting

### Backend Won't Start

**Check**:
1. `ANTHROPIC_API_KEY` is set
2. Port 8000 is not in use: `lsof -i :8000`
3. Dependencies are installed: `uv pip list`

### Frontend Can't Connect to Backend

**Check**:
1. Backend is running on port 8000
2. CORS origins include frontend URL
3. Browser console for errors
4. Network tab for failed requests

### Streaming Not Working

**Check**:
1. `stream: true` in request
2. No reverse proxy buffering (nginx: `proxy_buffering off`)
3. Client handles SSE correctly
4. Claude SDK version >=0.1.6

### High Memory Usage

**Causes**:
- Long conversations stored in memory
- No cleanup of old sessions

**Solutions**:
- Implement LRU cache for conversations
- Add TTL for session storage
- Move to database storage

## Cost Optimization

### Model Selection

- **Development**: Use Haiku (fastest, cheapest)
- **Production**: Use Sonnet or Opus based on needs

### Token Management

- Limit conversation length (truncate old messages)
- Monitor usage via Claude SDK `ResultMessage.usage`
- Set `max_output_tokens` to prevent runaway responses

### Caching

- Cache common responses (if appropriate)
- Use Claude's prompt caching feature (if available)

## Additional Resources

- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Fly.io Documentation](https://fly.io/docs/)
- [Railway Documentation](https://docs.railway.app/)
