from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseChart(ABC):
    @abstractmethod
    def render(self, *args, **kwargs) -> Path:
        raise NotImplementedError