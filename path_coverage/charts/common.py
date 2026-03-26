from __future__ import annotations

import matplotlib.pyplot as plt
import seaborn as sns


COMPARISON_PALETTE = [
    "#3D5A80",
    "#2A9D8F",
    "#5B8E3E",
    "#B08968",
    "#E07A5F",
    "#B56576",
    "#6D597A",
    "#8D99AE",
    "#CDA15E",
]

sns.set_theme(style="whitegrid")


def build_comparison_palette(color_count: int) -> list[tuple[float, float, float]]:
    if color_count <= len(COMPARISON_PALETTE):
        return sns.color_palette(COMPARISON_PALETTE[:color_count])

    extra_colors = sns.color_palette("husl", n_colors=color_count - len(COMPARISON_PALETTE))
    return sns.color_palette(COMPARISON_PALETTE) + list(extra_colors)


def build_annotation_offsets(target_values: list[float]) -> list[int]:
    if not target_values:
        return []

    sorted_pairs = sorted(enumerate(target_values), key=lambda pair: pair[1])
    offsets = [0] * len(target_values)
    for index, (original_index, _target_value) in enumerate(sorted_pairs):
        offsets[original_index] = 6 + index * 4
    return offsets


def save_and_close(fig: plt.Figure, output_file) -> None:
    fig.tight_layout()
    fig.savefig(output_file, dpi=200)
    plt.close(fig)