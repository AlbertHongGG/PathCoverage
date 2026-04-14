from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from adjustText import adjust_text

from path_coverage.analysis.metrics import CoverageMetricResolver
from path_coverage.charts.common import build_comparison_palette, save_and_close
from path_coverage.common import DEFAULT_PATH_LIMITS, OUTPUT_ANALYSIS_DIRNAME, natural_label_key, path_limit_dir_name
from path_coverage.coverage import CoverageCalculator
from path_coverage.graph_loader import GraphLoader
from path_coverage.models import CoverageMetric
from path_coverage.outputs.json_writers import JsonWriter
from path_coverage.settings import SettingsLoader


FEATURE_COMPLETION_OUTPUT_DIRNAME = "feature_completion_scatter"
DEFAULT_MANUAL_JSON_DIRNAME = "每個專案的 32 Path整理"
DEFAULT_CHECKLIST_ROOT_PARTS = ("文件資料", "專案計畫")


@dataclass(frozen=True)
class ManualVerificationItem:
    label: str
    completed: bool


@dataclass(frozen=True)
class ManualVerificationPath:
    rank: int
    edge_ids: list[str]
    items: list[ManualVerificationItem]


@dataclass(frozen=True)
class StrategyManualData:
    strategy_name: str
    paths: list[ManualVerificationPath]


@dataclass(frozen=True)
class FeatureCompletionPoint:
    strategy_name: str
    state_coverage: int
    state_coverage_ratio: float
    transition_coverage: int
    transition_coverage_ratio: float
    feature_observed_item_count: int
    feature_completed_item_count: int
    feature_completion_ratio: float
    actual_path_count_used: int


@dataclass(frozen=True)
class FeatureCompletionDataset:
    project_name: str
    path_limit: int
    checklist_item_total: int
    checklist_total_source: str
    strategy_points: list[FeatureCompletionPoint]


@dataclass(frozen=True)
class FeatureCompletionComparisonPoint:
    strategy_name: str
    state_coverage_average: float
    state_coverage_ratio_average: float
    transition_coverage_average: float
    transition_coverage_ratio_average: float
    feature_completion_ratio_average: float
    project_count: int
    actual_path_counts: dict[str, int]


@dataclass(frozen=True)
class FeatureCompletionComparisonDataset:
    path_limit: int
    strategy_order: list[str]
    project_names: list[str]
    checklist_totals_by_project: dict[str, int]
    checklist_total_sources_by_project: dict[str, str]
    strategy_points: list[FeatureCompletionComparisonPoint]


def positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return parsed_value


def parse_path_limits(value: str) -> tuple[int, ...]:
    if not value.strip():
        raise argparse.ArgumentTypeError("Path limits cannot be empty.")

    parts = [part.strip() for part in value.split(",")]
    try:
        parsed_limits = tuple(sorted({positive_int(part) for part in parts if part}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Path limits must be comma-separated integers.") from exc

    if not parsed_limits:
        raise argparse.ArgumentTypeError("Path limits cannot be empty.")

    return parsed_limits


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent
    settings = SettingsLoader(project_root=project_root).load()
    default_checklist_root = project_root.parent.parent / DEFAULT_CHECKLIST_ROOT_PARTS[0] / DEFAULT_CHECKLIST_ROOT_PARTS[1]
    parser = argparse.ArgumentParser(
        description=(
            "Generate project-level scatter charts where X is state/transition coverage and Y is "
            "manual verification feature coverage computed from the top-N paths in 每個專案的 32 Path整理."
        )
    )
    parser.add_argument(
        "--manual-json-dir",
        type=Path,
        default=project_root / DEFAULT_MANUAL_JSON_DIRNAME,
        help="Directory containing per-project top-32 manual verification JSON files.",
    )
    parser.add_argument(
        "--graph-dir",
        type=Path,
        default=settings.graph_root_dir,
        help="Directory containing graph/<project>/data.json files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.output_dir / OUTPUT_ANALYSIS_DIRNAME / FEATURE_COMPLETION_OUTPUT_DIRNAME,
        help="Directory for feature coverage scatter outputs.",
    )
    parser.add_argument(
        "--checklist-root",
        type=Path,
        default=default_checklist_root,
        help="Root directory containing <project>/FeatureChecklist.md files.",
    )
    parser.add_argument(
        "--project",
        action="append",
        dest="projects",
        help="Project name to analyze, for example 1-1. Repeat to analyze multiple projects. Defaults to all JSON files.",
    )
    parser.add_argument(
        "--path-limits",
        type=parse_path_limits,
        default=DEFAULT_PATH_LIMITS,
        help="Comma-separated path limits to analyze. Defaults to 5,10,15,20,25,30.",
    )
    parser.add_argument(
        "--checklist-total",
        type=positive_int,
        help=(
            "Override the total checklist item count. If omitted, the tool first tries "
            "<checklist-root>/<project>/FeatureChecklist.md and falls back to the union of observed labels."
        ),
    )
    parser.add_argument(
        "--comparison-only",
        action="store_true",
        help="Only generate cross-project average comparison charts and summaries.",
    )
    return parser.parse_args()


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip())


def _count_markdown_checklist_items(checklist_file: Path) -> int:
    pattern = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+)\[[ xX]\]\s+.+$")
    count = 0
    for line in checklist_file.read_text(encoding="utf-8").splitlines():
        if pattern.match(line):
            count += 1
    return count


def _load_manual_project(manual_json_file: Path) -> tuple[str, list[StrategyManualData]]:
    payload = json.loads(manual_json_file.read_text(encoding="utf-8"))
    project_name = payload.get("projectName") or manual_json_file.stem
    strategy_payloads = payload.get("strategies", [])
    strategies: list[StrategyManualData] = []

    for strategy_payload in sorted(strategy_payloads, key=lambda item: natural_label_key(item.get("strategyName", ""))):
        paths: list[ManualVerificationPath] = []
        for path_payload in sorted(strategy_payload.get("paths", []), key=lambda item: item.get("rank", 0)):
            manual_verification = path_payload.get("manualVerification", {})
            items = [
                ManualVerificationItem(
                    label=_normalize_label(item.get("label", "")),
                    completed=bool(item.get("completed", False)),
                )
                for item in manual_verification.get("items", [])
                if _normalize_label(item.get("label", ""))
            ]
            paths.append(
                ManualVerificationPath(
                    rank=int(path_payload.get("rank", len(paths) + 1)),
                    edge_ids=list(path_payload.get("edgeIds", [])),
                    items=items,
                )
            )

        strategies.append(
            StrategyManualData(
                strategy_name=strategy_payload.get("strategyName") or strategy_payload.get("strategyFolder") or "unknown",
                paths=paths,
            )
        )

    return project_name, strategies


def _resolve_checklist_total(
    project_name: str,
    strategies: list[StrategyManualData],
    checklist_root: Path,
    checklist_total_override: int | None,
) -> tuple[int, str]:
    if checklist_total_override is not None:
        return checklist_total_override, "cli-override"

    checklist_file = checklist_root / project_name / "FeatureChecklist.md"
    if checklist_file.exists():
        checklist_count = _count_markdown_checklist_items(checklist_file)
        if checklist_count > 0:
            return checklist_count, str(checklist_file)

    observed_labels = {
        item.label
        for strategy in strategies
        for path in strategy.paths
        for item in path.items
        if item.label
    }
    return len(observed_labels), "fallback: union of observed manualVerification.items labels"


def _build_feature_completion_dataset(
    project_name: str,
    strategies: list[StrategyManualData],
    graph_file: Path,
    path_limit: int,
    checklist_item_total: int,
    checklist_total_source: str,
) -> FeatureCompletionDataset:
    graph = GraphLoader().load(graph_file)
    coverage_calculator = CoverageCalculator()
    strategy_points: list[FeatureCompletionPoint] = []

    for strategy in strategies:
        if not strategy.paths:
            continue

        ordered_edge_ids = [path.edge_ids for path in strategy.paths]
        coverage_points, totals = coverage_calculator.calculate(ordered_edge_ids, graph)
        actual_path_count = min(path_limit, len(strategy.paths), len(coverage_points))
        if actual_path_count == 0:
            continue

        coverage_point = coverage_points[actual_path_count - 1]
        observed_labels: set[str] = set()
        completed_labels: set[str] = set()
        for path in strategy.paths[:actual_path_count]:
            for item in path.items:
                observed_labels.add(item.label)
                if item.completed:
                    completed_labels.add(item.label)

        strategy_points.append(
            FeatureCompletionPoint(
                strategy_name=strategy.strategy_name,
                state_coverage=coverage_point.covered_states,
                state_coverage_ratio=(coverage_point.covered_states / totals.total_states) if totals.total_states else 0.0,
                transition_coverage=coverage_point.covered_transitions,
                transition_coverage_ratio=(coverage_point.covered_transitions / totals.total_transitions)
                if totals.total_transitions
                else 0.0,
                feature_observed_item_count=len(observed_labels),
                feature_completed_item_count=len(completed_labels),
                feature_completion_ratio=(len(completed_labels) / checklist_item_total) if checklist_item_total else 0.0,
                actual_path_count_used=actual_path_count,
            )
        )

    return FeatureCompletionDataset(
        project_name=project_name,
        path_limit=path_limit,
        checklist_item_total=checklist_item_total,
        checklist_total_source=checklist_total_source,
        strategy_points=strategy_points,
    )


def _pareto_frontier_indices(x_values: list[float], y_values: list[float]) -> set[int]:
    frontier_indices: set[int] = set()
    for candidate_index, (candidate_x, candidate_y) in enumerate(zip(x_values, y_values)):
        dominated = False
        for other_index, (other_x, other_y) in enumerate(zip(x_values, y_values)):
            if candidate_index == other_index:
                continue

            if other_x >= candidate_x and other_y >= candidate_y and (
                other_x > candidate_x or other_y > candidate_y
            ):
                dominated = True
                break

        if not dominated:
            frontier_indices.add(candidate_index)

    return frontier_indices


class FeatureCompletionScatterChart:
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(
        self,
        dataset: FeatureCompletionDataset,
        metric: CoverageMetric,
        output_file: Path,
        emphasize_frontier: bool = False,
    ) -> Path:
        palette = build_comparison_palette(len(dataset.strategy_points))
        fig, ax = plt.subplots(figsize=(12, 7))

        x_values = [self._resolve_x_value(point, metric) for point in dataset.strategy_points]
        y_values = [point.feature_completion_ratio for point in dataset.strategy_points]
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
                point.feature_completion_ratio,
                color=palette[index],
                s=80,
                label=point.strategy_name,
                alpha=point_alpha,
                zorder=3 if is_frontier else 1,
            )
            if emphasize_frontier and not is_frontier:
                ax.scatter(
                    x_value,
                    point.feature_completion_ratio,
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
                    point.feature_completion_ratio,
                    self._build_label_text(point, x_value, metric),
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
        ax.set_title(self._build_title(dataset, metric, emphasize_frontier), pad=20)
        ax.set_xlabel(self._metric_resolver.y_label(metric))
        ax.set_ylabel("Feature Coverage")
        ax.spines[["top", "right"]].set_visible(False)
        self._set_axis_limits(ax, x_values, metric)
        self._adjust_labels(ax, texts, x_values, y_values)
        ax.legend(title="Strategy", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
        save_and_close(fig, output_file)
        return output_file

    def _resolve_x_value(self, point: FeatureCompletionPoint, metric: CoverageMetric) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return float(point.state_coverage)
        if metric == CoverageMetric.STATE_COVERAGE_RATIO:
            return point.state_coverage_ratio
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return float(point.transition_coverage)
        return point.transition_coverage_ratio

    def _build_label_text(
        self,
        point: FeatureCompletionPoint,
        x_value: float,
        metric: CoverageMetric,
    ) -> str:
        return f"{point.strategy_name} ({self._format_value(x_value, metric)}, {point.feature_completion_ratio:.3f})"

    def _build_title(
        self,
        dataset: FeatureCompletionDataset,
        metric: CoverageMetric,
        emphasize_frontier: bool,
    ) -> str:
        title = (
            f"{self._metric_resolver.display_name(metric)} vs Feature Coverage "
            f"({dataset.project_name}, Top {dataset.path_limit} Paths Cap)"
        )
        if not emphasize_frontier:
            return title
        return f"{title} - Pareto Frontier Highlighted"

    def _format_value(self, value: float, metric: CoverageMetric) -> str:
        if self._metric_resolver.is_ratio(metric):
            return f"{value:.3f}"
        rounded_value = round(value)
        if abs(value - rounded_value) < 1e-9:
            return f"{int(rounded_value)}"
        return f"{value:.2f}"

    def _set_axis_limits(self, ax, x_values: list[float], metric: CoverageMetric) -> None:
        if x_values:
            max_x = max(x_values)
            ax.set_xlim(0, max_x * 1.1 if max_x else 1.0)
            if self._metric_resolver.is_ratio(metric):
                ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)

    def _adjust_labels(self, ax, texts: list, x_values: list[float], y_values: list[float]) -> None:
        if not texts:
            return

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
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

    def _draw_frontier(self, ax, x_values: list[float], y_values: list[float], frontier_indices: set[int]) -> None:
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


class FeatureCompletionSummaryWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, dataset: FeatureCompletionDataset, output_file: Path) -> Path:
        payload = {
            "projectName": dataset.project_name,
            "pathLimit": dataset.path_limit,
            "checklistItemTotal": dataset.checklist_item_total,
            "checklistTotalSource": dataset.checklist_total_source,
            "points": [
                {
                    "strategyName": point.strategy_name,
                    "stateCoverage": point.state_coverage,
                    "stateCoverageRatio": point.state_coverage_ratio,
                    "transitionCoverage": point.transition_coverage,
                    "transitionCoverageRatio": point.transition_coverage_ratio,
                    "featureObservedItemCount": point.feature_observed_item_count,
                    "featureCompletedItemCount": point.feature_completed_item_count,
                    "featureCompletionRatio": point.feature_completion_ratio,
                    "actualPathCountUsed": point.actual_path_count_used,
                }
                for point in dataset.strategy_points
            ],
        }
        return self._json_writer.write(payload, output_file)


class FeatureCompletionComparisonScatterChart:
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(
        self,
        dataset: FeatureCompletionComparisonDataset,
        metric: CoverageMetric,
        output_file: Path,
        emphasize_frontier: bool = False,
    ) -> Path:
        palette = build_comparison_palette(len(dataset.strategy_points))
        fig, ax = plt.subplots(figsize=(12, 7))

        x_values = [self._resolve_x_value(point, metric) for point in dataset.strategy_points]
        y_values = [point.feature_completion_ratio_average for point in dataset.strategy_points]
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
                point.feature_completion_ratio_average,
                color=palette[index],
                s=80,
                label=point.strategy_name,
                alpha=point_alpha,
                zorder=3 if is_frontier else 1,
            )
            if emphasize_frontier and not is_frontier:
                ax.scatter(
                    x_value,
                    point.feature_completion_ratio_average,
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
                    point.feature_completion_ratio_average,
                    self._build_label_text(point, x_value, metric),
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
        ax.set_title(self._build_title(dataset, metric, emphasize_frontier), pad=20)
        ax.set_xlabel(f"Average {self._metric_resolver.y_label(metric)}")
        ax.set_ylabel("Average Feature Coverage")
        ax.spines[["top", "right"]].set_visible(False)
        self._set_axis_limits(ax, x_values, metric)
        self._adjust_labels(ax, texts, x_values, y_values)
        ax.legend(title="Strategy", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
        save_and_close(fig, output_file)
        return output_file

    def _resolve_x_value(self, point: FeatureCompletionComparisonPoint, metric: CoverageMetric) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return point.state_coverage_average
        if metric == CoverageMetric.STATE_COVERAGE_RATIO:
            return point.state_coverage_ratio_average
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return point.transition_coverage_average
        return point.transition_coverage_ratio_average

    def _build_label_text(
        self,
        point: FeatureCompletionComparisonPoint,
        x_value: float,
        metric: CoverageMetric,
    ) -> str:
        return (
            f"{point.strategy_name} ({self._format_value(x_value, metric)}, "
            f"{point.feature_completion_ratio_average:.3f})"
        )

    def _build_title(
        self,
        dataset: FeatureCompletionComparisonDataset,
        metric: CoverageMetric,
        emphasize_frontier: bool,
    ) -> str:
        title = (
            f"Average {self._metric_resolver.display_name(metric)} vs Average Feature Coverage Across Projects "
            f"(Top {dataset.path_limit} Paths Cap)"
        )
        if not emphasize_frontier:
            return title
        return f"{title} - Pareto Frontier Highlighted"

    def _format_value(self, value: float, metric: CoverageMetric) -> str:
        if self._metric_resolver.is_ratio(metric):
            return f"{value:.3f}"
        rounded_value = round(value)
        if abs(value - rounded_value) < 1e-9:
            return f"{int(rounded_value)}"
        return f"{value:.2f}"

    def _set_axis_limits(self, ax, x_values: list[float], metric: CoverageMetric) -> None:
        if x_values:
            max_x = max(x_values)
            ax.set_xlim(0, max_x * 1.1 if max_x else 1.0)
            if self._metric_resolver.is_ratio(metric):
                ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)

    def _adjust_labels(self, ax, texts: list, x_values: list[float], y_values: list[float]) -> None:
        if not texts:
            return

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
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

    def _draw_frontier(self, ax, x_values: list[float], y_values: list[float], frontier_indices: set[int]) -> None:
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


class FeatureCompletionComparisonSummaryWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, dataset: FeatureCompletionComparisonDataset, output_file: Path) -> Path:
        payload = {
            "pathLimit": dataset.path_limit,
            "strategyOrder": dataset.strategy_order,
            "projectCount": len(dataset.project_names),
            "projectNames": dataset.project_names,
            "checklistTotalsByProject": dataset.checklist_totals_by_project,
            "checklistTotalSourcesByProject": dataset.checklist_total_sources_by_project,
            "points": [
                {
                    "strategyName": point.strategy_name,
                    "stateCoverageAverage": point.state_coverage_average,
                    "stateCoverageRatioAverage": point.state_coverage_ratio_average,
                    "transitionCoverageAverage": point.transition_coverage_average,
                    "transitionCoverageRatioAverage": point.transition_coverage_ratio_average,
                    "featureCompletionRatioAverage": point.feature_completion_ratio_average,
                    "projectCount": point.project_count,
                    "actualPathCounts": point.actual_path_counts,
                }
                for point in dataset.strategy_points
            ],
        }
        return self._json_writer.write(payload, output_file)


def _build_comparison_dataset(
    datasets: list[FeatureCompletionDataset],
    path_limit: int,
) -> FeatureCompletionComparisonDataset | None:
    if not datasets:
        return None

    ordered_project_names = sorted((dataset.project_name for dataset in datasets), key=natural_label_key)
    checklist_totals_by_project = {dataset.project_name: dataset.checklist_item_total for dataset in datasets}
    checklist_total_sources_by_project = {dataset.project_name: dataset.checklist_total_source for dataset in datasets}
    point_lookup = {
        dataset.project_name: {point.strategy_name: point for point in dataset.strategy_points}
        for dataset in datasets
    }
    strategy_names = sorted(
        {
            point.strategy_name
            for dataset in datasets
            for point in dataset.strategy_points
        },
        key=natural_label_key,
    )

    strategy_points: list[FeatureCompletionComparisonPoint] = []
    for strategy_name in strategy_names:
        matching_points = [
            point_lookup[project_name][strategy_name]
            for project_name in ordered_project_names
            if strategy_name in point_lookup[project_name]
        ]
        if not matching_points:
            continue

        strategy_points.append(
            FeatureCompletionComparisonPoint(
                strategy_name=strategy_name,
                state_coverage_average=sum(point.state_coverage for point in matching_points) / len(matching_points),
                state_coverage_ratio_average=sum(point.state_coverage_ratio for point in matching_points)
                / len(matching_points),
                transition_coverage_average=sum(point.transition_coverage for point in matching_points)
                / len(matching_points),
                transition_coverage_ratio_average=sum(point.transition_coverage_ratio for point in matching_points)
                / len(matching_points),
                feature_completion_ratio_average=sum(point.feature_completion_ratio for point in matching_points)
                / len(matching_points),
                project_count=len(matching_points),
                actual_path_counts={
                    project_name: point_lookup[project_name][strategy_name].actual_path_count_used
                    for project_name in ordered_project_names
                    if strategy_name in point_lookup[project_name]
                },
            )
        )

    if not strategy_points:
        return None

    return FeatureCompletionComparisonDataset(
        path_limit=path_limit,
        strategy_order=strategy_names,
        project_names=ordered_project_names,
        checklist_totals_by_project=checklist_totals_by_project,
        checklist_total_sources_by_project=checklist_total_sources_by_project,
        strategy_points=strategy_points,
    )


def _resolve_projects(manual_json_dir: Path, selected_projects: list[str] | None) -> list[Path]:
    if selected_projects:
        return [manual_json_dir / f"{project_name}.json" for project_name in selected_projects]

    return sorted(manual_json_dir.glob("*.json"), key=lambda path: natural_label_key(path.stem))


def main() -> None:
    args = parse_args()
    manual_json_dir = args.manual_json_dir.resolve()
    graph_dir = args.graph_dir.resolve()
    output_dir = args.output_dir.resolve()
    checklist_root = args.checklist_root.resolve()
    project_files = _resolve_projects(manual_json_dir, args.projects)

    chart = FeatureCompletionScatterChart()
    summary_writer = FeatureCompletionSummaryWriter()
    comparison_chart = FeatureCompletionComparisonScatterChart()
    comparison_summary_writer = FeatureCompletionComparisonSummaryWriter()
    datasets_by_path_limit: dict[int, list[FeatureCompletionDataset]] = {
        path_limit: [] for path_limit in args.path_limits
    }

    print(f"Manual verification JSON root: {manual_json_dir}")
    print(f"Graph root: {graph_dir}")
    print(f"Checklist root: {checklist_root}")
    print(f"Output root: {output_dir}")
    print(f"Projects to analyze: {', '.join(path.stem for path in project_files)}")
    print(f"Path limits: {', '.join(str(path_limit) for path_limit in args.path_limits)}")
    print(f"Comparison only: {args.comparison_only}")

    for manual_json_file in project_files:
        if not manual_json_file.exists():
            raise FileNotFoundError(f"Manual verification JSON file not found: {manual_json_file}")

        project_name, strategies = _load_manual_project(manual_json_file)
        graph_file = graph_dir / project_name / "data.json"
        if not graph_file.exists():
            raise FileNotFoundError(f"Graph JSON file not found: {graph_file}")

        checklist_item_total, checklist_total_source = _resolve_checklist_total(
            project_name=project_name,
            strategies=strategies,
            checklist_root=checklist_root,
            checklist_total_override=args.checklist_total,
        )
        print(
            f"[{project_name}] Checklist total: {checklist_item_total} "
            f"(source: {checklist_total_source})"
        )

        for path_limit in args.path_limits:
            dataset = _build_feature_completion_dataset(
                project_name=project_name,
                strategies=strategies,
                graph_file=graph_file,
                path_limit=path_limit,
                checklist_item_total=checklist_item_total,
                checklist_total_source=checklist_total_source,
            )
            datasets_by_path_limit[path_limit].append(dataset)
            if args.comparison_only:
                continue

            scatter_dir = output_dir / project_name / path_limit_dir_name(path_limit)
            scatter_dir.mkdir(parents=True, exist_ok=True)
            for metric in (
                CoverageMetric.STATE_COVERAGE,
                CoverageMetric.STATE_COVERAGE_RATIO,
                CoverageMetric.TRANSITION_COVERAGE,
                CoverageMetric.TRANSITION_COVERAGE_RATIO,
            ):
                base_filename = f"{metric.value}_vs_feature_completion_ratio"
                chart.render(dataset, metric, scatter_dir / f"{base_filename}.png")
                chart.render(
                    dataset,
                    metric,
                    scatter_dir / f"{base_filename}_pareto_frontier.png",
                    emphasize_frontier=True,
                )
            summary_writer.write(dataset, scatter_dir / "summary.json")
            print(f"[{project_name}] Wrote {scatter_dir}")

    comparison_root_dir = output_dir / "comparison"
    for path_limit in args.path_limits:
        comparison_dataset = _build_comparison_dataset(datasets_by_path_limit[path_limit], path_limit)
        if comparison_dataset is None:
            continue

        scatter_dir = comparison_root_dir / path_limit_dir_name(path_limit)
        scatter_dir.mkdir(parents=True, exist_ok=True)
        for metric in (
            CoverageMetric.STATE_COVERAGE,
            CoverageMetric.STATE_COVERAGE_RATIO,
            CoverageMetric.TRANSITION_COVERAGE,
            CoverageMetric.TRANSITION_COVERAGE_RATIO,
        ):
            base_filename = f"{metric.value}_vs_feature_completion_ratio"
            comparison_chart.render(comparison_dataset, metric, scatter_dir / f"{base_filename}.png")
            comparison_chart.render(
                comparison_dataset,
                metric,
                scatter_dir / f"{base_filename}_pareto_frontier.png",
                emphasize_frontier=True,
            )
        comparison_summary_writer.write(comparison_dataset, scatter_dir / "summary.json")
        print(f"[comparison] Wrote {scatter_dir}")


if __name__ == "__main__":
    main()