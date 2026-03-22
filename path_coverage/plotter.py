from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

from .models import AnalysisResult, CoveragePoint, CoverageTotals


class CoveragePlotter:
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
            for strategy_name in sorted(strategy_results)
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
        ax.set_title(title)
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
        fig, ax = plt.subplots(figsize=(12, 7))
        palette = sns.color_palette("tab10", n_colors=max(len(strategy_results), 3))

        for index, (strategy_name, result) in enumerate(strategy_results.items()):
            x_values = [point.path_count for point in result.coverage_points]
            y_values = [value_resolver(point, result.totals) for point in result.coverage_points]
            if not x_values:
                continue

            ax.plot(
                x_values,
                y_values,
                marker="o",
                linewidth=2.2,
                color=palette[index],
                label=strategy_name,
            )

        reference_label = f"Total = {total_value:.2f}" if ratio_mode else f"Total = {int(total_value)}"
        ax.axhline(total_value, linestyle="--", linewidth=1.2, color="#6B7280", label=reference_label)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        if ratio_mode:
            ax.set_ylim(0, 1.05)
        ax.legend(title="Strategy")
        fig.tight_layout()
        fig.savefig(output_file, dpi=200)
        plt.close(fig)