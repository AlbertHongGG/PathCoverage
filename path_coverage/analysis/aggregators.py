from __future__ import annotations

from collections.abc import Mapping

from .metrics import CoverageMetricResolver
from .snapshots import PathLimitSnapshotSelector
from ..common import DEFAULT_PATH_LIMITS, natural_label_key
from ..models import (
    AnalysisResult,
    CoverageMetric,
    PathCountComparisonDataset,
    PathCountComparisonRow,
    ProjectScatterDataset,
    ProjectScatterPoint,
)


class PathCountComparisonBuilder:
    def __init__(
        self,
        snapshot_selector: PathLimitSnapshotSelector | None = None,
        metric_resolver: CoverageMetricResolver | None = None,
    ) -> None:
        self._snapshot_selector = snapshot_selector or PathLimitSnapshotSelector()
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def build(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
        path_limits: tuple[int, ...] = DEFAULT_PATH_LIMITS,
    ) -> list[PathCountComparisonDataset]:
        ordered_project_names = sorted(results_by_project, key=natural_label_key)
        strategy_names = sorted(
            {
                strategy_name
                for strategy_results in results_by_project.values()
                for strategy_name in strategy_results
            },
            key=natural_label_key,
        )

        datasets: list[PathCountComparisonDataset] = []
        for path_limit in path_limits:
            snapshots_by_strategy: dict[str, list] = {strategy_name: [] for strategy_name in strategy_names}
            for project_name in ordered_project_names:
                strategy_results = results_by_project[project_name]
                for strategy_name, result in strategy_results.items():
                    snapshot = self._snapshot_selector.select(result, path_limit)
                    if snapshot is not None:
                        snapshots_by_strategy[strategy_name].append(snapshot)

            for metric in CoverageMetric:
                rows: list[PathCountComparisonRow] = []
                for strategy_name in strategy_names:
                    snapshots = snapshots_by_strategy[strategy_name]
                    if not snapshots:
                        continue

                    project_values = {
                        snapshot.project_name: self._metric_resolver.value_from_snapshot(metric, snapshot)
                        for snapshot in snapshots
                    }
                    average_value = sum(project_values.values()) / len(project_values)
                    rows.append(
                        PathCountComparisonRow(
                            strategy_name=strategy_name,
                            average_value=average_value,
                            project_count=len(project_values),
                            actual_path_counts=[snapshot.actual_path_count for snapshot in snapshots],
                            project_values=project_values,
                        )
                    )

                datasets.append(
                    PathCountComparisonDataset(
                        path_limit=path_limit,
                        metric=metric,
                        strategy_order=strategy_names,
                        project_names=ordered_project_names,
                        strategy_rows=rows,
                    )
                )

        return datasets


class ProjectScatterDatasetBuilder:
    def __init__(self, snapshot_selector: PathLimitSnapshotSelector | None = None) -> None:
        self._snapshot_selector = snapshot_selector or PathLimitSnapshotSelector()

    def build(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
        path_limits: tuple[int, ...] = DEFAULT_PATH_LIMITS,
    ) -> list[ProjectScatterDataset]:
        datasets: list[ProjectScatterDataset] = []
        for project_name in sorted(results_by_project, key=natural_label_key):
            strategy_results = results_by_project[project_name]
            ordered_strategy_names = sorted(strategy_results, key=natural_label_key)
            for path_limit in path_limits:
                points: list[ProjectScatterPoint] = []
                for strategy_name in ordered_strategy_names:
                    snapshot = self._snapshot_selector.select(strategy_results[strategy_name], path_limit)
                    if snapshot is None:
                        continue

                    points.append(
                        ProjectScatterPoint(
                            strategy_name=strategy_name,
                            state_coverage=snapshot.covered_states,
                            state_coverage_ratio=snapshot.state_coverage_ratio,
                            transition_coverage=snapshot.covered_transitions,
                            transition_coverage_ratio=snapshot.transition_coverage_ratio,
                            average_path_length=snapshot.average_path_length,
                            actual_path_count_used=snapshot.actual_path_count,
                        )
                    )

                if not points:
                    continue

                datasets.append(
                    ProjectScatterDataset(
                        project_name=project_name,
                        path_limit=path_limit,
                        strategy_points=points,
                    )
                )

        return datasets