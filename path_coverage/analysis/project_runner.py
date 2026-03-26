from __future__ import annotations

from pathlib import Path

from ..coverage import CoverageCalculator
from ..graph_loader import GraphLoader
from ..models import AnalysisResult
from ..path_loader import PathLoader
from ..sorter import PathCandidateSorter


class ProjectAnalysisRunner:
    def __init__(
        self,
        graph_loader: GraphLoader | None = None,
        path_loader: PathLoader | None = None,
        sorter: PathCandidateSorter | None = None,
        coverage_calculator: CoverageCalculator | None = None,
    ) -> None:
        self._graph_loader = graph_loader or GraphLoader()
        self._path_loader = path_loader or PathLoader()
        self._sorter = sorter or PathCandidateSorter()
        self._coverage_calculator = coverage_calculator or CoverageCalculator()

    def analyze(
        self,
        strategy_name: str,
        project_name: str,
        graph_file: Path,
        path_files: list[Path],
        max_paths: int | None = None,
    ) -> AnalysisResult:
        graph = self._graph_loader.load(graph_file)
        aggregated_paths = self._path_loader.load_many(path_files)
        sorted_paths = self._sorter.sort(aggregated_paths, graph)
        if max_paths is not None:
            sorted_paths = sorted_paths[:max_paths]

        coverage_points, totals = self._coverage_calculator.calculate(
            [path.edge_ids for path in sorted_paths],
            graph,
        )

        return AnalysisResult(
            strategy_name=strategy_name,
            project_name=project_name,
            sorted_paths=sorted_paths,
            coverage_points=coverage_points,
            totals=totals,
        )