import re
import time
from typing import Dict, Optional

from mcdreforged.api.all import *

from iridium.version_util import tr

DATA_PREFIX_RE = re.compile(r"^.+ has the following entity data: ", re.IGNORECASE)
# A payload that looks like an item / entity SNBT, not an error line
SNBT_ITEM_RE = re.compile(r'id\s*:\s*"', re.IGNORECASE)
# Only allow Minecraft-safe name characters
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]")
MAX_NAME_LEN = 32

# player -> last success timestamp
_cooldowns: Dict[str, float] = {}


def sanitize_name(raw: str) -> str:
	"""Keep only [A-Za-z0-9_], cap length. Empty string means invalid."""
	return SAFE_NAME_RE.sub("", raw or "").strip()[:MAX_NAME_LEN]


def sanitize_cmd(text: str) -> str:
	"""Neutralize characters that could split a console/RCON command line."""
	# Newlines/carriage returns would create a second command on stdin
	return (text or "").replace("\r", " ").replace("\n", " ")


def safe_execute(server: PluginServerInterface, command: str) -> None:
	server.execute(sanitize_cmd(command))


def check_permission(src: CommandSource, level: int) -> bool:
	if src.has_permission(level):
		return True
	src.reply(RText(tr("required_permission", level), RColor.red))
	return False


def require_player(src: CommandSource) -> Optional[str]:
	if not src.is_player:
		src.reply(RText(tr("player_only"), RColor.red))
		return None
	return src.get_info().player


def check_cooldown(src: CommandSource, player: str, bucket: str, seconds: int) -> bool:
	"""Return True if the player may proceed. seconds <= 0 disables the limit."""
	if seconds <= 0:
		return True
	key = f"{bucket}:{player}"
	now = time.time()
	last = _cooldowns.get(key)
	if last is not None and now - last < seconds:
		remain = max(1, int(seconds - (now - last) + 0.999))
		src.reply(RText(tr("on_cooldown", remain), RColor.red))
		return False
	return True


def mark_cooldown(player: str, bucket: str) -> None:
	_cooldowns[f"{bucket}:{player}"] = time.time()


def strip_data_prefix(payload: str) -> str:
	"""Strip the '<name> has the following entity data: ' prefix."""
	return DATA_PREFIX_RE.sub("", payload, count=1).strip()


def looks_like_item_snbt(snbt: str) -> bool:
	"""True when the text contains an item id field (not a command error line)."""
	return bool(snbt) and bool(SNBT_ITEM_RE.search(snbt))


def _read_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Optional[str]:
	"""Return the balanced substring starting at text[start] == open_ch."""
	if start >= len(text) or text[start] != open_ch:
		return None
	depth = 0
	for i in range(start, len(text)):
		c = text[i]
		if c == open_ch:
			depth += 1
		elif c == close_ch:
			depth -= 1
			if depth == 0:
				return text[start : i + 1]
	return None


def extract_compound(payload: str, key: str) -> Optional[str]:
	"""
	Extract a top-level field such as SelectedItem from entity NBT text.
	Supports compound `{...}` and list `[...]` values.
	"""
	m = re.search(rf"(?:^|[{{,\s]){re.escape(key)}\s*:", payload)
	if m is None:
		return None
	i = m.end()
	while i < len(payload) and payload[i].isspace():
		i += 1
	if i >= len(payload):
		return None
	if payload[i] == "{":
		return _read_balanced(payload, i, "{", "}")
	if payload[i] == "[":
		return _read_balanced(payload, i, "[", "]")
	# primitive value until comma or closing brace/bracket
	j = i
	while j < len(payload) and payload[j] not in ",}]":
		j += 1
	return payload[i:j].strip()


def parse_selected_item(entity_nbt: str) -> Optional[str]:
	"""Pull SelectedItem (or first HandItems entry) out of a full player NBT dump."""
	value = extract_compound(entity_nbt, "SelectedItem")
	if value is not None and looks_like_item_snbt(value):
		return value

	hand_items = extract_compound(entity_nbt, "HandItems")
	if hand_items is None:
		return None
	# HandItems: [{id:"...",Count:1b},{}] — take the first non-empty item
	inner = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", hand_items)
	if inner is not None:
		item = inner.group(0)
		if looks_like_item_snbt(item):
			return item
	return None


def rcon_query(server: PluginServerInterface, command: str) -> Optional[str]:
	if not server.is_rcon_running():
		return None
	try:
		return server.rcon_query(command)
	except Exception as e:
		server.logger.debug(f"RCON query failed: {e}")
		return None
