from __future__ import annotations

import shutil
from pathlib import Path

from .common import (
    OUTPUT_ANALYSIS_DIRNAME,
    OUTPUT_AVERAGE_COMPARISON_DIRNAME,
    OUTPUT_COMPARISON_DIRNAME,
    OUTPUT_COVERAGE_DIRNAME,
    OUTPUT_PATH_COUNT_COMPARE_DIRNAME,
    OUTPUT_PATH_SCATTER_DIRNAME,
    OUTPUT_STRATEGY_RESULTS_DIRNAME,
    natural_label_key,
)
from .input_resolver import PathInputResolver
from .models import AnalysisResult, ApplicationProjectResult, ApplicationRunSummary
from .service import PathCoverageService


class CoverageApplication:
    def __init__(
        self,
        service: PathCoverageService | None = None,
        resolver: PathInputResolver | None = None,
    ) -> None:
        self._service = service or PathCoverageService()
        self._resolver = resolver or PathInputResolver()

    def run(
        self,
        graph_root_dir: Path,
        path_root_dir: Path,
        output_root_dir: Path,
        max_paths_per_project: int | None = None,
    ) -> ApplicationRunSummary:
        resolved_output_root = output_root_dir.resolve()
        project_inputs = self._resolver.resolve_projects(
            graph_root_dir=graph_root_dir,
            path_root_dir=path_root_dir,
            output_root_dir=output_root_dir,
        )
        strategy_names = sorted(
            {project_input.strategy_name for project_input in project_inputs},
            key=natural_label_key,
        )
        coverage_root_dir = resolved_output_root / OUTPUT_COVERAGE_DIRNAME
        strategy_outputs_root_dir = coverage_root_dir / OUTPUT_STRATEGY_RESULTS_DIRNAME
        comparison_root_dir = coverage_root_dir / OUTPUT_COMPARISON_DIRNAME
        average_comparison_root_dir = comparison_root_dir / OUTPUT_AVERAGE_COMPARISON_DIRNAME
        analysis_root_dir = resolved_output_root / OUTPUT_ANALYSIS_DIRNAME
        path_count_compare_root_dir = analysis_root_dir / OUTPUT_PATH_COUNT_COMPARE_DIRNAME
        path_scatter_root_dir = analysis_root_dir / OUTPUT_PATH_SCATTER_DIRNAME

        self._reset_output_directories(
            output_root_dir=resolved_output_root,
            strategy_names=strategy_names,
            managed_dirs=(coverage_root_dir, analysis_root_dir),
        )

        results_by_project: dict[str, dict[str, AnalysisResult]] = {}
        project_results: list[ApplicationProjectResult] = []

        for project_input in project_inputs:
            result = self._service.run(
                strategy_name=project_input.strategy_name,
                project_name=project_input.project_name,
                graph_file=project_input.graph_file,
                path_files=project_input.path_files,
                output_dir=project_input.output_dir,
                max_paths=max_paths_per_project,
            )
            results_by_project.setdefault(project_input.project_name, {})[project_input.strategy_name] = result
            project_results.append(ApplicationProjectResult(project_input=project_input, result=result))

        for project_name in sorted(results_by_project, key=natural_label_key):
            comparison_output_dir = comparison_root_dir / project_name
            self._service.write_strategy_comparison(
                project_name=project_name,
                strategy_results=results_by_project[project_name],
                output_dir=comparison_output_dir,
            )

        self._service.write_average_strategy_comparison(
            results_by_project=results_by_project,
            output_dir=average_comparison_root_dir,
        )

        strategy_score_summary_path, strategy_score_chart_path = self._service.write_strategy_score_summary(
            results_by_project=results_by_project,
            output_dir=comparison_root_dir,
        )

        self._service.write_path_count_comparisons(
            results_by_project=results_by_project,
            output_dir=path_count_compare_root_dir,
        )

        self._service.write_comparison_path_scatters(
            results_by_project=results_by_project,
            output_dir=path_scatter_root_dir / "comparison",
        )
        self._service.write_project_path_scatters(
            results_by_project=results_by_project,
            output_dir=path_scatter_root_dir,
        )

        return ApplicationRunSummary(
            strategy_names=strategy_names,
            project_results=project_results,
            results_by_project=results_by_project,
            coverage_root_dir=coverage_root_dir,
            strategy_outputs_root_dir=strategy_outputs_root_dir,
            comparison_root_dir=comparison_root_dir,
            average_comparison_root_dir=average_comparison_root_dir,
            analysis_root_dir=analysis_root_dir,
            path_count_compare_root_dir=path_count_compare_root_dir,
            path_scatter_root_dir=path_scatter_root_dir,
            strategy_score_summary_path=strategy_score_summary_path,
            strategy_score_chart_path=strategy_score_chart_path,
        )

    def _reset_output_directories(
        self,
        output_root_dir: Path,
        strategy_names: list[str],
        managed_dirs: tuple[Path, ...],
    ) -> None:
        for managed_dir in managed_dirs:
            if managed_dir.is_dir():
                shutil.rmtree(managed_dir)

        legacy_dirs = [
            output_root_dir / "comparison",
            output_root_dir / "compare",
            output_root_dir / "path_count_compare",
            output_root_dir / "path_scatter",
            *[output_root_dir / strategy_name for strategy_name in strategy_names],
        ]
        for legacy_dir in legacy_dirs:
            if legacy_dir.is_dir():
                shutil.rmtree(legacy_dir)