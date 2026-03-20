"""Optimization API routes."""

from fastapi import APIRouter


router = APIRouter()


@router.post("/")
def optimize_pipeline() -> dict[str, str]:
    """Placeholder route for optimization workflow access."""

    return {"message": "Optimization workflow trigger placeholder"}
