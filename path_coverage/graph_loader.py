from __future__ import annotations

import json
from pathlib import Path

from .models import RuntimeEdge, RuntimeGraph


class GraphLoader:
    def load(self, graph_file: Path) -> RuntimeGraph:
        payload = json.loads(graph_file.read_text(encoding="utf-8"))
        diagrams = payload.get("diagrams", [])

        state_ids: set[str] = set()
        edges_by_id: dict[str, RuntimeEdge] = {}
        entry_state_id: str | None = None

        for diagram in diagrams:
            diagram_id = diagram["id"]
            meta = diagram.get("meta", {})
            if diagram_id == "page_entry":
                entry_state_id = meta.get("entryStateId") or entry_state_id

            for state in diagram.get("states", []):
                state_id = state.get("id")
                if state_id:
                    state_ids.add(state_id)

            for transition in diagram.get("transitions", []):
                edge = self._build_transition_edge(diagram_id, transition)
                edges_by_id[edge.id] = edge

            for connector in diagram.get("connectors", []):
                if connector.get("type") == "contains":
                    continue
                edge = self._build_connector_edge(connector)
                edges_by_id[edge.id] = edge

        if not entry_state_id:
            raise ValueError("Cannot resolve page_entry entryStateId from graph JSON.")

        return RuntimeGraph(
            entry_state_id=entry_state_id,
            state_ids=state_ids,
            edges_by_id=edges_by_id,
        )

    def _build_transition_edge(self, diagram_id: str, transition: dict) -> RuntimeEdge:
        return RuntimeEdge(
            id=transition["id"],
            from_diagram_id=diagram_id,
            from_state_id=transition["from"],
            to_diagram_id=diagram_id,
            to_state_id=transition["to"],
            semantic=self._task_description(transition),
        )

    def _build_connector_edge(self, connector: dict) -> RuntimeEdge:
        from_ref = connector.get("from", {})
        to_ref = connector.get("to", {})
        return RuntimeEdge(
            id=connector["id"],
            from_diagram_id=from_ref.get("diagramId", ""),
            from_state_id=from_ref.get("stateId", ""),
            to_diagram_id=to_ref.get("diagramId", ""),
            to_state_id=to_ref.get("stateId", ""),
            semantic=self._task_description(connector),
        )

    def _task_description(self, edge_payload: dict) -> str:
        narrative = edge_payload.get("narrative", {})
        return narrative.get("taskDescription") or edge_payload.get("id", "")