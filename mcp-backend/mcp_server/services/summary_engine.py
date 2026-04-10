from __future__ import annotations

from mcp_server.domain.schemas import MatchStats, SummaryResponse


def generate_summary(stats: MatchStats, scope: str = "match", round_number: int | None = None) -> SummaryResponse:
    if scope == "round" and round_number is not None:
        selected = next((r for r in stats.round_stats if r.round_number == round_number), None)
        if not selected:
            return SummaryResponse(
                match_id=stats.match_id,
                scope="round",
                summary=f"Round {round_number} was not found."
            )

        summary = (
            f"Round {selected.round_number}: {selected.kills} kill, "
            f"{selected.plants} plant, dominant zone: {selected.dominant_zone}, "
            f"activity score: {selected.activity_score:.1f}."
        )
        return SummaryResponse(match_id=stats.match_id, scope="round", summary=summary)

    total_rounds = len(stats.round_stats)
    total_kills = sum(r.kills for r in stats.round_stats)
    total_plants = sum(r.plants for r in stats.round_stats)

    dominant_zone = "unknown"
    if stats.round_stats:
        dominant_zone = max(
            stats.round_stats,
            key=lambda r: r.activity_score
        ).dominant_zone

    summary = (
        f"The match contains {total_rounds} analyzed rounds, {total_kills} kill events, "
        f"and {total_plants} plant events. The most active dominant zone across the analyzed "
        f"rounds was {dominant_zone}."
    )
    return SummaryResponse(match_id=stats.match_id, scope="match", summary=summary)