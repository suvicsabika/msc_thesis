"""REST endpoint for checking service availability."""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return the service status and version."""

    return {
        "status": "ok",
        "service": "mcp-ticket-analyzer-api",
        "version": "2.2.0",  # Second Semester - 2nd version (based on the commits)
    }