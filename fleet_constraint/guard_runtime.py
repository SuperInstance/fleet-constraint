"""GuardRuntime — GUARD DSL → FLUX-C constraint evaluation engine."""

from __future__ import annotations

import re
from typing import List, Tuple, Dict, NamedTuple
from enum import Enum
from datetime import datetime


class GuardLine(NamedTuple):
    """A single guard constraint line parsed from a .guard file."""
    name: str
    var: str
    op: str
    value: float
    priority: int
    condition: str


class ConstraintStatus(Enum):
    """Status of a constraint evaluation."""
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    PENDING = "pending"


class ConstraintResult:
    """Result of constraint evaluation with status and timestamp."""

    def __init__(self, name: str, status: ConstraintStatus, tick: int = 0, reason: str = ""):
        self.name = name
        self.status = status
        self.tick = tick
        self.reason = reason
        self.timestamp = datetime.utcnow()

    def satisfied(self) -> bool:
        return self.status == ConstraintStatus.SATISFIED

    def violated(self) -> bool:
        return self.status == ConstraintStatus.VIOLATED

    def pending(self) -> bool:
        return self.status == ConstraintStatus.PENDING

    def __repr__(self) -> str:
        return f"ConstraintResult({self.name}, {self.status.value}, tick={self.tick})"


# Operators supported in guard lines
VALID_OPS = {"<", "<=", ">", ">=", "==", "!=", "eq", "ne", "lt", "le", "gt", "ge"}


def _normalize_op(op: str) -> str:
    """Normalize operator variants to a canonical form."""
    mapping = {
        "eq": "==",
        "ne": "!=",
        "lt": "<",
        "le": "<=",
        "gt": ">",
        "ge": ">=",
    }
    return mapping.get(op.lower(), op)


def parse_guard_line(line: str) -> GuardLine:
    """
    Parse a single guard line string into a GuardLine namedtuple.

    Format: name:var:op:value:priority[:condition]

    Examples:
        h1_guard:h1:<:0.95:10
        zhc_guard:zhc:>=:0.85:5:if_phase_SYNC
    """
    line = line.strip()
    if not line or line.startswith("#"):
        raise ValueError(f"Empty or comment line: {line!r}")

    parts = line.split(":")
    if len(parts) < 5:
        raise ValueError(f"Guard line must have at least 5 fields (name:var:op:value:priority): {line!r}")

    name = parts[0].strip()
    var = parts[1].strip()
    op = _normalize_op(parts[2].strip())
    raw_value = parts[3].strip()
    priority = int(parts[4].strip())
    condition = parts[5].strip() if len(parts) > 5 else ""

    try:
        value = float(raw_value)
    except ValueError:
        raise ValueError(f"Cannot parse value as float: {raw_value!r}")

    if op not in VALID_OPS:
        raise ValueError(f"Invalid operator: {op!r}. Must be one of {VALID_OPS}")

    return GuardLine(name=name, var=var, op=op, value=value, priority=priority, condition=condition)


def _eval_guard_expr(var: str, op: str, value: float, context: Dict) -> bool:
    """Evaluate a single guard expression against a context."""
    ctx_val = context.get(var)
    if ctx_val is None:
        # Variable not present in context — treat as pending
        return False

    # Handle different types gracefully
    try:
        ctx_val = float(ctx_val)
    except (TypeError, ValueError):
        return False

    if op == "==":
        return abs(ctx_val - value) < 1e-9
    elif op == "!=":
        return abs(ctx_val - value) >= 1e-9
    elif op == "<":
        return ctx_val < value
    elif op == "<=":
        return ctx_val <= value
    elif op == ">":
        return ctx_val > value
    elif op == ">=":
        return ctx_val >= value
    else:
        raise ValueError(f"Unknown operator: {op}")


class GuardRuntime:
    """
    Runtime for loading and evaluating .guard constraint files.

    Usage:
        runtime = GuardRuntime()
        lines = runtime.load_file("safety.guard")
        results = runtime.evaluate(lines, {"h1": 0.8, "zhc": 0.9})
    """

    # FLUX-C bytecode operation mnemonics
    FLUXC_OPS = {
        "CHECK": "CHECK",      # check a constraint
        "AND": "AND",          # logical and
        "OR": "OR",            # logical or
        "NOT": "NOT",          # logical not
        "LOAD": "LOAD",        # load variable
        "PUSH": "PUSH",        # push constant
        "JUMP": "JUMP",        # jump if false
        "HALT": "HALT",        # halt evaluation
    }

    def load_file(self, path: str) -> List[GuardLine]:
        """Load guard lines from a .guard file."""
        lines: List[GuardLine] = []
        with open(path, "r") as f:
            for lineno, raw_line in enumerate(f, 1):
                raw_line = raw_line.strip()
                if not raw_line or raw_line.startswith("#"):
                    continue
                try:
                    lines.append(parse_guard_line(raw_line))
                except ValueError as e:
                    raise ValueError(f"{path}:{lineno}: {e}")
        return lines

    def evaluate(self, lines: List[GuardLine], context: Dict) -> List[Tuple[GuardLine, bool]]:
        """
        Evaluate a list of guard lines against a context.

        Returns list of (GuardLine, satisfied) tuples.
        """
        results: List[Tuple[GuardLine, bool]] = []
        for line in lines:
            satisfied = _eval_guard_expr(line.var, line.op, line.value, context)
            results.append((line, satisfied))
        return results

    def compile_to_fluxc(self, lines: List[GuardLine]) -> List[str]:
        """
        Compile guard lines to FLUX-C bytecode operation list.

        Produces a list of FLUX-C op strings representing the constraint program.
        """
        ops: List[str] = []
        for line in lines:
            # LOAD the variable
            ops.append(f"LOAD {line.var}")
            # PUSH the threshold value
            ops.append(f"PUSH {line.value}")
            # CHECK with the operator
            ops.append(f"CHECK {line.op}")
            # Name the constraint for traceability
            ops.append(f"# guard: {line.name} [priority={line.priority}]")
        return ops
