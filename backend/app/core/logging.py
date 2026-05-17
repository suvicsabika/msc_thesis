"""Application logging configuration.

This module configures console logging for the FastAPI host application.
"""

import logging
import sys


def configure_logging() -> None:
    """Configure root logging for the backend application.

    The logging configuration writes structured informational and error
    output to standard error, which is useful for service monitoring and
    local development.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )