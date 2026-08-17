import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import review_service, router
from .config import REPO_ROOT


_recovery_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(_: FastAPI):
    for review_id in review_service.recover_interrupted_auto_gate2():
        task = asyncio.create_task(
            asyncio.to_thread(review_service.run_auto_gate2, review_id),
            name=f"recover-auto-gate2-{review_id}",
        )
        _recovery_tasks.add(task)
        task.add_done_callback(_recovery_tasks.discard)
    yield


app = FastAPI(
    title="AI Security Gate",
    description="Speckit-driven AI security review and threat modeling service",
    version="0.1.0",
    lifespan=lifespan,
)

static_dir = REPO_ROOT / "backend" / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(
        static_dir / "index.html",
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )
