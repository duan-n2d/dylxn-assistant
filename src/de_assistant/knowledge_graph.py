from __future__ import annotations

from collections import defaultdict


class KnowledgeGraph:
    def __init__(self) -> None:
        self.entities: dict[str, str] = {}
        self.relations: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

    def add_entity(self, name: str, kind: str) -> None:
        self.entities[name] = kind

    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
    ) -> None:
        self.add_entity(source, self.entities.get(source, "entity"))
        self.add_entity(target, self.entities.get(target, "entity"))
        self.relations[source][relation].add(target)

    def has_relation(
        self,
        source: str,
        relation: str,
        target: str,
    ) -> bool:
        return target in self.relations.get(source, {}).get(relation, set())

    def related_nodes(self, source: str) -> set[str]:
        related: set[str] = set()
        for relation_map in self.relations.get(source, {}).values():
            related.update(relation_map)
        return related

    def as_dict(self) -> dict[str, object]:
        return {
            "entities": dict(self.entities),
            "relations": {
                source: {
                    relation: sorted(targets)
                    for relation, targets in rel_map.items()
                }
                for source, rel_map in self.relations.items()
            },
        }
