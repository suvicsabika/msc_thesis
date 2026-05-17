from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "mcp-ticket-analyzer-api",
        "version": "0.1.0",
    }