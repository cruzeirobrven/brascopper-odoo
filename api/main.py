import sys
from pathlib import Path

# Allow running as `python3 api/main.py` or `python3 -m api.main`
_parent = Path(__file__).resolve().parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.config import settings
from api.routers import nfe, erp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="NF-e Hub API",
    description="API centralizada para geracao e envio de NF-e",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nfe.router, prefix="/api/v1")
app.include_router(erp.router, prefix="/api/v1")

# Serve frontend (app/dist)
frontend_dir = Path(__file__).resolve().parent.parent / "app" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.get("/")
async def root():
    return {"app": "NF-e Hub", "version": "0.1.0"}


@app.get("/api/v1/status")
async def status():
    from services.acbr_monitor import ACBrMonitorClient

    try:
        acbr = ACBrMonitorClient(
            host=settings.acbr_host,
            port=settings.acbr_port,
            timeout=settings.acbr_timeout,
        )
        acbr_status = acbr.status()
        acbr_ok = True
    except Exception as e:
        acbr_status = str(e)
        acbr_ok = False

    return {
        "api": "ok",
        "acbr_monitor": {
            "ok": acbr_ok,
            "status": acbr_status,
            "host": settings.acbr_host,
            "port": settings.acbr_port,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
