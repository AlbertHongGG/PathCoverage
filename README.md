# Path Coverage

Use `uv run main.py` to process each matching strategy/project folder under `graph/` and `path/`, sort the path planner JSON files by incremental coverage, and generate absolute-count and ratio charts.

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
- After all runs finish, the tool generates four comparison charts for every discovered project under `output/comparison/<project>/`, so the comparison folder structure follows the actual project folders found under the strategy inputs.