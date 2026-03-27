from __future__ import annotations

from pathlib import Path

from .common import natural_label_key
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
        project_inputs = self._resolver.resolve_projects(
            graph_root_dir=graph_root_dir,
            path_root_dir=path_root_dir,
            output_root_dir=output_root_dir,
        )
        strategy_names = sorted(
            {project_input.strategy_name for project_input in project_inputs},
            key=natural_label_key,
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

        comparison_root_dir = output_root_dir.resolve() / "comparison"
        for project_name in sorted(results_by_project, key=natural_label_key):
            comparison_output_dir = comparison_root_dir / project_name
            self._service.write_strategy_comparison(
                project_name=project_name,
                strategy_results=results_by_project[project_name],
                output_dir=comparison_output_dir,
            )

        strategy_score_summary_path, strategy_score_chart_path = self._service.write_strategy_score_summary(
            results_by_project=results_by_project,
            output_dir=comparison_root_dir,
        )

        path_count_compare_root_dir = output_root_dir.resolve() / "path_count_compare"
        self._service.write_path_count_comparisons(
            results_by_project=results_by_project,
            output_dir=path_count_compare_root_dir,
        )

        path_scatter_root_dir = output_root_dir.resolve() / "path_scatter"
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
            comparison_root_dir=comparison_root_dir,
            path_count_compare_root_dir=path_count_compare_root_dir,
            path_scatter_root_dir=path_scatter_root_dir,
            strategy_score_summary_path=strategy_score_summary_path,
            strategy_score_chart_path=strategy_score_chart_path,
        )