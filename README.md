# Path Coverage

Use `uv run main.py` to process each matching strategy/project folder under `graph/` and `path/`, sort the path planner JSON files by incremental coverage, and generate absolute-count and ratio charts.

If you want every strategy/project output to compare only up to the same number of paths, pass `--max-paths-per-project <N>`. The limit is applied after sorting, so each chart and JSON summary uses at most the top `N` paths for that strategy/project.

Example:

```bash
uv run main.py --max-paths-per-project 20
```

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
```

Notes:

- `graph/<project>/data.json` remains the single source of graph data for each project.
- `path/<strategy>/<project>/*.json` contains one strategy's routing results for one project.
- Each strategy/project pair produces its own JSON summaries and four single-strategy charts under `output/<strategy>/<project>/`.
- `--max-paths-per-project` can be used to cap how many sorted paths are included per strategy/project, which makes cross-strategy project comparison easier when the original path counts differ.
- After all runs finish, the tool generates four comparison charts for every discovered project under `output/comparison/<project>/`, so the comparison folder structure follows the actual project folders found under the strategy inputs.