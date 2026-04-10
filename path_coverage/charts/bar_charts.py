from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

from .base import BaseChart
from .common import build_comparison_palette, save_and_close
from ..analysis.metrics import CoverageMetricResolver
from ..models import PathCountComparisonDataset


class PathCountAverageBarChart(BaseChart):
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def render(self, dataset: PathCountComparisonDataset, output_file: Path) -> Path:
        labels = [row.strategy_name for row in dataset.strategy_rows]
        values = [row.average_value for row in dataset.strategy_rows]
        palette = build_comparison_palette(len(labels))
        fig, ax = plt.subplots(figsize=(max(12, len(labels) * 1.2), 7))
        bars = sns.barplot(x=labels, y=values, palette=palette, ax=ax)

        for bar, value in zip(bars.patches, values, strict=True):
            ax.annotate(
                self._metric_resolver.format_value(dataset.metric, value),
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                va="bottom",
                fontsize=9,
                color="#1F2937",
            )

        ax.set_title(self._metric_resolver.average_title(dataset.metric, dataset.path_limit), pad=20)
        ax.set_xlabel("Strategy")
        ax.set_ylabel(self._metric_resolver.average_value_label(dataset.metric))
        ax.spines[["top", "right"]].set_visible(False)
        if self._metric_resolver.is_ratio(dataset.metric):
            ax.set_ylim(0, 1.05)
        else:
            max_value = max(values, default=0.0)
            ax.set_ylim(0, max_value * 1.15 if max_value else 1.0)
        save_and_close(fig, output_file)
        return output_file