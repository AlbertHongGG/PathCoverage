from __future__ import annotations

import warnings
from pathlib import Path

from .models import ProjectInput


class PathInputResolver:
    def resolve_projects(
        self,
        graph_root_dir: Path,
        path_root_dir: Path,
        output_root_dir: Path,
    ) -> list[ProjectInput]:
        resolved_graph_root = graph_root_dir.resolve()
        resolved_path_root = path_root_dir.resolve()
        resolved_output_root = output_root_dir.resolve()

        if not resolved_graph_root.is_dir():
            raise ValueError(f"Graph root directory does not exist: {graph_root_dir}")
        if not resolved_path_root.is_dir():
            raise ValueError(f"Path root directory does not exist: {path_root_dir}")

        graph_projects = self._project_directories(resolved_graph_root)
        strategy_directories = self._project_directories(resolved_path_root)

        if not graph_projects:
            raise ValueError(f"No graph project directories were found in: {graph_root_dir}")
        if not strategy_directories:
            raise ValueError(f"No strategy directories were found in path root: {path_root_dir}")

        graph_names = set(graph_projects)

        project_inputs: list[ProjectInput] = []
        for strategy_name, strategy_dir in sorted(strategy_directories.items()):
            strategy_projects = self._project_directories(strategy_dir)
            if not strategy_projects:
                raise ValueError(f"No project directories were found in strategy directory: {strategy_dir}")

            strategy_project_names = set(strategy_projects)
            unknown_graph_projects = sorted(strategy_project_names - graph_names)
            if unknown_graph_projects:
                warnings.warn(
                    "Skipping path projects with no matching graph data under strategy "
                    f"'{strategy_name}': {', '.join(unknown_graph_projects)}",
                    stacklevel=2,
                )

            matched_project_names = sorted(strategy_project_names & graph_names)
            if not matched_project_names:
                warnings.warn(
                    f"Strategy '{strategy_name}' has no projects that match graph data and will be skipped.",
                    stacklevel=2,
                )
                continue

            for project_name in matched_project_names:
                graph_file = graph_projects[project_name] / "data.json"
                if not graph_file.is_file():
                    raise ValueError(f"Graph data.json does not exist for project '{project_name}': {graph_file}")

                try:
                    path_files = self._resolve_path_files(strategy_projects[project_name])
                except ValueError:
                    warnings.warn(
                        "Skipping strategy/project directory with no path JSON files: "
                        f"{strategy_name}/{project_name}",
                        stacklevel=2,
                    )
                    continue

                project_inputs.append(
                    ProjectInput(
                        strategy_name=strategy_name,
                        project_name=project_name,
                        graph_file=graph_file,
                        path_files=path_files,
                        output_dir=resolved_output_root / strategy_name / project_name,
                    )
                )

        if not project_inputs:
            raise ValueError(
                "No matching strategy/project inputs were found between graph and path roots: "
                f"graph={graph_root_dir}, path={path_root_dir}"
            )

        return project_inputs

    def _project_directories(self, root_dir: Path) -> dict[str, Path]:
        return {
            candidate.name: candidate.resolve()
            for candidate in sorted(root_dir.iterdir())
            if candidate.is_dir()
        }

    def _resolve_path_files(self, directory: Path) -> list[Path]:
        resolved_paths: list[Path] = []
        seen: set[Path] = set()

        for candidate in sorted(directory.glob("*.json")):
            resolved_candidate = candidate.resolve()
            if resolved_candidate not in seen:
                resolved_paths.append(resolved_candidate)
                seen.add(resolved_candidate)

        if not resolved_paths:
            raise ValueError(f"No path JSON files were found in directory: {directory}")

        return resolved_paths