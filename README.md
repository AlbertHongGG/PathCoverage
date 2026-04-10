# Path Coverage

Use `uv run main.py` to process each matching strategy/project folder under `graph/` and `path/`, sort the path planner JSON files by incremental coverage, and generate per-strategy charts, cross-strategy comparison charts, fixed-path comparison charts, and project scatter plots.

If you want every strategy/project output to compare only up to the same number of paths, pass `--max-paths-per-project <N>`. The limit is applied after sorting, so each chart and JSON summary uses at most the top `N` paths for that strategy/project.

Example:

```bash
uv run main.py --max-paths-per-project 20
```

Chinese output guide: [docs/output-structure-zh.md](docs/output-structure-zh.md)

Expected layout:

```text
graph/
	1-1/
		data.json
	1-2/
		data.json
path/
	Ex1/
		1-1/
			*.json
		1-2/
			*.json
	Ex2/
		1-1/
			*.json
		1-2/
			*.json
output/
	coverage/
		strategies/
			Ex1/
				1-1/
					1-1_sorted_paths.json
					1-1_coverage_summary.json
					1-1_state_coverage.png
					...
			Ex2/
				1-1/
					1-1_sorted_paths.json
					1-1_coverage_summary.json
					1-1_state_coverage.png
					...
		comparison/
			1-1/
				1-1_strategy_state_coverage.png
				1-1_strategy_transition_coverage.png
				1-1_strategy_state_coverage_ratio.png
				1-1_strategy_transition_coverage_ratio.png
			average/
				average_strategy_state_coverage.png
				average_strategy_transition_coverage.png
				average_strategy_state_coverage_ratio.png
				average_strategy_transition_coverage_ratio.png
				summary.json
			strategy_score_summary.json
			strategy_score_cumulative.png
	analysis/
		path_count_compare/
			paths-5/
				state_coverage.png
				transition_coverage.png
				state_coverage_ratio.png
				transition_coverage_ratio.png
				summary.json
			paths-10/
				...
		path_scatter/
			comparison/
				paths-5/
					state_coverage_vs_average_path_length.png
					state_coverage_ratio_vs_average_path_length.png
					transition_coverage_vs_average_path_length.png
					transition_coverage_ratio_vs_average_path_length.png
					summary.json
				paths-10/
					...
			1-1/
				paths-5/
					state_coverage_vs_average_path_length.png
					state_coverage_ratio_vs_average_path_length.png
					transition_coverage_vs_average_path_length.png
					transition_coverage_ratio_vs_average_path_length.png
					summary.json
				paths-10/
					...
```

Notes:

- `graph/<project>/data.json` remains the single source of graph data for each project.
- `path/<strategy>/<project>/*.json` contains one strategy's routing results for one project.
- Each strategy/project pair produces its own JSON summaries and four single-strategy charts under `output/coverage/strategies/<strategy>/<project>/`.
- `--max-paths-per-project` can be used to cap how many sorted paths are included per strategy/project, which makes cross-strategy project comparison easier when the original path counts differ.
- After all runs finish, the tool generates four comparison charts for every discovered project under `output/coverage/comparison/<project>/`, so the comparison folder structure follows the actual project folders found under the strategy inputs.
- `output/coverage/comparison/average/` contains four average comparison line charts and a `summary.json`. Each chart averages the per-path coverage value across all discovered projects, and the X axis respects the effective `--max-paths-per-project` cap.
- The root `output/coverage/comparison/` folder also includes an aggregated strategy scoreboard JSON and a cumulative score chart built from all project comparison metrics.
- The root `output/analysis/path_count_compare/` folder contains one subfolder per fixed path cap (`paths-5`, `paths-10`, `paths-15`, `paths-20`, `paths-25`, `paths-30`). Each subfolder includes four bar charts that compare average coverage across all projects at that path cap, plus a `summary.json` file.
- The root `output/analysis/path_scatter/comparison/` folder contains one subfolder per fixed path cap. Each subfolder includes four scatter plots where the X axis is the average value of one coverage metric across all projects, the Y axis is average path length across all projects, and every strategy is rendered as a labeled point. Each metric also includes a matching `_pareto_frontier.png` variant that fades and crosses out dominated strategies so the Pareto-optimal choices stand out.
- The root `output/analysis/path_scatter/` folder contains one subfolder per project, and inside each project folder one subfolder per fixed path cap. Each of those subfolders contains four scatter plots where the X axis is one of state coverage, state coverage ratio, transition coverage, or transition coverage ratio, the Y axis is average path length, and every strategy is rendered as a labeled point. Each metric also includes a matching `_pareto_frontier.png` variant that keeps the same data but highlights the Pareto frontier for "higher coverage, shorter paths" decisions.
- `uv run manual_verification_scatter.py --project 1-1` reads `每個專案的 32 Path整理/1-1.json` and writes `output/analysis/feature_completion_scatter/1-1/paths-N/`. These scatter plots reuse the same four X-axis coverage metrics, but the Y axis becomes the ratio of distinct `manualVerification.items` labels with `completed=true` against the project checklist total. When `文件資料/專案計畫/<project>/FeatureChecklist.md` is not available, the script falls back to the union of observed item labels and records that fallback source in `summary.json`.
- `uv run manual_verification_scatter.py --comparison-only` writes cross-project averages to `output/analysis/feature_completion_scatter/comparison/paths-N/`. Each subfolder contains the same four coverage metrics, but both axes are averaged across all analyzed projects and the Y axis is the average feature completion ratio.
- The fixed path counts are treated as a path cap rather than a minimum requirement. If a strategy/project pair has fewer than `N` sorted paths, the charts use the last available coverage snapshot and the average path length over the actual available path count.