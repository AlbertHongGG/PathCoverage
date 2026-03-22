from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    graph_root_dir: Path
    path_root_dir: Path
    output_dir: Path


class SettingsLoader:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def load(self) -> AppSettings:
        env_file = self._project_root / ".env"
        if env_file.exists():
            self._load_env_file(env_file)

        graph_root_dir = self._resolve_project_directory(
            os.getenv("PATH_COVERAGE_GRAPH_DIR") or os.getenv("PATH_COVERAGE_GRAPH_JSON", "/graph"),
        )
        path_root_dir = self._resolve_project_directory(
            os.getenv("PATH_COVERAGE_PATH_DIR") or os.getenv("PATH_COVERAGE_PATH_JSON_DIR", "/path"),
        )
        output_dir = self._resolve_project_path(
            os.getenv("PATH_COVERAGE_OUTPUT_DIR", "/output"),
        )

        return AppSettings(
            graph_root_dir=graph_root_dir,
            path_root_dir=path_root_dir,
            output_dir=output_dir,
        )

    def _load_env_file(self, env_file: Path) -> None:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip()

    def _resolve_project_path(self, raw_value: str) -> Path:
        value = raw_value.strip()
        if value.startswith("/"):
            value = value[1:]

        candidate = Path(value)
        if candidate.is_absolute():
            return candidate

        return (self._project_root / candidate).resolve()

    def _resolve_project_directory(self, raw_value: str) -> Path:
        candidate = self._resolve_project_path(raw_value)
        if candidate.suffix:
            return candidate.parent
        return candidate