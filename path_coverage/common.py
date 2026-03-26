from __future__ import annotations

import re

DEFAULT_PATH_LIMITS: tuple[int, ...] = (5, 10, 15, 20, 25, 30)


def natural_label_key(label: str) -> tuple[object, ...]:
    parts = re.split(r"(\d+)", label.casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def path_limit_dir_name(path_limit: int) -> str:
    return f"paths-{path_limit}"