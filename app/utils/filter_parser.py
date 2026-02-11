import re
from datetime import datetime
from typing import Optional
from sqlalchemy import and_, asc, desc, or_
from sqlalchemy.orm import aliased, InstrumentedAttribute
from sqlalchemy import String, cast
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy import  Unicode, Text, UnicodeText, CHAR, VARCHAR,NVARCHAR


def auto_cast(value: str):
    if value is None:
        return None

    # try int
    try:
        return int(value)
    except:
        pass

    # try float
    try:
        return float(value)
    except:
        pass

    # try datetime
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except:
            pass

    # bool
    v = value.lower()
    if v in ("true", "false"):
        return v == "true"

    return value


def build_filter(column, operator, value):
    col_type = getattr(column, "type", None)
    print(col_type)
    is_string = isinstance(col_type, (String, Unicode, Text, UnicodeText, CHAR, VARCHAR,NVARCHAR))

    if operator == "isNull":
        return column.is_(None)
    if operator == "isNotNull":
        return column.isnot(None)

    if operator in ("in", "notIn", "between", "notBetween"):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        parts = [auto_cast(p) for p in parts]

        if operator == "in":
            return column.in_(parts)
        if operator == "notIn":
            return ~column.in_(parts)
        if operator == "between":
            if len(parts) != 2:
                raise ValueError("between expects 2 values")
            return column.between(parts[0], parts[1])
        if operator == "notBetween":
            if len(parts) != 2:
                raise ValueError("notBetween expects 2 values")
            return ~column.between(parts[0], parts[1])

    v = auto_cast(value)

    if operator == "eq":
        return column == v
    if operator == "notEq":
        return column != v
    if operator == "gt":
        return column > v
    if operator == "gte":
        return column >= v
    if operator == "lt":
        return column < v
    if operator == "lte":
        return column <= v

    
    print(is_string)
    if operator in (
        "ilike",
        "notIlike",
        "startsWith",
        "endsWith",
        "contains",
        "notContains",
    ):
        col = column if is_string else cast(column, String)
        val = str(v)

        if operator == "ilike":
            return col.ilike(f"%{val}%")
        if operator == "notIlike":
            return ~col.ilike(f"%{val}%")
        if operator == "startsWith":
            return col.ilike(f"{val}%")
        if operator == "endsWith":
            return col.ilike(f"%{val}")
        if operator == "contains":
            return col.ilike(f"%{val}%")
        if operator == "notContains":
            return ~col.ilike(f"%{val}%")

    raise ValueError(f"Unsupported operator: {operator}")


def parse_filter_input(filters_str: str):
    """
    Example:
        (employee_id=0000~ilike|0001~ilike)&departments.name=IT~eq
    becomes DSL:
        ((employee_id=0000~ilike|0001~ilike))&(departments.name=IT~eq)
    """
    if not filters_str:
        return ""

    expr = ""
    for part in filters_str.split("&"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        expr += f"({part})&"

    return expr.rstrip("&")


def parse_sort(sort: Optional[str], model=None):
    if not sort or not model:
        return None

    parts = sort.split(".")
    if len(parts) != 2:
        return None

    field, direction = parts
    column = getattr(model, field, None)
    if not column:
        return None

    order = asc if direction == "asc" else desc
    return order(column)


# ============================================================
#  TOKENIZER
# ============================================================

TOKENS = re.compile(
    r"""
    (?P<LPAREN>\() |
    (?P<RPAREN>\)) |
    (?P<AND>&) |
    (?P<OR>\|) |
    (?P<FILTER>[^&|()]+) |
    (?P<SPACE>\s+)
""",
    re.VERBOSE,
)


def tokenize(expr: str):
    tokens = []
    for m in TOKENS.finditer(expr):
        kind = m.lastgroup
        val = m.group().strip()
        if kind != "SPACE":
            tokens.append((kind, val))
    return tokens


# ============================================================
#  PARSE FILTER NODE
# ============================================================


def parse_filter(raw: str):
    field, rhs = raw.split("=", 1)
    value, operator = rhs.split("~", 1)
    return {
        "field_path": field.split("."),
        "operator": operator,
        "value": value,
    }


# ============================================================
#  AST BUILDER (Recursive Descent)
#  Grammar:
#    expr   := term (OR term)*
#    term   := factor (AND factor)*
#    factor := FILTER | LPAREN expr RPAREN
# ============================================================


def parse_expression(tokens):
    def parse_factor(i):
        tok, val = tokens[i]
        if tok == "FILTER":
            return {"type": "filter", "raw": val}, i + 1
        if tok == "LPAREN":
            node, j = parse_or(i + 1)
            if tokens[j][0] != "RPAREN":
                raise Exception("Missing )")
            return node, j + 1
        raise Exception("Unexpected token in factor")

    def parse_and(i):
        node, i = parse_factor(i)
        while i < len(tokens) and tokens[i][0] == "AND":
            right, j = parse_factor(i + 1)
            node = {"type": "and", "left": node, "right": right}
            i = j
        return node, i

    def parse_or(i):
        node, i = parse_and(i)
        while i < len(tokens) and tokens[i][0] == "OR":
            right, j = parse_and(i + 1)
            node = {"type": "or", "left": node, "right": right}
            i = j
        return node, i

    root, _ = parse_or(0)
    return root


# ============================================================
#  NESTED FIELD RESOLVER (JOIN BUILDER)
# ============================================================


def get_column_from_path(model, path, aliases, base_query):
    curr_model = model
    curr_alias = model

    for i, part in enumerate(path[:-1]):
        rel = getattr(curr_model, part, None)
        if not isinstance(rel, InstrumentedAttribute):
            return None, base_query

        key = ".".join(path[: i + 1])
        if key not in aliases:
            related = rel.property.mapper.class_
            alias = aliased(related)
            aliases[key] = alias
            base_query = base_query.join(alias, rel)

        curr_model = aliases[key]
        curr_alias = aliases[key]

    return getattr(curr_alias, path[-1]), base_query


# ============================================================
#  AST → SQLAlchemy CONDITION
# ============================================================


def ast_to_sql(ast, base_model, aliases, query):
    t = ast["type"]

    if t == "filter":
        pf = parse_filter(ast["raw"])
        col, query = get_column_from_path(base_model, pf["field_path"], aliases, query)
        return build_filter(col, pf["operator"], pf["value"]), query

    left, query = ast_to_sql(ast["left"], base_model, aliases, query)
    right, query = ast_to_sql(ast["right"], base_model, aliases, query)

    if t == "and":
        return and_(left, right), query
    if t == "or":
        return or_(left, right), query

    raise Exception("Unknown node type")


def normalize_filter_str(filters_str: str):
    """
    Accepts:
        employee_id:000000~ilike
        employee_id=000000~ilike
    Converts ':' to '=' only for field/value pairs
    """
    normalized = []
    for part in filters_str.split("&"):
        part = part.strip()
        if not part:
            continue
        # if part has ':' but no '=', convert
        if ":" in part and "=" not in part:
            field, rhs = part.split(":", 1)
            part = f"{field}={rhs}"
        normalized.append(part)
    return "&".join(normalized)


def apply_filters(query, filters_str, base_model):
    if not filters_str:
        return query

    if ":" in filters_str and "=" not in filters_str:
        field, rest = filters_str.split(":", 1)
        filters_str = f"{field}={rest}"

    field, rest = filters_str.split("=", 1)
    value, operator = rest.split("~", 1)
    column = getattr(base_model, field)

    # special case: zero-padded numeric prefixes
    if operator == "ilike" and value.isdigit():
        return query.filter(cast(column, String).ilike(f"{value}%"))

    if operator == "ilike":
        return query.filter(cast(column, String).ilike(f"%{value}%"))

    if operator == "eq":
        return query.filter(column == value)

    if operator == "contains":
        return query.filter(cast(column, String).ilike(f"%{value}%"))

    return query.filter(column == value)
