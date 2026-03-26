from __future__ import annotations

from collections.abc import Mapping

from .metrics import CoverageMetricResolver
from ..common import natural_label_key
from ..models import AnalysisResult, CoverageMetric


class StrategyScoreSummaryBuilder:
    def __init__(self, metric_resolver: CoverageMetricResolver | None = None) -> None:
        self._metric_resolver = metric_resolver or CoverageMetricResolver()

    def build(
        self,
        results_by_project: Mapping[str, Mapping[str, AnalysisResult]],
    ) -> tuple[dict[str, object], list[str], dict[str, list[int]]]:
        strategy_names = sorted(
            {
                strategy_name
                for project_results in results_by_project.values()
                for strategy_name in project_results
            },
            key=natural_label_key,
        )
        if not strategy_names:
            raise ValueError("No strategy results were provided for score aggregation.")

        total_scores = {strategy_name: 0 for strategy_name in strategy_names}
        per_project_scores = {strategy_name: [] for strategy_name in strategy_names}
        cumulative_scores_by_strategy = {strategy_name: [] for strategy_name in strategy_names}
        project_breakdowns: list[dict[str, object]] = []
        ordered_project_names = sorted(results_by_project, key=natural_label_key)

        for project_name in ordered_project_names:
            strategy_results = results_by_project[project_name]
            metric_breakdowns: list[dict[str, object]] = []
            project_total_scores = {strategy_name: 0 for strategy_name in strategy_names}
            for metric in CoverageMetric:
                metric_scores, ranking_rows = self._score_metric(strategy_results, metric)
                for strategy_name, score in metric_scores.items():
                    total_scores[strategy_name] += score
                    project_total_scores[strategy_name] += score

                metric_breakdowns.append(
                    {
                        "metric": metric.value,
                        "scores": metric_scores,
                        "ranking": ranking_rows,
                    }
                )

            for strategy_name in strategy_names:
                per_project_scores[strategy_name].append(project_total_scores[strategy_name])
                cumulative_total = project_total_scores[strategy_name]
                if cumulative_scores_by_strategy[strategy_name]:
                    cumulative_total += cumulative_scores_by_strategy[strategy_name][-1]
                cumulative_scores_by_strategy[strategy_name].append(cumulative_total)

            project_breakdowns.append(
                {
                    "projectName": project_name,
                    "strategyScores": project_total_scores,
                    "metrics": metric_breakdowns,
                }
            )

        ordered_total_scores = {strategy_name: total_scores[strategy_name] for strategy_name in strategy_names}
        ordered_project_scores = {
            strategy_name: per_project_scores[strategy_name] for strategy_name in strategy_names
        }
        ordered_cumulative_scores = {
            strategy_name: cumulative_scores_by_strategy[strategy_name] for strategy_name in strategy_names
        }
        payload = {
            "projectNames": ordered_project_names,
            "strategyCount": len(strategy_names),
            "strategyScores": ordered_total_scores,
            "projectScoresByStrategy": ordered_project_scores,
            "cumulativeScoresByStrategy": ordered_cumulative_scores,
            "projects": project_breakdowns,
        }
        return payload, ordered_project_names, ordered_cumulative_scores

    def _score_metric(
        self,
        strategy_results: Mapping[str, AnalysisResult],
        metric: CoverageMetric,
    ) -> tuple[dict[str, int], list[dict[str, object]]]:
        evaluations: list[dict[str, object]] = []
        for strategy_name, result in strategy_results.items():
            reached_total, comparison_value = self._resolve_metric_value(metric, result)
            evaluations.append(
                {
                    "strategyName": strategy_name,
                    "reachedTotal": reached_total,
                    "comparisonValue": comparison_value,
                }
            )

        evaluations.sort(
            key=lambda row: (
                0 if row["reachedTotal"] else 1,
                row["comparisonValue"] if row["reachedTotal"] else -row["comparisonValue"],
                natural_label_key(str(row["strategyName"])),
            )
        )

        scores: dict[str, int] = {}
        ranking_rows: list[dict[str, object]] = []
        dense_rank = 0
        previous_signature: tuple[bool, float] | None = None
        strategy_count = len(evaluations)
        for row in evaluations:
            signature = (bool(row["reachedTotal"]), float(row["comparisonValue"]))
            if signature != previous_signature:
                dense_rank += 1
                previous_signature = signature

            score = strategy_count - dense_rank + 1
            strategy_name = str(row["strategyName"])
            scores[strategy_name] = score
            ranking_rows.append(
                {
                    "strategyName": strategy_name,
                    "rank": dense_rank,
                    "score": score,
                    "reachedTotal": row["reachedTotal"],
                    "comparisonValue": row["comparisonValue"],
                }
            )

        return scores, ranking_rows

    def _resolve_metric_value(self, metric: CoverageMetric, result: AnalysisResult) -> tuple[bool, float]:
        tolerance = 1e-9
        total_value = self._metric_resolver.reference_total(metric, result.totals)
        for point in result.coverage_points:
            metric_value = self._metric_resolver.value_from_point(metric, point, result.totals)
            if metric_value >= total_value - tolerance:
                return True, float(point.path_count)

        if not result.coverage_points:
            return False, 0.0

        last_value = self._metric_resolver.value_from_point(metric, result.coverage_points[-1], result.totals)
        return False, float(last_value)