from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class RuntimeEdge:
    id: str
    from_diagram_id: str
    from_state_id: str
    to_diagram_id: str
    to_state_id: str
    semantic: str


@dataclass(frozen=True)
class PathDraft:
    source_file: Path
    source_path_id: str | None
    source_name: str | None
    semantic_goal: str | None
    edge_ids: list[str]


@dataclass(frozen=True)
class AggregatedPath:
    sequence_number: int
    source_file: Path
    source_path_id: str | None
    source_name: str | None
    semantic_goal: str | None
    edge_ids: list[str]

    @property
    def display_name(self) -> str:
        return self.source_name or f"Path {self.sequence_number}"

    @property
    def signature(self) -> str:
        return ">".join(self.edge_ids)


@dataclass(frozen=True)
class ProjectInput:
    strategy_name: str
    project_name: str
    graph_file: Path
    path_files: list[Path]
    output_dir: Path


@dataclass(frozen=True)
class PlannerCandidate:
    path: AggregatedPath
    edges: list[RuntimeEdge]
    signature: str
    path_length: int
    new_edge_ids: list[str]
    new_node_ids: list[str]
    touched_node_ids: list[str]
    new_edge_count: int
    new_node_count: int
    has_new_coverage: bool


@dataclass(frozen=True)
class CandidateScore:
    incremental_new_edge_count: int
    incremental_new_node_count: int
    first_fresh_step_index: int | float
    touched_node_count: int
    historical_overlap_count: int
    path_length: int


@dataclass(frozen=True)
class CoveragePoint:
    path_count: int
    covered_states: int
    covered_transitions: int


@dataclass(frozen=True)
class CoverageTotals:
    total_states: int
    total_transitions: int


@dataclass(frozen=True)
class RuntimeGraph:
    entry_state_id: str
    state_ids: set[str]
    edges_by_id: dict[str, RuntimeEdge]

    @property
    def transition_ids(self) -> set[str]:
        return set(self.edges_by_id)


@dataclass(frozen=True)
class AnalysisResult:
    strategy_name: str
    project_name: str
    sorted_paths: list[AggregatedPath]
    coverage_points: list[CoveragePoint]
    totals: CoverageTotals


class CoverageMetric(str, Enum):
    STATE_COVERAGE = "state_coverage"
    STATE_COVERAGE_RATIO = "state_coverage_ratio"
    TRANSITION_COVERAGE = "transition_coverage"
    TRANSITION_COVERAGE_RATIO = "transition_coverage_ratio"


@dataclass(frozen=True)
class CoverageSnapshot:
    strategy_name: str
    project_name: str
    path_limit: int
    actual_path_count: int
    covered_states: int
    state_coverage_ratio: float
    covered_transitions: int
    transition_coverage_ratio: float
    average_path_length: float


@dataclass(frozen=True)
class PathCountComparisonRow:
    strategy_name: str
    average_value: float
    project_count: int
    actual_path_counts: list[int]
    project_values: dict[str, float]


@dataclass(frozen=True)
class PathCountComparisonDataset:
    path_limit: int
    metric: CoverageMetric
    strategy_order: list[str]
    project_names: list[str]
    strategy_rows: list[PathCountComparisonRow]


@dataclass(frozen=True)
class ProjectScatterPoint:
    strategy_name: str
    state_coverage: int
    state_coverage_ratio: float
    transition_coverage: int
    transition_coverage_ratio: float
    average_path_length: float
    actual_path_count_used: int


@dataclass(frozen=True)
class ProjectScatterDataset:
    project_name: str
    path_limit: int
    strategy_points: list[ProjectScatterPoint]


@dataclass(frozen=True)
class ComparisonScatterPoint:
    strategy_name: str
    state_coverage_average: float
    state_coverage_ratio_average: float
    transition_coverage_average: float
    transition_coverage_ratio_average: float
    average_path_length_average: float
    project_count: int
    actual_path_counts: dict[str, int]


@dataclass(frozen=True)
class ComparisonScatterDataset:
    path_limit: int
    strategy_order: list[str]
    project_names: list[str]
    strategy_points: list[ComparisonScatterPoint]


@dataclass(frozen=True)
class ApplicationProjectResult:
    project_input: ProjectInput
    result: AnalysisResult


@dataclass(frozen=True)
class ApplicationRunSummary:
    strategy_names: list[str]
    project_results: list[ApplicationProjectResult]
    results_by_project: dict[str, dict[str, AnalysisResult]]
    comparison_root_dir: Path
    path_count_compare_root_dir: Path
    path_scatter_root_dir: Path
    strategy_score_summary_path: Path
    strategy_score_chart_path: Path