from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

from .base import BaseChart
from .common import build_annotation_offsets, build_comparison_palette, save_and_close
from ..analysis.metrics import CoverageMetricResolver
from ..common import natural_label_key
from ..models import AnalysisResult, AverageComparisonDataset, CoverageMetric


class SingleCoverageLineChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(self, result: AnalysisResult, metric: CoverageMetric, output_file: Path) -> Path:
        x_values = [point.path_count for point in result.coverage_points]
        y_values = [
            self._metric_resolver.value_from_point(metric, point, result.totals)
            for point in result.coverage_points
        ]
        total_value = self._metric_resolver.reference_total(metric, result.totals)
        line_color = self._metric_resolver.line_color(metric)

        fig, ax = plt.subplots(figsize=(12, 7))
        sns.lineplot(x=x_values, y=y_values, marker="o", linewidth=2.2, color=line_color, ax=ax)

        for x_value, y_value in zip(x_values, y_values, strict=True):
            ax.annotate(
                self._metric_resolver.format_value(metric, y_value),
                (x_value, y_value),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=9,
                color=line_color,
            )

        reference_label = f"Total = {total_value:.2f}" if self._metric_resolver.is_ratio(metric) else f"Total = {int(total_value)}"
        ax.axhline(total_value, linestyle="--", linewidth=1.2, color="#6B7280", label=reference_label)
        ax.set_title(self._metric_resolver.single_title(metric), pad=20)
        ax.set_xlabel("Number of Paths")
        ax.set_ylabel(self._metric_resolver.y_label(metric))
        if self._metric_resolver.is_ratio(metric):
            ax.set_ylim(0, 1.05)
        ax.legend()
        save_and_close(fig, output_file)
        return output_file


class StrategyComparisonLineChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(
        self,
        project_name: str,
        strategy_results: Mapping[str, AnalysisResult],
        metric: CoverageMetric,
        output_file: Path,
    ) -> Path:
        if not strategy_results:
            raise ValueError(f"No strategy results were provided for project '{project_name}'")

        ordered_results = {
            strategy_name: strategy_results[strategy_name]
            for strategy_name in sorted(strategy_results, key=natural_label_key)
        }
        first_result = next(iter(ordered_results.values()))
        for strategy_name, result in ordered_results.items():
            if result.project_name != project_name:
                raise ValueError(
                    f"Strategy '{strategy_name}' does not belong to project '{project_name}': {result.project_name}"
                )
            if result.totals != first_result.totals:
                raise ValueError(f"Coverage totals do not match for project '{project_name}' across strategies.")

        fig, ax = plt.subplots(figsize=(13, 7))
        palette = build_comparison_palette(len(ordered_results))
        annotation_targets: list[dict[str, object]] = []
        max_path_count = 0
        total_value = self._metric_resolver.reference_total(metric, first_result.totals)

        for index, (strategy_name, result) in enumerate(ordered_results.items()):
            x_values = [point.path_count for point in result.coverage_points]
            y_values = [
                self._metric_resolver.value_from_point(metric, point, result.totals)
                for point in result.coverage_points
            ]
            if not x_values:
                continue

            max_path_count = max(max_path_count, max(x_values))
            ax.plot(
                x_values,
                y_values,
                marker="o",
                markersize=4.5,
                linewidth=2.0,
                color=palette[index],
                label=strategy_name,
                alpha=0.95,
            )

            target_path_count, target_value = self._select_annotation_target(x_values, y_values, total_value)
            annotation_targets.append(
                {
                    "strategy_name": strategy_name,
                    "target_path_count": target_path_count,
                    "target_value": target_value,
                    "label_text": f"{target_path_count}",
                    "color": palette[index],
                }
            )

        if max_path_count == 0:
            raise ValueError("At least one strategy must include coverage points to generate a comparison chart.")

        label_y_offsets = build_annotation_offsets(
            [float(target["target_value"]) for target in annotation_targets]
        )
        for target, label_y_offset in zip(annotation_targets, label_y_offsets, strict=True):
            ax.annotate(
                target["label_text"],
                xy=(float(target["target_path_count"]), float(target["target_value"])),
                xytext=(0, label_y_offset),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="semibold",
                color=target["color"],
            )

        reference_label = f"Total = {total_value:.2f}" if self._metric_resolver.is_ratio(metric) else f"Total = {int(total_value)}"
        ax.axhline(total_value, linestyle="--", linewidth=1.2, color="#6B7280", label=reference_label)
        ax.set_title(self._metric_resolver.comparison_title(metric, project_name), pad=20)
        ax.set_xlabel("Number of Paths")
        ax.set_ylabel(self._metric_resolver.y_label(metric))
        ax.set_xlim(1, max_path_count + 1)
        if self._metric_resolver.is_ratio(metric):
            ax.set_ylim(0, 1.1)
        else:
            ax.set_ylim(0, total_value * 1.1 if total_value else 1.0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(
            0.015,
            0.98,
            f"Dashed line: {reference_label}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            color="#4B5563",
        )
        ax.legend(title="Strategy", loc="lower right", frameon=True)
        save_and_close(fig, output_file)
        return output_file

    def _select_annotation_target(
        self,
        x_values: list[int],
        y_values: list[float],
        total_value: float,
    ) -> tuple[int, float]:
        tolerance = 1e-9
        for path_count, coverage_value in zip(x_values, y_values, strict=True):
            if coverage_value >= total_value - tolerance:
                return path_count, coverage_value
        return x_values[-1], y_values[-1]


class StrategyScoreCumulativeChart(BaseChart):
    def render(
        self,
        project_labels: list[str],
        strategy_cumulative_scores: Mapping[str, list[int]],
        output_file: Path,
    ) -> Path:
        if not project_labels:
            raise ValueError("At least one project label is required to generate the cumulative score chart.")
        if not strategy_cumulative_scores:
            raise ValueError("At least one strategy score series is required to generate the cumulative score chart.")

        ordered_series = {
            strategy_name: strategy_cumulative_scores[strategy_name]
            for strategy_name in sorted(strategy_cumulative_scores, key=natural_label_key)
        }
        palette = build_comparison_palette(len(ordered_series))
        x_positions = list(range(1, len(project_labels) + 1))
        fig, ax = plt.subplots(figsize=(14, 7))
        for index, (strategy_name, cumulative_scores) in enumerate(ordered_series.items()):
            ax.plot(
                x_positions,
                cumulative_scores,
                marker="o",
                markersize=5,
                linewidth=2.0,
                color=palette[index],
                label=strategy_name,
                alpha=0.95,
            )
            if cumulative_scores:
                ax.annotate(
                    f"{cumulative_scores[-1]}",
                    (x_positions[-1], cumulative_scores[-1]),
                    textcoords="offset points",
                    xytext=(8, 0),
                    ha="left",
                    va="center",
                    fontsize=9,
                    color=palette[index],
                )

        ax.set_title("Cumulative Strategy Score by Project", pad=20)
        ax.set_xlabel("Project")
        ax.set_ylabel("Cumulative Score")
        ax.set_xticks(x_positions)
        ax.set_xticklabels([str(index) for index in x_positions])
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(title="Strategy", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
        save_and_close(fig, output_file)
        return output_file


class AverageStrategyComparisonLineChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(self, dataset: AverageComparisonDataset, output_file: Path) -> Path:
        if not dataset.strategy_series:
            raise ValueError("At least one strategy series is required to generate the average comparison chart.")

        ordered_series = sorted(
            dataset.strategy_series,
            key=lambda series: natural_label_key(series.strategy_name),
        )
        fig, ax = plt.subplots(figsize=(13, 7))
        palette = build_comparison_palette(len(ordered_series))
        annotation_targets: list[dict[str, object]] = []
        max_path_count = 0
        total_value = dataset.average_reference_total

        for index, series in enumerate(ordered_series):
            x_values = [point.path_count for point in series.points]
            y_values = [point.average_value for point in series.points]
            if not x_values:
                continue

            max_path_count = max(max_path_count, max(x_values))
            ax.plot(
                x_values,
                y_values,
                marker="o",
                markersize=4.5,
                linewidth=2.0,
                color=palette[index],
                label=series.strategy_name,
                alpha=0.95,
            )

            target_path_count, target_value = self._select_annotation_target(x_values, y_values, total_value)
            annotation_targets.append(
                {
                    "target_path_count": target_path_count,
                    "target_value": target_value,
                    "label_text": f"{target_path_count}",
                    "color": palette[index],
                }
            )

        if max_path_count == 0:
            raise ValueError("At least one strategy must include average coverage points to generate a chart.")

        label_y_offsets = build_annotation_offsets(
            [float(target["target_value"]) for target in annotation_targets]
        )
        for target, label_y_offset in zip(annotation_targets, label_y_offsets, strict=True):
            ax.annotate(
                target["label_text"],
                xy=(float(target["target_path_count"]), float(target["target_value"])),
                xytext=(0, label_y_offset),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="semibold",
                color=target["color"],
            )

        reference_prefix = "Total" if self._metric_resolver.is_ratio(dataset.metric) else "Average Total"
        reference_label = (
            f"{reference_prefix} = {total_value:.2f}"
            if self._metric_resolver.is_ratio(dataset.metric)
            else f"{reference_prefix} = {int(round(total_value))}"
        )
        ax.axhline(total_value, linestyle="--", linewidth=1.2, color="#6B7280", label=reference_label)
        ax.set_title(
            self._metric_resolver.average_comparison_title(
                dataset.metric,
                len(dataset.project_names),
                dataset.max_path_count,
            ),
            pad=20,
        )
        ax.set_xlabel("Number of Paths")
        ax.set_ylabel(f"Average {self._metric_resolver.y_label(dataset.metric)}")
        ax.set_xlim(1, max(dataset.max_path_count, max_path_count) + 1)
        if self._metric_resolver.is_ratio(dataset.metric):
            ax.set_ylim(0, 1.1)
        else:
            ax.set_ylim(0, total_value * 1.1 if total_value else 1.0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(
            0.015,
            0.98,
            "Dashed line: average reachable total across projects",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            color="#4B5563",
        )
        ax.legend(title="Strategy", loc="lower right", frameon=True)
        save_and_close(fig, output_file)
        return output_file

    def _select_annotation_target(
        self,
        x_values: list[int],
        y_values: list[float],
        total_value: float,
    ) -> tuple[int, float]:
        tolerance = 1e-9
        for path_count, coverage_value in zip(x_values, y_values, strict=True):
            if coverage_value >= total_value - tolerance:
                return path_count, coverage_value
        return x_values[-1], y_values[-1]