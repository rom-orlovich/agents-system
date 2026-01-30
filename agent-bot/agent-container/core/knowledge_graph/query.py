from .models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    FunctionCallers,
    ClassHierarchy,
    ImpactAnalysis,
)


class KnowledgeGraphQuery:
    def __init__(
        self,
        entities: list[Entity],
        relations: list[Relation],
    ) -> None:
        self._entities = entities
        self._relations = relations
        self._entity_by_id: dict[str, Entity] = {e.id: e for e in entities}
        self._entity_by_name: dict[str, list[Entity]] = {}

        for entity in entities:
            if entity.name not in self._entity_by_name:
                self._entity_by_name[entity.name] = []
            self._entity_by_name[entity.name].append(entity)

    def find_callers(self, function_name: str) -> list[Entity]:
        target_entities = self._entity_by_name.get(function_name, [])
        target_ids = {f"func:{function_name}"} | {e.id for e in target_entities}

        callers: list[Entity] = []
        for relation in self._relations:
            if relation.type != RelationType.CALLS:
                continue
            if relation.target_id not in target_ids:
                continue

            caller_id = relation.source_id
            if caller_id.startswith("file:"):
                continue

            caller = self._entity_by_id.get(caller_id)
            if caller:
                callers.append(caller)

        return callers

    def find_class_hierarchy(self, class_name: str) -> ClassHierarchy:
        parents: list[Entity] = []
        children: list[Entity] = []

        class_entities = [
            e for e in self._entity_by_name.get(class_name, [])
            if e.type == EntityType.CLASS
        ]
        class_ids = {e.id for e in class_entities}

        for relation in self._relations:
            if relation.type != RelationType.EXTENDS:
                continue

            if relation.source_id in class_ids:
                parent = self._entity_by_id.get(relation.target_id)
                if parent:
                    parents.append(parent)

            if relation.target_id in class_ids:
                child = self._entity_by_id.get(relation.source_id)
                if child:
                    children.append(child)

        return ClassHierarchy(
            class_name=class_name,
            parents=parents,
            children=children,
        )

    def find_affected_by_change(self, file_path: str) -> list[str]:
        affected: set[str] = set()
        visited: set[str] = set()

        file_entities = [
            e for e in self._entities
            if e.file_path == file_path
        ]
        file_ids = {e.id for e in file_entities}
        file_ids.add(f"file:{file_path}")

        queue = list(file_ids)

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            for relation in self._relations:
                if relation.target_id != current_id:
                    continue
                if relation.type not in {
                    RelationType.IMPORTS,
                    RelationType.DEPENDS_ON,
                    RelationType.CALLS,
                }:
                    continue

                source = self._entity_by_id.get(relation.source_id)
                if source and source.file_path != file_path:
                    affected.add(source.file_path)
                    queue.append(relation.source_id)

        return list(affected)

    def find_tests_for_file(self, file_path: str) -> list[Entity]:
        tests: list[Entity] = []

        file_entities = [
            e for e in self._entities
            if e.file_path == file_path
        ]
        file_ids = {e.id for e in file_entities}

        for relation in self._relations:
            if relation.type != RelationType.TESTS:
                continue
            if relation.target_id not in file_ids:
                continue

            test = self._entity_by_id.get(relation.source_id)
            if test:
                tests.append(test)

        return tests

    def get_impact_analysis(self, file_path: str) -> ImpactAnalysis:
        affected_files = self.find_affected_by_change(file_path)
        tests = self.find_tests_for_file(file_path)
        affected_tests = [t.file_path for t in tests]

        risk_score = min(1.0, len(affected_files) / 10.0)

        return ImpactAnalysis(
            file_path=file_path,
            affected_files=affected_files,
            affected_tests=affected_tests,
            risk_score=risk_score,
        )
