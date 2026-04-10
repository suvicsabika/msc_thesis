from __future__ import annotations

from pathlib import Path

from mcp_server.domain.schemas import MatchEvents, MatchStats, HeatmapData, SummaryResponse
from mcp_server.services.video_ingest import save_uploaded_video
from mcp_server.services.minimap_extractor import extract_minimap_and_events
from mcp_server.services.stats_engine import compute_stats
from mcp_server.services.summary_engine import generate_summary
from mcp_server.utils.config import settings
from mcp_server.utils.file_io import write_json, read_json


def _events_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "events.json"


def _stats_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "stats.json"


def _heatmap_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "heatmap.json"


def _summary_path(match_id: str) -> Path:
    return settings.resources_dir / match_id / "summary.txt"


def register_tools(mcp) -> None:
    @mcp.tool
    def analyze_video(source_path: str, match_name: str | None = None) -> dict:
        """Analyze a Valorant video and generate the initial structured events resource."""
        saved = save_uploaded_video(source_path=source_path, match_name=match_name)
        match_id = saved["match_id"]

        events = extract_minimap_and_events(match_id=match_id, match_name=saved["match_name"])
        write_json(_events_path(match_id), events.model_dump())

        return {
            "match_id": match_id,
            "status": "events_generated",
            "generated_resources": [
                f"match://{match_id}/events",
            ],
        }

    @mcp.tool
    def compute_round_stats(match_id: str) -> dict:
        """Compute structured round-level stats and heatmap data from extracted events."""
        data = read_json(_events_path(match_id))
        if not data:
            return {
                "match_id": match_id,
                "status": "error",
                "message": "events resource not found"
            }

        events = MatchEvents.model_validate(data)
        stats, heatmap = compute_stats(events)

        write_json(_stats_path(match_id), stats.model_dump())
        write_json(_heatmap_path(match_id), heatmap.model_dump())

        return {
            "match_id": match_id,
            "status": "stats_generated",
            "generated_resources": [
                f"match://{match_id}/stats",
                f"match://{match_id}/heatmap",
            ],
        }

    @mcp.tool
    def generate_tactical_summary(match_id: str, scope: str = "match", round_number: int | None = None) -> dict:
        """Generate a tactical summary from existing structured stats."""
        data = read_json(_stats_path(match_id))
        if not data:
            return {
                "match_id": match_id,
                "status": "error",
                "message": "stats resource not found"
            }

        stats = MatchStats.model_validate(data)
        summary = generate_summary(stats, scope=scope, round_number=round_number)

        (_summary_path(match_id)).parent.mkdir(parents=True, exist_ok=True)
        _summary_path(match_id).write_text(summary.summary, encoding="utf-8")

        return summary.model_dump()