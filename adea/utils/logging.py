"""Centralized logging configuration."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("fastapi").setLevel(level)