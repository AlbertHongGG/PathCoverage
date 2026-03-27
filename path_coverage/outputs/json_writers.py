from __future__ import annotations

import json
from pathlib import Path

from ..models import AnalysisResult, ComparisonScatterDataset, PathCountComparisonDataset, ProjectScatterDataset


class JsonWriter:
    def write(self, payload: dict[str, object], output_file: Path) -> Path:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_file


class SortedPathsWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, result: AnalysisResult, output_dir: Path) -> Path:
        payload = {
            "strategyName": result.strategy_name,
            "projectName": result.project_name,
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
                    "pathLength": len(path.edge_ids),
                }
                for index, path in enumerate(result.sorted_paths, start=1)
            ],
        }
        return self._json_writer.write(payload, output_dir / f"{result.project_name}_sorted_paths.json")


class CoverageSummaryWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, result: AnalysisResult, output_dir: Path, max_paths: int | None = None) -> Path:
        payload = {
            "strategyName": result.strategy_name,
            "projectName": result.project_name,
            "maxPathsPerProject": max_paths,
            "totals": {
                "states": result.totals.total_states,
                "transitions": result.totals.total_transitions,
            },
            "points": [
                {
                    "pathCount": point.path_count,
                    "coveredStates": point.covered_states,
                    "stateCoverageRatio": point.covered_states / result.totals.total_states if result.totals.total_states else 0.0,
                    "coveredTransitions": point.covered_transitions,
                    "transitionCoverageRatio": point.covered_transitions / result.totals.total_transitions if result.totals.total_transitions else 0.0,
                }
                for point in result.coverage_points
            ],
        }
        return self._json_writer.write(payload, output_dir / f"{result.project_name}_coverage_summary.json")


class PathCountComparisonSummaryWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, datasets: list[PathCountComparisonDataset], output_file: Path) -> Path:
        if not datasets:
            raise ValueError("At least one dataset is required to write a path count comparison summary.")

        first_dataset = datasets[0]
        payload = {
            "pathLimit": first_dataset.path_limit,
            "strategyOrder": first_dataset.strategy_order,
            "projectCount": len(first_dataset.project_names),
            "projectNames": first_dataset.project_names,
            "metrics": {
                dataset.metric.value: {
                    "strategies": [
                        {
                            "strategyName": row.strategy_name,
                            "averageValue": row.average_value,
                            "projectCount": row.project_count,
                            "actualPathCounts": row.actual_path_counts,
                            "projectValues": row.project_values,
                        }
                        for row in dataset.strategy_rows
                    ]
                }
                for dataset in datasets
            },
        }
        return self._json_writer.write(payload, output_file)


class ProjectScatterSummaryWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, dataset: ProjectScatterDataset, output_file: Path) -> Path:
        payload = {
            "projectName": dataset.project_name,
            "pathLimit": dataset.path_limit,
            "points": [
                {
                    "strategyName": point.strategy_name,
                    "stateCoverage": point.state_coverage,
                    "stateCoverageRatio": point.state_coverage_ratio,
                    "transitionCoverage": point.transition_coverage,
                    "transitionCoverageRatio": point.transition_coverage_ratio,
                    "averagePathLength": point.average_path_length,
                    "actualPathCountUsed": point.actual_path_count_used,
                }
                for point in dataset.strategy_points
            ],
        }
        return self._json_writer.write(payload, output_file)


class ComparisonScatterSummaryWriter:
    def __init__(self, json_writer: JsonWriter | None = None) -> None:
        self._json_writer = json_writer or JsonWriter()

    def write(self, dataset: ComparisonScatterDataset, output_file: Path) -> Path:
        payload = {
            "pathLimit": dataset.path_limit,
            "strategyOrder": dataset.strategy_order,
            "projectCount": len(dataset.project_names),
            "projectNames": dataset.project_names,
            "points": [
                {
                    "strategyName": point.strategy_name,
                    "stateCoverageAverage": point.state_coverage_average,
                    "stateCoverageRatioAverage": point.state_coverage_ratio_average,
                    "transitionCoverageAverage": point.transition_coverage_average,
                    "transitionCoverageRatioAverage": point.transition_coverage_ratio_average,
                    "averagePathLengthAverage": point.average_path_length_average,
                    "projectCount": point.project_count,
                    "actualPathCounts": point.actual_path_counts,
                }
                for point in dataset.strategy_points
            ],
        }
        return self._json_writer.write(payload, output_file)