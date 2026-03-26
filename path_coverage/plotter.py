from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .analysis import CoverageMetricResolver
from .charts import SingleCoverageLineChart, StrategyComparisonLineChart, StrategyScoreCumulativeChart
from .common import natural_label_key
from .models import AnalysisResult, CoverageMetric, CoveragePoint, CoverageTotals


CHART_METRIC_ORDER: tuple[CoverageMetric, ...] = (
    CoverageMetric.STATE_COVERAGE,
    CoverageMetric.TRANSITION_COVERAGE,
    CoverageMetric.STATE_COVERAGE_RATIO,
    CoverageMetric.TRANSITION_COVERAGE_RATIO,
)


class CoveragePlotter:
    def __init__(self) -> None:
        self._metric_resolver = CoverageMetricResolver()
        self._single_chart = SingleCoverageLineChart(self._metric_resolver)
        self._comparison_chart = StrategyComparisonLineChart(self._metric_resolver)
        self._score_chart = StrategyScoreCumulativeChart()

    def plot(
        self,
        points: list[CoveragePoint],
        totals: CoverageTotals,
        output_dir: Path,
        file_prefix: str,
    ) -> tuple[Path, Path, Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = AnalysisResult(
            strategy_name="",
            project_name=file_prefix,
            sorted_paths=[],
            coverage_points=points,
            totals=totals,
        )
        chart_paths = [
            self._single_chart.render(result, metric, output_dir / f"{file_prefix}_{metric.value}.png")
            for metric in CHART_METRIC_ORDER
        ]
        return tuple(chart_paths)  # type: ignore[return-value]

    def plot_strategy_comparison(
        self,
        project_name: str,
        strategy_results: Mapping[str, AnalysisResult],
        output_dir: Path,
    ) -> tuple[Path, Path, Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        chart_paths = [
            self._comparison_chart.render(
                project_name,
                strategy_results,
                metric,
                output_dir / f"{project_name}_strategy_{metric.value}.png",
            )
            for metric in CHART_METRIC_ORDER
        ]
        return tuple(chart_paths)  # type: ignore[return-value]

    def plot_strategy_score_cumulative(
        self,
        project_labels: list[str],
        strategy_cumulative_scores: Mapping[str, list[int]],
        output_file: Path,
    ) -> Path:
        return self._score_chart.render(project_labels, strategy_cumulative_scores, output_file)

    def _natural_label_key(self, label: str) -> tuple[object, ...]:
        return natural_label_key(label)