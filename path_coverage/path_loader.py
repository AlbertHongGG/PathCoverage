from __future__ import annotations

import json
from pathlib import Path

from .models import AggregatedPath


class PathLoader:
    def load_many(self, path_files: list[Path]) -> list[AggregatedPath]:
        aggregated_paths: list[AggregatedPath] = []
        next_sequence = 1

        for path_file in path_files:
            payload = json.loads(path_file.read_text(encoding="utf-8"))
            parsed_response = payload.get("parsedResponse", {})
            paths = parsed_response.get("paths", [])

            for raw_path in paths:
                edge_ids = [
                    edge_id
                    for edge_id in (raw_path.get("edgeIds") or [])
                    if ".contains." not in edge_id
                ]
                if not edge_ids:
                    continue

                aggregated_paths.append(
                    AggregatedPath(
                        sequence_number=next_sequence,
                        source_file=path_file,
                        source_path_id=raw_path.get("pathId"),
                        source_name=raw_path.get("name") or raw_path.get("pathName"),
                        semantic_goal=raw_path.get("semanticGoal"),
                        edge_ids=list(edge_ids),
                    )
                )
                next_sequence += 1

        return aggregated_paths