from __future__ import annotations

import argparse
from pathlib import Path

from path_coverage import PathCoverageService
from path_coverage.input_resolver import PathInputResolver
from path_coverage.models import AnalysisResult
from path_coverage.settings import SettingsLoader


def parse_args() -> argparse.Namespace:
    settings = SettingsLoader(project_root=Path(__file__).resolve().parent).load()
    parser = argparse.ArgumentParser(
        description="Aggregate planner path JSON files per strategy/project pair, sort them by incremental coverage, and generate Seaborn charts.",
    )
    parser.add_argument(
        "--graph-dir",
        type=Path,
        default=settings.graph_root_dir,
        help="Root directory containing graph project folders. Defaults to PATH_COVERAGE_GRAPH_DIR or PATH_COVERAGE_GRAPH_JSON from .env.",
    )
    parser.add_argument(
        "--path-dir",
        type=Path,
        default=settings.path_root_dir,
        help="Root directory containing path project folders. Defaults to PATH_COVERAGE_PATH_DIR or PATH_COVERAGE_PATH_JSON_DIR from .env.",
    )
    parser.add_argument(
        "--output-dir",
        default=settings.output_dir,
        type=Path,
        help="Directory for sorted output and charts. Defaults to PATH_COVERAGE_OUTPUT_DIR from .env.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = PathCoverageService()
    resolver = PathInputResolver()
    project_inputs = resolver.resolve_projects(
        graph_root_dir=args.graph_dir,
        path_root_dir=args.path_dir,
        output_root_dir=args.output_dir,
    )
    strategy_names = sorted({project_input.strategy_name for project_input in project_inputs})
    results_by_project: dict[str, dict[str, AnalysisResult]] = {}

    print(f"Strategy/project pairs: {len(project_inputs)}")
    print(f"Strategies: {len(strategy_names)} ({', '.join(strategy_names)})")
    print(f"Graph root: {args.graph_dir.resolve()}")
    print(f"Path root: {args.path_dir.resolve()}")
    print(f"Output root: {args.output_dir.resolve()}")

    for project_input in project_inputs:
        result = service.run(
            strategy_name=project_input.strategy_name,
            project_name=project_input.project_name,
            graph_file=project_input.graph_file,
            path_files=project_input.path_files,
            output_dir=project_input.output_dir,
        )
        results_by_project.setdefault(project_input.project_name, {})[project_input.strategy_name] = result

        project_label = f"{project_input.strategy_name}/{project_input.project_name}"
        print(f"[{project_label}] Sorted paths: {len(result.sorted_paths)}")
        print(f"[{project_label}] Path JSON files: {len(project_input.path_files)}")
        print(f"[{project_label}] Graph JSON: {project_input.graph_file.resolve()}")
        print(f"[{project_label}] Output directory: {project_input.output_dir.resolve()}")
        print(f"[{project_label}] Total states: {result.totals.total_states}")
        print(f"[{project_label}] Total transitions: {result.totals.total_transitions}")

    comparison_root_dir = args.output_dir.resolve() / "comparison"
    for project_name in sorted(results_by_project):
        comparison_results = results_by_project[project_name]
        if not comparison_results:
            print(f"[comparison/{project_name}] No strategy results were found; comparison charts were skipped.")
            continue

        comparison_output_dir = comparison_root_dir / project_name
        service.write_strategy_comparison(
            project_name=project_name,
            strategy_results=comparison_results,
            output_dir=comparison_output_dir,
        )
        print(f"[comparison/{project_name}] Strategies: {len(comparison_results)}")
        print(f"[comparison/{project_name}] Output directory: {comparison_output_dir}")


if __name__ == "__main__":
    main()