from __future__ import annotations


def register_prompts(mcp) -> None:
    @mcp.prompt
    def summarize_match_tactics(match_id: str, scope: str = "match") -> str:
        """Prompt template for tactical match summarization."""
        return f"""
You are a tactical Valorant analysis assistant.

Your task is to summarize the tactical behavior of match "{match_id}".
Scope: {scope}

Focus on:
- dominant zones
- event density
- round-level trends
- notable kill and plant patterns

Do not invent missing events.
Base your answer strictly on the structured stats and events resources.
""".strip()