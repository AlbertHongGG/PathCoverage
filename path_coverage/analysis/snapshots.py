from __future__ import annotations

from ..models import AnalysisResult, CoverageSnapshot


class PathStatisticsBuilder:
    def average_path_length(self, result: AnalysisResult, path_limit: int) -> tuple[float, int]:
        actual_path_count = min(path_limit, len(result.sorted_paths))
        if actual_path_count == 0:
            return 0.0, 0

        total_path_length = sum(len(path.edge_ids) for path in result.sorted_paths[:actual_path_count])
        return total_path_length / actual_path_count, actual_path_count


class PathLimitSnapshotSelector:
    def __init__(self, path_statistics_builder: PathStatisticsBuilder | None = None) -> None:
        self._path_statistics_builder = path_statistics_builder or PathStatisticsBuilder()

    def select(self, result: AnalysisResult, path_limit: int) -> CoverageSnapshot | None:
        if not result.coverage_points:
            return None

        actual_path_count = min(path_limit, len(result.coverage_points))
        if actual_path_count == 0:
            return None

        point = result.coverage_points[actual_path_count - 1]
        average_path_length, _ = self._path_statistics_builder.average_path_length(result, path_limit)
        total_states = result.totals.total_states
        total_transitions = result.totals.total_transitions
        return CoverageSnapshot(
            strategy_name=result.strategy_name,
            project_name=result.project_name,
            path_limit=path_limit,
            actual_path_count=actual_path_count,
            covered_states=point.covered_states,
            state_coverage_ratio=(point.covered_states / total_states) if total_states else 0.0,
            covered_transitions=point.covered_transitions,
            transition_coverage_ratio=(point.covered_transitions / total_transitions) if total_transitions else 0.0,
            average_path_length=average_path_length,
        )