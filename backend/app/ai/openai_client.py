"""OpenAI integration for ticket triage.

This module belongs to the Host-side AI layer. It calls the OpenAI Responses API
and returns structured ticket triage decisions to the application workflow.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from app.ai.prompts import TRIAGE_SYSTEM_PROMPT, build_ticket_triage_prompt
from app.ai.schemas import TicketTriageDecision


logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def get_openai_client() -> OpenAI:
    """Create an OpenAI client using configured credentials."""

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_ADMIN_KEY")
    return OpenAI(api_key=api_key)


def get_analysis_model() -> str:
    """Return the OpenAI model name to use for ticket analysis."""

    return os.getenv("OPENAI_MODEL", "gpt-4.1-nano")


def analyze_ticket_with_openai(ticket_id: str, ticket_json: str) -> TicketTriageDecision:
    model = get_analysis_model()
    client = get_openai_client()

    logger.info(
        "Sending ticket triage request to OpenAI | ticket_id=%s | model=%s",
        ticket_id,
        model,
    )

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": TRIAGE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_ticket_triage_prompt(ticket_json),
            },
        ],
        text_format=TicketTriageDecision,
    )

    usage = getattr(response, "usage", None)

    if usage is not None:
        logger.info(
            "OpenAI response received | ticket_id=%s | response_id=%s | input_tokens=%s | output_tokens=%s | total_tokens=%s",
            ticket_id,
            getattr(response, "id", None),
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
            getattr(usage, "total_tokens", None),
        )
    else:
        logger.info(
            "OpenAI response received | ticket_id=%s | response_id=%s | usage=unavailable",
            ticket_id,
            getattr(response, "id", None),
        )

    if response.output_parsed is None:
        logger.error(
            "OpenAI response did not contain parsed structured output | ticket_id=%s",
            ticket_id,
        )
        raise RuntimeError("OpenAI response did not contain parsed structured output.")

    logger.info(
        "OpenAI structured triage parsed | ticket_id=%s | category=%s | sentiment=%s | priority=%s",
        ticket_id,
        response.output_parsed.category,
        response.output_parsed.sentiment,
        response.output_parsed.priority,
    )

    return response.output_parsed