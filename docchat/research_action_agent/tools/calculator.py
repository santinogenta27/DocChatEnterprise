"""Safe calculator tool for Research & Action Agent."""

from __future__ import annotations

import math
import ast
import operator
from langchain.tools import tool

# Safe evaluation environment
SAFE_NAMES = {
    k: getattr(math, k) for k in dir(math) if not k.startswith("__")
}
SAFE_NAMES.update({
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "pi": math.pi,
    "e": math.e,
})

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


def safe_eval(node):
    """Safely evaluate an AST node."""
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op = ALLOWED_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op)}")
        return op(safe_eval(node.left), safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        op = ALLOWED_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        return op(safe_eval(node.operand))
    elif isinstance(node, ast.Compare):
        left = safe_eval(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            op_func = ALLOWED_OPERATORS.get(type(op))
            if op_func is None:
                raise ValueError(f"Unsupported comparison operator: {type(op)}")
            right = safe_eval(comparator)
            if not op_func(left, right):
                return False
            left = right
        return True
    elif isinstance(node, ast.Call):
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        if func_name not in SAFE_NAMES:
            raise ValueError(f"Unsafe function: {func_name}")
        args = [safe_eval(a) for a in node.args]
        return SAFE_NAMES[func_name](*args)
    elif isinstance(node, ast.Name):
        if node.id in SAFE_NAMES:
            return SAFE_NAMES[node.id]
        raise ValueError(f"Unsafe name: {node.id}")
    elif isinstance(node, ast.Expression):
        return safe_eval(node.body)
    else:
        raise ValueError(f"Unsupported AST node: {type(node)}")


@tool
def calculator_tool(expression: str) -> str:
    """
    Safely evaluate a mathematical expression and return result as string.
    
    Accepts: basic arithmetic, math functions (sqrt, sin, cos, log, etc.), and comparisons.
    
    Examples:
        "2 + 3 * 4" -> "14"
        "sqrt(16)" -> "4.0"
        "sin(pi/2)" -> "1.0"
        "15 * 0.15" -> "2.25"
    
    Args:
        expression: Mathematical expression as string
    
    Returns:
        Result as string, or error message if evaluation fails
    """
    try:
        # Parse the expression
        node = ast.parse(expression, mode="eval")
        
        # Evaluate safely
        result = safe_eval(node.body)
        
        # Format result
        if isinstance(result, float):
            # Round to reasonable precision
            if abs(result) < 1e-10:
                return "0.0"
            return str(round(result, 10))
        elif isinstance(result, bool):
            return str(result)
        else:
            return str(result)
            
    except SyntaxError as e:
        return f"ERROR: Invalid syntax - {str(e)}"
    except ValueError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR: {str(e)}"

