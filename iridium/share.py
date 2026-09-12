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


def _sound_command(version: Version) -> str:
	if is_at_least(version, "1.9"):
		return "playsound minecraft:entity.arrow.hit_player master @a"
	return "playsound random.successful_hit @a"


def _is_air(snbt: Optional[str]) -> bool:
	if snbt is None:
		return True
	stripped = snbt.strip()
	return stripped in ("{}", "", "[]") or bool(
		re.search(r'id\s*:\s*"(minecraft:)?air"', stripped)
	)


def _json_str(value: str) -> str:
	return json.dumps(value, ensure_ascii=False)[1:-1]


def _extract_display_name(item_snbt: str) -> str:
	"""Best-effort human-readable name from item SNBT."""
	# JSON text component: "text":"Name"
	m = re.search(r'"text"\s*:\s*"([^"]+)"', item_snbt)
	if m and m.group(1).strip():
		return _strip_mc_codes(m.group(1).strip())
	# display.Name / custom_name as plain string
	m = re.search(r'(?:Name|custom_name)\s*:\s*"([^"]+)"', item_snbt)
	if m and m.group(1).strip():
		return _strip_mc_codes(m.group(1).strip())
	m = re.search(r"(?:Name|custom_name)\s*:\s*'([^']+)'", item_snbt)
	if m and m.group(1).strip():
		return _strip_mc_codes(m.group(1).strip())
	# translation key fallback (e.g. block.ae2.fluix_covered_cable)
	m = re.search(r'"translate"\s*:\s*"([^"]+)"', item_snbt)
	if m and m.group(1).strip():
		key = m.group(1).strip()
		short = key.rsplit(".", 1)[-1]
		return short.replace("_", " ")
	id_match = re.search(r'id\s*:\s*"([^"]+)"', item_snbt)
	if id_match:
		return id_match.group(1)
	return "?"


def _strip_mc_codes(text: str) -> str:
	return re.sub(r"§[0-9a-fk-orA-FK-OR]", "", text)


def _build_tellraw(player: str, item_snbt: str, version: Version) -> str:
	# Truncate pathological NBT (huge books etc.) so the command stays valid
	if len(item_snbt) > MAX_SNBT_LEN:
		item_snbt = item_snbt[:MAX_SNBT_LEN] + "..."
	snbt = _json_str(item_snbt)
	player_js = _json_str(sanitize_name(player) or player)

	if is_at_least(version, "1.21.5"):
		hover = '{"action":"show_item","contents":"' + snbt + '"}'
	else:
		hover = '{"action":"show_item","value":"' + snbt + '"}'

	if is_at_least(version, "1.16"):
		click = '{"action":"copy_to_clipboard","value":"' + snbt + '"}'
		click_label = _json_str(tr("click_copy"))
	else:
		# pre-1.16 has no copy_to_clipboard; suggest the version-appropriate query cmd
		safe_player = sanitize_name(player)
		if is_at_least(version, "1.13"):
			suggest = f"/data get entity {safe_player} SelectedItem"
		else:
			suggest = f"/entitydata {safe_player} {{}}"
		click = '{"action":"suggest_command","value":"' + _json_str(suggest) + '"}'
		click_label = _json_str(tr("click_suggest"))

	display = _extract_display_name(item_snbt)
	display_js = _json_str(display)

	json_text = (
		'[{"text":"[Iridium] ","color":"gray"},'
		'{"text":"' + player_js + '","color":"yellow"},'
		'{"text":" ' + _json_str(tr("share_showing")) + ' "},'
		'{"text":"' + display_js + '","color":"aqua","hoverEvent":' + hover + "},"
		'{"text":" [' + click_label + ']","color":"aqua","bold":true,'
		'"underlined":true,"hoverEvent":' + hover + ',"clickEvent":' + click + "}]"
	)
	return f"tellraw @a {json_text}"


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
		safe_execute(server, _sound_command(version))
	server.logger.info(f"[Iridium] !!share: {player} shared an item ({len(item_snbt)} chars)")
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
