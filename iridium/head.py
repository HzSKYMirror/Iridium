from mcdreforged.api.all import *

from iridium.config import config
from iridium.utils import (
	check_cooldown,
	check_permission,
	mark_cooldown,
	require_player,
	safe_execute,
	sanitize_name,
)
from iridium.version_util import is_at_least, require_version, tr


def _give_head_command(player: str, target: str, version: Version) -> str:
	# Defense in depth: never interpolate an unsanitized name
	safe_player = sanitize_name(player) or "Steve"
	safe_target = sanitize_name(target) or safe_player
	if is_at_least(version, "1.20.5"):
		return f'give {safe_player} minecraft:player_head[minecraft:profile="{safe_target}"] 1'
	if is_at_least(version, "1.13"):
		return f'give {safe_player} minecraft:player_head{{SkullOwner:"{safe_target}"}} 1'
	return f'give {safe_player} minecraft:skull 1 3 {{SkullOwner:"{safe_target}"}}'


def do_head(server: PluginServerInterface, src: CommandSource, context: dict) -> None:
	player = require_player(src)
	if player is None:
		return
	if not check_permission(src, config.permission):
		return
	version = require_version(server, src)
	if version is None:
		return

	target = context.get("player_name") or player
	safe_target = sanitize_name(target) or sanitize_name(player) or player
	if not check_cooldown(src, player, "head", config.head_cooldown_seconds):
		return

	safe_execute(server, _give_head_command(player, safe_target, version))
	mark_cooldown(player, "head")
	src.reply(RText(tr("head_success", safe_target), RColor.green))


def register(server: PluginServerInterface) -> None:
	builder = SimpleCommandBuilder()
	builder.command("!!head", lambda src: do_head(server, src, {}))
	builder.command("!!head <player_name>", lambda src, ctx: do_head(server, src, ctx))
	builder.arg("player_name", Text)
	builder.register(server)
	server.register_help_message("!!head [player]", tr("head_help", config.head_cooldown_seconds))
