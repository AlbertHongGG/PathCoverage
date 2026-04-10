from __future__ import annotations

from .snapshots import PathLimitSnapshotSelector
from ..models import CoverageMetric, CoveragePoint, CoverageSnapshot, CoverageTotals


class CoverageMetricResolver:
    _DISPLAY_NAMES = {
        CoverageMetric.STATE_COVERAGE: "State Coverage",
        CoverageMetric.STATE_COVERAGE_RATIO: "State Coverage",
        CoverageMetric.TRANSITION_COVERAGE: "Transition Coverage",
        CoverageMetric.TRANSITION_COVERAGE_RATIO: "Transition Coverage",
    }

    _VALUE_LABELS = {
        CoverageMetric.STATE_COVERAGE: "State Coverage",
        CoverageMetric.STATE_COVERAGE_RATIO: "State Coverage",
        CoverageMetric.TRANSITION_COVERAGE: "Transition Coverage",
        CoverageMetric.TRANSITION_COVERAGE_RATIO: "Transition Coverage",
    }

    _LINE_COLORS = {
        CoverageMetric.STATE_COVERAGE: "#2C7FB8",
        CoverageMetric.STATE_COVERAGE_RATIO: "#1B9E77",
        CoverageMetric.TRANSITION_COVERAGE: "#D95F0E",
        CoverageMetric.TRANSITION_COVERAGE_RATIO: "#7570B3",
    }

    def display_name(self, metric: CoverageMetric) -> str:
        return self._DISPLAY_NAMES[metric]

    def value_label(self, metric: CoverageMetric) -> str:
        return self._VALUE_LABELS[metric]

    def average_value_label(self, metric: CoverageMetric) -> str:
        return f"Average {self.value_label(metric)}"

    def y_label(self, metric: CoverageMetric) -> str:
        return self.value_label(metric)

    def line_color(self, metric: CoverageMetric) -> str:
        return self._LINE_COLORS[metric]

    def is_ratio(self, metric: CoverageMetric) -> bool:
        return metric in {
            CoverageMetric.STATE_COVERAGE_RATIO,
            CoverageMetric.TRANSITION_COVERAGE_RATIO,
        }

    def reference_total(self, metric: CoverageMetric, totals: CoverageTotals) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return float(totals.total_states)
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return float(totals.total_transitions)
        return 1.0

    def value_from_point(
        self,
        metric: CoverageMetric,
        point: CoveragePoint,
        totals: CoverageTotals,
    ) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return float(point.covered_states)
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return float(point.covered_transitions)
        if metric == CoverageMetric.STATE_COVERAGE_RATIO:
            return (point.covered_states / totals.total_states) if totals.total_states else 0.0
        return (point.covered_transitions / totals.total_transitions) if totals.total_transitions else 0.0

    def value_from_snapshot(self, metric: CoverageMetric, snapshot: CoverageSnapshot) -> float:
        if metric == CoverageMetric.STATE_COVERAGE:
            return float(snapshot.covered_states)
        if metric == CoverageMetric.TRANSITION_COVERAGE:
            return float(snapshot.covered_transitions)
        if metric == CoverageMetric.STATE_COVERAGE_RATIO:
            return snapshot.state_coverage_ratio
        return snapshot.transition_coverage_ratio

    def resolve_metric_value(self, metric: CoverageMetric, snapshot: CoverageSnapshot) -> float:
        return self.value_from_snapshot(metric, snapshot)

    def format_value(self, metric: CoverageMetric, value: float) -> str:
        if self.is_ratio(metric):
            return f"{value:.2f}"
        return f"{int(round(value))}"

    def comparison_title(self, metric: CoverageMetric, project_name: str) -> str:
        return f"{self.display_name(metric)} by Strategy ({project_name})"

    def single_title(self, metric: CoverageMetric) -> str:
        return f"{self.display_name(metric)} by Path Count"

    def average_title(self, metric: CoverageMetric, path_limit: int) -> str:
        return f"Average {self.display_name(metric)} Across Strategies"

    def average_comparison_title(
        self,
        metric: CoverageMetric,
        project_count: int,
        max_path_count: int,
    ) -> str:
        return f"Average {self.display_name(metric)} by Strategy Across Projects"

    def scatter_title(self, metric: CoverageMetric, project_name: str, path_limit: int) -> str:
        return f"{self.display_name(metric)} and Average Path Length ({project_name})"