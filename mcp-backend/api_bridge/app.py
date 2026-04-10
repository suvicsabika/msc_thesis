from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from mcp_server.capabilities.tools import (
    register_tools,
)
from mcp_server.utils.config import settings
from mcp_server.services.video_ingest import save_uploaded_video
from mcp_server.services.minimap_extractor import extract_minimap_and_events
from mcp_server.services.stats_engine import compute_stats
from mcp_server.services.summary_engine import generate_summary
from mcp_server.utils.file_io import write_json, read_json
from mcp_server.domain.schemas import MatchEvents, MatchStats

app = FastAPI(title="Valorant MCP Bridge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _events_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "events.json"


def _stats_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "stats.json"


def _heatmap_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "heatmap.json"


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)) -> dict:
    ext = Path(file.filename or "upload.mp4").suffix or ".mp4"
    temp_name = f"upload_{uuid.uuid4().hex[:8]}{ext}"
    temp_path = settings.temp_dir / temp_name

    with temp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"temp_path": str(temp_path), "filename": file.filename}


@app.post("/analyze")
async def analyze_video_http(temp_path: str, match_name: str | None = None) -> dict:
    try:
        saved = save_uploaded_video(temp_path, match_name=match_name)
        match_id = saved["match_id"]

        events = extract_minimap_and_events(match_id=match_id, match_name=saved["match_name"])
        write_json(_events_path(match_id), events.model_dump())

        stats, heatmap = compute_stats(events)
        write_json(_stats_path(match_id), stats.model_dump())
        write_json(_heatmap_path(match_id), heatmap.model_dump())

        summary = generate_summary(stats, scope="match")

        return {
            "match_id": match_id,
            "events": events.model_dump(),
            "stats": stats.model_dump(),
            "heatmap": heatmap.model_dump(),
            "summary": summary.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/{match_id}")
async def get_results(match_id: str) -> dict:
    events = read_json(_events_path(match_id))
    stats = read_json(_stats_path(match_id))
    heatmap = read_json(_heatmap_path(match_id))

    if not events and not stats and not heatmap:
        raise HTTPException(status_code=404, detail="No results found")

    return {
        "match_id": match_id,
        "events": events,
        "stats": stats,
        "heatmap": heatmap,
    }