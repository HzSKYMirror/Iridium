import re
from typing import Optional, Tuple

from mcdreforged.api.all import *

from iridium.config import config
from iridium.utils import (
	check_cooldown,
	check_permission,
	looks_like_item_snbt,
	mark_cooldown,
	parse_selected_item,
	require_player,
	rcon_query,
	safe_execute,
	sanitize_name,
	strip_data_prefix,
)
from iridium.version_util import is_at_least, require_version, tr

AIR_RE = re.compile(r'id\s*:\s*"(minecraft:)?air"')


def _is_air(snbt: Optional[str]) -> bool:
	if snbt is None:
		return True
	stripped = snbt.strip()
	return stripped in ("{}", "", "[]") or bool(AIR_RE.search(stripped))


def _can_swap(version: Version) -> bool:
	return is_at_least(version, "1.8")


def _entitydata_query(player: str) -> str:
	return f"entitydata {sanitize_name(player)} {{}}"


def _selected_query(player: str, version: Version) -> str:
	name = sanitize_name(player)
	if is_at_least(version, "1.13"):
		return f"data get entity {name} SelectedItem"
	return _entitydata_query(player)


def _head_query(player: str, version: Version) -> str:
	name = sanitize_name(player)
	if is_at_least(version, "1.13"):
		return f"data get entity {name} equipment.head"
	return _entitydata_query(player)


def _head_slot(version: Version) -> str:
	if is_at_least(version, "1.13"):
		return "armor.head"
	return "slot.armor.head"


def _hand_slot(version: Version, hotbar_index: int = 0) -> str:
	if is_at_least(version, "1.13"):
		return "weapon.mainhand"
	if is_at_least(version, "1.9"):
		return "slot.weapon"
	return f"slot.hotbar.{hotbar_index}"


def _extract_selected_slot(payload: str) -> int:
	body = strip_data_prefix(payload)
	m = re.search(r"SelectedItemSlot\s*:\s*(\d+)", body)
	return int(m.group(1)) if m else 0


def _extract_head_item(payload: str, version: Version) -> Optional[str]:
	body = strip_data_prefix(payload)
	if not body or not looks_like_item_snbt(body):
		return None
	if is_at_least(version, "1.13"):
		body = body.strip()
		if _is_air(body):
			return None
		return body
	m = re.search(r"Inventory\s*:", body)
	if m is None:
		return None
	i = m.end()
	while i < len(body) and body[i].isspace():
		i += 1
	if i >= len(body) or body[i] != "[":
		return None
	depth = 0
	inv = ""
	for j in range(i, len(body)):
		if body[j] == "[":
			depth += 1
		elif body[j] == "]":
			depth -= 1
			if depth == 0:
				inv = body[i : j + 1]
				break
	if not inv:
		return None
	for sm in re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\}", inv):
		if re.search(r"Slot\s*:\s*103b?", sm.group(0)):
			item = sm.group(0)
			return None if _is_air(item) else item
	return None


def _split_snbt_compound(snbt: str, key: str) -> Optional[str]:
	m = re.search(rf"(?:^|[{{,\s]){re.escape(key)}\s*:\s*(\{{)", snbt)
	if m is None:
		return None
	start = m.start(1)
	depth = 0
	for i in range(start, len(snbt)):
		if snbt[i] == "{":
			depth += 1
		elif snbt[i] == "}":
			depth -= 1
			if depth == 0:
				return snbt[start : i + 1]
	return None


def _components_to_command_inner(components_compound: str) -> str:
	"""
	Convert a data-get components compound into item-command component list form.

	data get (1.20.5+):  components:{"minecraft:custom_name":{...}, "minecraft:damage":1}
	item replace form:   minecraft:item[minecraft:custom_name={...},minecraft:damage=1]
	"""
	inner = components_compound.strip()[1:-1].strip()
	if not inner:
		return ""
	# Top-level key:value pairs. Values may be compounds/lists/scalars.
	parts = []
	i = 0
	n = len(inner)
	while i < n:
		while i < n and inner[i] in ", \t\n":
			i += 1
		if i >= n:
			break
		# key
		key_m = re.match(r'"([^"]+)"', inner[i:])
		if key_m is None:
			key_m = re.match(r"([A-Za-z0-9_.:\-]+)", inner[i:])
			if key_m is None:
				i += 1
				continue
		key = key_m.group(1)
		i += key_m.end()
		while i < n and inner[i].isspace():
			i += 1
		if i >= n or inner[i] != ":":
			continue
		i += 1
		while i < n and inner[i].isspace():
			i += 1
		# value
		if i >= n:
			break
		if inner[i] == "{":
			depth = 0
			start = i
			while i < n:
				if inner[i] == "{":
					depth += 1
				elif inner[i] == "}":
					depth -= 1
					if depth == 0:
						i += 1
						break
				i += 1
			value = inner[start:i]
		elif inner[i] == "[":
			depth = 0
			start = i
			while i < n:
				if inner[i] == "[":
					depth += 1
				elif inner[i] == "]":
					depth -= 1
					if depth == 0:
						i += 1
						break
				i += 1
			value = inner[start:i]
		elif inner[i] == '"':
			start = i
			i += 1
			while i < n:
				if inner[i] == "\\":
					i += 2
					continue
				if inner[i] == '"':
					i += 1
					break
				i += 1
			value = inner[start:i]
		else:
			start = i
			while i < n and inner[i] not in ",":
				i += 1
			value = inner[start:i].strip()
		parts.append(f"{key}={value}")
	return ", ".join(parts)


def _item_to_command_form(snbt: str, version: Version) -> Tuple[str, Optional[int]]:
	id_m = re.search(r'id\s*:\s*"([^"]+)"', snbt)
	if id_m is None:
		return "minecraft:air", 1
	item_id = id_m.group(1)
	cnt: Optional[int] = None
	if is_at_least(version, "1.20.5"):
		c_m = re.search(r"\bcount\s*:\s*(\d+)", snbt)
		cnt = int(c_m.group(1)) if c_m else 1
		comps = _split_snbt_compound(snbt, "components")
		if comps and comps != "{}":
			inner = _components_to_command_inner(comps)
			if inner:
				return f"{item_id}[{inner}]", cnt
		return item_id, cnt

	c_m = re.search(r"Count\s*:\s*(\d+)", snbt)
	cnt = int(c_m.group(1)) if c_m else 1
	tag = _split_snbt_compound(snbt, "tag")
	if tag and tag != "{}":
		return f"{item_id}{tag}", cnt
	return item_id, cnt


def _replace_with(player: str, slot: str, item_snbt: str, version: Version) -> str:
	name = sanitize_name(player)
	part, count = _item_to_command_form(item_snbt, version)
	if part.endswith(":air") or part == "air":
		part = "air"
		count = None
	if is_at_least(version, "1.17"):
		cmd = f"item replace entity {name} {slot} with {part}"
		if count is not None and count != 1:
			cmd += f" {count}"
		return cmd
	cmd = f"replaceitem entity {name} {slot} {part}"
	if count is not None and count != 1:
		cmd += f" {count}"
	return cmd


def _extract_item_payload(payload: str, version: Version) -> Optional[str]:
	body = strip_data_prefix(payload)
	if not looks_like_item_snbt(body):
		return None
	if is_at_least(version, "1.13"):
		return body.strip()
	return parse_selected_item(body)


def _do_swap(server: PluginServerInterface, src: CommandSource, player: str, version: Version) -> bool:
	name = sanitize_name(player)
	head_slot = _head_slot(version)

	# 1.17+: true swap via offhand buffer — no need to rebuild item NBT
	if is_at_least(version, "1.17"):
		hand_raw = rcon_query(server, _selected_query(player, version))
		if hand_raw is None:
			src.reply(RText(tr("hat_query_failed"), RColor.red))
			return False
		hand = _extract_item_payload(hand_raw, version)
		if hand is None or _is_air(hand):
			src.reply(RText(tr("hand_is_empty"), RColor.red))
			return False

		off_raw = rcon_query(server, f"data get entity {name} weapon.offhand")
		off = None
		if off_raw is not None:
			off = _extract_item_payload(off_raw, version)
		if off and not _is_air(off):
			src.reply(RText(tr("hat_offhand_busy"), RColor.red))
			return False

		# 1) save head -> offhand  2) hand -> head  3) offhand -> hand  4) clear offhand
		safe_execute(
			server,
			f"item replace entity {name} weapon.offhand from entity {name} {head_slot}",
		)
		safe_execute(
			server,
			f"item replace entity {name} {head_slot} from entity {name} weapon.mainhand",
		)
		safe_execute(
			server,
			f"item replace entity {name} weapon.mainhand from entity {name} weapon.offhand",
		)
		safe_execute(server, f"item replace entity {name} weapon.offhand with air")
		src.reply(RText(tr("hat_success"), RColor.green))
		return True

	# 1.8–1.16: rebuild via parsed SNBT
	dump = rcon_query(server, _entitydata_query(player))
	if dump is None:
		src.reply(RText(tr("hat_query_failed"), RColor.red))
		return False
	hotbar_index = _extract_selected_slot(dump)
	hand_slot = _hand_slot(version, hotbar_index)
	hand = _extract_item_payload(dump, version)
	if hand is None or _is_air(hand):
		src.reply(RText(tr("hand_is_empty"), RColor.red))
		return False
	head = _extract_head_item(dump, version)

	safe_execute(server, _replace_with(player, head_slot, hand, version))
	if head and not _is_air(head):
		safe_execute(server, _replace_with(player, hand_slot, head, version))
	else:
		safe_execute(server, _replace_with(player, hand_slot, "minecraft:air", version))

	src.reply(RText(tr("hat_success"), RColor.green))
	return True


def do_hat(server: PluginServerInterface, src: CommandSource) -> None:
	player = require_player(src)
	if player is None:
		return
	if not check_permission(src, config.permission):
		return
	version = require_version(server, src)
	if version is None:
		return
	if not _can_swap(version):
		src.reply(RText(tr("hat_unsupported_version", str(version)), RColor.red))
		return
	if not server.is_rcon_running():
		src.reply(RText(tr("hat_need_rcon"), RColor.red))
		return
	if not check_cooldown(src, player, "hat", config.hat_cooldown_seconds):
		return

	if _do_swap(server, src, player, version):
		mark_cooldown(player, "hat")
		server.logger.info(f"[Iridium] !!hat: {player} swapped hand/head gear")


def register(server: PluginServerInterface) -> None:
	server.register_command(Literal("!!hat").runs(lambda src: do_hat(server, src)))
	server.register_help_message("!!hat", tr("hat_help"))
