import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router as api_router

app = FastAPI(
    title="Legacy-to-Lakehouse Migration Copilot API",
    description="Backend API and SSE Event Stream for Operator Console (ui-2.md)",
    version="2.0.0",
)

# CORS middleware for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")

# Static frontend directory
web_dist_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "web",
    "dist",
)

if os.path.exists(web_dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(web_dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_spa(full_path: str):
        # Allow /api to pass through
        if full_path.startswith("api/"):
            return None
        file_candidate = os.path.join(web_dist_path, full_path)
        if os.path.exists(file_candidate) and os.path.isfile(file_candidate):
            return FileResponse(file_candidate)
        return FileResponse(os.path.join(web_dist_path, "index.html"))
else:
    @app.get("/", response_class=HTMLResponse)
    async def index_root():
        return """
        <!DOCTYPE html>
        <html>
        <head>
          <title>LEGACY // LAKEHOUSE API</title>
          <style>
            body { font-family: monospace; background: #000; color: #fff; padding: 40px; }
            a { color: #5B9BF6; }
          </style>
        </head>
        <body>
          <h2>LEGACY-TO-LAKEHOUSE // BACKEND READY</h2>
          <p>Target: LOCAL · DUCKDB</p>
          <p>Endpoints:</p>
          <ul>
            <li><a href="/api/health">/api/health</a></li>
            <li><a href="/api/runs/run_07">/api/runs/run_07 (Board snapshot)</a></li>
            <li><a href="/api/threads/thread_cust_01/state">/api/threads/thread_cust_01/state (Passed review)</a></li>
            <li><a href="/api/threads/thread_orders_02/state">/api/threads/thread_orders_02/state (Mid-repair)</a></li>
            <li><a href="/api/threads/thread_payments_03/state">/api/threads/thread_payments_03/state (Failed closed)</a></li>
          </ul>
        </body>
        </html>
        """
