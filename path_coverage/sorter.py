from __future__ import annotations

from functools import cmp_to_key

from .models import AggregatedPath, CandidateScore, PlannerCandidate, RuntimeEdge, RuntimeGraph


class PathCandidateSorter:
    def sort(self, paths: list[AggregatedPath], graph: RuntimeGraph) -> list[AggregatedPath]:
        candidates = [
            candidate
            for candidate in (self._build_candidate(path, graph, set(), set()) for path in paths)
            if candidate is not None
        ]

        prioritized = self._prioritize_candidates(candidates)
        seen_signatures: set[str] = set()
        covered_edge_ids: set[str] = set()
        covered_node_ids: set[str] = set()
        remaining = [candidate for candidate in prioritized if candidate.signature not in seen_signatures]
        sorted_paths: list[AggregatedPath] = []

        while remaining:
            remaining.sort(
                key=cmp_to_key(
                    lambda left, right: self._compare_candidate_scores(
                        left,
                        right,
                        covered_edge_ids,
                        covered_node_ids,
                        set(),
                    )
                )
            )

            candidate = remaining.pop(0)
            if candidate.signature in seen_signatures:
                continue

            seen_signatures.add(candidate.signature)
            sorted_paths.append(candidate.path)

            for edge in candidate.edges:
                covered_edge_ids.add(edge.id)
                covered_node_ids.add(edge.from_state_id)
                covered_node_ids.add(edge.to_state_id)

        return sorted_paths

    def _build_candidate(
        self,
        path: AggregatedPath,
        graph: RuntimeGraph,
        walked_edge_ids: set[str],
        walked_node_ids: set[str],
    ) -> PlannerCandidate | None:
        if not path.edge_ids:
            return None

        edges: list[RuntimeEdge] = []
        for edge_id in path.edge_ids:
            edge = graph.edges_by_id.get(edge_id)
            if edge is None:
                return None
            edges.append(edge)

        first_edge = edges[0]
        if first_edge.from_diagram_id != "page_entry":
            return None
        if first_edge.from_state_id != graph.entry_state_id:
            return None
        if not self._is_connected(edges):
            return None

        new_edge_ids = [edge.id for edge in edges if edge.id not in walked_edge_ids]
        new_node_ids: set[str] = set()
        touched_node_ids: set[str] = set()

        for edge in edges:
            touched_node_ids.add(edge.from_state_id)
            touched_node_ids.add(edge.to_state_id)
            if edge.from_state_id not in walked_node_ids:
                new_node_ids.add(edge.from_state_id)
            if edge.to_state_id not in walked_node_ids:
                new_node_ids.add(edge.to_state_id)

        return PlannerCandidate(
            path=path,
            edges=edges,
            signature=path.signature,
            path_length=len(edges),
            new_edge_ids=new_edge_ids,
            new_node_ids=list(new_node_ids),
            touched_node_ids=list(touched_node_ids),
            new_edge_count=len(new_edge_ids),
            new_node_count=len(new_node_ids),
            has_new_coverage=bool(new_edge_ids or new_node_ids),
        )

    def _prioritize_candidates(self, candidates: list[PlannerCandidate]) -> list[PlannerCandidate]:
        new_coverage_candidates = [candidate for candidate in candidates if candidate.has_new_coverage]
        return new_coverage_candidates if new_coverage_candidates else candidates

    def _score_candidate(
        self,
        candidate: PlannerCandidate,
        covered_edge_ids: set[str],
        covered_node_ids: set[str],
        walked_edge_ids: set[str],
    ) -> CandidateScore:
        incremental_new_edge_count = sum(1 for edge_id in candidate.new_edge_ids if edge_id not in covered_edge_ids)
        incremental_new_node_count = sum(1 for node_id in candidate.new_node_ids if node_id not in covered_node_ids)

        first_fresh_index = -1
        for index, edge in enumerate(candidate.edges):
            if (
                edge.id not in covered_edge_ids
                or edge.from_state_id not in covered_node_ids
                or edge.to_state_id not in covered_node_ids
            ):
                first_fresh_index = index + 1
                break

        return CandidateScore(
            incremental_new_edge_count=incremental_new_edge_count,
            incremental_new_node_count=incremental_new_node_count,
            first_fresh_step_index=first_fresh_index if first_fresh_index != -1 else float("inf"),
            touched_node_count=len(candidate.touched_node_ids),
            historical_overlap_count=sum(1 for edge in candidate.edges if edge.id in walked_edge_ids),
            path_length=candidate.path_length,
        )

    def _compare_candidate_scores(
        self,
        left: PlannerCandidate,
        right: PlannerCandidate,
        covered_edge_ids: set[str],
        covered_node_ids: set[str],
        walked_edge_ids: set[str],
    ) -> int:
        left_score = self._score_candidate(left, covered_edge_ids, covered_node_ids, walked_edge_ids)
        right_score = self._score_candidate(right, covered_edge_ids, covered_node_ids, walked_edge_ids)

        if left_score.incremental_new_edge_count != right_score.incremental_new_edge_count:
            return right_score.incremental_new_edge_count - left_score.incremental_new_edge_count
        if left_score.incremental_new_node_count != right_score.incremental_new_node_count:
            return right_score.incremental_new_node_count - left_score.incremental_new_node_count
        if left_score.first_fresh_step_index != right_score.first_fresh_step_index:
            return -1 if left_score.first_fresh_step_index < right_score.first_fresh_step_index else 1
        if left_score.path_length != right_score.path_length:
            return right_score.path_length - left_score.path_length
        if left_score.touched_node_count != right_score.touched_node_count:
            return right_score.touched_node_count - left_score.touched_node_count
        if left_score.historical_overlap_count != right_score.historical_overlap_count:
            return left_score.historical_overlap_count - right_score.historical_overlap_count

        left_signature = left.signature
        right_signature = right.signature
        if left_signature < right_signature:
            return -1
        if left_signature > right_signature:
            return 1
        return 0

    def _is_connected(self, edges: list[RuntimeEdge]) -> bool:
        for index in range(1, len(edges)):
            if edges[index - 1].to_state_id != edges[index].from_state_id:
                return False
        return True