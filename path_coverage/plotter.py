from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
import re

import matplotlib.pyplot as plt
import seaborn as sns

from .models import AnalysisResult, CoveragePoint, CoverageTotals


class CoveragePlotter:
    _COMPARISON_PALETTE = [
        "#3D5A80",
        "#2A9D8F",
        "#5B8E3E",
        "#B08968",
        "#E07A5F",
        "#B56576",
        "#6D597A",
        "#8D99AE",
        "#CDA15E",
    ]

    def __init__(self) -> None:
        sns.set_theme(style="whitegrid")

    def plot(
        self,
        points: list[CoveragePoint],
        totals: CoverageTotals,
        output_dir: Path,
        file_prefix: str,
    ) -> tuple[Path, Path, Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        state_chart_path = output_dir / f"{file_prefix}_state_coverage.png"
        transition_chart_path = output_dir / f"{file_prefix}_transition_coverage.png"
        state_ratio_chart_path = output_dir / f"{file_prefix}_state_coverage_ratio.png"
        transition_ratio_chart_path = output_dir / f"{file_prefix}_transition_coverage_ratio.png"

        self._plot_single_chart(
            points=points,
            total_value=totals.total_states,
            x_attr="path_count",
            y_attr="covered_states",
            title="State Coverage by Path Count",
            x_label="Number of Paths",
            y_label="Covered States",
            output_file=state_chart_path,
            line_color="#2C7FB8",
        )
        self._plot_single_chart(
            points=points,
            total_value=totals.total_transitions,
            x_attr="path_count",
            y_attr="covered_transitions",
            title="Transition Coverage by Path Count",
            x_label="Number of Paths",
            y_label="Covered Transitions",
            output_file=transition_chart_path,
            line_color="#D95F0E",
        )
        self._plot_single_chart(
            points=points,
            total_value=1.0,
            x_attr="path_count",
            y_attr="covered_states",
            title="State Coverage Ratio by Path Count",
            x_label="Number of Paths",
            y_label="Covered States / Total States",
            output_file=state_ratio_chart_path,
            line_color="#1B9E77",
            y_values_override=[point.covered_states / totals.total_states for point in points],
        )
        self._plot_single_chart(
            points=points,
            total_value=1.0,
            x_attr="path_count",
            y_attr="covered_transitions",
            title="Transition Coverage Ratio by Path Count",
            x_label="Number of Paths",
            y_label="Covered Transitions / Total Transitions",
            output_file=transition_ratio_chart_path,
            line_color="#7570B3",
            y_values_override=[point.covered_transitions / totals.total_transitions for point in points],
        )

        return state_chart_path, transition_chart_path, state_ratio_chart_path, transition_ratio_chart_path

    def plot_strategy_comparison(
        self,
        project_name: str,
        strategy_results: Mapping[str, AnalysisResult],
        output_dir: Path,
    ) -> tuple[Path, Path, Path, Path]:
        if not strategy_results:
            raise ValueError(f"No strategy results were provided for project '{project_name}'")

        ordered_results = {
            strategy_name: strategy_results[strategy_name]
            for strategy_name in sorted(strategy_results, key=self._natural_label_key)
        }
        first_result = next(iter(ordered_results.values()))
        for strategy_name, result in ordered_results.items():
            if result.project_name != project_name:
                raise ValueError(
                    f"Strategy '{strategy_name}' does not belong to project '{project_name}': {result.project_name}"
                )
            if result.totals != first_result.totals:
                raise ValueError(
                    f"Coverage totals do not match for project '{project_name}' across strategies."
                )

        output_dir.mkdir(parents=True, exist_ok=True)
        state_chart_path = output_dir / f"{project_name}_strategy_state_coverage.png"
        transition_chart_path = output_dir / f"{project_name}_strategy_transition_coverage.png"
        state_ratio_chart_path = output_dir / f"{project_name}_strategy_state_coverage_ratio.png"
        transition_ratio_chart_path = output_dir / f"{project_name}_strategy_transition_coverage_ratio.png"

        self._plot_multi_strategy_chart(
            strategy_results=ordered_results,
            title=f"State Coverage Comparison by Strategy ({project_name})",
            x_label="Number of Paths",
            y_label="Covered States",
            output_file=state_chart_path,
            total_value=float(first_result.totals.total_states),
            value_resolver=lambda point, _totals: float(point.covered_states),
        )
        self._plot_multi_strategy_chart(
            strategy_results=ordered_results,
            title=f"Transition Coverage Comparison by Strategy ({project_name})",
            x_label="Number of Paths",
            y_label="Covered Transitions",
            output_file=transition_chart_path,
            total_value=float(first_result.totals.total_transitions),
            value_resolver=lambda point, _totals: float(point.covered_transitions),
        )
        self._plot_multi_strategy_chart(
            strategy_results=ordered_results,
            title=f"State Coverage Ratio Comparison by Strategy ({project_name})",
            x_label="Number of Paths",
            y_label="Covered States / Total States",
            output_file=state_ratio_chart_path,
            total_value=1.0,
            value_resolver=lambda point, totals: (
                point.covered_states / totals.total_states if totals.total_states else 0.0
            ),
            ratio_mode=True,
        )
        self._plot_multi_strategy_chart(
            strategy_results=ordered_results,
            title=f"Transition Coverage Ratio Comparison by Strategy ({project_name})",
            x_label="Number of Paths",
            y_label="Covered Transitions / Total Transitions",
            output_file=transition_ratio_chart_path,
            total_value=1.0,
            value_resolver=lambda point, totals: (
                point.covered_transitions / totals.total_transitions if totals.total_transitions else 0.0
            ),
            ratio_mode=True,
        )

        return state_chart_path, transition_chart_path, state_ratio_chart_path, transition_ratio_chart_path

    def _plot_single_chart(
        self,
        points: list[CoveragePoint],
        total_value: int,
        x_attr: str,
        y_attr: str,
        title: str,
        x_label: str,
        y_label: str,
        output_file: Path,
        line_color: str,
        y_values_override: list[float] | None = None,
    ) -> None:
        x_values = [getattr(point, x_attr) for point in points]
        y_values = y_values_override or [getattr(point, y_attr) for point in points]

        fig, ax = plt.subplots(figsize=(12, 7))
        sns.lineplot(x=x_values, y=y_values, marker="o", linewidth=2.2, color=line_color, ax=ax)

        for x_value, y_value in zip(x_values, y_values, strict=True):
            label = f"{y_value:.2f}" if total_value == 1.0 else f"{int(y_value)}"
            ax.annotate(
                label,
                (x_value, y_value),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=9,
                color=line_color,
            )

        ax.axhline(total_value, linestyle="--", linewidth=1.2, color="#6B7280", label=f"Total = {total_value}")
        ax.set_title(title, pad=20)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        if total_value == 1.0:
            ax.set_ylim(0, 1.05)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_file, dpi=200)
        plt.close(fig)

    def _plot_multi_strategy_chart(
        self,
        strategy_results: Mapping[str, AnalysisResult],
        title: str,
        x_label: str,
        y_label: str,
        output_file: Path,
        total_value: float,
        value_resolver: Callable[[CoveragePoint, CoverageTotals], float],
        ratio_mode: bool = False,
    ) -> None:
        fig, ax = plt.subplots(figsize=(13, 7))
        palette = self._build_comparison_palette(len(strategy_results))
        annotation_targets: list[dict[str, object]] = []
        max_path_count = 0

        for index, (strategy_name, result) in enumerate(strategy_results.items()):
            x_values = [point.path_count for point in result.coverage_points]
            y_values = [value_resolver(point, result.totals) for point in result.coverage_points]
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

            target_path_count, target_value, reached_total = self._select_annotation_target(
                x_values=x_values,
                y_values=y_values,
                total_value=total_value,
            )
            annotation_targets.append(
                {
                    "strategy_name": strategy_name,
                    "target_path_count": target_path_count,
                    "target_value": target_value,
                    "label_text": f"{target_path_count}",
                    "color": palette[index],
                    "reached_total": reached_total,
                }
            )

        if max_path_count == 0:
            raise ValueError("At least one strategy must include coverage points to generate a comparison chart.")

        label_y_offsets = self._build_annotation_offsets(
            target_values=[float(target["target_value"]) for target in annotation_targets],
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

        reference_label = f"Total = {total_value:.2f}" if ratio_mode else f"Total = {int(total_value)}"
        ax.axhline(total_value, linestyle="--", linewidth=1.2, color="#6B7280", label=reference_label)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_xlim(1, max_path_count + 1)
        if ratio_mode:
            ax.set_ylim(0, 1.1)
        else:
            ax.set_ylim(0, total_value * 1.1)
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
        fig.tight_layout()
        fig.savefig(output_file, dpi=200)
        plt.close(fig)

    def _select_annotation_target(
        self,
        x_values: list[int],
        y_values: list[float],
        total_value: float,
    ) -> tuple[int, float, bool]:
        tolerance = 1e-9
        for path_count, coverage_value in zip(x_values, y_values, strict=True):
            if coverage_value >= total_value - tolerance:
                return path_count, coverage_value, True

        return x_values[-1], y_values[-1], False

    def _build_annotation_offsets(
        self,
        target_values: list[float],
    ) -> list[int]:
        if not target_values:
            return []

        sorted_pairs = sorted(enumerate(target_values), key=lambda pair: pair[1])
        offsets = [0] * len(target_values)
        for index, (original_index, _target_value) in enumerate(sorted_pairs):
            offsets[original_index] = 6 + index * 4

        return offsets

    def _build_comparison_palette(self, color_count: int) -> list[tuple[float, float, float]]:
        if color_count <= len(self._COMPARISON_PALETTE):
            return sns.color_palette(self._COMPARISON_PALETTE[:color_count])

        extra_colors = sns.color_palette("husl", n_colors=color_count - len(self._COMPARISON_PALETTE))
        return sns.color_palette(self._COMPARISON_PALETTE) + list(extra_colors)

    def _natural_label_key(self, label: str) -> tuple[object, ...]:
        parts = re.split(r"(\d+)", label.casefold())
        return tuple(int(part) if part.isdigit() else part for part in parts)