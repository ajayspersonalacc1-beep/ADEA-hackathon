"""Base interface for all agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adea.orchestration.state import PipelineState

import logging 
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all workflow agents."""

    @abstractmethod
    def run(self, state: PipelineState) -> PipelineState:
        """Execute the agent against the shared pipeline state."""

        raise NotImplementedError
