from typing import Optional

from mcdreforged.api.all import *

from iridium.config import config

# Fallback strings when ServerInterface is unavailable (unit tests / early import)
_FALLBACK = {
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


def _as_version(value) -> Optional[Version]:
	if value is None:
		return None
	if isinstance(value, Version):
		return value
	try:
		return Version(str(value))
	except Exception:
		return None


def get_mc_version(server: PluginServerInterface) -> Optional[Version]:
	"""Return the detected Minecraft server version, or None."""
	if config.force_version:
		forced = _as_version(config.force_version)
		if forced is not None:
			return forced
		server.logger.warning(tr("bad_force_version", config.force_version))
	info = server.get_server_information()
	if info is None:
		return None
	return _as_version(info.version)


def require_version(server: PluginServerInterface, src: CommandSource) -> Optional[Version]:
	version = get_mc_version(server)
	if version is None:
		src.reply(RText(tr("version_unknown"), RColor.red))
	return version


def is_at_least(version, target: str) -> bool:
	left = _as_version(version)
	right = _as_version(target)
	if left is None or right is None:
		return False
	return left >= right
