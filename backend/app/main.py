from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import REPO_ROOT

app = FastAPI(
    title="AI Security Gate",
    description="Speckit-driven AI security review and threat modeling service",
    version="0.1.0",
)

static_dir = REPO_ROOT / "backend" / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")
