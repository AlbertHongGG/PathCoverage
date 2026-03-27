from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from .base import BaseChart
from .common import build_comparison_palette, save_and_close
from ..analysis.metrics import CoverageMetricResolver
from ..models import ComparisonScatterDataset, ComparisonScatterPoint, CoverageMetric, ProjectScatterDataset, ProjectScatterPoint


class TransitionCoveragePathLengthScatterChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(
        self,
        dataset: ProjectScatterDataset,
        metric: CoverageMetric,
        output_file: Path,
    ) -> Path:
        palette = build_comparison_palette(len(dataset.strategy_points))
        fig, ax = plt.subplots(figsize=(12, 7))

        x_values = [self._resolve_x_value(point, metric) for point in dataset.strategy_points]
        y_values = [point.average_path_length for point in dataset.strategy_points]
        for index, point in enumerate(dataset.strategy_points):
            x_value = self._resolve_x_value(point, metric)
            ax.scatter(
                x_value,
                point.average_path_length,
                color=palette[index],
                s=80,
                label=point.strategy_name,
                alpha=0.9,
            )
            ax.annotate(
                point.strategy_name,
                (x_value, point.average_path_length),
                textcoords="offset points",
                xytext=(6, 6),
                ha="left",
                va="bottom",
                fontsize=9,
                color=palette[index],
            )

        ax.set_title(self._metric_resolver.scatter_title(metric, dataset.project_name, dataset.path_limit), pad=20)
        ax.set_xlabel(self._metric_resolver.y_label(metric))
        ax.set_ylabel("Average Path Length")
        ax.spines[["top", "right"]].set_visible(False)
        if x_values:
            max_x = max(x_values)
            ax.set_xlim(0, max_x * 1.1 if max_x else 1.0)
            if self._metric_resolver.is_ratio(metric):
                ax.set_xlim(0, 1.05)
        if y_values:
            max_y = max(y_values)
            ax.set_ylim(0, max_y * 1.15 if max_y else 1.0)
        ax.legend(title="Strategy", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
        save_and_close(fig, output_file)
        return output_file

    def _resolve_x_value(self, point: ProjectScatterPoint, metric: CoverageMetric) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return float(point.state_coverage)
        if metric == CoverageMetric.STATE_COVERAGE_RATIO:
            return point.state_coverage_ratio
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return float(point.transition_coverage)
        return point.transition_coverage_ratio


class ComparisonAveragePathLengthScatterChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(
        self,
        dataset: ComparisonScatterDataset,
        metric: CoverageMetric,
        output_file: Path,
    ) -> Path:
        palette = build_comparison_palette(len(dataset.strategy_points))
        fig, ax = plt.subplots(figsize=(12, 7))

        x_values = [self._resolve_x_value(point, metric) for point in dataset.strategy_points]
        y_values = [point.average_path_length_average for point in dataset.strategy_points]
        for index, point in enumerate(dataset.strategy_points):
            x_value = self._resolve_x_value(point, metric)
            ax.scatter(
                x_value,
                point.average_path_length_average,
                color=palette[index],
                s=80,
                label=point.strategy_name,
                alpha=0.9,
            )
            ax.annotate(
                point.strategy_name,
                (x_value, point.average_path_length_average),
                textcoords="offset points",
                xytext=(6, 6),
                ha="left",
                va="bottom",
                fontsize=9,
                color=palette[index],
            )

        ax.set_title(
            f"Average {self._metric_resolver.display_name(metric)} vs Average Path Length Across Projects "
            f"(Top {dataset.path_limit} Paths Cap)",
            pad=20,
        )
        ax.set_xlabel(f"Average {self._metric_resolver.y_label(metric)}")
        ax.set_ylabel("Average Path Length")
        ax.spines[["top", "right"]].set_visible(False)
        if x_values:
            max_x = max(x_values)
            ax.set_xlim(0, max_x * 1.1 if max_x else 1.0)
            if self._metric_resolver.is_ratio(metric):
                ax.set_xlim(0, 1.05)
        if y_values:
            max_y = max(y_values)
            ax.set_ylim(0, max_y * 1.15 if max_y else 1.0)
        ax.legend(title="Strategy", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
        save_and_close(fig, output_file)
        return output_file

    def _resolve_x_value(self, point: ComparisonScatterPoint, metric: CoverageMetric) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return point.state_coverage_average
        if metric == CoverageMetric.STATE_COVERAGE_RATIO:
            return point.state_coverage_ratio_average
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return point.transition_coverage_average
        return point.transition_coverage_ratio_average