from __future__ import annotations

from collections import Counter

from mcp_server.domain.schemas import MatchEvents, MatchStats, RoundStats, HeatmapData, PositionPoint


def compute_stats(events: MatchEvents) -> tuple[MatchStats, HeatmapData]:
    round_stats: list[RoundStats] = []
    heatmap_points: list[PositionPoint] = []

    for rnd in events.rounds:
        kills = sum(1 for e in rnd.events if e.event_type == "kill")
        plants = sum(1 for e in rnd.events if e.event_type == "plant")
        activity_score = float(len(rnd.events))

        dominant_zone = "mid"
        if rnd.events:
            avg_x = sum(e.position.x for e in rnd.events if e.position) / max(
                1, sum(1 for e in rnd.events if e.position)
            )
            dominant_zone = "A-site" if avg_x > 0.66 else "mid" if avg_x > 0.33 else "B-site"

        round_stats.append(
            RoundStats(
                round_number=rnd.round_number,
                kills=kills,
                plants=plants,
                dominant_zone=dominant_zone,
                activity_score=activity_score,
            )
        )

        for event in rnd.events:
            if event.position:
                heatmap_points.append(
                    PositionPoint(
                        x=event.position.x,
                        y=event.position.y,
                        weight=1,
                    )
                )

    stats = MatchStats(match_id=events.match_id, round_stats=round_stats)
    heatmap = HeatmapData(match_id=events.match_id, map_name=events.map_name, points=heatmap_points)
    return stats, heatmap