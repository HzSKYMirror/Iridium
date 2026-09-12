import ast
import operator
import re
from typing import Any, Union

from mcdreforged.api.all import *

from iridium.config import config
from iridium.utils import check_permission
from iridium.version_util import tr

Number = Union[int, float]

_BIN_OPS = {
	ast.Add: operator.add,
	ast.Sub: operator.sub,
	ast.Mult: operator.mul,
	ast.Div: operator.truediv,
	ast.FloorDiv: operator.floordiv,
	ast.Mod: operator.mod,
	ast.Pow: operator.pow,
}
_UNARY_OPS = {
	ast.UAdd: operator.pos,
	ast.USub: operator.neg,
}

MAX_EXPR_LEN = 200
MAX_POW = 64


class CalcError(Exception):
	pass


def _eval_node(node: ast.AST) -> Any:
	if isinstance(node, ast.Expression):
		return _eval_node(node.body)
	# ast.Constant covers int/float on Python 3.8+; do not touch ast.Num (removed in 3.12)
	if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
		return node.value
	if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
		return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
	if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
		left = _eval_node(node.left)
		right = _eval_node(node.right)
		if isinstance(node.op, ast.Pow):
			if isinstance(right, (int, float)) and abs(right) > MAX_POW:
				raise CalcError("power too large")
		return _BIN_OPS[type(node.op)](left, right)
	raise CalcError("unsupported expression")


def safe_eval(expression: str) -> Number:
	expr = expression.strip()
	if not expr:
		raise CalcError("empty")
	if len(expr) > MAX_EXPR_LEN:
		raise CalcError("expression too long")
	if not re.fullmatch(r"[0-9+\-*/%().\s^]+", expr):
		raise CalcError("illegal character")
	expr = expr.replace("^", "**")
	try:
		tree = ast.parse(expr, mode="eval")
	except SyntaxError as e:
		raise CalcError(str(e))
	return _eval_node(tree)


def _format_result(value: Number) -> str:
	if isinstance(value, float):
		if value.is_integer() and abs(value) < 1e15:
			return str(int(value))
		return f"{value:.12g}"
	return str(value)


def do_calc(server: PluginServerInterface, src: CommandSource, context: dict) -> None:
	if not check_permission(src, config.permission):
		return
	expression = context.get("expression", "").strip()
	try:
		result = safe_eval(expression)
	except CalcError as e:
		src.reply(RText(tr("calc_error", expression, str(e)), RColor.red))
		return
	except ZeroDivisionError:
		src.reply(RText(tr("calc_div_zero"), RColor.red))
		return
	except Exception as e:
		src.reply(RText(tr("calc_error", expression, str(e)), RColor.red))
		return

	out = _format_result(result)
	# Private reply to avoid flooding public chat
	src.reply(
		RTextList(
			RText("[Iridium] ", RColor.gray),
			RText(expression, RColor.yellow),
			RText(" = ", RColor.gray),
			RText(out, RColor.aqua, styles=RStyle.bold),
		)
	)


def register(server: PluginServerInterface) -> None:
	builder = SimpleCommandBuilder()
	builder.command("!!c", lambda src: src.reply(RText(tr("calc_usage"), RColor.yellow)))
	builder.command("!!c <expression>", do_calc)
	builder.arg("expression", GreedyText)
	builder.register(server)
	server.register_help_message("!!c <expression>", tr("calc_help"))
