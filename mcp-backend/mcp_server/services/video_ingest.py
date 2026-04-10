from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from mcp_server.utils.config import settings


def save_uploaded_video(source_path: str, match_name: str | None = None) -> dict:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Video file not found: {source_path}")

    match_id = f"match_{uuid.uuid4().hex[:8]}"
    suffix = src.suffix or ".mp4"
    dest = settings.raw_dir / f"{match_id}{suffix}"
    shutil.copy2(src, dest)

    return {
        "match_id": match_id,
        "match_name": match_name or src.stem,
        "video_path": str(dest),
        "status": "uploaded",
    }