from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path

from .analysis import (
    ComparisonScatterDatasetBuilder,
    CoverageMetricResolver,
    PathCountComparisonBuilder,
    ProjectAnalysisRunner,
    ProjectScatterDatasetBuilder,
    StrategyScoreSummaryBuilder,
)
from .charts import (
    ComparisonAveragePathLengthScatterChart,
    PathCountAverageBarChart,
    SingleCoverageLineChart,
    StrategyComparisonLineChart,
    StrategyScoreCumulativeChart,
    TransitionCoveragePathLengthScatterChart,
)
from .common import DEFAULT_PATH_LIMITS, path_limit_dir_name
from .models import AnalysisResult, CoverageMetric
from .outputs import (
    ComparisonScatterSummaryWriter,
    CoverageSummaryWriter,
    JsonWriter,
    PathCountComparisonSummaryWriter,
    ProjectScatterSummaryWriter,
    SortedPathsWriter,
)


CHART_METRIC_ORDER: tuple[CoverageMetric, ...] = (
    CoverageMetric.STATE_COVERAGE,
    CoverageMetric.TRANSITION_COVERAGE,
    CoverageMetric.STATE_COVERAGE_RATIO,
    CoverageMetric.TRANSITION_COVERAGE_RATIO,
)


class PathCoverageService:
    def __init__(
        self,
        analysis_runner: ProjectAnalysisRunner | None = None,
        metric_resolver: CoverageMetricResolver | None = None,
        sorted_paths_writer: SortedPathsWriter | None = None,
        coverage_summary_writer: CoverageSummaryWriter | None = None,
        json_writer: JsonWriter | None = None,
        path_count_summary_writer: PathCountComparisonSummaryWriter | None = None,
        project_scatter_summary_writer: ProjectScatterSummaryWriter | None = None,
        comparison_scatter_summary_writer: ComparisonScatterSummaryWriter | None = None,
        single_chart: SingleCoverageLineChart | None = None,
        comparison_chart: StrategyComparisonLineChart | None = None,
        score_chart: StrategyScoreCumulativeChart | None = None,
        path_count_chart: PathCountAverageBarChart | None = None,
        path_scatter_chart: TransitionCoveragePathLengthScatterChart | None = None,
        comparison_path_scatter_chart: ComparisonAveragePathLengthScatterChart | None = None,
        path_count_comparison_builder: PathCountComparisonBuilder | None = None,
        project_scatter_builder: ProjectScatterDatasetBuilder | None = None,
        comparison_scatter_builder: ComparisonScatterDatasetBuilder | None = None,
        strategy_score_summary_builder: StrategyScoreSummaryBuilder | None = None,
    ) -> None:
        self._analysis_runner = analysis_runner or ProjectAnalysisRunner()
        self._metric_resolver = metric_resolver or CoverageMetricResolver()
        self._sorted_paths_writer = sorted_paths_writer or SortedPathsWriter()
        self._coverage_summary_writer = coverage_summary_writer or CoverageSummaryWriter()
        self._json_writer = json_writer or JsonWriter()
        self._path_count_summary_writer = path_count_summary_writer or PathCountComparisonSummaryWriter()
        self._project_scatter_summary_writer = project_scatter_summary_writer or ProjectScatterSummaryWriter()
        self._comparison_scatter_summary_writer = (
            comparison_scatter_summary_writer or ComparisonScatterSummaryWriter()
        )
        self._single_chart = single_chart or SingleCoverageLineChart(self._metric_resolver)
        self._comparison_chart = comparison_chart or StrategyComparisonLineChart(self._metric_resolver)
        self._score_chart = score_chart or StrategyScoreCumulativeChart()
        self._path_count_chart = path_count_chart or PathCountAverageBarChart(self._metric_resolver)
        self._path_scatter_chart = path_scatter_chart or TransitionCoveragePathLengthScatterChart(self._metric_resolver)
        self._comparison_path_scatter_chart = (
            comparison_path_scatter_chart or ComparisonAveragePathLengthScatterChart(self._metric_resolver)
        )
        self._path_count_comparison_builder = path_count_comparison_builder or PathCountComparisonBuilder(
            metric_resolver=self._metric_resolver,
        )
        self._project_scatter_builder = project_scatter_builder or ProjectScatterDatasetBuilder()
        self._comparison_scatter_builder = comparison_scatter_builder or ComparisonScatterDatasetBuilder(
            metric_resolver=self._metric_resolver,
        )
        self._strategy_score_summary_builder = strategy_score_summary_builder or StrategyScoreSummaryBuilder(
            metric_resolver=self._metric_resolver,
        )

    def run(
        self,
        strategy_name: str,
        project_name: str,
        graph_file: Path,
        path_files: list[Path],
        output_dir: Path,
        max_paths: int | None = None,
    ) -> AnalysisResult:
        result = self._analysis_runner.analyze(
            strategy_name=strategy_name,
            project_name=project_name,
            graph_file=graph_file,
            path_files=path_files,
            max_paths=max_paths,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        self._sorted_paths_writer.write(result, output_dir)
        self._coverage_summary_writer.write(result, output_dir, max_paths=max_paths)
        self._write_single_strategy_charts(result, output_dir)
        return result

    def write_strategy_comparison(
        self,
        project_name: str,
        strategy_results: Mapping[str, AnalysisResult],
        output_dir: Path,
    ) -> tuple[Path, Path, Path, Path]:
        if not strategy_results:
            raise ValueError(f"No strategy results were provided for project '{project_name}'")

        output_dir.mkdir(parents=True, exist_ok=True)
        chart_paths = [
            self._comparison_chart.render(
                project_name=project_name,
                strategy_results=strategy_results,
                metric=metric,
                output_file=output_dir / f"{project_name}_strategy_{metric.value}.png",
            )
            for metric in CHART_METRIC_ORDER
        ]
        return tuple(chart_paths)  # type: ignore[return-value]

    def write_strategy_score_summary(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
        output_dir: Path,
    ) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload, ordered_project_names, ordered_cumulative_scores = self._strategy_score_summary_builder.build(
            results_by_project
        )
        summary_path = self._json_writer.write(payload, output_dir / "strategy_score_summary.json")
        chart_path = self._score_chart.render(
            project_labels=ordered_project_names,
            strategy_cumulative_scores=ordered_cumulative_scores,
            output_file=output_dir / "strategy_score_cumulative.png",
        )
        return summary_path, chart_path

    def write_path_count_comparisons(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
        output_dir: Path,
        path_limits: tuple[int, ...] = DEFAULT_PATH_LIMITS,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        datasets = self._path_count_comparison_builder.build(results_by_project, path_limits=path_limits)
        datasets_by_limit: dict[int, list] = defaultdict(list)
        for dataset in datasets:
            datasets_by_limit[dataset.path_limit].append(dataset)

        output_paths: list[Path] = []
        metric_order = {metric: index for index, metric in enumerate(CHART_METRIC_ORDER)}
        for path_limit, grouped_datasets in sorted(datasets_by_limit.items()):
            limit_dir = output_dir / path_limit_dir_name(path_limit)
            limit_dir.mkdir(parents=True, exist_ok=True)
            ordered_datasets = sorted(grouped_datasets, key=lambda dataset: metric_order[dataset.metric])
            for dataset in ordered_datasets:
                output_paths.append(
                    self._path_count_chart.render(dataset, limit_dir / f"{dataset.metric.value}.png")
                )
            output_paths.append(
                self._path_count_summary_writer.write(ordered_datasets, limit_dir / "summary.json")
            )

        return output_paths

    def write_project_path_scatters(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
        output_dir: Path,
        path_limits: tuple[int, ...] = DEFAULT_PATH_LIMITS,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        datasets = self._project_scatter_builder.build(results_by_project, path_limits=path_limits)
        output_paths: list[Path] = []
        for dataset in datasets:
            scatter_dir = output_dir / dataset.project_name / path_limit_dir_name(dataset.path_limit)
            scatter_dir.mkdir(parents=True, exist_ok=True)
            for metric in CHART_METRIC_ORDER:
                output_paths.append(
                    self._path_scatter_chart.render(
                        dataset,
                        metric,
                        scatter_dir / f"{metric.value}_vs_average_path_length.png",
                    )
                )
            output_paths.append(
                self._project_scatter_summary_writer.write(dataset, scatter_dir / "summary.json")
            )

        return output_paths

    def write_comparison_path_scatters(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
        output_dir: Path,
        path_limits: tuple[int, ...] = DEFAULT_PATH_LIMITS,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        datasets = self._comparison_scatter_builder.build(results_by_project, path_limits=path_limits)
        output_paths: list[Path] = []
        for dataset in datasets:
            scatter_dir = output_dir / path_limit_dir_name(dataset.path_limit)
            scatter_dir.mkdir(parents=True, exist_ok=True)
            for metric in CHART_METRIC_ORDER:
                output_paths.append(
                    self._comparison_path_scatter_chart.render(
                        dataset,
                        metric,
                        scatter_dir / f"{metric.value}_vs_average_path_length.png",
                    )
                )
            output_paths.append(
                self._comparison_scatter_summary_writer.write(dataset, scatter_dir / "summary.json")
            )

        return output_paths

    def _write_single_strategy_charts(
        self,
        result: AnalysisResult,
        output_dir: Path,
    ) -> tuple[Path, Path, Path, Path]:
        chart_paths = [
            self._single_chart.render(
                result=result,
                metric=metric,
                output_file=output_dir / f"{result.project_name}_{metric.value}.png",
            )
            for metric in CHART_METRIC_ORDER
        ]
        return tuple(chart_paths)  # type: ignore[return-value]