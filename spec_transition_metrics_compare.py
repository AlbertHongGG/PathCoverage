from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from dataclasses import asdict, dataclass
from functools import lru_cache
from matplotlib.lines import Line2D
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt

from path_coverage.charts.common import build_comparison_palette, save_and_close
from path_coverage.common import OUTPUT_ANALYSIS_DIRNAME, natural_label_key
from path_coverage.outputs.json_writers import JsonWriter


OUTPUT_DIRNAME = "spec_transition_compare"
DEFAULT_METRICS_DIRNAME = "專案基本測量數據"
FUNCTION_CHART_FILENAME = "function_completion_dumbbell.png"
LOC_CHART_FILENAME = "loc_stability_scatter.png"
COGNITIVE_COMPLEXITY_CHART_FILENAME = "cognitive_complexity_scatter.png"
CYCLOMATIC_COMPLEXITY_CHART_FILENAME = "cyclomatic_complexity_scatter.png"
SUMMARY_FILENAME = "summary.json"
SCATTER_REFERENCE_BAND_RATIO = 0.20


@dataclass(frozen=True)
class FunctionMetric:
    count: int
    ratio: float


@dataclass(frozen=True)
class ProjectMetricRecord:
    display_index: int
    project_id: str
    project_name: str
    function_spec: FunctionMetric
    function_spec_transition: FunctionMetric
    lines_spec: float
    lines_spec_transition: float
    cognitive_per_function_spec: float
    cognitive_per_function_spec_transition: float
    cyclomatic_per_function_spec: float
    cyclomatic_per_function_spec_transition: float

    @property
    def function_count_delta(self) -> int:
        return self.function_spec_transition.count - self.function_spec.count

    @property
    def function_ratio_delta(self) -> float:
        return self.function_spec_transition.ratio - self.function_spec.ratio

    @property
    def lines_delta(self) -> float:
        return self.lines_spec_transition - self.lines_spec

    @property
    def lines_ratio_change(self) -> float:
        return _safe_ratio_change(self.lines_spec, self.lines_spec_transition)

    @property
    def cognitive_delta(self) -> float:
        return self.cognitive_per_function_spec_transition - self.cognitive_per_function_spec

    @property
    def cognitive_ratio_change(self) -> float:
        return _safe_ratio_change(
            self.cognitive_per_function_spec,
            self.cognitive_per_function_spec_transition,
        )

    @property
    def cyclomatic_delta(self) -> float:
        return self.cyclomatic_per_function_spec_transition - self.cyclomatic_per_function_spec

    @property
    def cyclomatic_ratio_change(self) -> float:
        return _safe_ratio_change(
            self.cyclomatic_per_function_spec,
            self.cyclomatic_per_function_spec_transition,
        )

    @property
    def display_label(self) -> str:
        return str(self.display_index)


@dataclass(frozen=True)
class FigureOutput:
    file_name: str
    title: str
    stats: dict[str, object]
    order: list[str]


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Generate summary figures comparing SPEC-only outputs against SPEC+TRANSITION outputs "
            "from the 專案基本測量數據 Notion export."
        )
    )
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=project_root / DEFAULT_METRICS_DIRNAME / "data.json",
        help="Path to the Notion-exported JSON metrics file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "output" / OUTPUT_ANALYSIS_DIRNAME / OUTPUT_DIRNAME,
        help="Directory where the summary figures and JSON summary will be written.",
    )
    return parser.parse_args()


def _safe_ratio_change(base_value: float, compared_value: float) -> float:
    if math.isclose(base_value, 0.0):
        return 0.0
    return (compared_value - base_value) / base_value


def _records_by_display_index(records: list[ProjectMetricRecord]) -> list[ProjectMetricRecord]:
    return sorted(records, key=lambda record: record.display_index)


@lru_cache(maxsize=1)
def _cached_project_palette(display_indexes: tuple[int, ...]) -> dict[int, tuple[float, float, float]]:
    palette = build_comparison_palette(len(display_indexes))
    return {display_index: palette[index] for index, display_index in enumerate(display_indexes)}


def _project_palette(records: list[ProjectMetricRecord]) -> dict[int, tuple[float, float, float]]:
    ordered_indexes = tuple(record.display_index for record in _records_by_display_index(records))
    return _cached_project_palette(ordered_indexes)


def _add_project_legend(ax, records: list[ProjectMetricRecord], palette: dict[int, tuple[float, float, float]]) -> None:
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markersize=7,
            markerfacecolor=palette[record.display_index],
            markeredgecolor=palette[record.display_index],
            label=record.display_label,
        )
        for record in _records_by_display_index(records)
    ]
    ax.legend(
        handles=handles,
        title="Projects",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=9,
        title_fontsize=9.5,
        ncol=1,
    )


def _parse_property_value(properties: dict[str, object], key: str) -> object:
    property_payload = properties.get(key)
    if not isinstance(property_payload, dict):
        raise ValueError(f"Missing property: {key}")
    return property_payload.get("value")


def _parse_required_text(properties: dict[str, object], key: str) -> str:
    raw_value = _parse_property_value(properties, key)
    if not isinstance(raw_value, str):
        raise ValueError(f"Expected text value for property: {key}")
    normalized = raw_value.strip()
    if not normalized:
        raise ValueError(f"Blank text value for property: {key}")
    return normalized


def _parse_numeric_text(properties: dict[str, object], key: str) -> float:
    text_value = _parse_required_text(properties, key).replace(",", "")
    try:
        return float(text_value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for property {key}: {text_value!r}") from exc


def _parse_function_metric(properties: dict[str, object], key: str) -> FunctionMetric:
    text_value = _parse_required_text(properties, key)
    match = re.fullmatch(r"(\d+)\s*\((\d+(?:\.\d+)?)%\)", text_value)
    if not match:
        raise ValueError(f"Invalid function metric format for property {key}: {text_value!r}")
    return FunctionMetric(count=int(match.group(1)), ratio=float(match.group(2)) / 100.0)


def _load_metrics(metrics_file: Path) -> tuple[list[ProjectMetricRecord], list[dict[str, object]]]:
    payload = json.loads(metrics_file.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("The metrics file must contain a top-level rows array.")

    records: list[ProjectMetricRecord] = []
    skipped_rows: list[dict[str, object]] = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every row in the metrics file must be an object.")

        properties = row.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("Each row must contain a properties object.")

        project_id = str(_parse_property_value(properties, "ID") or "").strip()
        project_name = str(_parse_property_value(properties, "專案名稱") or "").strip()
        row_index = row.get("index")

        if not project_id or not project_name:
            skipped_rows.append(
                {
                    "index": row_index,
                    "projectId": project_id,
                    "projectName": project_name,
                    "reason": "blank project identifier or project name",
                }
            )
            continue

        records.append(
            ProjectMetricRecord(
                display_index=int(_parse_required_text(properties, "Index")),
                project_id=project_id,
                project_name=project_name,
                function_spec=_parse_function_metric(properties, "[Func] Spec "),
                function_spec_transition=_parse_function_metric(properties, "[Func] Spec+Transition"),
                lines_spec=_parse_numeric_text(properties, "[行數] S"),
                lines_spec_transition=_parse_numeric_text(properties, "[行數] S+T"),
                cognitive_per_function_spec=_parse_numeric_text(properties, "[Cog/Fn] S"),
                cognitive_per_function_spec_transition=_parse_numeric_text(properties, "[Cog/Fn] S+T"),
                cyclomatic_per_function_spec=_parse_numeric_text(properties, "[Cyclo/Fn] S"),
                cyclomatic_per_function_spec_transition=_parse_numeric_text(properties, "[Cyclo/Fn] S+T"),
            )
        )

    ordered_records = sorted(records, key=lambda record: natural_label_key(record.project_id))
    if len(ordered_records) != 15:
        raise ValueError(f"Expected 15 valid project rows, but parsed {len(ordered_records)}.")
    return ordered_records, skipped_rows


def _build_function_figure(
    records: list[ProjectMetricRecord],
    output_dir: Path,
) -> FigureOutput:
    ordered_records = sorted(
        records,
        key=lambda record: (record.function_count_delta, record.function_ratio_delta, record.project_id),
        reverse=True,
    )
    palette = build_comparison_palette(2)
    fig, ax = plt.subplots(figsize=(12.5, 8.8))
    y_positions = list(range(len(ordered_records)))

    for y_position, record in zip(y_positions, ordered_records):
        ax.plot(
            [record.function_spec.count, record.function_spec_transition.count],
            [y_position, y_position],
            color="#CBD5E1",
            linewidth=2.2,
            zorder=1,
        )

    spec_counts = [record.function_spec.count for record in ordered_records]
    transition_counts = [record.function_spec_transition.count for record in ordered_records]
    ax.scatter(spec_counts, y_positions, s=72, color=palette[0], label="SPEC only", zorder=3)
    ax.scatter(transition_counts, y_positions, s=72, color=palette[1], label="SPEC + TRANSITION", zorder=4)

    improved_count = sum(record.function_count_delta > 0 for record in ordered_records)
    unchanged_count = sum(record.function_count_delta == 0 for record in ordered_records)
    regressed_count = sum(record.function_count_delta < 0 for record in ordered_records)
    mean_delta = mean(record.function_count_delta for record in ordered_records)
    mean_ratio_delta_pp = mean(record.function_ratio_delta for record in ordered_records) * 100.0
    ax.set_title("Implemented Function Count: SPEC only vs SPEC + TRANSITION", pad=26)
    ax.set_xlabel("Implemented Function Count")
    ax.set_yticks(y_positions)
    ax.set_yticklabels([record.display_label for record in ordered_records])
    ax.set_ylabel("Project")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.12)
    ax.legend(loc="upper left", frameon=False)
    ax.set_xlim(left=0, right=max(transition_counts + spec_counts) * 1.08)
    save_and_close(fig, output_dir / FUNCTION_CHART_FILENAME)

    return FigureOutput(
        file_name=FUNCTION_CHART_FILENAME,
        title="Implemented Function Count: SPEC only vs SPEC + TRANSITION",
        stats={
            "projectCount": len(ordered_records),
            "improvedCount": improved_count,
            "unchangedCount": unchanged_count,
            "regressedCount": regressed_count,
            "meanFunctionDelta": round(mean_delta, 4),
            "medianFunctionDelta": median(record.function_count_delta for record in ordered_records),
            "meanCompletionRateDeltaPp": round(mean_ratio_delta_pp, 4),
        },
        order=[record.display_label for record in ordered_records],
    )


def _draw_identity_band(ax, limit: float, band_ratio: float) -> None:
    x_values = [0.0, limit]
    lower = [value * (1.0 - band_ratio) for value in x_values]
    upper = [value * (1.0 + band_ratio) for value in x_values]
    ax.fill_between(x_values, lower, upper, color="#DBEAFE", alpha=0.35, zorder=0)
    ax.plot(x_values, x_values, linestyle="--", linewidth=1.2, color="#0F172A", alpha=0.8, zorder=1)


def _build_loc_figure(
    records: list[ProjectMetricRecord],
    output_dir: Path,
) -> FigureOutput:
    x_values = [record.lines_spec for record in records]
    y_values = [record.lines_spec_transition for record in records]
    limit = max(x_values + y_values) * 1.07
    palette = _project_palette(records)
    fig, ax = plt.subplots(figsize=(9.4, 8.2))

    _draw_identity_band(ax, limit, SCATTER_REFERENCE_BAND_RATIO)
    for record in _records_by_display_index(records):
        ax.scatter(
            record.lines_spec,
            record.lines_spec_transition,
            color=palette[record.display_index],
            s=72,
            alpha=0.9,
            zorder=3,
        )

    within_band_count = sum(abs(record.lines_ratio_change) <= SCATTER_REFERENCE_BAND_RATIO for record in records)
    median_delta = median(record.lines_delta for record in records)
    max_increase_ratio = max(record.lines_ratio_change for record in records)
    ax.set_title("Lines of Code: SPEC only vs SPEC + TRANSITION", pad=18)
    ax.set_xlabel("Lines of Code, SPEC only")
    ax.set_ylabel("Lines of Code, SPEC + TRANSITION")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, limit)
    ax.set_ylim(0, limit)
    _add_project_legend(ax, records, palette)
    save_and_close(fig, output_dir / LOC_CHART_FILENAME)

    return FigureOutput(
        file_name=LOC_CHART_FILENAME,
        title="Lines of Code: SPEC only vs SPEC + TRANSITION",
        stats={
            "projectCount": len(records),
            "within20PercentBandCount": within_band_count,
            "medianLocDelta": round(median_delta, 4),
            "meanLocDelta": round(mean(record.lines_delta for record in records), 4),
            "maxIncreaseRatio": round(max_increase_ratio, 6),
            "minRatioChange": round(min(record.lines_ratio_change for record in records), 6),
        },
        order=[record.display_label for record in sorted(records, key=lambda record: abs(record.lines_ratio_change), reverse=True)],
    )


def _render_complexity_panel(
    ax,
    records: list[ProjectMetricRecord],
    title: str,
    spec_getter,
    transition_getter,
    ratio_getter,
) -> dict[str, int | float]:
    x_values = [spec_getter(record) for record in records]
    y_values = [transition_getter(record) for record in records]
    limit = max(x_values + y_values) * 1.08
    palette = _project_palette(records)

    _draw_identity_band(ax, limit, SCATTER_REFERENCE_BAND_RATIO)
    for record in _records_by_display_index(records):
        ax.scatter(
            spec_getter(record),
            transition_getter(record),
            color=palette[record.display_index],
            s=68,
            alpha=0.9,
            zorder=3,
        )

    within_band_count = sum(abs(ratio_getter(record)) <= SCATTER_REFERENCE_BAND_RATIO for record in records)
    deltas = [transition_getter(record) - spec_getter(record) for record in records]
    ratio_changes = [ratio_getter(record) for record in records]
    ax.set_title(title, pad=12)
    ax.set_xlabel("SPEC only")
    ax.set_ylabel("SPEC + TRANSITION")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, limit)
    ax.set_ylim(0, limit)
    _add_project_legend(ax, records, palette)
    return {
        "withinBandCount": within_band_count,
        "medianDelta": round(median(deltas), 6),
        "meanDelta": round(mean(deltas), 6),
        "medianRatioChange": round(median(ratio_changes), 6),
        "maxAbsRatioChange": round(max(abs(value) for value in ratio_changes), 6),
    }


def _build_complexity_figure(
    records: list[ProjectMetricRecord],
    output_dir: Path,
) -> tuple[FigureOutput, FigureOutput]:
    fig, ax = plt.subplots(figsize=(9.1, 7.2))
    cognitive_stats = _render_complexity_panel(
        ax,
        records,
        title="Cognitive Complexity per Function: SPEC only vs SPEC + TRANSITION",
        spec_getter=lambda record: record.cognitive_per_function_spec,
        transition_getter=lambda record: record.cognitive_per_function_spec_transition,
        ratio_getter=lambda record: record.cognitive_ratio_change,
    )
    save_and_close(fig, output_dir / COGNITIVE_COMPLEXITY_CHART_FILENAME)

    fig, ax = plt.subplots(figsize=(9.1, 7.2))
    cyclomatic_stats = _render_complexity_panel(
        ax,
        records,
        title="Cyclomatic Complexity per Function: SPEC only vs SPEC + TRANSITION",
        spec_getter=lambda record: record.cyclomatic_per_function_spec,
        transition_getter=lambda record: record.cyclomatic_per_function_spec_transition,
        ratio_getter=lambda record: record.cyclomatic_ratio_change,
    )
    save_and_close(fig, output_dir / CYCLOMATIC_COMPLEXITY_CHART_FILENAME)

    cognitive_order = sorted(
        records,
        key=lambda record: abs(record.cognitive_ratio_change),
        reverse=True,
    )
    cyclomatic_order = sorted(
        records,
        key=lambda record: abs(record.cyclomatic_ratio_change),
        reverse=True,
    )

    return (
        FigureOutput(
        file_name=COGNITIVE_COMPLEXITY_CHART_FILENAME,
        title="Cognitive Complexity per Function: SPEC only vs SPEC + TRANSITION",
        stats={
            "projectCount": len(records),
            **cognitive_stats,
        },
        order=[record.display_label for record in cognitive_order],
    ),
        FigureOutput(
        file_name=CYCLOMATIC_COMPLEXITY_CHART_FILENAME,
        title="Cyclomatic Complexity per Function: SPEC only vs SPEC + TRANSITION",
        stats={
            "projectCount": len(records),
            **cyclomatic_stats,
        },
        order=[record.display_label for record in cyclomatic_order],
    ),
    )


def _build_summary_payload(
    metrics_file: Path,
    records: list[ProjectMetricRecord],
    skipped_rows: list[dict[str, object]],
    figures: list[FigureOutput],
) -> dict[str, object]:
    normalized_projects = []
    for record in records:
        normalized_projects.append(
            {
                "projectId": record.project_id,
                "displayIndex": record.display_index,
                "projectName": record.project_name,
                "functionSpec": asdict(record.function_spec),
                "functionSpecTransition": asdict(record.function_spec_transition),
                "linesSpec": record.lines_spec,
                "linesSpecTransition": record.lines_spec_transition,
                "cognitivePerFunctionSpec": record.cognitive_per_function_spec,
                "cognitivePerFunctionSpecTransition": record.cognitive_per_function_spec_transition,
                "cyclomaticPerFunctionSpec": record.cyclomatic_per_function_spec,
                "cyclomaticPerFunctionSpecTransition": record.cyclomatic_per_function_spec_transition,
                "functionCountDelta": record.function_count_delta,
                "functionRatioDelta": record.function_ratio_delta,
                "linesDelta": record.lines_delta,
                "linesRatioChange": record.lines_ratio_change,
                "cognitiveDelta": record.cognitive_delta,
                "cognitiveRatioChange": record.cognitive_ratio_change,
                "cyclomaticDelta": record.cyclomatic_delta,
                "cyclomaticRatioChange": record.cyclomatic_ratio_change,
            }
        )

    return {
        "metricsFile": str(metrics_file),
        "projectCount": len(records),
        "skippedRows": skipped_rows,
        "figureFiles": [asdict(figure) for figure in figures],
        "normalizedProjects": normalized_projects,
        "displayIndexToProject": {
            str(record.display_index): {
                "projectId": record.project_id,
                "projectName": record.project_name,
            }
            for record in records
        },
        "projectIdToName": {record.project_id: record.project_name for record in records},
    }


def main() -> None:
    args = parse_args()
    metrics_file = args.metrics_file.resolve()
    output_dir = args.output_dir.resolve()

    if not metrics_file.exists():
        raise FileNotFoundError(f"Metrics file not found: {metrics_file}")

    records, skipped_rows = _load_metrics(metrics_file)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Metrics file: {metrics_file}")
    print(f"Output directory: {output_dir}")
    print(f"Project rows: {len(records)}")
    print(f"Skipped rows: {len(skipped_rows)}")

    cognitive_figure, cyclomatic_figure = _build_complexity_figure(records, output_dir)
    figures = [
        _build_function_figure(records, output_dir),
        _build_loc_figure(records, output_dir),
        cognitive_figure,
        cyclomatic_figure,
    ]

    summary_path = JsonWriter().write(
        _build_summary_payload(metrics_file, records, skipped_rows, figures),
        output_dir / SUMMARY_FILENAME,
    )

    for figure in figures:
        print(f"Wrote {output_dir / figure.file_name}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()