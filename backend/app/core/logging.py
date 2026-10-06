"""Application logging configuration.

This module configures console logging for the FastAPI host application.
"""

import logging
import sys


def configure_logging() -> None:
    """Configure root logging for the backend application."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
