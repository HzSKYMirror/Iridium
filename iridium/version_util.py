from typing import Optional

from mcdreforged.api.all import *

from iridium.config import config

# Fallback strings when ServerInterface is unavailable (unit tests / early import)
_FALLBACK = {
	"click_copy": "click to copy data",
	"click_suggest": "click for data command",
	"calc_usage": "Usage: !!c <expression>",
	"share_showing": "is showing",
}


def tr(key: str, *args) -> str:
	si = ServerInterface.get_instance()
	if si is None:
		text = _FALLBACK.get(key, key)
		if args:
			try:
				return text.format(*args)
			except Exception:
				return text
		return text
	return si.tr(f"iridium.{key}", *args)


def get_mc_version(server: PluginServerInterface) -> Optional[Version]:
	"""Return the detected Minecraft server version, or None."""
	if config.force_version:
		try:
			return Version(config.force_version)
		except Exception:
			server.logger.warning(tr("bad_force_version", config.force_version))
	info = server.get_server_information()
	if info is None or info.version is None:
		return None
	return info.version


def require_version(server: PluginServerInterface, src: CommandSource) -> Optional[Version]:
	version = get_mc_version(server)
	if version is None:
		src.reply(RText(tr("version_unknown"), RColor.red))
	return version


def is_at_least(version: Version, target: str) -> bool:
	return version >= Version(target)
