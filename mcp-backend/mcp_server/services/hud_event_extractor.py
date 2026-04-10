from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from mcp_server.domain.schemas import EventItem


@dataclass(frozen=True)
class NormalizedROI:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class KillTrack:
    signature: np.ndarray
    y_center: float
    last_seen_ts: float


@dataclass
class KillfeedState:
    tracks: list[KillTrack] = field(default_factory=list)
    ttl_sec: float = 4.0


@dataclass
class BannerState:
    active: bool = False
    last_emit_ts: float = -9999.0


def crop_normalized(frame: np.ndarray, roi: NormalizedROI) -> np.ndarray:
    h, w = frame.shape[:2]
    x1 = max(0, min(w - 1, int(roi.x1 * w)))
    y1 = max(0, min(h - 1, int(roi.y1 * h)))
    x2 = max(x1 + 1, min(w, int(roi.x2 * w)))
    y2 = max(y1 + 1, min(h, int(roi.y2 * h)))
    return frame[y1:y2, x1:x2]


def pixel_rect_from_normalized(frame: np.ndarray, roi: NormalizedROI) -> tuple[int, int, int, int]:
    h, w = frame.shape[:2]
    x1 = max(0, min(w - 1, int(roi.x1 * w)))
    y1 = max(0, min(h - 1, int(roi.y1 * h)))
    x2 = max(x1 + 1, min(w, int(roi.x2 * w)))
    y2 = max(y1 + 1, min(h, int(roi.y2 * h)))
    return x1, y1, x2, y2


def detect_kill_events(
    frame: np.ndarray,
    timestamp: float,
    state: KillfeedState,
    roi: NormalizedROI,
    similarity_threshold: float = 18.0,
) -> tuple[list[EventItem], dict[str, Any], np.ndarray]:
    """
    Detects kill feed rows and emits a kill event only when a NEW row appears.
    This avoids duplicate events while the same kill row remains visible.
    """
    crop = crop_normalized(frame, roi)
    rows = _extract_kill_rows(crop)

    current_tracks_used: set[int] = set()
    emitted: list[EventItem] = []
    row_debug: list[dict[str, Any]] = []

    for row in rows:
        y_center = row["y_center"]
        signature = row["signature"]

        best_idx = None
        best_score = float("inf")

        for idx, track in enumerate(state.tracks):
            sig_score = _signature_distance(signature, track.signature)
            y_score = abs(y_center - track.y_center)

            if sig_score < best_score and sig_score <= similarity_threshold and y_score <= 0.18:
                best_score = sig_score
                best_idx = idx

        if best_idx is None:
            emitted.append(
                EventItem(
                    timestamp=round(timestamp, 2),
                    event_type="kill",
                    position=None,
                    description="New kill-feed row detected."
                )
            )
            state.tracks.append(
                KillTrack(
                    signature=signature,
                    y_center=y_center,
                    last_seen_ts=timestamp,
                )
            )
            row_debug.append(
                {
                    "bbox": row["bbox"],
                    "status": "NEW",
                    "score": None,
                }
            )
        else:
            state.tracks[best_idx].signature = signature
            state.tracks[best_idx].y_center = y_center
            state.tracks[best_idx].last_seen_ts = timestamp
            current_tracks_used.add(best_idx)
            row_debug.append(
                {
                    "bbox": row["bbox"],
                    "status": "MATCHED",
                    "score": round(best_score, 2),
                }
            )

    # remove stale tracks
    state.tracks = [
        track for track in state.tracks
        if (timestamp - track.last_seen_ts) <= state.ttl_sec
    ]

    debug = {
        "rows": row_debug,
        "row_count": len(rows),
        "track_count": len(state.tracks),
    }
    return emitted, debug, crop


def detect_plant_event(
    frame: np.ndarray,
    timestamp: float,
    state: BannerState,
    roi: NormalizedROI,
    brightness_threshold: float = 0.08,
    cooldown_sec: float = 6.0,
) -> tuple[list[EventItem], dict[str, Any], np.ndarray]:
    """
    Detects a planting banner by looking for a bright, stable UI block in a narrow upper-middle ROI.
    This is heuristic but much more controlled than using the whole screen center.
    """
    crop = crop_normalized(frame, roi)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    bright_ratio = float((gray > 160).mean())
    active_now = bright_ratio >= brightness_threshold

    emitted: list[EventItem] = []
    if active_now and not state.active and (timestamp - state.last_emit_ts) >= cooldown_sec:
        emitted.append(
            EventItem(
                timestamp=round(timestamp, 2),
                event_type="plant",
                position=None,
                description="Plant banner activated."
            )
        )
        state.last_emit_ts = timestamp

    state.active = active_now

    debug = {
        "bright_ratio": round(bright_ratio, 4),
        "active": active_now,
    }
    return emitted, debug, crop


def _extract_kill_rows(crop: np.ndarray) -> list[dict[str, Any]]:
    if crop.size == 0:
        return []

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    white_mask = cv2.inRange(gray, np.array([180]), np.array([255]))
    cyan_mask = cv2.inRange(hsv, np.array([70, 40, 80]), np.array([105, 255, 255]))
    red1 = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([12, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([168, 60, 60]), np.array([180, 255, 255]))

    mask = cv2.bitwise_or(white_mask, cyan_mask)
    mask = cv2.bitwise_or(mask, red1)
    mask = cv2.bitwise_or(mask, red2)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = crop.shape[:2]
    rows: list[dict[str, Any]] = []

    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)

        if bw < int(w * 0.22):
            continue
        if bh < max(8, int(h * 0.05)) or bh > int(h * 0.50):
            continue

        pad = 4
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + bw + pad)
        y2 = min(h, y + bh + pad)

        row_img = crop[y1:y2, x1:x2]
        signature = _make_signature(row_img)

        rows.append(
            {
                "bbox": (x1, y1, x2, y2),
                "y_center": (y1 + y2) / 2 / h,
                "signature": signature,
            }
        )

    rows.sort(key=lambda item: item["bbox"][1])
    return rows


def _make_signature(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (48, 12), interpolation=cv2.INTER_AREA)
    normalized = cv2.normalize(resized, np.empty_like(resized), 0, 255, cv2.NORM_MINMAX)
    return normalized.astype(np.float32)


def _signature_distance(sig1: np.ndarray, sig2: np.ndarray) -> float:
    if sig1.shape != sig2.shape:
        return 9999.0
    return float(np.mean(np.abs(sig1 - sig2)))