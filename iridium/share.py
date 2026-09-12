import json
import re
import threading
import time
from typing import Dict, Optional, Tuple

from mcdreforged.api.all import *

from iridium.config import config
from iridium.utils import (
	check_permission,
	looks_like_item_snbt,
	parse_selected_item,
	require_player,
	rcon_query,
	safe_execute,
	sanitize_name,
	strip_data_prefix,
)
from iridium.version_util import is_at_least, require_version, tr

# pending share requests: player -> (src, version, expire_ts)
_pending: Dict[str, Tuple[CommandSource, Version, float]] = {}
_pending_lock = threading.Lock()

PENDING_TTL = 5.0
# Keep tellraw well under typical command-length limits
MAX_SNBT_LEN = 20000

PLAYER_DATA_RE = re.compile(
	r"^(?P<name>\S+) has the following entity data: (?P<data>.*)$",
	re.IGNORECASE,
)


def _can_read_selected_item(version: Version) -> bool:
	return is_at_least(version, "1.8")


def _query_command(player: str, version: Version) -> str:
	name = sanitize_name(player)
	if is_at_least(version, "1.13"):
		return f"data get entity {name} SelectedItem"
	return f"entitydata {name} {{}}"


def _sound_command(player: str, version: Version) -> str:
	name = sanitize_name(player)
	# Play at the player so @a nearby can hear; default command origin is often too far
	if is_at_least(version, "1.9"):
		return (
			f"execute at {name} run playsound minecraft:entity.arrow.hit_player "
			f"master @a ~ ~ ~ 64 1"
		)
	return f"execute at {name} run playsound random.successful_hit @a ~ ~ ~ 64 1"


def _is_air(snbt: Optional[str]) -> bool:
	if snbt is None:
		return True
	stripped = snbt.strip()
	return stripped in ("{}", "", "[]") or bool(
		re.search(r'id\s*:\s*"(minecraft:)?air"', stripped)
	)


def _json_str(value: str) -> str:
	return json.dumps(value, ensure_ascii=False)[1:-1]


def _item_id(item_snbt: str) -> str:
	m = re.search(r'id\s*:\s*"([^"]+)"', item_snbt)
	return m.group(1) if m else "?"


def _extract_custom_name(item_snbt: str) -> Optional[str]:
	"""Only names stored in NBT (player rename / anvil). Registry names are not here."""
	m = re.search(r'"text"\s*:\s*"([^"]+)"', item_snbt)
	if m and m.group(1).strip():
		return _strip_mc_codes(m.group(1).strip())
	m = re.search(r'["\']?(?:Name|custom_name)["\']?\s*:\s*"([^"]+)"', item_snbt)
	if m and m.group(1).strip():
		return _strip_mc_codes(m.group(1).strip())
	m = re.search(r"['\"]?(?:Name|custom_name)['\"]?\s*:\s*'([^']+)'", item_snbt)
	if m and m.group(1).strip():
		return _strip_mc_codes(m.group(1).strip())
	return None


def _translate_key(item_id: str) -> str:
	"""Guess client language key from item id (best-effort)."""
	if ":" not in item_id:
		return f"item.minecraft.{item_id}"
	ns, path = item_id.split(":", 1)
	if ns == "minecraft":
		# Most block-items use block.minecraft.*; tools/items use item.minecraft.*
		# Prefer item.* — missing key falls back via "fallback"
		return f"item.minecraft.{path}"
	# Modded cables/blocks: block.<mod>.<path>
	return f"block.{ns}.{path}"


def _display_json(item_snbt: str) -> str:
	"""JSON text component: custom name if any, else client-side translate key."""
	custom = _extract_custom_name(item_snbt)
	if custom:
		return '{"text":"' + _json_str(custom) + '"}'
	item_id = _item_id(item_snbt)
	key = _translate_key(item_id)
	return (
		'{"translate":"' + _json_str(key) + '","fallback":"' + _json_str(item_id) + '"}'
	)


def _strip_mc_codes(text: str) -> str:
	return re.sub(r"§[0-9a-fk-orA-FK-OR]", "", text)


def _build_tellraw(player: str, item_snbt: str, version: Version) -> str:
	# Truncate pathological NBT (huge books etc.) so the command stays valid
	if len(item_snbt) > MAX_SNBT_LEN:
		item_snbt = item_snbt[:MAX_SNBT_LEN] + "..."
	snbt = _json_str(item_snbt)
	player_js = _json_str(sanitize_name(player) or player)

	if is_at_least(version, "1.21.5"):
		hover = {"action": "show_item", "contents": item_snbt}
	else:
		hover = {"action": "show_item", "value": item_snbt}

	if is_at_least(version, "1.16"):
		click = {"action": "copy_to_clipboard", "value": item_snbt}
		click_label = tr("click_copy")
	else:
		safe_player = sanitize_name(player)
		if is_at_least(version, "1.13"):
			suggest = f"/data get entity {safe_player} SelectedItem"
		else:
			suggest = f"/entitydata {safe_player} {{}}"
		click = {"action": "suggest_command", "value": suggest}
		click_label = tr("click_suggest")

	display = json.loads(_display_json(item_snbt))
	display["color"] = "aqua"
	display["hoverEvent"] = hover

	click_comp = {
		"text": f" [{click_label}]",
		"color": "aqua",
		"bold": True,
		"underlined": True,
		"hoverEvent": hover,
		"clickEvent": click,
	}

	payload = [
		{"text": "[Iridium] ", "color": "gray"},
		{"text": sanitize_name(player) or player, "color": "yellow"},
		{"text": f" {tr('share_showing')} "},
		display,
		click_comp,
	]
	return "tellraw @a " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _send_share(
	server: PluginServerInterface,
	src: CommandSource,
	player: str,
	item_snbt: str,
	version: Version,
) -> bool:
	if _is_air(item_snbt) or not looks_like_item_snbt(item_snbt):
		src.reply(RText(tr("hand_is_empty"), RColor.red))
		return False
	safe_execute(server, _build_tellraw(player, item_snbt, version))
	if config.share_sound:
		safe_execute(server, _sound_command(player, version))
	server.logger.info(
		f"[Iridium] !!share: {player} shared item id={_item_id(item_snbt)} "
		f"({len(item_snbt)} chars)"
	)
	src.reply(RText(tr("share_done"), RColor.green))
	return True


def _extract_item(payload: str, version: Version) -> Optional[str]:
	"""Normalize an entity-data payload into a single-item SNBT string, or None."""
	if not payload:
		return None
	body = strip_data_prefix(payload)
	if not looks_like_item_snbt(body):
		return None
	if is_at_least(version, "1.13"):
		return body.strip()
	return parse_selected_item(body)


def _purge_expired_pending() -> None:
	now = time.time()
	expired = [p for p, (_, _, exp) in _pending.items() if now >= exp]
	for p in expired:
		_pending.pop(p, None)


def do_share(server: PluginServerInterface, src: CommandSource) -> None:
	player = require_player(src)
	if player is None:
		return
	if not check_permission(src, config.permission):
		return
	version = require_version(server, src)
	if version is None:
		return
	if not _can_read_selected_item(version):
		src.reply(RText(tr("share_unsupported_version", str(version)), RColor.red))
		return

	query = _query_command(player, version)
	raw = rcon_query(server, query)
	if raw is not None:
		item = _extract_item(raw, version)
		if item is None:
			src.reply(RText(tr("hand_is_empty"), RColor.red))
			return
		_send_share(server, src, player, item, version)
		return

	with _pending_lock:
		_purge_expired_pending()
		_pending[player] = (src, version, time.time() + PENDING_TTL)
	safe_execute(server, query)

	# If the console never answers (empty hand / command error), tell the player
	def _timeout_notice() -> None:
		with _pending_lock:
			pending = _pending.get(player)
			if pending is None:
				return
			src2, _ver, expire = pending
			if time.time() < expire:
				return
			_pending.pop(player, None)
		src2.reply(RText(tr("share_timeout"), RColor.red))

	timer = threading.Timer(PENDING_TTL + 0.1, _timeout_notice)
	timer.daemon = True
	timer.start()


def handle_info(server: PluginServerInterface, info: Info) -> None:
	if info.is_player:
		return
	match = PLAYER_DATA_RE.match(info.content)
	if match is None:
		return
	name = match.group("name")
	with _pending_lock:
		pending = _pending.pop(name, None)
	if pending is None:
		return
	src, version, expire = pending
	if time.time() >= expire:
		src.reply(RText(tr("share_timeout"), RColor.red))
		return
	item = _extract_item(match.group(0), version)
	if item is None:
		src.reply(RText(tr("hand_is_empty"), RColor.red))
		return
	_send_share(server, src, name, item, version)


def register(server: PluginServerInterface) -> None:
	server.register_command(Literal("!!share").runs(lambda src: do_share(server, src)))
	server.register_help_message("!!share", tr("share_help"))
