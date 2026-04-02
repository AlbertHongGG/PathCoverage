from __future__ import annotations

from collections.abc import Mapping

from .metrics import CoverageMetricResolver
from .snapshots import PathLimitSnapshotSelector
from ..common import DEFAULT_PATH_LIMITS, natural_label_key
from ..models import (
    AnalysisResult,
    AverageComparisonDataset,
    AverageComparisonPoint,
    AverageComparisonSeries,
    ComparisonScatterDataset,
    ComparisonScatterPoint,
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


class AverageComparisonDatasetBuilder:
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
    ) -> list[AverageComparisonDataset]:
        ordered_project_names = sorted(results_by_project, key=natural_label_key)
        strategy_names = sorted(
            {
                strategy_name
                for strategy_results in results_by_project.values()
                for strategy_name in strategy_results
            },
            key=natural_label_key,
        )
        max_path_count = max(
            (
                len(result.coverage_points)
                for strategy_results in results_by_project.values()
                for result in strategy_results.values()
            ),
            default=0,
        )
        if max_path_count == 0:
            return []

        datasets: list[AverageComparisonDataset] = []
        for metric in CoverageMetric:
            series_rows: list[AverageComparisonSeries] = []
            for strategy_name in strategy_names:
                points: list[AverageComparisonPoint] = []
                for path_count in range(1, max_path_count + 1):
                    snapshots = []
                    for project_name in ordered_project_names:
                        result = results_by_project[project_name].get(strategy_name)
                        if result is None:
                            continue

                        snapshot = self._snapshot_selector.select(result, path_count)
                        if snapshot is not None:
                            snapshots.append(snapshot)

                    if not snapshots:
                        continue

                    actual_path_counts = {
                        snapshot.project_name: snapshot.actual_path_count for snapshot in snapshots
                    }
                    average_value = sum(
                        self._metric_resolver.value_from_snapshot(metric, snapshot)
                        for snapshot in snapshots
                    ) / len(snapshots)
                    points.append(
                        AverageComparisonPoint(
                            path_count=path_count,
                            average_value=average_value,
                            project_count=len(snapshots),
                            actual_path_counts=actual_path_counts,
                        )
                    )

                if points:
                    series_rows.append(
                        AverageComparisonSeries(
                            strategy_name=strategy_name,
                            points=points,
                        )
                    )

            if not series_rows:
                continue

            datasets.append(
                AverageComparisonDataset(
                    metric=metric,
                    strategy_order=strategy_names,
                    project_names=ordered_project_names,
                    average_reference_total=self._average_reference_total(metric, results_by_project),
                    max_path_count=max_path_count,
                    strategy_series=series_rows,
                )
            )

        return datasets

    def _average_reference_total(
        self,
        metric: CoverageMetric,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
    ) -> float:
        reference_totals = []
        for project_name in sorted(results_by_project, key=natural_label_key):
            strategy_results = results_by_project[project_name]
            if not strategy_results:
                continue

            first_result = next(iter(strategy_results.values()))
            reference_totals.append(
                self._metric_resolver.reference_total(metric, first_result.totals)
            )

        if not reference_totals:
            return 0.0

        return sum(reference_totals) / len(reference_totals)


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


class ComparisonScatterDatasetBuilder:
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
    ) -> list[ComparisonScatterDataset]:
        ordered_project_names = sorted(results_by_project, key=natural_label_key)
        strategy_names = sorted(
            {
                strategy_name
                for strategy_results in results_by_project.values()
                for strategy_name in strategy_results
            },
            key=natural_label_key,
        )

        datasets: list[ComparisonScatterDataset] = []
        for path_limit in path_limits:
            snapshots_by_strategy: dict[str, list] = {strategy_name: [] for strategy_name in strategy_names}
            for project_name in ordered_project_names:
                strategy_results = results_by_project[project_name]
                for strategy_name, result in strategy_results.items():
                    snapshot = self._snapshot_selector.select(result, path_limit)
                    if snapshot is not None:
                        snapshots_by_strategy[strategy_name].append(snapshot)

            strategy_points: list[ComparisonScatterPoint] = []
            for strategy_name in strategy_names:
                snapshots = snapshots_by_strategy[strategy_name]
                if not snapshots:
                    continue

                actual_path_counts = {
                    snapshot.project_name: snapshot.actual_path_count for snapshot in snapshots
                }
                strategy_points.append(
                    ComparisonScatterPoint(
                        strategy_name=strategy_name,
                        state_coverage_average=self._average_metric(CoverageMetric.STATE_COVERAGE, snapshots),
                        state_coverage_ratio_average=self._average_metric(
                            CoverageMetric.STATE_COVERAGE_RATIO,
                            snapshots,
                        ),
                        transition_coverage_average=self._average_metric(
                            CoverageMetric.TRANSITION_COVERAGE,
                            snapshots,
                        ),
                        transition_coverage_ratio_average=self._average_metric(
                            CoverageMetric.TRANSITION_COVERAGE_RATIO,
                            snapshots,
                        ),
                        average_path_length_average=sum(
                            snapshot.average_path_length for snapshot in snapshots
                        )
                        / len(snapshots),
                        project_count=len(snapshots),
                        actual_path_counts=actual_path_counts,
                    )
                )

            if not strategy_points:
                continue

            datasets.append(
                ComparisonScatterDataset(
                    path_limit=path_limit,
                    strategy_order=strategy_names,
                    project_names=ordered_project_names,
                    strategy_points=strategy_points,
                )
            )

        return datasets

    def _average_metric(self, metric: CoverageMetric, snapshots: list) -> float:
        return sum(self._metric_resolver.value_from_snapshot(metric, snapshot) for snapshot in snapshots) / len(snapshots)