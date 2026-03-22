from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .coverage import CoverageCalculator
from .graph_loader import GraphLoader
from .models import AnalysisResult
from .path_loader import PathLoader
from .plotter import CoveragePlotter
from .sorter import PathCandidateSorter


class PathCoverageService:
    def __init__(
        self,
        graph_loader: GraphLoader | None = None,
        path_loader: PathLoader | None = None,
        sorter: PathCandidateSorter | None = None,
        coverage_calculator: CoverageCalculator | None = None,
        plotter: CoveragePlotter | None = None,
    ) -> None:
        self._graph_loader = graph_loader or GraphLoader()
        self._path_loader = path_loader or PathLoader()
        self._sorter = sorter or PathCandidateSorter()
        self._coverage_calculator = coverage_calculator or CoverageCalculator()
        self._plotter = plotter or CoveragePlotter()

    def run(
        self,
        strategy_name: str,
        project_name: str,
        graph_file: Path,
        path_files: list[Path],
        output_dir: Path,
    ) -> AnalysisResult:
        graph = self._graph_loader.load(graph_file)
        aggregated_paths = self._path_loader.load_many(path_files)
        sorted_paths = self._sorter.sort(aggregated_paths, graph)
        coverage_points, totals = self._coverage_calculator.calculate(
            [path.edge_ids for path in sorted_paths],
            graph,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_sorted_paths(strategy_name, project_name, sorted_paths, output_dir)
        self._write_coverage_summary(
            strategy_name,
            project_name,
            coverage_points,
            totals.total_states,
            totals.total_transitions,
            output_dir,
        )
        self._plotter.plot(coverage_points, totals, output_dir, file_prefix=project_name)

        return AnalysisResult(
            strategy_name=strategy_name,
            project_name=project_name,
            sorted_paths=sorted_paths,
            coverage_points=coverage_points,
            totals=totals,
        )

    def write_strategy_comparison(
        self,
        project_name: str,
        strategy_results: Mapping[str, AnalysisResult],
        output_dir: Path,
    ) -> tuple[Path, Path, Path, Path]:
        if not strategy_results:
            raise ValueError(f"No strategy results were provided for project '{project_name}'")

        output_dir.mkdir(parents=True, exist_ok=True)
        return self._plotter.plot_strategy_comparison(project_name, strategy_results, output_dir)

    def _write_sorted_paths(self, strategy_name: str, project_name: str, sorted_paths, output_dir: Path) -> None:
        payload = {
            "strategyName": strategy_name,
            "projectName": project_name,
            "paths": [
                {
                    "sortedIndex": index,
                    "pathId": f"path-{index}",
                    "originalSequence": path.sequence_number,
                    "sourceFile": str(path.source_file),
                    "sourcePathId": path.source_path_id,
                    "name": path.display_name,
                    "semanticGoal": path.semantic_goal,
                    "edgeIds": path.edge_ids,
                }
                for index, path in enumerate(sorted_paths, start=1)
            ]
        }
        (output_dir / f"{project_name}_sorted_paths.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_coverage_summary(
        self,
        strategy_name: str,
        project_name: str,
        coverage_points,
        total_states: int,
        total_transitions: int,
        output_dir: Path,
    ) -> None:
        payload = {
            "strategyName": strategy_name,
            "projectName": project_name,
            "totals": {
                "states": total_states,
                "transitions": total_transitions,
            },
            "points": [
                {
                    "pathCount": point.path_count,
                    "coveredStates": point.covered_states,
                    "stateCoverageRatio": point.covered_states / total_states if total_states else 0.0,
                    "coveredTransitions": point.covered_transitions,
                    "transitionCoverageRatio": point.covered_transitions / total_transitions if total_transitions else 0.0,
                }
                for point in coverage_points
            ],
        }
        (output_dir / f"{project_name}_coverage_summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )