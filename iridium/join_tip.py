import re
import threading
from datetime import datetime
from typing import List, Optional, Tuple

from mcdreforged.api.all import *

from iridium.config import config
from iridium.utils import sanitize_name
from iridium.version_util import tr

LINK_WITH_TEXT_RE = re.compile(r"\{link:(?P<text>[^|}]+)\|(?P<url>[^}]+)\}")
LINK_URL_ONLY_RE = re.compile(r"\{link:(?P<url>[^}|]+)\}")

_COLOR_MAP = {
	"0": RColor.black,
	"1": RColor.dark_blue,
	"2": RColor.dark_green,
	"3": RColor.dark_aqua,
	"4": RColor.dark_red,
	"5": RColor.dark_purple,
	"6": RColor.gold,
	"7": RColor.gray,
	"8": RColor.dark_gray,
	"9": RColor.blue,
	"a": RColor.green,
	"b": RColor.aqua,
	"c": RColor.red,
	"d": RColor.light_purple,
	"e": RColor.yellow,
	"f": RColor.white,
}

_STYLE_MAP = {
	"k": RStyle.obfuscated,
	"l": RStyle.bold,
	"m": RStyle.strikethrough,
	"n": RStyle.underlined,
	"o": RStyle.italic,
}


def server_days() -> Optional[int]:
	raw = (config.motd_start_day or "").strip()
	if not raw:
		return None
	for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
		try:
			start = datetime.strptime(raw, fmt)
		except ValueError:
			continue
		return max(0, (datetime.now() - start).days) + 1
	return None


def online_hint(server: ServerInterface) -> str:
	try:
		info = server.get_server_information()
		if info is not None and getattr(info, "player_count", None) is not None:
			return str(info.player_count)
	except Exception:
		pass
	return "?"


def replace_placeholders(line: str, player: str, server: ServerInterface) -> str:
	days = server_days()
	days_text = str(days) if days is not None else "?"
	# Sanitize player name before it can re-enter the {link:...} parser or § codes
	safe_player = sanitize_name(player) or "Player"
	return (
		line.replace("{player}", safe_player)
		.replace("{days}", days_text)
		.replace("{day}", days_text)
		.replace("{online}", online_hint(server))
	)


def parse_colored_pieces(segment: str) -> List[RText]:
	"""Split a string with § color codes into RText pieces."""
	pieces: List[RText] = []
	color: Optional[RColor] = None
	styles: List[RStyle] = []
	buf = ""

	def flush() -> None:
		nonlocal buf
		if not buf:
			return
		pieces.append(RText(buf, color=color, styles=list(styles) if styles else None))
		buf = ""

	i = 0
	n = len(segment)
	while i < n:
		if segment[i] == "§" and i + 1 < n:
			code = segment[i + 1].lower()
			i += 2
			if code == "r":
				flush()
				color = None
				styles = []
				continue
			if code in _COLOR_MAP:
				flush()
				color = _COLOR_MAP[code]
				styles = []
				continue
			if code in _STYLE_MAP:
				flush()
				style = _STYLE_MAP[code]
				if style not in styles:
					styles.append(style)
				continue
			buf += f"§{code}"
			continue
		buf += segment[i]
		i += 1
	flush()
	return pieces or [RText(segment or "")]


def _apply_click(piece: RText, url: str) -> RText:
	return piece.c(RAction.open_url, url).h(RText(url, RColor.gray))


def render_motd_line(line: str, player: str, server: ServerInterface) -> List[RText]:
	raw = replace_placeholders(line, player, server)

	# Tokenize: plain text | (text, url)
	tokens: List[Tuple[str, str, Optional[str]]] = []
	last = 0

	def push_text(chunk: str) -> None:
		if chunk:
			tokens.append(("text", chunk, None))

	for match in LINK_WITH_TEXT_RE.finditer(raw):
		push_text(raw[last : match.start()])
		tokens.append(("link", match.group("text"), match.group("url").strip()))
		last = match.end()

	# Remaining part may still contain {link:url}
	rest = raw[last:]
	pos = 0
	for match in LINK_URL_ONLY_RE.finditer(rest):
		push_text(rest[pos : match.start()])
		url = match.group("url").strip()
		tokens.append(("link", url, url))
		pos = match.end()
	push_text(rest[pos:])
	if not tokens:
		tokens.append(("text", raw, None))

	out: List[RText] = []
	for kind, text, url in tokens:
		if kind == "text":
			out.extend(parse_colored_pieces(text))
			continue
		assert url is not None
		if not url.lower().startswith(("http://", "https://")):
			out.extend(parse_colored_pieces(text))
			continue
		colored = parse_colored_pieces(text)
		if not colored:
			colored = [RText(text, RColor.aqua)]
		for piece in colored:
			out.append(_apply_click(piece, url))
	return out


def build_motd(player: str, server: ServerInterface) -> Optional[RTextList]:
	if not config.motd_enabled:
		return None
	lines = list(config.motd_lines or [])
	if not lines:
		return None
	parts: List[RText] = [
		RText(tr("motd_header"), RColor.gold, styles=[RStyle.bold])
	]
	for line in lines:
		parts.append(RText("\n"))
		parts.extend(render_motd_line(line, player, server))
	# Only auto-append the day footer when no line already uses {days}/{day}
	days = server_days()
	if days is not None and not any(("{days}" in ln or "{day}" in ln) for ln in lines):
		parts.append(RText("\n"))
		parts.append(RText(tr("motd_days", days), RColor.gray))
	return RTextList(*parts)


def command_line(cmd: str, desc: str) -> List[RText]:
	return [
		RText(cmd, RColor.aqua, styles=[RStyle.underlined])
		.c(RAction.suggest_command, cmd)
		.h(RText(tr("join_tip_click"), RColor.gray)),
		RText(" - ", RColor.dark_gray),
		RText(desc, RColor.white),
	]


def build_command_tip() -> RTextList:
	parts: List[RText] = [
		RText("[Iridium] ", RColor.gray),
		RText(tr("join_tip_header"), RColor.gold),
	]
	for cmd, desc in (
		("!!share", tr("share_help")),
		("!!hat", tr("hat_help")),
		("!!head", tr("head_help_short")),
		("!!c 1+1", tr("calc_help")),
	):
		parts.append(RText("\n"))
		parts.extend(command_line(cmd, desc))
	return RTextList(*parts)


def send_join_message(server: ServerInterface, player: str) -> None:
	try:
		motd = build_motd(player, server)
		if motd is not None:
			server.tell(player, motd)
		if config.join_tip:
			server.tell(player, build_command_tip())
	except Exception as e:
		server.logger.debug(f"join message failed for {player}: {e}")


def on_player_joined(server: PluginServerInterface, player: str, info: Info) -> None:
	if not config.motd_enabled and not config.join_tip:
		return
	delay = max(0.0, float(config.join_tip_delay_seconds))
	if delay <= 0:
		send_join_message(server, player)
		return
	timer = threading.Timer(delay, lambda: send_join_message(server, player))
	timer.daemon = True
	timer.start()


def register(server: PluginServerInterface) -> None:
	# MCDR event name is PLAYER_JOINED (not PLAYER_JOIN)
	server.register_event_listener(MCDRPluginEvents.PLAYER_JOINED, on_player_joined)
