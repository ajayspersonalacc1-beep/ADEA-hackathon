"""Pipeline builder utilities for dependency-aware step ordering."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from heapq import heappop, heappush
from typing import Any

from adea.utils.lineage import extract_step_metadata


class PipelineBuilder:
    """Build execution-ready pipeline plans from generated steps."""

    def order_plan(self, pipeline_plan: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of the pipeline plan with steps ordered by dependencies."""

        ordered_plan = deepcopy(pipeline_plan)
        steps = ordered_plan.get("steps", [])
        if not isinstance(steps, list) or len(steps) < 2:
            return ordered_plan

        ordered_plan["steps"] = self._topologically_sort_steps(steps)
        return ordered_plan

    def _topologically_sort_steps(
        self,
        steps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort steps by inferred lineage dependencies when possible."""

        step_metadata = [extract_step_metadata(step) for step in steps]
        producer_map: dict[str, list[int]] = defaultdict(list)

        for index, metadata in enumerate(step_metadata):
            target = metadata.get("target")
            if isinstance(target, str) and target:
                producer_map[target].append(index)

        outgoing_edges: dict[int, set[int]] = defaultdict(set)
        indegree: list[int] = [0] * len(steps)

        for producer_indexes in producer_map.values():
            for left, right in zip(producer_indexes, producer_indexes[1:]):
                if right not in outgoing_edges[left]:
                    outgoing_edges[left].add(right)
                    indegree[right] += 1

        for index, metadata in enumerate(step_metadata):
            sources = metadata.get("sources", [])
            if not isinstance(sources, list):
                continue

            for source in sources:
                for producer_index in producer_map.get(source, []):
                    if producer_index == index:
                        continue
                    if index not in outgoing_edges[producer_index]:
                        outgoing_edges[producer_index].add(index)
                        indegree[index] += 1

        queue: list[int] = []
        for index, degree in enumerate(indegree):
            if degree == 0:
                heappush(queue, index)

        ordered_indexes: list[int] = []
        while queue:
            current_index = heappop(queue)
            ordered_indexes.append(current_index)

            for dependent_index in sorted(outgoing_edges.get(current_index, set())):
                indegree[dependent_index] -= 1
                if indegree[dependent_index] == 0:
                    heappush(queue, dependent_index)

        if len(ordered_indexes) != len(steps):
            return steps

        if ordered_indexes == list(range(len(steps))):
            return steps

        return [steps[index] for index in ordered_indexes]
