from __future__ import annotations

from .models import CoveragePoint, CoverageTotals, RuntimeGraph


class CoverageCalculator:
    def calculate(self, ordered_edge_ids: list[list[str]], graph: RuntimeGraph) -> tuple[list[CoveragePoint], CoverageTotals]:
        covered_states: set[str] = set()
        covered_transitions: set[str] = set()
        points: list[CoveragePoint] = []

        for index, edge_ids in enumerate(ordered_edge_ids, start=1):
            for edge_id in edge_ids:
                edge = graph.edges_by_id[edge_id]
                covered_transitions.add(edge.id)
                covered_states.add(edge.from_state_id)
                covered_states.add(edge.to_state_id)

            points.append(
                CoveragePoint(
                    path_count=index,
                    covered_states=len(covered_states),
                    covered_transitions=len(covered_transitions),
                )
            )

        totals = CoverageTotals(
            total_states=len(graph.state_ids),
            total_transitions=len(graph.transition_ids),
        )
        return points, totals