"""Monitoring API routes."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def monitor_pipeline() -> dict[str, str]:
    """Placeholder route for monitoring workflow access."""

    return {"message": "Monitoring workflow trigger placeholder"}
