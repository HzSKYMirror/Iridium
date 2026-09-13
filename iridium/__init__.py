"""Iridium — item share / hat / head / calculator for MCDReforged.

Copyright (c) 2026 云镜之端/SKYMirror. All Rights Reserved.
"""

from mcdreforged.api.all import *

import iridium.calculator as calculator
import iridium.hat as hat
import iridium.head as head
import iridium.join_tip as join_tip
import iridium.share as share
from iridium.config import apply_config, load_config
from iridium.version_util import tr


def on_load(server: PluginServerInterface, prev_module) -> None:
	loaded = load_config(server)
	apply_config(loaded)
	server.logger.info(tr("loaded"))

	share.register(server)
	hat.register(server)
	head.register(server)
	calculator.register(server)
	join_tip.register(server)

	server.register_event_listener(MCDRPluginEvents.GENERAL_INFO, share.handle_info)

	ver_hint = loaded.force_version or "auto"
	server.logger.info(tr("version_mode", ver_hint))


def on_unload(server: PluginServerInterface) -> None:
	server.logger.info(tr("unloaded"))
