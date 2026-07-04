"""
Vercel entrypoint (docs/01 §2).

Vercel's Python runtime detects the ASGI `app` object exported from
api/index.py and serves the whole FastAPI application as ONE serverless
function; vercel.json rewrites every path to it. Nothing else lives here —
all real code stays in app/ so the same app runs unchanged under uvicorn in
dev (docs/01 §7).

Required env on Vercel: SERVERLESS=true (NullPool), DATABASE_URL (Supabase
transaction pooler, port 6543), USE_LOCAL_STORAGE=false, SUPABASE_URL,
SUPABASE_SERVICE_KEY, JWT_SECRET_KEY, FRONTEND_URL. Full list and runbook:
docs/07-DEPLOYMENT.md.
"""

from app.main import app  # noqa: F401
