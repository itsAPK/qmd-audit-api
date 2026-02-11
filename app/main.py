from contextlib import asynccontextmanager
import logging
from typing import Set

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import get_session, init_db, engine, async_session
from app.core.logging import configure_logging
from app.middlewares.slow_request import SlowRequestMiddleware
from app.middlewares.telegram_error import TelegramErrorMiddleware
from app.middlewares.tracing import TraceAndTimingMiddleware
from app.router import api_router
from starlette.middleware.sessions import SessionMiddleware
import time

@asynccontextmanager
async def lifespan(application: FastAPI): 

    configure_logging()
    yield


responses: Set[int] = {
    status.HTTP_400_BAD_REQUEST,
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
    status.HTTP_500_INTERNAL_SERVER_ERROR,
}

app = FastAPI(
    titale=" E- audit management system API",
    lifespan=lifespan,
)

if settings.CORS_ORIGINS:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if settings.USE_CORRELATION_ID:
    from app.middlewares.correlation import CorrelationMiddleware

    app.add_middleware(CorrelationMiddleware)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


# app.add_middleware(
#     TelegramErrorMiddleware,
#     telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
#     telegram_chat_id=settings.TELEGRAM_CHAT_ID,
# )

# app.add_middleware(TraceAndTimingMiddleware)
# app.add_middleware(SlowRequestMiddleware)


app.include_router(api_router)



start_time = time.time()
DB_FAILURE_THRESHOLD = 3
DB_COOLDOWN_SECONDS = 30
SLOW_DB_MS = 300

_db_failures = 0
_db_opened_at = None


@app.get("/health", tags=["Health"])
async def health_check():
    global _db_failures, _db_opened_at

    elapsed = int(time.time() - start_time)
    days, rem = divmod(elapsed, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime = f"{days}d {hours:02}h {minutes:02}m {seconds:02}s"

    postgres_status = "ok"
    latency_ms = None

    if _db_opened_at and (time.time() - _db_opened_at < DB_COOLDOWN_SECONDS):
        postgres_status = "circuit_open"
    else:
        start = time.perf_counter()
        try:
            async with async_session() as session:

                pass
                

            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if latency_ms >= SLOW_DB_MS:
                logging.warning(
                    "slow_db_health_check",
                    latency_ms=latency_ms,
                )

            _db_failures = 0
            _db_opened_at = None

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            postgres_status = "error"
            _db_failures += 1

            logging.warning(
                "postgres_health_failed",
                error=str(exc),
                latency_ms=latency_ms,
                failures=_db_failures,
            )

            if _db_failures >= DB_FAILURE_THRESHOLD:
                _db_opened_at = time.time()

    try:
        pool = engine.sync_engine.pool
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception:
        pool_stats = None

    try:
        worker_status = "ok"
    except Exception:
        worker_status = "error"

    degraded = postgres_status != "ok" or worker_status != "ok"
    http_status = (
        status.HTTP_200_OK if not degraded else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ok" if not degraded else "degraded",
            "version": "1.0.0",
            "uptime": uptime,
            "timestamp": int(time.time()),
            "services": {
                "postgres": {
                    "status": postgres_status,
                    "latency_ms": latency_ms,
                    "pool": pool_stats,
                },
                "worker": {
                    "status": worker_status,
                },
            },
        },
    )


@app.get("/", include_in_schema=False)
async def custom_docs():
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title> E-Audit Management System API</title>

  <!-- RapiDoc -->
  <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>

  <!-- Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Fira+Code&display=swap" rel="stylesheet" />

  <style>
    body {
      margin: 0;
      padding: 0;
      background: radial-gradient(circle at top, #2f2f45, #151521);
      font-family: 'Inter', sans-serif;
      color: #e5e7eb;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 18px 28px;
      background: linear-gradient(
        90deg,
        #3b4cb8,
        #6a1bb0
      );
      color: #ffffff;
      backdrop-filter: blur(10px);
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .header img {
      height: 38px;
      width: 38px;
      border-radius: 8px;
    }

    .header-text {
      display: flex;
      flex-direction: column;
    }

    .header-text h1 {
      font-size: 18px;
      margin: 0;
      font-weight: 600;
      color: #ffffff;
    }

    .header-text p {
      font-size: 13px;
      margin: 0;
      opacity: 0.85;
    }

    rapi-doc {
      height: calc(100vh - 76px);
    }
  </style>
</head>

<body>
  <!-- Top Branding Header -->
  <div class="header">
    <img src="https://xewnjhdnjxlaadjthrex.supabase.co/storage/v1/object/public/logos//Screenshot_2025-02-04_at_3.28.12_PM-removebg-preview.png" alt="QMD Logo" width="60px" height="40">
    <div class="header-text">
      <h1> E-Audit Management System API</h1>
      <p>Seamless & secure audit integrations</p>
    </div>
  </div>

  <!-- API Docs -->
  <rapi-doc
    spec-url="/openapi.json"

    theme="tokyonight"
    render-style="focused"
    layout="column"
show-method-in-nav-bar="as-colored-block"
allow-server-selection="false"
  

  primary-color="#6366F1"        
nav-accent-color="#8B5CF6"     

bg-color="#0B1020"             
text-color="#E5E7EB"            

nav-text-color="#CBD5E1"        
nav-hover-bg-color="#1E1B4B"     

header-color="#0F172A"          
header-text-color="#FFFFFF"


    regular-font="Inter, sans-serif"
    mono-font="Fira Code, monospace"
    font-size="15px"
  >
  </rapi-doc>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


