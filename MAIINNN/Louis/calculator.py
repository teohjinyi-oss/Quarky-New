"""
Analytical Brain: Calculator Department

Safe math expression evaluator — zero eval()/exec().
Supports: +, -, *, /, **, %, sqrt, abs, round, parentheses.
Worker-pool capable for chained calculations.

Strategy: Parse expression into AST tokens, evaluate with operator precedence.
"""

import ast
import math
import operator
import re
from dataclasses import dataclass
from typing import Any

from AppStudio.Infrastructure.base import Department
from MAIINNN.Louis.parser import ParsedInput


@dataclass
class CalcResult:
    """Result of a math evaluation."""
    expression: str
    result: float | int | None
    formatted: str          # human-readable answer
    success: bool
    error: str = ""


# ─── Safe AST-based evaluator ───────────────────────────────
# Only allows: numbers, unary ops, binary ops, and approved functions.
# No variable access, no attribute access, no imports.

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}

_MAX_RESULT = 10 ** 15  # prevent absurdly large outputs


def _safe_eval_node(node: ast.AST) -> float | int:
    """Recursively evaluate an AST node safely."""
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")

    if isinstance(node, ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        return op(_safe_eval_node(node.operand))

    if isinstance(node, ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        # Prevent division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ZeroDivisionError("Division by zero")
        result = op(left, right)
        if isinstance(result, float) and abs(result) > _MAX_RESULT:
            raise OverflowError("Result too large")
        return result

    if isinstance(node, ast.Call):
        # Only allow calls to safe functions
        if isinstance(node.func, ast.Name):
            func = _SAFE_FUNCS.get(node.func.id)
            if func is None:
                raise ValueError(f"Unknown function: {node.func.id}")
            if callable(func):
                args = [_safe_eval_node(a) for a in node.args]
                result = func(*args)
                if not isinstance(result, (int, float)):
                    raise ValueError(f"Function {node.func.id} returned non-numeric")
                return result
            return func  # constant like pi, e
        raise ValueError("Only simple function calls allowed")

    if isinstance(node, ast.Name):
        # Allow constants
        val = _SAFE_FUNCS.get(node.id)
        if val is not None and not callable(val):
            return val
        raise ValueError(f"Unknown variable: {node.id}")

    raise ValueError(f"Unsupported node: {type(node).__name__}")


def safe_eval(expression: str) -> float | int:
    """
    Safely evaluate a math expression using AST parsing.
    No eval(), no exec(), no arbitrary code execution.
    """
    tree = ast.parse(expression, mode='eval')
    return _safe_eval_node(tree)


# ─── Natural language → expression conversion ───────────────

_NL_MATH = [
    (re.compile(r'(\d+)\s*plus\s*(\d+)', re.I), r'\1 + \2'),
    (re.compile(r'(\d+)\s*minus\s*(\d+)', re.I), r'\1 - \2'),
    (re.compile(r'(\d+)\s*times\s*(\d+)', re.I), r'\1 * \2'),
    (re.compile(r'(\d+)\s*divided\s*by\s*(\d+)', re.I), r'\1 / \2'),
    (re.compile(r'(\d+)\s*to\s*the\s*power\s*(?:of\s*)?(\d+)', re.I), r'\1 ** \2'),
    (re.compile(r'square\s*root\s*(?:of\s*)?(\d+(?:\.\d+)?)', re.I), r'sqrt(\1)'),
    (re.compile(r'(\d+)\s*(?:percent|%)\s*of\s*(\d+)', re.I), r'(\1 / 100) * \2'),
    (re.compile(r'what\s*is\s+', re.I), ''),
    (re.compile(r'calculate\s+', re.I), ''),
    (re.compile(r'compute\s+', re.I), ''),
    (re.compile(r'solve\s+', re.I), ''),
    (re.compile(r'\?$'), ''),
]


def normalize_expression(text: str) -> str:
    """Convert natural language math to evaluable expression."""
    result = text.strip()
    for pattern, replacement in _NL_MATH:
        result = pattern.sub(replacement, result)
    return result.strip()


# ─── Calculator Department ──────────────────────────────────

class Calculator(Department):
    """
    Evaluates math expressions safely.
    Handles both symbolic (2+3) and natural language ("5 plus 3").
    """

    def __init__(self):
        super().__init__("calculator", "core.analytical")

    def process(self, data: Any) -> Any:
        """
        If ParsedInput has math_expressions, evaluate them.
        Otherwise pass through unchanged for next department.
        """
        if not isinstance(data, ParsedInput):
            return data

        if data.task_type != "math" and not data.math_expressions:
            return data  # not a math task — pass through

        # Try evaluating the full expression first
        expression = normalize_expression(data.brain_input.text)
        result = self.evaluate(expression)

        if result.success:
            data.brain_input.context["calc_result"] = result
        else:
            # Try each sub-expression
            results = []
            for expr in data.math_expressions:
                r = self.evaluate(normalize_expression(expr))
                results.append(r)
            data.brain_input.context["calc_results"] = results

        return data

    def evaluate(self, expression: str) -> CalcResult:
        """Evaluate a single math expression."""
        if not expression:
            return CalcResult("", None, "", False, "Empty expression")

        try:
            result = safe_eval(expression)

            # Format nicely
            if isinstance(result, float) and result == int(result):
                result = int(result)
            formatted = f"{expression} = {result}"

            return CalcResult(
                expression=expression,
                result=result,
                formatted=formatted,
                success=True,
            )
        except ZeroDivisionError:
            return CalcResult(expression, None, "", False, "Cannot divide by zero")
        except (ValueError, TypeError, SyntaxError, OverflowError) as e:
            return CalcResult(expression, None, "", False, str(e))
