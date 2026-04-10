from pathlib import Path

from mcp_server.utils.config import settings
from mcp_server.utils.file_io import read_json, read_text


def register_resources(mcp) -> None:
    @mcp.resource("match://demo/events")
    def demo_events() -> dict:
        return {
            "match_id": "demo",
            "rounds": [
                {
                    "round_number": 1,
                    "events": [
                        {
                            "timestamp": 12.4,
                            "event_type": "kill",
                            "position": {"x": 0.72, "y": 0.41, "weight": 1},
                        }
                    ],
                }
            ],
        }

    @mcp.resource("match://{match_id}/events")
    def match_events(match_id: str) -> dict:
        path = settings.resources_dir / match_id / "events.json"
        return read_json(path) or {"match_id": match_id, "error": "events resource not found"}

    @mcp.resource("match://{match_id}/stats")
    def match_stats(match_id: str) -> dict:
        path = settings.resources_dir / match_id / "stats.json"
        return read_json(path) or {"match_id": match_id, "error": "stats resource not found"}

    @mcp.resource("match://{match_id}/heatmap")
    def match_heatmap(match_id: str) -> dict:
        path = settings.resources_dir / match_id / "heatmap.json"
        return read_json(path) or {"match_id": match_id, "error": "heatmap resource not found"}

    @mcp.resource("match://{match_id}/summary")
    def match_summary(match_id: str) -> str:
        path = settings.resources_dir / match_id / "summary.txt"
        return read_text(path) or f"No summary found for {match_id}"