from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from adjustText import adjust_text

from .base import BaseChart
from .common import build_comparison_palette, save_and_close
from ..analysis.metrics import CoverageMetricResolver
from ..models import ComparisonScatterDataset, ComparisonScatterPoint, CoverageMetric, ProjectScatterDataset, ProjectScatterPoint


def _pareto_frontier_indices(x_values: list[float], y_values: list[float]) -> set[int]:
    frontier_indices: set[int] = set()
    for candidate_index, (candidate_x, candidate_y) in enumerate(zip(x_values, y_values)):
        dominated = False
        for other_index, (other_x, other_y) in enumerate(zip(x_values, y_values)):
            if candidate_index == other_index:
                continue

            if other_x >= candidate_x and other_y <= candidate_y and (
                other_x > candidate_x or other_y < candidate_y
            ):
                dominated = True
                break

        if not dominated:
            frontier_indices.add(candidate_index)

    return frontier_indices


class TransitionCoveragePathLengthScatterChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(
        self,
        dataset: ProjectScatterDataset,
        metric: CoverageMetric,
        output_file: Path,
        emphasize_frontier: bool = False,
    ) -> Path:
        palette = build_comparison_palette(len(dataset.strategy_points))
        fig, ax = plt.subplots(figsize=(12, 7))

        x_values = [self._resolve_x_value(point, metric) for point in dataset.strategy_points]
        y_values = [point.average_path_length for point in dataset.strategy_points]
        frontier_indices = _pareto_frontier_indices(x_values, y_values) if emphasize_frontier else set(
            range(len(dataset.strategy_points))
        )
        texts = []
        for index, point in enumerate(dataset.strategy_points):
            x_value = self._resolve_x_value(point, metric)
            is_frontier = index in frontier_indices
            point_alpha = 0.9 if is_frontier else 0.18
            label_alpha = 0.82 if is_frontier else 0.48
            label_text_alpha = 1.0 if is_frontier else 0.72
            label_color = palette[index] if is_frontier else "#6B7280"
            label_edge_color = palette[index] if is_frontier else "#9CA3AF"
            label_face_color = "white" if is_frontier else "#F3F4F6"
            ax.scatter(
                x_value,
                point.average_path_length,
                color=palette[index],
                s=80,
                label=point.strategy_name,
                alpha=point_alpha,
                zorder=3 if is_frontier else 1,
            )
            if emphasize_frontier and not is_frontier:
                ax.scatter(
                    x_value,
                    point.average_path_length,
                    color="#6B7280",
                    marker="x",
                    s=96,
                    linewidths=1.6,
                    alpha=0.9,
                    zorder=4,
                )
            ax.annotate(
                point.strategy_name,
                (x_value, point.average_path_length),
                textcoords="offset points",
                xytext=(6, 6),
                ha="left",
                va="bottom",
                fontsize=9,
                color=label_color,
                alpha=label_text_alpha,
            )
            texts.append(
                ax.text(
                    x_value,
                    point.average_path_length,
                    self._build_label_text(point.strategy_name, x_value, point.average_path_length, metric),
                    fontsize=8.5,
                    color=label_color,
                    ha="left",
                    va="bottom",
                    alpha=label_text_alpha,
                    bbox={
                        "boxstyle": "round,pad=0.22",
                        "facecolor": label_face_color,
                        "edgecolor": label_edge_color,
                        "alpha": label_alpha,
                        "linewidth": 0.8,
                    },
                )
            )

        if emphasize_frontier:
            self._draw_frontier(ax, x_values, y_values, frontier_indices)
        ax.set_title(
            self._build_title(metric, dataset.project_name, dataset.path_limit, emphasize_frontier),
            pad=20,
        )
        ax.set_xlabel(self._metric_resolver.y_label(metric))
        ax.set_ylabel("Average Path Length")
        ax.spines[["top", "right"]].set_visible(False)
        self._set_axis_limits(ax, x_values, y_values, metric)
        self._adjust_labels(ax, texts, x_values, y_values)
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

    def _build_label_text(
        self,
        strategy_name: str,
        x_value: float,
        y_value: float,
        metric: CoverageMetric,
    ) -> str:
        return (
            f"{strategy_name}\n"
            f"x={self._format_value(x_value, metric)}\n"
            f"y={self._format_number(y_value)}"
        )

    def _build_title(
        self,
        metric: CoverageMetric,
        project_name: str,
        path_limit: int,
        emphasize_frontier: bool,
    ) -> str:
        title = self._metric_resolver.scatter_title(metric, project_name, path_limit)
        if not emphasize_frontier:
            return title
        return f"{title} - Pareto Frontier Highlighted"

    def _format_value(self, value: float, metric: CoverageMetric) -> str:
        return self._format_number(value, ratio=self._metric_resolver.is_ratio(metric))

    def _format_number(self, value: float, ratio: bool = False) -> str:
        if ratio:
            return f"{value:.3f}"
        rounded_value = round(value)
        if abs(value - rounded_value) < 1e-9:
            return f"{int(rounded_value)}"
        return f"{value:.2f}"

    def _set_axis_limits(
        self,
        ax,
        x_values: list[float],
        y_values: list[float],
        metric: CoverageMetric,
    ) -> None:
        if x_values:
            max_x = max(x_values)
            ax.set_xlim(0, max_x * 1.1 if max_x else 1.0)
            if self._metric_resolver.is_ratio(metric):
                ax.set_xlim(0, 1.05)
        if y_values:
            max_y = max(y_values)
            ax.set_ylim(0, max_y * 1.15 if max_y else 1.0)

    def _adjust_labels(
        self,
        ax,
        texts: list,
        x_values: list[float],
        y_values: list[float],
    ) -> None:
        if not texts:
            return

        adjust_text(
            texts,
            x=x_values,
            y=y_values,
            ax=ax,
            expand=(1.15, 1.35),
            force_text=(0.35, 0.45),
            force_static=(0.2, 0.25),
            only_move={"text": "xy", "static": "xy", "explode": "xy", "pull": "xy"},
            arrowprops={
                "arrowstyle": "-",
                "color": "#6B7280",
                "lw": 0.8,
                "alpha": 0.6,
                "shrinkA": 4,
                "shrinkB": 4,
            },
        )

    def _draw_frontier(
        self,
        ax,
        x_values: list[float],
        y_values: list[float],
        frontier_indices: set[int],
    ) -> None:
        if len(frontier_indices) < 2:
            return

        frontier_points = sorted(
            ((x_values[index], y_values[index]) for index in frontier_indices),
            key=lambda point: (point[0], point[1]),
        )
        frontier_x, frontier_y = zip(*frontier_points)
        ax.plot(
            frontier_x,
            frontier_y,
            linestyle="--",
            linewidth=1.2,
            color="#111827",
            alpha=0.7,
            zorder=2,
        )


class ComparisonAveragePathLengthScatterChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()
        self._project_chart = TransitionCoveragePathLengthScatterChart(self._metric_resolver)

    def render(
        self,
        dataset: ComparisonScatterDataset,
        metric: CoverageMetric,
        output_file: Path,
        emphasize_frontier: bool = False,
    ) -> Path:
        palette = build_comparison_palette(len(dataset.strategy_points))
        fig, ax = plt.subplots(figsize=(12, 7))

        x_values = [self._resolve_x_value(point, metric) for point in dataset.strategy_points]
        y_values = [point.average_path_length_average for point in dataset.strategy_points]
        frontier_indices = _pareto_frontier_indices(x_values, y_values) if emphasize_frontier else set(
            range(len(dataset.strategy_points))
        )
        texts = []
        for index, point in enumerate(dataset.strategy_points):
            x_value = self._resolve_x_value(point, metric)
            is_frontier = index in frontier_indices
            point_alpha = 0.9 if is_frontier else 0.18
            label_alpha = 0.82 if is_frontier else 0.48
            label_text_alpha = 1.0 if is_frontier else 0.72
            label_color = palette[index] if is_frontier else "#6B7280"
            label_edge_color = palette[index] if is_frontier else "#9CA3AF"
            label_face_color = "white" if is_frontier else "#F3F4F6"
            ax.scatter(
                x_value,
                point.average_path_length_average,
                color=palette[index],
                s=80,
                label=point.strategy_name,
                alpha=point_alpha,
                zorder=3 if is_frontier else 1,
            )
            if emphasize_frontier and not is_frontier:
                ax.scatter(
                    x_value,
                    point.average_path_length_average,
                    color="#6B7280",
                    marker="x",
                    s=96,
                    linewidths=1.6,
                    alpha=0.9,
                    zorder=4,
                )
            texts.append(
                ax.text(
                    x_value,
                    point.average_path_length_average,
                    self._project_chart._build_label_text(
                        point.strategy_name,
                        x_value,
                        point.average_path_length_average,
                        metric,
                    ),
                    fontsize=8.5,
                    color=label_color,
                    ha="left",
                    va="bottom",
                    alpha=label_text_alpha,
                    bbox={
                        "boxstyle": "round,pad=0.22",
                        "facecolor": label_face_color,
                        "edgecolor": label_edge_color,
                        "alpha": label_alpha,
                        "linewidth": 0.8,
                    },
                )
            )

        if emphasize_frontier:
            self._project_chart._draw_frontier(ax, x_values, y_values, frontier_indices)
        ax.set_title(
            self._build_title(dataset, metric, emphasize_frontier),
            pad=20,
        )
        ax.set_xlabel(f"Average {self._metric_resolver.y_label(metric)}")
        ax.set_ylabel("Average Path Length")
        ax.spines[["top", "right"]].set_visible(False)
        self._project_chart._set_axis_limits(ax, x_values, y_values, metric)
        self._project_chart._adjust_labels(ax, texts, x_values, y_values)
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

    def _build_title(
        self,
        dataset: ComparisonScatterDataset,
        metric: CoverageMetric,
        emphasize_frontier: bool,
    ) -> str:
        title = (
            f"Average {self._metric_resolver.display_name(metric)} vs Average Path Length Across Projects "
            f"(Top {dataset.path_limit} Paths Cap)"
        )
        if not emphasize_frontier:
            return title
        return f"{title} - Pareto Frontier Highlighted"