from __future__ import annotations

import argparse
from pathlib import Path

from path_coverage import CoverageApplication
from path_coverage.input_resolver import PathInputResolver
from path_coverage.settings import SettingsLoader


def positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return parsed_value


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
    parser.add_argument(
        "--max-paths-per-project",
        type=positive_int,
        default=32,
        help="Maximum number of sorted paths to keep per strategy/project when generating summaries and charts. Defaults to 32.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    resolver = PathInputResolver()
    project_inputs = resolver.resolve_projects(
        graph_root_dir=args.graph_dir,
        path_root_dir=args.path_dir,
        output_root_dir=args.output_dir,
    )
    strategy_names = sorted({project_input.strategy_name for project_input in project_inputs})
    app = CoverageApplication(resolver=resolver)

    print(f"Strategy/project pairs: {len(project_inputs)}")
    print(f"Strategies: {len(strategy_names)} ({', '.join(strategy_names)})")
    print(f"Graph root: {args.graph_dir.resolve()}")
    print(f"Path root: {args.path_dir.resolve()}")
    print(f"Output root: {args.output_dir.resolve()}")
    print(
        "Max paths per project: "
        f"{args.max_paths_per_project if args.max_paths_per_project is not None else 'unlimited'}"
    )

    summary = app.run(
        graph_root_dir=args.graph_dir,
        path_root_dir=args.path_dir,
        output_root_dir=args.output_dir,
        max_paths_per_project=args.max_paths_per_project,
    )

    print(f"Coverage output root: {summary.coverage_root_dir}")
    print(f"Analysis output root: {summary.analysis_root_dir}")

    for project_result in summary.project_results:
        project_input = project_result.project_input
        result = project_result.result
        project_label = f"{project_input.strategy_name}/{project_input.project_name}"
        print(f"[{project_label}] Sorted paths: {len(result.sorted_paths)}")
        print(f"[{project_label}] Path JSON files: {len(project_input.path_files)}")
        print(f"[{project_label}] Graph JSON: {project_input.graph_file.resolve()}")
        print(f"[{project_label}] Output directory: {project_input.output_dir.resolve()}")
        print(f"[{project_label}] Total states: {result.totals.total_states}")
        print(f"[{project_label}] Total transitions: {result.totals.total_transitions}")

    for project_name in sorted(summary.results_by_project):
        comparison_results = summary.results_by_project[project_name]
        if not comparison_results:
            print(
                f"[coverage/comparison/{project_name}] No strategy results were found; comparison charts were skipped."
            )
            continue

        comparison_output_dir = summary.comparison_root_dir / project_name
        print(f"[coverage/comparison/{project_name}] Strategies: {len(comparison_results)}")
        print(f"[coverage/comparison/{project_name}] Output directory: {comparison_output_dir}")

    print(f"[coverage/comparison/average] Output directory: {summary.average_comparison_root_dir}")
    print(f"[coverage/comparison] Strategy score summary: {summary.strategy_score_summary_path}")
    print(f"[coverage/comparison] Strategy score chart: {summary.strategy_score_chart_path}")
    print(f"[analysis/path_count_compare] Output directory: {summary.path_count_compare_root_dir}")
    print(f"[analysis/path_scatter] Output directory: {summary.path_scatter_root_dir}")


if __name__ == "__main__":
    main()