# dsl_filter.py

from __future__ import annotations

import re
import uuid
import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from functools import lru_cache
from sqlalchemy import and_, or_, asc, desc, func, literal, text, cast
from sqlalchemy.sql import operators
from sqlmodel import SQLModel
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.selectable import Select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from .model_graph import ModelGraph

"""
#  DSL FILTER OPTIONS & EXAMPLES

The filter string follows the format: `field_path:value~operator`
You can combine filters using:
  - `,` or `&` : Logical AND
  - `|`       : Logical OR
  - `()`      : Grouping for precedence

## 1. SUPPORTED OPERATORS (~operator)
-------------------------------------------------------------------------
| Operator     | Description                | Example                   |
|--------------|----------------------------|---------------------------|
| eq           | Exact match                | is_active:true~eq         |
| notEq        | Not equal                  | role:user~notEq           |
| ilike        | Case-insensitive contains  | name:alex~ilike           |
| startsWith   | Matches beginning          | employee_id:EMP~startsWith|
| gt / lt      | Greater / Less than        | age:18~gt                 |
| gte / lte    | Greater/Less or Equal      | created_at:2023-01-01~gte |
| in           | Match any in list          | id:1,2,3~in               |
| notIn        | Match none in list         | status:hidden,deleted~notIn|

## 2. FILTERABLE PATHS (Based on your ModelGraph)
-------------------------------------------------------------------------
### User Attributes (Direct)
- id, employee_id, name, email, role, is_active, designation, qualification

### Relationship Paths (Nested)
- departments.department.name         (Filter by Department Name)
- departments.role.role               (Filter by Role Name in Dept)
- departments.department_id           (Filter by Department UUID)
- departments.role_id                 (Filter by Role UUID)

## 3. REAL-WORLD EXAMPLES
-------------------------------------------------------------------------
# Find active users in the Engineering department
filters = "is_active:true~eq & departments.department.name:Engineering~ilike"

# Find users who are either Admins OR Managers in any department
filters = "(role:admin~eq) | (departments.role.role:Manager~eq)"

# Find specific employees by their IDs
filters = "employee_id:101,105,110~in"

# Complex: Active users named 'John' in 'Sales' OR any user in 'IT'
filters = "(is_active:true~eq & name:John~ilike & departments.department.name:Sales~eq) | (departments.department.name:IT~eq)"

## 4. SORTING OPTIONS
-------------------------------------------------------------------------
Pass as `field_path.direction` (asc/desc):
- created_at.desc
- name.asc
- departments.department.name.asc
"""

TOKEN_REGEX = re.compile(r"""
    (\()|       # LPAREN
    (\))|       # RPAREN
    (\|)|       # OR
    (&)|        # AND
    ([^()&|]+)  # FILTER TOKEN
""", re.VERBOSE)


def tokenize(expr: str) -> List[str]:
    tokens = []
    for match in TOKEN_REGEX.finditer(expr):
        tok = match.group()
        if tok.strip():
            tokens.append(tok)
    return tokens


# --------------------------
# FILTER PARSER (AST)
# --------------------------

class ASTNode:
    pass


class FilterNode(ASTNode):
    def __init__(self, field: str, value: str, op: str) -> None:
        self.field = field
        self.value = value
        self.op = op


class AndNode(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode) -> None:
        self.left = left
        self.right = right


class OrNode(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode) -> None:
        self.left = left
        self.right = right


def parse_filter_token(token: str) -> FilterNode:
    if ':' not in token:
        raise ValueError(f"Invalid filter: {token}")

    field, cond = token.split(':', 1)
    if '~' not in cond:
        raise ValueError(f"Missing operator in: {token}")

    value, op = cond.split('~', 1)
    return FilterNode(field=field.strip(), value=value.strip(), op=op.strip())


def parse_expression(tokens: List[str]) -> ASTNode:
    pos = 0

    def parse_or() -> ASTNode:
        nonlocal pos
        node = parse_and()
        while pos < len(tokens) and tokens[pos] == '|':
            pos += 1
            node = OrNode(node, parse_and())
        return node

    def parse_and() -> ASTNode:
        nonlocal pos
        node = parse_factor()
        while pos < len(tokens) and tokens[pos] == '&':
            pos += 1
            node = AndNode(node, parse_factor())
        return node

    def parse_factor() -> ASTNode:
        nonlocal pos
        tok = tokens[pos]
        if tok == '(':
            pos += 1
            node = parse_or()
            if pos >= len(tokens) or tokens[pos] != ')':
                raise ValueError("Missing ')'")
            pos += 1
            return node
        else:
            pos += 1
            return parse_filter_token(tok)

    result = parse_or()
    if pos != len(tokens):
        raise ValueError("Unexpected extra tokens")
    return result


# --------------------------
# OPERATOR REGISTRY
# --------------------------

def op_ilike(col, val): return col.ilike(f"%{val}%")
def op_prefix(col, val): return col.ilike(f"{val}%")
def op_notlike(col, val): return ~col.ilike(f"%{val}%")
def op_eq(col, val): return col == val
def op_neq(col, val): return col != val
def op_gt(col, val): return col > val
def op_gte(col, val): return col >= val
def op_lt(col, val): return col < val
def op_lte(col, val): return col <= val
def op_in(col, val): return col.in_(val)
def op_notin(col, val): return ~col.in_(val)


OP_MAP = {
    "ilike": op_ilike,
    "startsWith": op_prefix,
    "notIlike": op_notlike,
    "eq": op_eq,
    "notEq": op_neq,
    "gt": op_gt,
    "gte": op_gte,
    "lt": op_lt,
    "lte": op_lte,
    "in": op_in,
    "notIn": op_notin,
}




def cast_value(col_type: Any, raw: str) -> Any:
    if raw is None:
        return None

    # boolean
    if isinstance(col_type, bool) or raw.lower() in ("true", "false", "1", "0"):
        return raw.lower() in ("true", "1")

    # UUID
    try:
        if col_type is uuid.UUID:
            return uuid.UUID(raw)
    except:
        pass

    # int/float
    try:
        if col_type is int:
            return int(raw)
        if col_type is float:
            return float(raw)
    except:
        pass

    # dates
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(raw, fmt)
        except:
            pass

    # default fallback
    return raw



def resolve_column(model: Type[SQLModel], path: str, graph: ModelGraph, alias_cache: Dict) -> Tuple[Any, Select]:
    attrs = path.split('.')
    plan, colname = graph.resolve_attr_path(model, attrs)
    
    # Get current statement from cache
    stmt = alias_cache.get("__stmt__")
    
    # Apply joins and get the last alias used in the path
    stmt, last_alias = graph.apply_joins(stmt, plan, alias_cache)
    
    # Update the statement in the cache so subsequent filters reuse these joins
    alias_cache["__stmt__"] = stmt
    
    target = last_alias if last_alias else model
    return getattr(target, colname), stmt


def resolve_python_type(col) -> Any:
    try:
        if hasattr(col.type, "python_type"):
            return col.type.python_type
    except NotImplementedError:
        pass

    # UUID detection by class name
    if col.type.__class__.__name__ in ("UUID", "PG_UUID", "UUIDType", "UUID"):
        return uuid.UUID

    # map common SQL types
    name = col.type.__class__.__name__.lower()

    if "char" in name or "text" in name or "string" in name:
        return str
    if "integer" in name or "int" in name:
        return int
    if "float" in name or "numeric" in name or "decimal" in name:
        return float
    if "bool" in name:
        return bool
    if "date" in name:
        return datetime.date
    if "time" in name:
        return datetime.datetime

    # fallback: treat as string
    return str


def build_condition(
    node: ASTNode,
    model: Type[SQLModel],
    graph: ModelGraph,
    alias_cache: Dict
) -> BinaryExpression:

    if isinstance(node, FilterNode):
        col, _ = resolve_column(model, node.field, graph, alias_cache)
        raw = node.value

        col_type = resolve_python_type(col)
        val = cast_value(col_type, raw)

        if node.op == "ilike" and node.field.lower() == "employee_id":
            return op_prefix(col, val)

        handler = OP_MAP.get(node.op)
        if handler is None:
            raise ValueError(f"Unsupported operator: {node.op}")

        if node.op in ("in", "notIn"):
            val = raw.split(',')
        return handler(col, val)

    if isinstance(node, AndNode):
        return and_(
            build_condition(node.left, model, graph, alias_cache),
            build_condition(node.right, model, graph, alias_cache),
        )

    if isinstance(node, OrNode):
        return or_(
            build_condition(node.left, model, graph, alias_cache),
            build_condition(node.right, model, graph, alias_cache),
        )

    raise TypeError("Invalid AST node")


def apply_filters(stmt: Select, filters: str, model: Type[SQLModel], graph: ModelGraph) -> Select:
    filters = filters.replace(",", "&")
    print(filters)
    alias_cache: Dict = {"__stmt__": stmt}
    tokens = tokenize(filters)
    ast = parse_expression(tokens)
    condition = build_condition(ast, model, graph, alias_cache)
    print(condition)
    stmt = alias_cache["__stmt__"]
    return stmt.where(condition)



def apply_sort(stmt: Select, sort: str, model: Type[SQLModel], graph: ModelGraph) -> Select:
    if not sort:
        return stmt

    parts = sort.split('.')
    direction = parts[-1]
    field = ".".join(parts[:-1])
    alias_cache = {"__stmt__": stmt}
    col, stmt = resolve_column(model, field, graph, alias_cache)
    if direction == "asc":
        return stmt.order_by(asc(col))
    return stmt.order_by(desc(col))
