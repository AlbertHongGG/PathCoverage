from __future__ import annotations

from dataclasses import dataclass
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