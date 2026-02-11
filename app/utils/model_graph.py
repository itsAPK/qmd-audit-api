# model_graph.py

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Type, Set, Any
from dataclasses import dataclass
from functools import lru_cache
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty, aliased
from sqlmodel import SQLModel
from sqlalchemy.sql.selectable import Select
from sqlalchemy.orm import contains_eager

@dataclass
class JoinStep:
    src: Type[SQLModel]
    attr: str
    dst: Type[SQLModel]
    uselist: bool


class ModelGraph:
    """
    Build relationship graph for SQLModel classes
    Allows:
        - forward traversal
        - reverse traversal
        - deep path
        - BFS shortest path
        - join application with alias reuse
    """

    def __init__(self) -> None:
        self.forward: Dict[Type[SQLModel], Dict[str, JoinStep]] = {}
        self.reverse: Dict[Type[SQLModel], Dict[str, JoinStep]] = {}

    def register(self, model: Type[SQLModel]) -> None:
        if model in self.forward:
            return

        self.forward[model] = {}
        self.reverse.setdefault(model, {})

        mapper = sa_inspect(model)
        for rel_key, rel in mapper.relationships.items():
            target = rel.mapper.class_
            step = JoinStep(src=model, attr=rel_key, dst=target, uselist=rel.uselist)
            self.forward[model][rel_key] = step

            # reverse relation by type, no attr name
            self.reverse.setdefault(target, {})
            self.reverse[target][model.__name__.lower()] = JoinStep(
                src=target, attr=model.__name__.lower(), dst=model, uselist=rel.uselist
            )

    def build(self, models: List[Type[SQLModel]]) -> None:
        for m in models:
            self.register(m)

    @lru_cache(None)
    def shortest_path(
        self, src: Type[SQLModel], dst: Type[SQLModel]
    ) -> Optional[List[JoinStep]]:
        if src == dst:
            return []

        from collections import deque
        visited: Set[Type[SQLModel]] = set()
        queue = deque([(src, [])])

        while queue:
            node, path = queue.popleft()
            if node == dst:
                return path
            visited.add(node)

            # forward edges
            for step in self.forward.get(node, {}).values():
                if step.dst not in visited:
                    queue.append((step.dst, path + [step]))

            # reverse edges
            for reverse_key, rev_step in self.reverse.get(node, {}).items():
                if rev_step.dst not in visited:
                    queue.append((rev_step.dst, path + [rev_step]))

        return None

    def resolve_attr_path(
        self, base: Type[SQLModel], attrs: List[str]
    ) -> Tuple[List[JoinStep], str]:
        current = base
        join_plan: List[JoinStep] = []

        for attr in attrs[:-1]:
            if attr in self.forward[current]:
                step = self.forward[current][attr]
                join_plan.append(step)
                current = step.dst
            else:
                raise ValueError(f"Invalid relationship: {current.__name__}.{attr}")

        return join_plan, attrs[-1]

    from sqlalchemy.orm import contains_eager

    def apply_joins(self, query, plan, alias_cache):
    # The starting point is the base model (e.g., User)
        last_target = None 

        for step in plan:
            key = (step.src, step.attr)

            if key not in alias_cache:
                alias = aliased(step.dst)
                alias_cache[key] = alias
                
                # If last_target is None, we are joining the base model to the first alias
                # Otherwise, we join the previous alias to the new alias
                source = last_target if last_target is not None else step.src
                rel_attr = getattr(source, step.attr)
                
                # Explicitly join the alias using the relationship attribute
                query = query.join(alias, rel_attr)
            
            last_target = alias_cache[key]

        return query, last_target