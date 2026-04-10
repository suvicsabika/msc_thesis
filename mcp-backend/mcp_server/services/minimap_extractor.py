from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from mcp_server.domain.schemas import MatchEvents, RoundEvents, EventItem
from mcp_server.utils.config import settings
from mcp_server.utils.file_io import write_json
from mcp_server.services.hud_event_extractor import (
    NormalizedROI,
    KillfeedState,
    BannerState,
    crop_normalized,
    pixel_rect_from_normalized,
    detect_kill_events,
    detect_plant_event,
)


@dataclass
class ExtractionConfig:
    sample_period_sec: float = settings.sample_period_sec
    max_video_seconds: int | None = settings.max_video_seconds

    killfeed_roi: NormalizedROI = field(
        default_factory=lambda: NormalizedROI(0.74, 0.02, 0.99, 0.24)
    )
    plant_banner_roi: NormalizedROI = field(
        default_factory=lambda: NormalizedROI(0.33, 0.11, 0.57, 0.21)
    )

    debug_visualize: bool = settings.debug_visualize
    debug_save_annotated_video: bool = settings.debug_save_annotated_video
    debug_save_debug_json: bool = settings.debug_save_debug_json
    debug_window_delay_ms: int = settings.debug_window_delay_ms
    debug_step_mode: bool = settings.debug_step_mode
    debug_preview_max_width: int = settings.debug_preview_max_width
    debug_preview_max_height: int = settings.debug_preview_max_height
    debug_panel_zoom: float = 3.0


def extract_minimap_and_events(match_id: str, match_name: str | None = None) -> MatchEvents:
    """
    HUD-only MVP:
    - kill feed state-machine detection
    - planting banner detection
    - no minimap, no center ROI
    """
    config = ExtractionConfig()
    video_path = _find_video_file(match_id)

    debug_dir = settings.processed_dir / match_id
    debug_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = frame_count / fps if frame_count > 0 else 0.0
    if config.max_video_seconds is not None:
        duration_sec = min(duration_sec, float(config.max_video_seconds))

    frame_step = max(1, int(fps * config.sample_period_sec))

    first_ok, first_frame = cap.read()
    if not first_ok or first_frame is None:
        cap.release()
        raise RuntimeError(f"Could not read first frame from: {video_path}")

    frame_h, frame_w = first_frame.shape[:2]
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    writer = None
    annotated_video_path = debug_dir / f"{match_id}_annotated.mp4"
    if config.debug_save_annotated_video:
        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(annotated_video_path),
            fourcc,
            max(1.0, fps / frame_step),
            (min(config.debug_preview_max_width, 1600), min(config.debug_preview_max_height, 900)),
        )

    kill_state = KillfeedState()
    plant_state = BannerState()

    emitted_events: list[EventItem] = []
    debug_entries: list[dict[str, Any]] = []

    frame_idx = 0
    try:
        while True:
            if duration_sec and (frame_idx / fps) > duration_sec:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                break

            timestamp = frame_idx / fps

            kill_events, kill_debug, kill_crop = detect_kill_events(
                frame=frame,
                timestamp=timestamp,
                state=kill_state,
                roi=config.killfeed_roi,
            )

            plant_events, plant_debug, plant_crop = detect_plant_event(
                frame=frame,
                timestamp=timestamp,
                state=plant_state,
                roi=config.plant_banner_roi,
            )

            emitted_now = []
            if kill_events:
                emitted_events.extend(kill_events)
                emitted_now.extend(["KILL"] * len(kill_events))

            if plant_events:
                emitted_events.extend(plant_events)
                emitted_now.extend(["PLANT"] * len(plant_events))

            debug_entries.append(
                {
                    "frame_idx": frame_idx,
                    "timestamp": round(timestamp, 2),
                    "kill_debug": kill_debug,
                    "plant_debug": plant_debug,
                    "emitted_now": emitted_now,
                }
            )

            annotated_full = _annotate_frame(
                frame=frame.copy(),
                timestamp=timestamp,
                match_id=match_id,
                config=config,
                kill_debug=kill_debug,
                plant_debug=plant_debug,
                emitted_now=emitted_now,
            )

            debug_panel = _build_debug_panel(
                frame=annotated_full,
                kill_crop=kill_crop,
                plant_crop=plant_crop,
                kill_debug=kill_debug,
                plant_debug=plant_debug,
                config=config,
            )

            if writer is not None:
                out_frame = _fit_exact(debug_panel, 1600, 900)
                writer.write(out_frame)

            if config.debug_visualize:
                cv2.namedWindow("Valorant MCP Debug", cv2.WINDOW_NORMAL)
                cv2.imshow("Valorant MCP Debug", debug_panel)

                if config.debug_step_mode:
                    while True:
                        key = cv2.waitKey(0) & 0xFF
                        if key == ord("q"):
                            return MatchEvents(
                                match_id=match_id,
                                match_name=match_name or video_path.stem,
                                map_name=_guess_map_name(video_path.name),
                                rounds=[RoundEvents(round_number=1, events=emitted_events)],
                            )
                        if key == ord("n") or key == 13:
                            break
                else:
                    key = cv2.waitKey(config.debug_window_delay_ms) & 0xFF
                    if key == ord("q"):
                        break

            frame_idx += frame_step

    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if config.debug_visualize:
            cv2.destroyAllWindows()

    if config.debug_save_debug_json:
        write_json(debug_dir / "debug_detections.json", debug_entries)

    return MatchEvents(
        match_id=match_id,
        match_name=match_name or video_path.stem,
        map_name=_guess_map_name(video_path.name),
        rounds=[
            RoundEvents(
                round_number=1,
                events=emitted_events,
            )
        ],
    )


def _find_video_file(match_id: str) -> Path:
    candidates = sorted(settings.raw_dir.glob(f"{match_id}.*"))
    if not candidates:
        raise FileNotFoundError(
            f"No uploaded video found for match_id={match_id} in {settings.raw_dir}"
        )
    return candidates[0]


def _guess_map_name(filename: str) -> str:
    lower = filename.lower()
    known_maps = [
        "ascent", "bind", "haven", "split", "icebox",
        "breeze", "fracture", "pearl", "lotus", "sunset", "abyss",
    ]
    for name in known_maps:
        if name in lower:
            return name.title()
    return "Unknown"


def _annotate_frame(
    frame: np.ndarray,
    timestamp: float,
    match_id: str,
    config: ExtractionConfig,
    kill_debug: dict[str, Any],
    plant_debug: dict[str, Any],
    emitted_now: list[str],
) -> np.ndarray:
    # Kill ROI
    x1, y1, x2, y2 = pixel_rect_from_normalized(frame, config.killfeed_roi)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(
        frame,
        "KILLFEED ROI",
        (x1 + 5, y1 + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    # Plant ROI
    x1b, y1b, x2b, y2b = pixel_rect_from_normalized(frame, config.plant_banner_roi)
    cv2.rectangle(frame, (x1b, y1b), (x2b, y2b), (255, 200, 0), 2)
    cv2.putText(
        frame,
        "PLANT ROI",
        (x1b + 5, y1b + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 200, 0),
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"match={match_id}   t={timestamp:.2f}s",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        3,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"kill rows={kill_debug.get('row_count', 0)}   tracks={kill_debug.get('track_count', 0)}   "
        f"plant_active={plant_debug.get('active', False)}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (220, 220, 220),
        2,
        cv2.LINE_AA,
    )

    y = 125
    for label in emitted_now:
        cv2.putText(
            frame,
            f"EVENT: {label}",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            3,
            cv2.LINE_AA,
        )
        y += 38

    return frame


def _build_debug_panel(
    frame: np.ndarray,
    kill_crop: np.ndarray,
    plant_crop: np.ndarray,
    kill_debug: dict[str, Any],
    plant_debug: dict[str, Any],
    config: ExtractionConfig,
) -> np.ndarray:
    full = _resize_to_fit(frame, 1100, 850)

    kill_panel = _annotate_kill_crop(kill_crop, kill_debug)
    plant_panel = _annotate_plant_crop(plant_crop, plant_debug)

    kill_panel = cv2.resize(
        kill_panel,
        (500, max(200, int(kill_panel.shape[0] * (500 / kill_panel.shape[1])))),
        interpolation=cv2.INTER_NEAREST,
    )
    plant_panel = cv2.resize(
        plant_panel,
        (500, max(160, int(plant_panel.shape[0] * (500 / plant_panel.shape[1])))),
        interpolation=cv2.INTER_NEAREST,
    )

    spacer = np.zeros((20, 500, 3), dtype=np.uint8)
    right_col = np.vstack([kill_panel, spacer, plant_panel])

    if right_col.shape[0] < full.shape[0]:
        pad = full.shape[0] - right_col.shape[0]
        right_col = cv2.copyMakeBorder(right_col, 0, pad, 0, 0, cv2.BORDER_CONSTANT, value=(20, 20, 20))
    elif full.shape[0] < right_col.shape[0]:
        pad = right_col.shape[0] - full.shape[0]
        full = cv2.copyMakeBorder(full, 0, pad, 0, 0, cv2.BORDER_CONSTANT, value=(20, 20, 20))

    panel = np.hstack([full, right_col])
    panel = _resize_to_fit(panel, config.debug_preview_max_width, config.debug_preview_max_height)
    return panel


def _annotate_kill_crop(crop: np.ndarray, kill_debug: dict[str, Any]) -> np.ndarray:
    if crop.size == 0:
        return np.zeros((200, 500, 3), dtype=np.uint8)

    out = crop.copy()
    rows = kill_debug.get("rows", [])

    for row in rows:
        x1, y1, x2, y2 = row["bbox"]
        color = (0, 255, 255) if row["status"] == "NEW" else (0, 200, 0)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            out,
            row["status"],
            (x1 + 4, max(18, y1 + 18)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        out,
        f"KILLFEED rows={kill_debug.get('row_count', 0)} tracks={kill_debug.get('track_count', 0)}",
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return out


def _annotate_plant_crop(crop: np.ndarray, plant_debug: dict[str, Any]) -> np.ndarray:
    if crop.size == 0:
        return np.zeros((120, 500, 3), dtype=np.uint8)

    out = crop.copy()
    active = plant_debug.get("active", False)
    bright_ratio = plant_debug.get("bright_ratio", 0.0)

    color = (0, 255, 255) if active else (180, 180, 180)
    cv2.rectangle(out, (0, 0), (out.shape[1] - 1, out.shape[0] - 1), color, 2)
    cv2.putText(
        out,
        f"PLANT active={active} bright={bright_ratio}",
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return out


def _resize_to_fit(image: np.ndarray, max_width: int, max_height: int) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(max_width / w, max_height / h, 1.0)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _fit_exact(image: np.ndarray, width: int, height: int) -> np.ndarray:
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    fitted = _resize_to_fit(image, width, height)
    h, w = fitted.shape[:2]
    canvas[:h, :w] = fitted
    return canvas